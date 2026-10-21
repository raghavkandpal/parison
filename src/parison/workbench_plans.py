"""Bounded schema controls and explicit edits over CLI-native recipe JSON."""

from __future__ import annotations

import json
from typing import Any

from .core import ParisonError
from .policies import load_schema


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _document(source: str) -> dict[str, Any]:
    try:
        document = json.loads(source, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise ParisonError("plan controls require finite JSON") from exc
    if not isinstance(document, dict) or type(document.get("recipe_version")) is not int:
        raise ParisonError("plan controls require an explicit recipe version")
    if document["recipe_version"] not in range(1, 7):
        raise ParisonError("plan controls support recipe versions 1 through 6")
    return document


def _matches(schema: dict, value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return all(name in value for name in schema.get("required", [])) and all(
        name not in value
        or (
            ("const" not in rule or value[name] == rule["const"])
            and ("enum" not in rule or value[name] in rule["enum"])
        )
        for name, rule in schema.get("properties", {}).items()
    )


def _schema(schema: dict, root: dict, value: Any) -> dict:
    if "$ref" in schema:
        schema = root["$defs"][schema["$ref"].removeprefix("#/$defs/")]
    schema = {**schema, "properties": dict(schema.get("properties", {}))}
    if "oneOf" in schema:
        choices = schema["oneOf"]
        selected = next(
            (choice for choice in choices if _matches({"properties": choice.get("properties", {})}, value)), choices[0]
        )
        schema.update(_schema(selected, root, value))
        for name in schema["properties"]:
            options = []
            for choice in choices:
                rule = choice.get("properties", {}).get(name, {})
                options.extend(rule.get("enum", [rule["const"]] if "const" in rule else []))
            if options:
                schema["properties"][name] = {"enum": list(dict.fromkeys(options))}
    required = set(schema.get("required", []))
    forbidden = set()
    for condition in schema.get("allOf", []):
        rule = condition
        if "if" in condition:
            rule = condition.get("then" if _matches(condition["if"], value) else "else", {})
        required.update(rule.get("required", []))
        schema["properties"].update(rule.get("properties", {}))
        forbidden.update(rule.get("not", {}).get("required", []))
    return {**schema, "required": sorted(required), "forbidden": forbidden}


def plan_controls(source: str) -> dict[str, Any]:
    """Describe every present or available policy field without choosing defaults."""
    document = _document(source)
    version = document["recipe_version"]
    root = load_schema("recipe" if version == 1 else f"recipe-v{version}")
    remaining = 4096

    def describe(schema: dict, value: Any, path: list, present=True, required=False):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or len(path) > 32:
            raise ParisonError("plan controls exceed their field or nesting limit; edit the JSON source")
        schema = _schema(schema, root, value)
        kind = schema.get("type")
        if isinstance(kind, list):
            kind = "json"
        if not kind:
            kind = "object" if isinstance(value, dict) else "array" if isinstance(value, list) else "string"
        node = {
            "path": path,
            "kind": kind,
            "present": present,
            "required": required,
            "description": schema.get("description", ""),
            "value": json.dumps(value, ensure_ascii=True, allow_nan=False) if present else "",
            "choices": [json.dumps(item) for item in schema.get("enum", [])],
            "fixed": "const" in schema,
            "initial": json.dumps(schema["const"])
            if "const" in schema
            else {"object": "{}", "array": "[]", "string": '""'}.get(kind, "null"),
        }
        if kind == "object" and present and isinstance(value, dict):
            properties = schema["properties"]
            names = list(dict.fromkeys([*properties, *value]))
            extra = schema.get("additionalProperties", False)
            node["additional"] = extra is not False
            extra_schema = _schema(extra, root, None) if isinstance(extra, dict) else {}
            node["additional_initial"] = {"object": "{}", "array": "[]", "string": '""'}.get(
                extra_schema.get("type"), "null"
            )
            node["children"] = [
                describe(
                    properties.get(name, extra if isinstance(extra, dict) else {}),
                    value.get(name),
                    [*path, name],
                    name in value,
                    name in schema["required"],
                )
                for name in names
                if name not in schema["forbidden"] or name in value
            ]
        elif kind == "array" and present and isinstance(value, list):
            node["children"] = [
                describe(schema.get("items", {}), item, [*path, index]) for index, item in enumerate(value)
            ]
            item = _schema(schema.get("items", {}), root, None)
            node["initial"] = json.dumps(item["const"]) if "const" in item else '""'
        return node

    try:
        return describe(root, document, [])
    except ParisonError:
        raise
    except (RecursionError, ValueError) as exc:
        raise ParisonError("plan controls require bounded finite JSON") from exc


def _edit_field(document: dict, path: object, operation: object, value: object) -> None:
    if (
        not isinstance(path, list)
        or not 1 <= len(path) <= 32
        or not isinstance(operation, str)
        or operation not in {"set", "remove"}
    ):
        raise ParisonError("invalid plan edit")
    if any(type(part) not in {str, int} for part in path):
        raise ParisonError("invalid plan edit path")
    try:
        parent = document
        for part in path[:-1]:
            parent = parent[part]
        key = path[-1]
        if isinstance(parent, dict):
            if not isinstance(key, str) or not key:
                raise ValueError("invalid property")
        elif isinstance(parent, list):
            if type(key) is not int or not 0 <= key <= len(parent):
                raise ValueError("invalid item")
        else:
            raise ValueError("invalid parent")
        if operation == "remove":
            del parent[key]
        else:
            if not isinstance(value, str):
                raise ValueError("value must be JSON text")
            replacement = json.loads(value, parse_constant=_reject_constant)
            if isinstance(parent, list) and key == len(parent):
                parent.append(replacement)
            else:
                parent[key] = replacement
    except (KeyError, IndexError, TypeError, ValueError, RecursionError) as exc:
        raise ParisonError("invalid plan field edit") from exc


def edit_plan(source: str, edits: object) -> dict[str, Any]:
    """Apply explicit field edits atomically in memory, without validation or persistence."""
    document = _document(source)
    if not isinstance(edits, list) or not 1 <= len(edits) <= 128:
        raise ParisonError("plan edits require 1 to 128 field operations")
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"path", "operation", "value"}:
            raise ParisonError("invalid plan field operation")
        _edit_field(document, **edit)
    try:
        edited = json.dumps(document, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    except (ValueError, RecursionError) as exc:
        raise ParisonError("plan edits require bounded finite JSON") from exc
    return {"source": edited, "controls": plan_controls(edited)}
