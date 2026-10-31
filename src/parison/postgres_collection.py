"""Optional bounded N-table reader outside offline verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from math import ceil
from pathlib import Path

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .postgres_ingress import (
    _acquire_table,
    _configure_transaction,
    _lock_tables,
    _metadata,
    _wall_cancellation,
    _write_json,
    _write_table_evidence,
)
from .representation import PROFILE as REPRESENTATION_PROFILE
from .representation import validate_representation
from .source_collection import (
    KIND,
    META_LIMIT,
    ONLY_PROFILE,
    _stat_stamp,
    collection_summary,
    validate_postgres_collection_plan,
    verify_postgres_collection,
)
from .source_receipt import _quote

# Promotion requires the exact live gates in docs/2.4/278 before integration.
LIVE_VERSIONS = frozenset({160015, 170011, 180006})
# Representation capture is qualified separately from the existing CSV profile.
REPRESENTATION_LIVE_VERSIONS = frozenset({160015, 170011, 180006})
_ERROR = "invalid or incomplete collection evidence"


def _load_plan(path: Path) -> dict:
    check_output_parent(path.parent)
    flags = os.O_RDONLY | (os.O_NOFOLLOW | os.O_NONBLOCK if os.name == "posix" else 0)
    if path.is_symlink():
        raise ParisonError(_ERROR)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > META_LIMIT:
            raise ParisonError(_ERROR)
        data = handle.read(META_LIMIT + 1)
        after = os.fstat(handle.fileno())
        if len(data) > META_LIMIT or _stat_stamp(before) != _stat_stamp(after):
            raise ParisonError(_ERROR)
    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )
    return validate_postgres_collection_plan(value)


def _remaining(started: float, limits: dict) -> float:
    remaining = limits["wall_timeout_ms"] / 1000 - (time.monotonic() - started)
    if remaining <= 0:
        raise ParisonError(_ERROR)
    return remaining


def _qualify_table(cursor, plan: dict) -> tuple[dict, str]:
    source, snapshot = _metadata(cursor, plan)
    if source["server_version_num"] not in LIVE_VERSIONS:
        raise ParisonError(_ERROR)
    cursor.execute(
        "SELECT rolcreaterole, rolcreatedb, rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user"
    )
    if cursor.fetchone() != (False, False, False):
        raise ParisonError(_ERROR)
    if source["server_version_num"] >= 170000:
        # MAINTAIN was introduced in PostgreSQL17; it is not SELECT-only.
        relation = f"{_quote(plan['schema'])}.{_quote(plan['table'])}"
        cursor.execute("SELECT has_table_privilege(%s, 'MAINTAIN')", (relation,))
        if cursor.fetchone() != (False,):
            raise ParisonError(_ERROR)
    cursor.execute(
        """
        SELECT c.relispartition,
               EXISTS(SELECT 1 FROM pg_catalog.pg_inherits i
                      WHERE i.inhrelid = c.oid OR i.inhparent = c.oid)
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s
    """,
        (plan["schema"], plan["table"]),
    )
    if cursor.fetchone() != (False, False):
        raise ParisonError(_ERROR)
    cursor.execute(
        """
        SELECT a.attname, t.typname, tn.nspname
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
        JOIN pg_catalog.pg_namespace tn ON tn.oid = t.typnamespace
        WHERE n.nspname = %s AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
    """,
        (plan["schema"], plan["table"]),
    )
    types = {name: (kind, namespace) for name, kind, namespace in cursor.fetchall()}
    if any(
        types.get(name) != (kind, "pg_catalog") for name, kind in zip(plan["columns"], source["types"], strict=True)
    ):
        raise ParisonError(_ERROR)
    # Force row-security planning on every member before any COPY. This also
    # observes each declared table under the already anchored shared snapshot.
    cursor.execute(f"SELECT COUNT(*) FROM ONLY {_quote(plan['schema'])}.{_quote(plan['table'])}")
    cursor.fetchone()
    return source, snapshot


def _capture_rows(cursor, query, parameters, names, maximum):
    cursor.execute(query, parameters)
    rows = cursor.fetchmany(maximum + 1)
    if len(rows) > maximum:
        raise ParisonError(_ERROR)
    return [dict(zip(names.split(), row, strict=True)) for row in rows]


def _provider_version(value, provider, collate, ctype):
    if value is not None:
        return {"state": "known", "value": value}
    state = (
        "not-versioned" if provider == "libc" and collate in {"C", "POSIX"} and ctype in {"C", "POSIX"} else "unknown"
    )
    return {"state": state, "value": None}


def _capture_collation(row, database):
    if row["collation_oid"] == 0:
        return {
            "state": "not-applicable",
            "origin": "none",
            **{
                key: None
                for key in (
                    "schema",
                    "name",
                    "provider",
                    "encoding",
                    "deterministic",
                    "collate",
                    "ctype",
                    "locale",
                    "rules",
                )
            },
            "recorded_version": {"state": "not-applicable", "value": None},
            "actual_version": {"state": "not-applicable", "value": None},
        }
    default = row["provider"] == "d"
    facts = database if default else row
    provider = {"c": "libc", "i": "icu", "b": "builtin"}.get(facts["provider"])
    if provider is None:
        raise ParisonError(_ERROR)
    collate, ctype = facts["collate"], facts["ctype"]
    return {
        "state": "resolved",
        "origin": "database-default" if default else "explicit",
        "schema": row["collation_schema"],
        "name": row["collation_name"],
        "provider": provider,
        "encoding": row["encoding"],
        "deterministic": row["deterministic"],
        "collate": collate,
        "ctype": ctype,
        "locale": facts["locale"],
        "rules": facts["rules"],
        "recorded_version": _provider_version(facts["recorded_version"], provider, collate, ctype),
        "actual_version": _provider_version(facts["actual_version"], provider, collate, ctype),
    }


def _capture_inventory(cursor, children, qualified):
    from .representation import _normal_facts

    major = next(iter(qualified.values()))[0]["server_version_num"] // 10000
    locale = "daticulocale" if major == 16 else "datlocale"
    database_rows = _capture_rows(
        cursor,
        f"SELECT datlocprovider, pg_catalog.left(datcollate,513), pg_catalog.left(datctype,513), pg_catalog.left({locale},513), pg_catalog.left(daticurules,4097), pg_catalog.left(datcollversion,513), pg_catalog.left(pg_catalog.pg_database_collation_actual_version(oid),513), pg_catalog.pg_encoding_to_char(encoding) FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()",
        (),
        "provider collate ctype locale rules recorded_version actual_version server_encoding",
        1,
    )
    if len(database_rows) != 1 or database_rows[0]["server_encoding"] != "UTF8":
        raise ParisonError(_ERROR)
    database = database_rows[0]
    locale = "co.colliculocale" if major == 16 else "co.colllocale"
    result = {}
    for table_id, plan in children.items():
        parameters = (plan["schema"], plan["table"])
        attributes = _capture_rows(
            cursor,
            f"""
            SELECT a.attname, a.attnum, tn.nspname, t.typname, t.oid,
                   a.atttypmod, pg_catalog.left(pg_catalog.format_type(a.atttypid,a.atttypmod),513),
                   a.attnotnull, a.attidentity, a.attgenerated, a.atthasdef,
                   a.attcollation, cn.nspname, co.collname, co.collprovider,
                   co.collencoding, co.collisdeterministic, pg_catalog.left(co.collcollate,513),
                   pg_catalog.left(co.collctype,513), pg_catalog.left({locale},513), pg_catalog.left(co.collicurules,4097), pg_catalog.left(co.collversion,513),
                   CASE WHEN co.oid IS NOT NULL THEN pg_catalog.left(pg_catalog.pg_collation_actual_version(co.oid),513) END
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON c.oid=a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_catalog.pg_type t ON t.oid=a.atttypid
            JOIN pg_catalog.pg_namespace tn ON tn.oid=t.typnamespace
            LEFT JOIN pg_catalog.pg_collation co ON co.oid=a.attcollation
            LEFT JOIN pg_catalog.pg_namespace cn ON cn.oid=co.collnamespace
            WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY a.attnum LIMIT 101
        """,
            parameters,
            "name ordinal type_schema type_name type_oid typmod display declared_not_null identity generated has_default collation_oid collation_schema collation_name provider encoding deterministic collate ctype locale rules recorded_version actual_version",
            100,
        )
        accessible = _capture_rows(
            cursor,
            """
            SELECT column_name, ordinal_position,
                   COALESCE(domain_schema, udt_schema), COALESCE(domain_name, udt_name),
                   numeric_precision, numeric_precision_radix, numeric_scale,
                   character_maximum_length, datetime_precision, is_nullable
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position LIMIT 101
        """,
            parameters,
            "name ordinal type_schema type_name precision radix raw_scale max_length datetime_precision information_schema_nullable",
            100,
        )
        if (
            not attributes
            or len(attributes) != len(accessible)
            or any(
                any(a[k] != b[k] for k in ("name", "ordinal", "type_schema", "type_name"))
                for a, b in zip(attributes, accessible, strict=True)
            )
        ):
            raise ParisonError(_ERROR)
        constraints = {a["ordinal"]: [] for a in attributes}
        if major == 18:
            rows = _capture_rows(
                cursor,
                """
                SELECT co.conname, co.convalidated, co.conenforced, co.conkey
                FROM pg_catalog.pg_constraint co
                JOIN pg_catalog.pg_class c ON c.oid=co.conrelid
                JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s AND co.contype='n'
                ORDER BY co.conname LIMIT 10001
            """,
                parameters,
                "name validated enforced columns",
                10000,
            )
            for row in rows:
                if (
                    not isinstance(row["columns"], list)
                    or len(row["columns"]) != 1
                    or row["columns"][0] not in constraints
                ):
                    raise ParisonError(_ERROR)
                target = constraints[row["columns"][0]]
                target.append({k: row[k] for k in ("name", "validated", "enforced")})
                if len(target) > 100:
                    raise ParisonError(_ERROR)
        columns = []
        for raw, info in zip(attributes, accessible, strict=True):
            type_fact = {
                "schema": raw["type_schema"],
                "name": raw["type_name"],
                "oid": raw["type_oid"],
                "typmod": raw["typmod"],
                "display": raw["display"],
            }
            supported, numeric, characters, datetime = _normal_facts(type_fact)
            type_fact["supported"] = supported
            if supported:
                if (
                    any(info[k] != numeric[k] for k in ("precision", "radix", "raw_scale"))
                    or info["max_length"] != characters["max_length"]
                    or info["datetime_precision"] != (0 if datetime["timezone"] == "date" else datetime["precision"])
                ):
                    raise ParisonError(_ERROR)
            native = constraints[raw["ordinal"]] if major == 18 else None
            if not supported:
                guarantee = "unknown"
            elif major < 18:
                guarantee = "non-null" if raw["declared_not_null"] else "nullable"
            elif raw["name"] in plan["primary_key"] or any(c["enforced"] and c["validated"] for c in native):
                guarantee = "non-null"
            else:
                guarantee = "unknown" if raw["declared_not_null"] or any(c["enforced"] for c in native) else "nullable"
            columns.append(
                {
                    "name": raw["name"],
                    "ordinal": raw["ordinal"],
                    "selected": raw["name"] in plan["columns"],
                    "type": type_fact,
                    "numeric": numeric,
                    "characters": characters,
                    "datetime": datetime,
                    "nullability": {
                        "declared_not_null": raw["declared_not_null"],
                        "information_schema_nullable": info["information_schema_nullable"],
                        "constraints": native,
                        "guarantee": guarantee,
                    },
                    "materialization": {
                        "identity": {"": "none", "a": "always", "d": "by-default"}[raw["identity"]],
                        "generated": {"": "none", "s": "stored", "v": "virtual"}[raw["generated"]],
                        "has_default": raw["has_default"],
                    },
                    "collation": _capture_collation(raw, database),
                }
            )
        result[table_id] = {
            "schema": plan["schema"],
            "table": plan["table"],
            "selected_columns": plan["columns"],
            "primary_key": plan["primary_key"],
            "columns": columns,
        }
    return result


def _representation_record(plan, source, snapshot, tables, manifests):
    from .representation import NOT_ASSESSED
    from .representation import PROFILE as REPRESENTATION_PROFILE

    return {
        "representation_version": 1,
        "kind": "postgresql-collection-representation",
        "capability_profile": REPRESENTATION_PROFILE,
        "normalization_profile": f"pg{source['server_version_num'] // 10000}-representation-v1",
        "collection_plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "source": {k: source[k] for k in ("source_id", "database", "role", "server_version_num")},
        "transaction": {"isolation": "repeatable read", "read_only": True, "row_security": "off", "snapshot": snapshot},
        "session": {"client_encoding": "UTF8", "date_style": "ISO, YMD", "time_zone": "UTC"},
        "table_manifests": manifests,
        "tables": tables,
        "not_assessed": NOT_ASSESSED,
    }


def parser() -> argparse.ArgumentParser:
    root = _SafeParser(
        prog="parison postgres collection", description="Acquire one bounded PostgreSQL snapshot collection"
    )
    root.add_argument("--plan", required=True)
    root.add_argument("--output", required=True)
    return root


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParisonError(_ERROR)


def export_postgres_collection(plan_path: str | Path, output: str | Path) -> dict:
    """Acquire every reviewed table or publish nothing."""
    stage = None
    try:
        plan = _load_plan(Path(plan_path))
        target = Path(output)
        check_output_parent(target.parent)
        if target.exists() or target.is_symlink():
            raise ParisonError(_ERROR)
        import psycopg

        limits = plan["limits"]
        started = time.monotonic()
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        tables = stage / "tables"
        tables.mkdir(mode=0o700)
        children = {
            table_id: {
                "plan_version": 2,
                "source_id": plan["source_id"],
                **selection,
                "limits": {k: v for k, v in limits.items() if k != "max_representation_bytes"},
            }
            for table_id, selection in sorted(plan["tables"].items())
        }
        for table_id in children:
            (tables / table_id).mkdir(mode=0o700)
        _remaining(started, limits)
        timeout = max(1, min(10, ceil(_remaining(started, limits))))
        acquired = {}
        with psycopg.connect("", autocommit=True, connect_timeout=timeout) as conn:
            try:
                with _wall_cancellation(conn, _remaining(started, limits)), conn.cursor() as cursor:
                    cursor.execute("SET client_encoding TO 'UTF8'")
                    cursor.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    _configure_transaction(cursor, limits)
                    cursor.execute("SET LOCAL search_path TO pg_catalog")
                    _remaining(started, limits)
                    _lock_tables(cursor, list(children.values()))
                    qualified = {}
                    for table_id, child_plan in children.items():
                        _remaining(started, limits)
                        qualified[table_id] = _qualify_table(cursor, child_plan)
                    first_source, first_snapshot = next(iter(qualified.values()))
                    for source, snapshot in qualified.values():
                        if snapshot != first_snapshot or any(
                            source[name] != first_source[name]
                            for name in ("source_id", "database", "role", "server_version_num")
                        ):
                            raise ParisonError(_ERROR)
                    captured = None
                    if plan["collection_plan_version"] == 2:
                        if first_source["server_version_num"] not in REPRESENTATION_LIVE_VERSIONS:
                            raise ParisonError(_ERROR)
                        captured = _capture_inventory(cursor, children, qualified)
                        temporary_manifests = {table_id: "0" * 64 for table_id in children}
                        record = _representation_record(
                            plan, first_source, first_snapshot, captured, temporary_manifests
                        )
                        validate_representation(
                            record,
                            record,
                            {table_id: ({"source": source}, "0" * 64) for table_id, (source, _) in qualified.items()},
                        )
                        if len(_canonical(record)) + 1 > limits["max_representation_bytes"]:
                            raise ParisonError(_ERROR)
                        _remaining(started, limits)
                    rows, size = 0, 0
                    for table_id, child_plan in children.items():
                        _remaining(started, limits)
                        item = _acquire_table(
                            cursor,
                            child_plan,
                            tables / table_id,
                            started,
                            limits["max_rows"] - rows,
                            limits["max_output_bytes"] - size,
                        )
                        if (item["source"], item["snapshot"]) != qualified[table_id]:
                            raise ParisonError(_ERROR)
                        acquired[table_id] = item
                        rows += item["local_rows"]
                        size += item["size"]
                        if rows > limits["max_rows"] or size > limits["max_output_bytes"]:
                            raise ParisonError(_ERROR)
                    _remaining(started, limits)
                    cursor.execute("COMMIT")
                    elapsed_ms = int((time.monotonic() - started) * 1000)
                    _remaining(started, limits)
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except psycopg.Error:
                    pass
                raise
        for table_id, child_plan in children.items():
            _remaining(started, limits)
            _write_table_evidence(tables / table_id, child_plan, acquired[table_id], elapsed_ms)
        receipt = {
            "postgres_collection_receipt_version": plan["collection_plan_version"],
            "kind": KIND,
            "collection_plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
            "capability_profile": REPRESENTATION_PROFILE if captured is not None else ONLY_PROFILE,
            "source": {name: first_source[name] for name in ("source_id", "database", "role", "server_version_num")},
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": first_snapshot,
            },
            "table_manifests": {
                table_id: hashlib.sha256((tables / table_id / "manifest.json").read_bytes()).hexdigest()
                for table_id in children
            },
            "limits": limits,
            "observed": {"rows": rows, "bytes": size, "elapsed_ms": elapsed_ms, "complete": True},
        }
        if captured is not None:
            representation_data = _write_json(
                stage / "representation.json",
                _representation_record(plan, first_source, first_snapshot, captured, receipt["table_manifests"]),
            )
            if len(representation_data) > limits["max_representation_bytes"]:
                raise ParisonError(_ERROR)
            receipt["representation_sha256"] = hashlib.sha256(representation_data).hexdigest()
            receipt["observed"]["representation_bytes"] = len(representation_data)
        receipt_data = _write_json(stage / "receipt.json", receipt)
        summary = collection_summary(receipt, receipt_data)
        summary_data = _write_json(stage / "summary.json", summary)
        _write_json(
            stage / "manifest.json",
            {
                "postgres_collection_manifest_version": plan["collection_plan_version"],
                "kind": KIND,
                "complete": True,
                "files": {
                    "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                    "summary.json": hashlib.sha256(summary_data).hexdigest(),
                    **({"representation.json": receipt["representation_sha256"]} if captured is not None else {}),
                },
                "table_manifests": receipt["table_manifests"],
            },
        )
        _remaining(started, limits)
        if verify_postgres_collection(stage) != summary:
            raise ParisonError(_ERROR)
        _remaining(started, limits)
        check_output_parent(target.parent)
        _remaining(started, limits)
        rename_no_replace(stage, target)
        stage = None
        return summary
    except KeyboardInterrupt:
        raise
    except Exception:
        raise ParisonError(_ERROR) from None
    finally:
        if stage is not None:
            try:
                shutil.rmtree(stage)
            except OSError:
                raise ParisonError(_ERROR) from None


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        print(_canonical(export_postgres_collection(args.plan, args.output)).decode("utf-8"))
        return 0
    except (ParisonError, OSError, ValueError, TypeError):
        print(f"parison postgres collection: {_ERROR}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("parison postgres collection: interrupted", file=sys.stderr)
        return 130
