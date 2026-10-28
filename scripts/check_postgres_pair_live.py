"""Controlled two-table snapshot gate; run explicitly with local PostgreSQL admin libpq settings."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql

from parison.core import ParisonError
from parison.postgres_pair import _acquire_table, export_postgres_pair
from parison.source_pair import verify_postgres_pair


def main() -> None:
    suffix = uuid.uuid4().hex[:12]
    schema, reader = f"parison_pair_{suffix}", f"parison_reader_{suffix}"
    original_user = os.environ.get("PGUSER")
    with psycopg.connect("", autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(reader)))
        try:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            for table in ("orders", "order_lines"):
                admin.execute(
                    sql.SQL("CREATE TABLE {}.{} (id integer PRIMARY KEY, note text)").format(
                        sql.Identifier(schema), sql.Identifier(table)
                    )
                )
                admin.execute(
                    sql.SQL("INSERT INTO {}.{} VALUES (1, %s)").format(sql.Identifier(schema), sql.Identifier(table)),
                    (table,),
                )
                admin.execute(
                    sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(table), sql.Identifier(reader)
                    )
                )
            admin.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(schema), sql.Identifier(reader))
            )
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                plan = {
                    "pair_plan_version": 1,
                    "source_id": "controlled-pair",
                    "tables": {
                        table: {"schema": schema, "table": table, "columns": ["id", "note"], "primary_key": ["id"]}
                        for table in ("orders", "order_lines")
                    },
                    "limits": {
                        "max_rows": 10,
                        "max_output_bytes": 10000,
                        "statement_timeout_ms": 5000,
                        "wall_timeout_ms": 10000,
                    },
                }
                plan_path = root / "plan.json"
                plan_path.write_text(json.dumps(plan))
                bundle = root / "pair"
                calls = 0

                def after_first(cursor, declared, stage, started, remaining_rows, remaining_bytes):
                    nonlocal calls
                    result = _acquire_table(cursor, declared, stage, started, remaining_rows, remaining_bytes)
                    calls += 1
                    if calls == 1:
                        admin.execute("SET lock_timeout TO '250ms'")
                        try:
                            admin.execute(
                                sql.SQL("ALTER TABLE {}.order_lines RENAME TO changed_lines").format(
                                    sql.Identifier(schema)
                                )
                            )
                        except psycopg.errors.LockNotAvailable:
                            pass
                        else:
                            raise AssertionError("second relation was not locked before first read")
                        for table in ("orders", "order_lines"):
                            admin.execute(
                                sql.SQL("INSERT INTO {}.{} VALUES (2, 'late')").format(
                                    sql.Identifier(schema), sql.Identifier(table)
                                )
                            )
                    return result

                os.environ["PGUSER"] = reader
                try:
                    with patch("parison.postgres_pair._acquire_table", after_first):
                        summary = export_postgres_pair(plan_path, bundle)
                    assert summary["rows"] == 2, summary
                    assert verify_postgres_pair(bundle) == summary
                    for table in ("orders", "order_lines"):
                        assert b"late" not in (bundle / "tables" / table / "data.csv").read_bytes()
                    try:
                        export_postgres_pair(plan_path, bundle)
                    except ParisonError:
                        pass
                    else:
                        raise AssertionError("pair no-overwrite gate failed")
                    limited = {**plan, "limits": {**plan["limits"], "max_output_bytes": 40}}
                    plan_path.write_text(json.dumps(limited))
                    try:
                        export_postgres_pair(plan_path, root / "limited")
                    except ParisonError:
                        assert not (root / "limited").exists()
                        assert not list(root.glob(".limited-*"))
                    else:
                        raise AssertionError("pair aggregate byte limit gate failed")
                    plan_path.write_text(json.dumps(plan))
                    admin.execute(
                        sql.SQL("ALTER TABLE {}.order_lines ENABLE ROW LEVEL SECURITY").format(sql.Identifier(schema))
                    )
                    admin.execute(
                        sql.SQL("CREATE POLICY only_first ON {}.order_lines FOR SELECT USING (id = 1)").format(
                            sql.Identifier(schema)
                        )
                    )
                    try:
                        export_postgres_pair(plan_path, root / "rls")
                    except ParisonError:
                        assert not (root / "rls").exists()
                    else:
                        raise AssertionError("pair RLS gate failed")
                finally:
                    if original_user is None:
                        os.environ.pop("PGUSER", None)
                    else:
                        os.environ["PGUSER"] = original_user
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
                assert verify_postgres_pair(bundle) == summary
                print(
                    "PostgreSQL pair live gate passed: common snapshot, pre-lock, second-table failure cleanup, RLS, offline"
                )
        finally:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(reader)))


if __name__ == "__main__":
    main()
