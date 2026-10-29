"""Private portable dossier that replays one local PostgreSQL rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .partition_discovery import _bounded_bytes, _digest
from .partition_investigation import verify_investigation
from .postgres_rehearsal import verify as verify_rehearsal
from .source_pair import SLOTS

_SHA = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_BASE_MEMBERS = {"rehearsal", "baseline", "candidate", "orders-recipe.json", "lines-recipe.json", "relationships.json"}
_TOP = {"plan.json", "receipt.json", "summary.json", "manifest.json", "members"}
_MAX_FILES = 128
_MAX_BYTES = 4 * 1024**3
_MAX_FILE_BYTES = 1024**3


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _exact(value: Any, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ParisonError(f"invalid {label}")
    return value


def _json(path: Path, limit: int = 4 * 1024**2) -> dict:
    data = _bounded_bytes(path, limit)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ParisonError("invalid dossier JSON") from exc
    if not isinstance(value, dict) or _canonical(value) + b"\n" != data:
        raise ParisonError("noncanonical dossier JSON")
    return value


def validate_plan(value: Any) -> dict:
    _exact(
        value,
        {"dossier_plan_version", "rehearsal_manifest_sha256", "investigations", "exceptions", "signoffs"},
        "dossier plan",
    )
    if (
        type(value["dossier_plan_version"]) is not int
        or value["dossier_plan_version"] != 1
        or not _sha(value["rehearsal_manifest_sha256"])
    ):
        raise ParisonError("unsupported dossier plan")
    investigations = _exact(value["investigations"], set(SLOTS), "investigations")
    if any(item is not None and not _sha(item) for item in investigations.values()):
        raise ParisonError("invalid investigation identity")
    for name, maximum, fields, id_field in (
        ("exceptions", 32, {"id", "reference_sha256", "disposition"}, "id"),
        ("signoffs", 16, {"role", "reference_sha256"}, "role"),
    ):
        records = value[name]
        if not isinstance(records, list) or len(records) > maximum:
            raise ParisonError("invalid dossier references")
        seen = set()
        for item in records:
            _exact(item, fields, "dossier reference")
            identifier = item[id_field]
            if (
                not isinstance(identifier, str)
                or not _ID.fullmatch(identifier)
                or identifier in seen
                or not _sha(item["reference_sha256"])
            ):
                raise ParisonError("invalid dossier reference")
            seen.add(identifier)
            if name == "exceptions" and item["disposition"] not in {"open", "accepted", "rejected"}:
                raise ParisonError("invalid exception disposition")
    return value


def _tree(root: Path) -> dict[str, str]:
    check_output_parent(root)
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("unsafe dossier directory")
    files: dict[str, str] = {}
    size = entries = 0

    def visit(directory: Path, depth: int, parent_fd: int | None = None) -> None:
        nonlocal size, entries
        if depth > 8:
            raise ParisonError("dossier nesting exceeds limit")
        if os.name == "posix":
            descriptor = os.open(
                directory if parent_fd is None else directory.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
            names = os.scandir(descriptor)
        else:
            descriptor = None
            names = os.scandir(directory)
        try:
            for entry in names:
                name = entry.name
                entries += 1
                if entries > 256:
                    raise ParisonError("dossier exceeds entry limit")
                path = directory / name
                if os.name == "posix":
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
                    mode = os.fstat(fd).st_mode
                else:
                    if path.is_symlink():
                        raise ParisonError("dossier contains symlink")
                    mode = path.stat(follow_symlinks=False).st_mode
                    fd = None
                try:
                    if stat.S_ISDIR(mode):
                        visit(path, depth + 1, descriptor)
                        continue
                    if not stat.S_ISREG(mode):
                        raise ParisonError("dossier has unsafe member")
                    length = os.fstat(fd).st_size if fd is not None else path.stat().st_size
                    size += length
                    if len(files) >= _MAX_FILES or length > _MAX_FILE_BYTES or size > _MAX_BYTES:
                        raise ParisonError("dossier exceeds member or byte limit")
                    if fd is not None:
                        digest = hashlib.sha256()
                        with os.fdopen(os.dup(fd), "rb") as handle:
                            for block in iter(lambda: handle.read(1024 * 1024), b""):
                                digest.update(block)
                        if os.fstat(fd).st_size != length:
                            raise ParisonError("dossier member changed during read")
                        files[path.relative_to(root).as_posix()] = digest.hexdigest()
                    else:
                        files[path.relative_to(root).as_posix()] = _digest(path)
                finally:
                    if fd is not None:
                        os.close(fd)
        finally:
            names.close()
            if descriptor is not None:
                os.close(descriptor)

    visit(root, 0)
    return files


def _members(root: Path, plan: dict) -> tuple[Path, dict[str, str]]:
    members = root / "members"
    expected = set(_BASE_MEMBERS)
    rehearsal = members / "rehearsal"
    rehearsal_plan = _json(rehearsal / "plan.json")
    if rehearsal_plan["coordination"]["mode"] == "source-owned":
        expected.add("claim.txt")
    selected = {slot for slot in SLOTS if plan["investigations"][slot] is not None}
    if selected:
        expected.add("investigations")
    if members.is_symlink() or not members.is_dir() or {p.name for p in members.iterdir()} != expected:
        raise ParisonError("invalid dossier members")
    for directory, names in (
        (rehearsal, {"plan.json", "receipt.json", "summary.json", "manifest.json", "discovery"}),
        (members / "baseline", {"receipt.json", "summary.json", "manifest.json", "tables"}),
        (members / "candidate", {"receipt.json", "summary.json", "manifest.json", "tables"}),
    ):
        if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()} != names:
            raise ParisonError("invalid dossier nested artifact")
    if selected:
        investigations = members / "investigations"
        if investigations.is_symlink() or {p.name for p in investigations.iterdir()} != selected:
            raise ParisonError("invalid dossier investigations")
    return members, {slot: _digest(members / "investigations" / slot / "manifest.json") for slot in selected}


def _replay(root: Path, plan: dict) -> dict:
    members, investigation_digests = _members(root, plan)
    rehearsal = members / "rehearsal"
    if _digest(rehearsal / "manifest.json") != plan["rehearsal_manifest_sha256"]:
        raise ParisonError("dossier rehearsal identity mismatch")
    kwargs = {
        "baseline": members / "baseline",
        "candidate": members / "candidate",
        "orders_recipe": members / "orders-recipe.json",
        "lines_recipe": members / "lines-recipe.json",
        "reconciliation": members / "relationships.json",
        "claim": members / "claim.txt" if (members / "claim.txt").exists() else None,
    }
    rehearsal_summary = verify_rehearsal(rehearsal, **kwargs)
    for slot in SLOTS:
        selected = plan["investigations"][slot]
        if selected is None:
            if slot in investigation_digests:
                raise ParisonError("unexpected dossier investigation")
            continue
        if investigation_digests.get(slot) != selected:
            raise ParisonError("dossier investigation identity mismatch")
        investigation = members / "investigations" / slot
        verified = verify_investigation(
            investigation,
            rehearsal / "discovery" / slot,
            members / ("orders-recipe.json" if slot == "orders" else "lines-recipe.json"),
            members / "baseline" / "tables" / slot / "data.csv",
            members / "candidate" / "tables" / slot / "data.csv",
        )
        if verified["verification"] != "exact-source-backed":
            raise ParisonError("dossier investigation is not source-backed")
    return {
        "dossier_receipt_version": 1,
        "rehearsal_manifest_sha256": plan["rehearsal_manifest_sha256"],
        "pair_manifests": {side: _digest(members / side / "manifest.json") for side in ("baseline", "candidate")},
        "investigation_manifests": plan["investigations"],
        "outcome": rehearsal_summary["outcome"],
        "coverage": rehearsal_summary["coverage"],
        "coordination": rehearsal_summary["coordination"],
        "complete": True,
        "exception_count": len(plan["exceptions"]),
        "open_exception_count": sum(item["disposition"] == "open" for item in plan["exceptions"]),
        "signoff_count": len(plan["signoffs"]),
        "verification": "source-backed-local",
    }


def _summary(receipt: dict) -> dict:
    return {
        "dossier_summary_version": 1,
        "kind": "decision-dossier",
        "outcome": receipt["outcome"],
        "coverage": receipt["coverage"],
        "coordination": receipt["coordination"],
        "complete": True,
        "exception_count": receipt["exception_count"],
        "open_exception_count": receipt["open_exception_count"],
        "signoff_count": receipt["signoff_count"],
        "authorization": "external-required",
        "receipt_sha256": hashlib.sha256(_canonical(receipt) + b"\n").hexdigest(),
    }


def _write(root: Path, name: str, value: dict) -> None:
    (root / name).write_bytes(_canonical(value) + b"\n")


def _verify(directory: str | Path) -> dict:
    root = Path(directory)
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != _TOP:
        raise ParisonError("invalid dossier root")
    all_files = _tree(root)
    plan = validate_plan(_json(root / "plan.json"))
    receipt = _json(root / "receipt.json")
    summary = _json(root / "summary.json")
    manifest = _exact(_json(root / "manifest.json"), {"dossier_manifest_version", "files"}, "dossier manifest")
    if type(manifest["dossier_manifest_version"]) is not int or manifest["dossier_manifest_version"] != 1:
        raise ParisonError("unsupported dossier manifest")
    files = manifest["files"]
    if not isinstance(files, dict) or files != {k: v for k, v in all_files.items() if k != "manifest.json"}:
        raise ParisonError("dossier manifest does not match all members")
    expected_receipt = _replay(root, plan)
    _exact(receipt, set(expected_receipt), "dossier receipt")
    if receipt != expected_receipt or summary != _summary(expected_receipt):
        raise ParisonError("dossier derived evidence does not reproduce")
    if _tree(root) != all_files:
        raise ParisonError("dossier changed during verification")
    return summary


def verify(directory: str | Path) -> dict:
    try:
        return _verify(directory)
    except ParisonError:
        raise
    except (OSError, KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ParisonError("invalid dossier evidence") from exc


def create(
    plan_path,
    rehearsal,
    baseline,
    candidate,
    orders_recipe,
    lines_recipe,
    relationships,
    output,
    claim=None,
    orders_investigation=None,
    lines_investigation=None,
) -> dict:
    plan_path, target = Path(plan_path), Path(output)
    check_output_parent(plan_path.parent)
    plan_bytes = _bounded_bytes(plan_path, 4 * 1024**2)
    plan = validate_plan(_json(plan_path))
    choices = {"orders": orders_investigation, "order_lines": lines_investigation}
    if any((choices[slot] is None) != (plan["investigations"][slot] is None) for slot in SLOTS):
        raise ParisonError("dossier investigation selection mismatch")
    check_output_parent(target.parent)
    source_directories = [
        Path(item)
        for item in (rehearsal, baseline, candidate, orders_investigation, lines_investigation)
        if item is not None
    ]
    absolute_target = target.absolute()
    if any(
        absolute_target == source.absolute() or absolute_target.is_relative_to(source.absolute())
        for source in source_directories
    ):
        raise ParisonError("dossier output must be outside all input directories")
    if target.exists() or target.is_symlink():
        raise ParisonError("dossier output exists")
    original_dirs = {"rehearsal": Path(rehearsal), "baseline": Path(baseline), "candidate": Path(candidate)}
    original_trees = {name: _tree(source) for name, source in original_dirs.items()}
    if _digest(Path(rehearsal) / "manifest.json") != plan["rehearsal_manifest_sha256"]:
        raise ParisonError("dossier rehearsal identity mismatch")
    original_kwargs = {
        "baseline": baseline,
        "candidate": candidate,
        "orders_recipe": orders_recipe,
        "lines_recipe": lines_recipe,
        "reconciliation": relationships,
        "claim": claim,
    }
    verify_rehearsal(rehearsal, **original_kwargs)
    for slot, selected in plan["investigations"].items():
        if selected is not None:
            source = Path(choices[slot])
            original_trees[f"investigation-{slot}"] = _tree(source)
            if _digest(source / "manifest.json") != selected:
                raise ParisonError("dossier investigation identity mismatch")
            verified = verify_investigation(
                source,
                Path(rehearsal) / "discovery" / slot,
                orders_recipe if slot == "orders" else lines_recipe,
                Path(baseline) / "tables" / slot / "data.csv",
                Path(candidate) / "tables" / slot / "data.csv",
            )
            if verified["verification"] != "exact-source-backed":
                raise ParisonError("dossier investigation is not source-backed")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    os.chmod(stage, 0o700)
    try:
        members = stage / "members"
        members.mkdir(mode=0o700)
        directories = original_dirs
        for name, source in directories.items():
            _tree(source)
            shutil.copytree(source, members / name, symlinks=True)
        files = {
            "orders-recipe.json": orders_recipe,
            "lines-recipe.json": lines_recipe,
            "relationships.json": relationships,
            **({"claim.txt": claim} if claim is not None else {}),
        }
        for name, source in files.items():
            check_output_parent(Path(source).parent)
            (members / name).write_bytes(
                _bounded_bytes(Path(source), 256 * 1024 if name == "claim.txt" else 4 * 1024**2)
            )
        selected = {slot: choices[slot] for slot in SLOTS if choices[slot] is not None}
        if selected:
            folder = members / "investigations"
            folder.mkdir(mode=0o700)
            for slot, path in selected.items():
                _tree(Path(path))
                shutil.copytree(path, folder / slot, symlinks=True)
        _write(stage, "plan.json", plan)
        receipt = _replay(stage, plan)
        _write(stage, "receipt.json", receipt)
        summary = _summary(receipt)
        _write(stage, "summary.json", summary)
        if _bounded_bytes(plan_path, 4 * 1024**2) != plan_bytes:
            raise ParisonError("dossier plan changed")
        if any(_tree(source) != original_trees[name] for name, source in original_dirs.items()) or any(
            _tree(Path(choices[slot])) != original_trees[f"investigation-{slot}"]
            for slot in SLOTS
            if choices[slot] is not None
        ):
            raise ParisonError("dossier source changed during publication")
        all_files = _tree(stage)
        _write(stage, "manifest.json", {"dossier_manifest_version": 1, "files": all_files})
        verify(stage)
        rename_no_replace(stage, target)
        return summary
    finally:
        if stage.exists():
            shutil.rmtree(stage)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParisonError("invalid dossier arguments")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(prog="parison-dossier")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_SafeParser)
    create_parser = sub.add_parser("create")
    for name in (
        "plan",
        "rehearsal",
        "baseline",
        "candidate",
        "orders-recipe",
        "lines-recipe",
        "relationships",
        "output",
    ):
        create_parser.add_argument("--" + name, required=True)
    for name in ("claim", "orders-investigation", "lines-investigation"):
        create_parser.add_argument("--" + name)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("directory")
    try:
        args = vars(parser.parse_args(argv))
        command = args.pop("command")
        if command == "create":
            args["plan_path"] = args.pop("plan")
        result = (create if command == "create" else verify)(**args)
        print(json.dumps(result, sort_keys=True))
        return {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 3}[result["outcome"]]
    except (ParisonError, OSError, ValueError, TypeError, KeyError, OverflowError):
        print("parison-dossier: invalid or incomplete dossier evidence", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
