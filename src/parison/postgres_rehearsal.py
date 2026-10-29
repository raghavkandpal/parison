"""Offline PostgreSQL migration rehearsal over reviewed local acquisition pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical
from .core import ParisonError
from .partition_discovery import _bounded_bytes, _digest, _read_json, _recipe, discover
from .partition_discovery import validate_plan as validate_partition_plan
from .reconciliation import (
    check_conservation,
    check_identity_references,
    normalize_reconciliation,
)
from .source_pair import SLOTS, verify_postgres_pair
from .source_receipt import NULL_MARKER, TYPES, _integer, _object, _sha, _text

SIDES = ("baseline", "candidate")
CAPS = {
    "max_input_bytes": 4 * 1024**3,
    "max_rows": 300_000,
    "max_keys": 300_000,
    "max_groups": 300_000,
    "max_temp_bytes": 5 * 1024**3,
}


def _identity(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_plan(value: Any) -> dict[str, Any]:
    _object(value, "rehearsal_plan_version pairs coordination policies partitions reconciliation_sha256 limits")
    if type(value["rehearsal_plan_version"]) is not int or value["rehearsal_plan_version"] != 1:
        raise ParisonError("unsupported rehearsal plan")
    _object(value["pairs"], "baseline candidate")
    for side in SIDES:
        pair = _object(value["pairs"][side], "manifest_sha256 pair_plan_sha256 snapshot expected_rows types")
        _sha(pair["manifest_sha256"])
        _sha(pair["pair_plan_sha256"])
        _text(pair["snapshot"])
        _object(pair["expected_rows"], "orders order_lines")
        _object(pair["types"], "orders order_lines")
        for slot in SLOTS:
            _integer(pair["expected_rows"][slot], 0, 300_000)
            types = pair["types"][slot]
            if not isinstance(types, list) or not types or any(not isinstance(t, str) or t not in TYPES for t in types):
                raise ParisonError("invalid reviewed source types")
    coordination = _object(value["coordination"], "mode claim_sha256")
    if coordination["mode"] == "source-owned":
        _sha(coordination["claim_sha256"])
    elif coordination["mode"] != "unestablished" or coordination["claim_sha256"] is not None:
        raise ParisonError("invalid coordination claim")
    for field in ("policies", "partitions"):
        _object(value[field], "orders order_lines")
    for slot in SLOTS:
        _sha(value["policies"][slot])
        validate_partition_plan(value["partitions"][slot])
    _sha(value["reconciliation_sha256"])
    _object(value["limits"], " ".join(CAPS))
    for name, cap in CAPS.items():
        _integer(value["limits"][name], 1, cap)
    return value


def _declaration(path: Path, plan: dict, recipes: dict) -> dict:
    value = _read_json(path)
    _object(value, "postgres_rehearsal_relationships_version datasets checks")
    if (
        type(value["postgres_rehearsal_relationships_version"]) is not int
        or value["postgres_rehearsal_relationships_version"] != 1
    ):
        raise ParisonError("unsupported rehearsal relationships")
    declaration = normalize_reconciliation(
        {
            "reconciliation_version": 1,
            "alignment_sha256": "0" * 64,
            "datasets": value["datasets"],
            "checks": value["checks"],
        }
    )
    normalized = {
        "postgres_rehearsal_relationships_version": 1,
        "datasets": declaration["datasets"],
        "checks": declaration["checks"],
    }
    if _identity(normalized) != plan["reconciliation_sha256"]:
        raise ParisonError("reconciliation identity mismatch")
    datasets = {item["id"]: item for item in declaration["datasets"]}
    if set(datasets) != set(SLOTS):
        raise ParisonError("rehearsal requires both datasets")
    for slot in SLOTS:
        if datasets[slot]["policy_sha256"] != plan["policies"][slot] or {
            item["name"]: item["type"] for item in datasets[slot]["columns"]
        } != {name: spec["type"] for name, spec in recipes[slot]["columns"].items()}:
            raise ParisonError("rehearsal dataset policy mismatch")
    checks = declaration["checks"]
    identities = {c["dataset"]: c for c in checks if c["kind"] == "identity"}
    references = [c for c in checks if c["kind"] == "reference"]
    sums = [c for c in checks if c["kind"] == "conservation"]
    if len(checks) != 4 or set(identities) != set(SLOTS) or len(references) != 1 or len(sums) != 1:
        raise ParisonError("rehearsal requires two identities, reference and conservation")
    if any(c["nulls"] != "forbid" for c in checks) or any(
        identities[slot]["columns"] != recipes[slot]["keys"] for slot in SLOTS
    ):
        raise ParisonError("rehearsal requires non-null primary key identities")
    reference, total = references[0], sums[0]
    if (
        reference["child_dataset"] != "order_lines"
        or reference["parent_identity"] != identities["orders"]["id"]
        or total["parent_dataset"] != "orders"
        or total["child_dataset"] != "order_lines"
        or total["parent_identity"] != identities["orders"]["id"]
        or total["child_group_columns"] != reference["child_columns"]
        or total["comparison"] != "exact"
    ):
        raise ParisonError("rehearsal requires per-order reference and exact conservation")
    return declaration


def _bindings(plan: dict, pairs: dict, recipe_paths: dict, reconciliation: Path, claim: Path | None):
    for path in (*recipe_paths.values(), reconciliation, *((claim,) if claim is not None else ())):
        check_output_parent(path.parent)
        _bounded_bytes(path, 256 * 1024)
    for root in pairs.values():
        check_output_parent(root)
    recipes = {}
    identities = {}
    for slot in SLOTS:
        recipes[slot], policy = _recipe(recipe_paths[slot])
        if policy != plan["policies"][slot]:
            raise ParisonError("rehearsal policy mismatch")
        recipe = recipes[slot]
        if any(recipe["delimiters"][side] != "," or recipe["null_tokens"][side] != [NULL_MARKER] for side in SIDES):
            raise ParisonError("rehearsal requires adapter CSV and null semantics")
        identities[str(recipe_paths[slot])] = _digest(recipe_paths[slot])
    _declaration(reconciliation, plan, recipes)
    identities[str(reconciliation)] = _digest(reconciliation)
    if plan["coordination"]["mode"] == "source-owned":
        if (
            claim is None
            or hashlib.sha256(_bounded_bytes(claim, 256 * 1024)).hexdigest() != plan["coordination"]["claim_sha256"]
        ):
            raise ParisonError("rehearsal coordination claim mismatch")
        identities[str(claim)] = _digest(claim)
    elif claim is not None:
        raise ParisonError("unexpected coordination claim")
    coverage = "PASS"
    total_bytes = 0
    for side, major in (("baseline", 16), ("candidate", 18)):
        root = pairs[side]
        verify_postgres_pair(root)
        declared = plan["pairs"][side]
        if _digest(root / "manifest.json") != declared["manifest_sha256"]:
            raise ParisonError("rehearsal pair identity mismatch")
        receipt = _read_json(root / "receipt.json")
        if (
            receipt["source"]["server_version_num"] // 10000 != major
            or receipt["pair_plan_sha256"] != declared["pair_plan_sha256"]
            or receipt["transaction"]["snapshot"] != declared["snapshot"]
        ):
            raise ParisonError("rehearsal source selection or snapshot mismatch")
        for slot in SLOTS:
            child = _read_json(root / "tables" / slot / "receipt.json")
            source, observed = child["source"], child["observed"]
            if (
                source["types"] != declared["types"][slot]
                or source["columns"] != list(recipes[slot]["columns"])
                or source["primary_key"] != recipes[slot]["keys"]
            ):
                raise ParisonError("rehearsal source columns, keys or types mismatch")
            if observed["local_rows"] != declared["expected_rows"][slot]:
                coverage = "INCONCLUSIVE"
            if observed["local_rows"] > plan["limits"]["max_rows"]:
                raise ParisonError("rehearsal row limit exceeded")
            total_bytes += observed["output_bytes"]
    if total_bytes > plan["limits"]["max_input_bytes"]:
        raise ParisonError("rehearsal input byte limit exceeded")
    return coverage, identities


def _outcome(values) -> str:
    return "FAIL" if "FAIL" in values else "INCONCLUSIVE" if "INCONCLUSIVE" in values else "PASS"


def _summary(receipt: dict) -> dict:
    return {
        "postgres_rehearsal_summary_version": 1,
        **{name: receipt[name] for name in ("outcome", "complete", "coverage", "coordination")},
        "parity": {slot: receipt["parity"][slot]["outcome"] for slot in SLOTS},
        "relationships": receipt["relationships"]["outcome"],
        "conservation": receipt["conservation"]["outcome"],
        "receipt_sha256": hashlib.sha256(_canonical(receipt) + b"\n").hexdigest(),
    }


def _evaluate(plan: dict, pairs: dict, recipes: dict, reconciliation: Path, claim: Path | None, stage: Path) -> dict:
    coverage, identities = _bindings(plan, pairs, recipes, reconciliation, claim)
    discovery = stage / "discovery"
    discovery.mkdir(mode=0o700)
    inputs = {
        slot: {"recipe": recipes[slot], **{side: pairs[side] / "tables" / slot / "data.csv" for side in SIDES}}
        for slot in SLOTS
    }
    parity = {}
    with tempfile.TemporaryDirectory(prefix=".rehearsal-work-", dir=stage) as temporary:
        workspace = Path(temporary)
        for slot in SLOTS:
            partition_plan = workspace / f"{slot}.json"
            partition_plan.write_bytes(_canonical(plan["partitions"][slot]))
            parity[slot] = discover(
                partition_plan, recipes[slot], inputs[slot]["baseline"], inputs[slot]["candidate"], discovery / slot
            )
        # The released evaluators consume an internal declaration; no alignment is
        # evaluated or published as a rehearsal claim.
        declaration_path = workspace / "relationships.json"
        loaded_recipes = {slot: _recipe(recipes[slot])[0] for slot in SLOTS}
        declaration_path.write_bytes(_canonical(_declaration(reconciliation, plan, loaded_recipes)))
        limits = plan["limits"]
        common = {
            "engine": "sqlite",
            "max_input_bytes": limits["max_input_bytes"],
            "max_decoded_bytes": limits["max_input_bytes"],
            "max_rows": limits["max_rows"],
            "max_temp_bytes": limits["max_temp_bytes"],
            "temp_directory": workspace,
        }
        relationships = check_identity_references(declaration_path, inputs, max_keys=limits["max_keys"], **common)
        conservation = check_conservation(declaration_path, inputs, max_groups=limits["max_groups"], **common)
    after_coverage, after = _bindings(plan, pairs, recipes, reconciliation, claim)
    if after != identities or after_coverage != coverage:
        raise ParisonError("rehearsal inputs changed")
    outcomes = [coverage, relationships["outcome"], conservation["outcome"], *(p["outcome"] for p in parity.values())]
    if plan["coordination"]["mode"] == "unestablished":
        outcomes.append("INCONCLUSIVE")
    return {
        "postgres_rehearsal_receipt_version": 1,
        "plan_sha256": _identity(plan),
        "pairs": {side: plan["pairs"][side]["manifest_sha256"] for side in SIDES},
        "parity": parity,
        "relationships": relationships,
        "conservation": conservation,
        "coverage": coverage,
        "coordination": plan["coordination"]["mode"],
        "outcome": _outcome(outcomes),
        "complete": True,
    }


def _write(stage: Path, plan: dict, receipt: dict) -> dict:
    summary = _summary(receipt)
    values = {"plan.json": plan, "receipt.json": receipt, "summary.json": summary}
    for name, value in values.items():
        (stage / name).write_bytes(_canonical(value) + b"\n")
    files = {name: _digest(stage / name) for name in values}
    files.update({slot: _digest(stage / "discovery" / slot / "manifest.json") for slot in SLOTS})
    (stage / "manifest.json").write_bytes(
        _canonical({"postgres_rehearsal_manifest_version": 1, "files": files}) + b"\n"
    )
    return summary


def run(plan_path, baseline, candidate, orders_recipe, lines_recipe, reconciliation, output, claim=None) -> dict:
    plan_path, target = Path(plan_path), Path(output)
    check_output_parent(plan_path.parent)
    plan_bytes = _bounded_bytes(plan_path, 256 * 1024)
    plan = validate_plan(_read_json(plan_path))
    check_output_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise ParisonError("rehearsal output exists")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    os.chmod(stage, 0o700)
    try:
        receipt = _evaluate(
            plan,
            {"baseline": Path(baseline), "candidate": Path(candidate)},
            {"orders": Path(orders_recipe), "order_lines": Path(lines_recipe)},
            Path(reconciliation),
            Path(claim) if claim is not None else None,
            stage,
        )
        if _bounded_bytes(plan_path, 256 * 1024) != plan_bytes:
            raise ParisonError("rehearsal plan changed")
        summary = _write(stage, plan, receipt)
        rename_no_replace(stage, target)
        return summary
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _tree_bytes(root: Path) -> dict[str, bytes]:
    check_output_parent(root)
    expected = {"plan.json", "receipt.json", "summary.json", "manifest.json", "discovery"}
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != expected:
        raise ParisonError("invalid rehearsal evidence members")
    discovery = root / "discovery"
    if discovery.is_symlink() or not discovery.is_dir() or {p.name for p in discovery.iterdir()} != set(SLOTS):
        raise ParisonError("invalid rehearsal discovery members")
    files = {name: _bounded_bytes(root / name, 4 * 1024**2) for name in expected - {"discovery"}}
    for slot in SLOTS:
        child = discovery / slot
        names = {"plan.json", "receipt.json", "summary.json", "manifest.json"}
        if child.is_symlink() or not child.is_dir() or {p.name for p in child.iterdir()} != names:
            raise ParisonError("invalid rehearsal partition members")
        files.update({f"discovery/{slot}/{name}": _bounded_bytes(child / name, 4 * 1024**2) for name in names})
    return files


def verify(directory, baseline, candidate, orders_recipe, lines_recipe, reconciliation, claim=None) -> dict:
    root = Path(directory)
    before = _tree_bytes(root)
    with tempfile.TemporaryDirectory(prefix="parison-rehearsal-verify-") as temporary:
        output = Path(temporary) / "replayed"
        summary = run(
            root / "plan.json", baseline, candidate, orders_recipe, lines_recipe, reconciliation, output, claim
        )
        if _tree_bytes(output) != before or _tree_bytes(root) != before:
            raise ParisonError("rehearsal evidence does not reproduce")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parison-rehearsal")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "verify"):
        child = sub.add_parser(command)
        if command == "run":
            child.add_argument("--plan", required=True)
            child.add_argument("--output", required=True)
        else:
            child.add_argument("directory")
        for name in ("baseline", "candidate", "orders-recipe", "lines-recipe", "reconciliation"):
            child.add_argument(f"--{name}", required=True)
        child.add_argument("--claim")
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "run":
            args["plan_path"] = args.pop("plan")
        summary = (run if command == "run" else verify)(**args)
        print(json.dumps(summary, sort_keys=True))
        return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 3}[summary["outcome"]]
    except (ParisonError, OSError, ValueError, TypeError, KeyError, OverflowError):
        print("parison-rehearsal: invalid or incomplete rehearsal evidence", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
