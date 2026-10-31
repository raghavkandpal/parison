"""Offline native representation facts; no database, expressions or policy inference."""

from __future__ import annotations

from .core import ParisonError
from .source_receipt import TYPES, _identifier, _integer, _names, _object, _sha

PROFILE = "postgresql-base-table-only-representation-v1"
MAX_REPRESENTATION_BYTES = 16 * 1024 * 1024
NOT_ASSESSED = [
    "check-constraints",
    "default-expression-semantics",
    "generated-expression-semantics",
    "triggers",
    "indexes-except-primary-key",
    "extension-behavior",
]
_ERROR = "invalid or incomplete representation evidence"


def _enum(value, choices):
    if type(value) is not str or value not in choices:
        raise ParisonError(_ERROR)
    return value


def _boolean(value):
    if type(value) is not bool:
        raise ParisonError(_ERROR)
    return value


def _text(value, maximum=512):
    if not isinstance(value, str) or "\x00" in value or len(value.encode("utf-8")) > maximum:
        raise ParisonError(_ERROR)
    return value


def _version(value, allowed):
    _object(value, "state value")
    _enum(value["state"], allowed)
    if value["state"] == "known":
        if not _text(value["value"]):
            raise ParisonError(_ERROR)
    elif value["value"] is not None:
        raise ParisonError(_ERROR)


def _collation(value, kind, supported, major):
    _object(
        value,
        "state origin schema name provider encoding deterministic collate ctype locale rules recorded_version actual_version",
    )
    state = _enum(value["state"], {"resolved", "not-applicable", "unknown"})
    scalars = ("schema", "name", "provider", "encoding", "deterministic", "collate", "ctype", "locale", "rules")
    if supported and (kind in {"text", "varchar"}) != (state != "not-applicable"):
        raise ParisonError(_ERROR)
    if state != "resolved":
        origin = "none" if state == "not-applicable" else "unknown"
        if value["origin"] != origin or any(value[k] is not None for k in scalars):
            raise ParisonError(_ERROR)
        for key in ("recorded_version", "actual_version"):
            _version(value[key], {state})
        return
    _enum(value["origin"], {"explicit", "database-default"})
    for key in ("schema", "name"):
        _identifier(value[key])
    _enum(value["provider"], {"libc", "icu", "builtin"})
    if value["provider"] == "builtin" and major < 17:
        raise ParisonError(_ERROR)
    _integer(value["encoding"], -1, 2147483647)
    _boolean(value["deterministic"])
    for key in ("collate", "ctype", "locale", "rules"):
        if value[key] is not None:
            _text(value[key], 4096 if key == "rules" else 512)
    for key in ("recorded_version", "actual_version"):
        _version(value[key], {"known", "unknown", "not-versioned"})
        if value[key]["state"] == "not-versioned" and not (
            value["provider"] == "libc" and value["collate"] in {"C", "POSIX"} and value["ctype"] in {"C", "POSIX"}
        ):
            raise ParisonError(_ERROR)


def _normal_facts(type_fact):
    kind, typmod = type_fact["name"], type_fact["typmod"]
    supported = type_fact["schema"] == "pg_catalog" and kind in TYPES
    state = "not-applicable" if supported else "unsupported"
    numeric = {"state": state, "precision": None, "radix": None, "scale": None, "raw_scale": None}
    characters = {"state": state, "max_length": None}
    datetime = {"state": state, "precision": None, "timezone": None}
    if not supported:
        return supported, numeric, characters, datetime
    if kind in {"int2", "int4", "int8"}:
        numeric.update(
            state="known", precision={"int2": 16, "int4": 32, "int8": 64}[kind], radix=2, scale=0, raw_scale=0
        )
    elif kind == "numeric":
        if typmod == -1:
            numeric.update(state="unbounded", radix=10)
        else:
            precision = ((typmod - 4) >> 16) & 65535
            scale = (((typmod - 4) & 2047) ^ 1024) - 1024
            _integer(precision, 1, 1000)
            _integer(scale, -1000, 1000)
            if typmod != 4 + (precision << 16) + (scale & 2047):
                raise ParisonError(_ERROR)
            numeric.update(state="known", precision=precision, radix=10, scale=scale, raw_scale=scale & 2047)
    elif kind == "varchar":
        if typmod == -1:
            characters["state"] = "unbounded"
        else:
            characters.update(state="known", max_length=_integer(typmod - 4, 1, 2147483647))
    elif kind == "text":
        characters["state"] = "unbounded"
    elif kind in {"timestamp", "timestamptz"}:
        datetime.update(
            state="known",
            precision=6 if typmod == -1 else _integer(typmod, 0, 6),
            timezone="naive" if kind == "timestamp" else "aware",
        )
    elif kind == "date":
        datetime.update(state="known", timezone="date")
    if kind not in {"numeric", "varchar", "timestamp", "timestamptz"} and typmod != -1:
        raise ParisonError(_ERROR)
    return supported, numeric, characters, datetime


def _nullability(value, major, supported, key):
    _object(value, "declared_not_null information_schema_nullable constraints guarantee")
    declared = _boolean(value["declared_not_null"])
    _enum(value["information_schema_nullable"], {"YES", "NO"})
    constraints = value["constraints"]
    if major < 18:
        if constraints is not None:
            raise ParisonError(_ERROR)
        guarantee = "non-null" if declared else "nullable"
    else:
        if not isinstance(constraints, list) or len(constraints) > 100:
            raise ParisonError(_ERROR)
        names = []
        for item in constraints:
            _object(item, "name validated enforced")
            names.append(_identifier(item["name"]))
            _boolean(item["validated"])
            _boolean(item["enforced"])
        if names != sorted(set(names)):
            raise ParisonError(_ERROR)
        enforced = any(c["enforced"] for c in constraints)
        validated = any(c["enforced"] and c["validated"] for c in constraints)
        if supported and not declared and (key or enforced):
            raise ParisonError(_ERROR)
        guarantee = "non-null" if key or validated else ("unknown" if declared or enforced else "nullable")
    if supported and ((key and not declared) or value["information_schema_nullable"] != ("NO" if declared else "YES")):
        raise ParisonError(_ERROR)
    if value["guarantee"] != (guarantee if supported else "unknown"):
        raise ParisonError(_ERROR)


def validate_representation(metadata, receipt, children):
    """Reconstruct normalized facts and reconcile every verified child binding."""
    _object(
        metadata,
        "representation_version kind capability_profile normalization_profile collection_plan_sha256 source transaction session table_manifests tables not_assessed",
    )
    _integer(metadata["representation_version"], 1, 1)
    if (
        metadata["kind"] != "postgresql-collection-representation"
        or metadata["capability_profile"] != PROFILE
        or metadata["not_assessed"] != NOT_ASSESSED
    ):
        raise ParisonError(_ERROR)
    _object(metadata["source"], "source_id database role server_version_num")
    _integer(metadata["source"]["server_version_num"], 160000, 189999)
    _object(metadata["transaction"], "isolation read_only row_security snapshot")
    _boolean(metadata["transaction"]["read_only"])
    major = receipt["source"]["server_version_num"] // 10000
    if major not in {16, 17, 18} or metadata["normalization_profile"] != f"pg{major}-representation-v1":
        raise ParisonError(_ERROR)
    for key in ("source", "transaction", "table_manifests", "collection_plan_sha256"):
        if metadata[key] != receipt[key]:
            raise ParisonError(_ERROR)
    _sha(metadata["collection_plan_sha256"])
    if metadata["session"] != {"client_encoding": "UTF8", "date_style": "ISO, YMD", "time_zone": "UTC"}:
        raise ParisonError(_ERROR)
    for key in ("source_id", "database", "role"):
        _text(metadata["source"][key])
    _text(metadata["transaction"]["snapshot"])
    tables = metadata["tables"]
    if not isinstance(tables, dict) or set(tables) != set(children):
        raise ParisonError(_ERROR)
    for table_id, (child, _) in children.items():
        table = _object(tables[table_id], "schema table selected_columns primary_key columns")
        for key in ("schema", "table"):
            if _identifier(table[key]) != child["source"][key]:
                raise ParisonError(_ERROR)
        if (
            _names(table["selected_columns"]) != child["source"]["columns"]
            or _names(table["primary_key"]) != child["source"]["primary_key"]
        ):
            raise ParisonError(_ERROR)
        columns = table["columns"]
        if not isinstance(columns, list) or not 1 <= len(columns) <= 100:
            raise ParisonError(_ERROR)
        names, ordinals = [], []
        for column in columns:
            _object(
                column, "name ordinal selected type numeric characters datetime nullability materialization collation"
            )
            name = _identifier(column["name"])
            names.append(name)
            ordinals.append(_integer(column["ordinal"], 1, 32767))
            if _boolean(column["selected"]) != (name in table["selected_columns"]):
                raise ParisonError(_ERROR)
            type_fact = _object(column["type"], "schema name oid typmod display supported")
            for key in ("schema", "name"):
                _identifier(type_fact[key])
            _integer(type_fact["oid"], 1, 4294967295)
            _integer(type_fact["typmod"], -2147483648, 2147483647)
            _text(type_fact["display"])
            supported, numeric, characters, datetime = _normal_facts(type_fact)
            if _boolean(type_fact["supported"]) != supported or (column["selected"] and not supported):
                raise ParisonError(_ERROR)
            for key, expected in (("numeric", numeric), ("characters", characters), ("datetime", datetime)):
                value = _object(column[key], " ".join(expected))
                # Python considers bool/int/float equal; compare exact scalar types too.
                if value != expected or any(type(value[k]) is not type(v) for k, v in expected.items()):
                    raise ParisonError(_ERROR)
            _nullability(column["nullability"], major, supported, name in table["primary_key"])
            materialization = _object(column["materialization"], "identity generated has_default")
            _enum(materialization["identity"], {"none", "always", "by-default"})
            _enum(materialization["generated"], {"none", "stored", "virtual"} if major == 18 else {"none", "stored"})
            _boolean(materialization["has_default"])
            _collation(column["collation"], type_fact["name"], supported, major)
        if (
            len(set(names)) != len(names)
            or ordinals != sorted(set(ordinals))
            or not set(table["selected_columns"]) <= set(names)
        ):
            raise ParisonError(_ERROR)
        by_name = {c["name"]: c for c in columns}
        if [by_name[n]["type"]["name"] for n in table["selected_columns"]] != child["source"]["types"]:
            raise ParisonError(_ERROR)
    return metadata
