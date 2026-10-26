"""Suite execution, assembly, resume, and worker orchestration."""

from __future__ import annotations

import html
import json
import multiprocessing
import os
import shutil
import tempfile
import time
from multiprocessing.connection import wait
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent as _check_output_parent
from ._safe_fs import rename_no_replace as _rename_no_replace
from .core import (
    _MAX_SUITE_JOBS,
    DEFAULT_MAX_TEMP_BYTES,
    ParisonError,
    _digest,
    _runtime_info,
    _source_digest,
    compare,
    load_recipe,
    load_suite,
    select_suite_cases,
)
from .evidence import (
    _read_bundle_result,
    error_result,
    inspect_bundle,
    publish,
    terminal_result,
    verify_bundle,
)
from .inputs import InputCancellation


def compare_suites(left: str | Path, right: str | Path) -> dict[str, Any]:
    """Compare complete, recursively verified suite rehearsals under one policy and scope."""
    bundles = [Path(left), Path(right)]
    inspected = [inspect_bundle(path) for path in bundles]
    if any(item.get("kind") not in {"suite", "suite-shard"} for item in inspected):
        raise ParisonError("suite comparison requires suite bundles")
    results = [json.loads((path / "suite-result.json").read_text(encoding="utf-8")) for path in bundles]
    if any(not result.get("execution_complete", result.get("complete")) for result in results):
        raise ParisonError("suite comparison requires completed executions")
    policy_field = "suite_policy_sha256" if results[0]["suite_version"] == 2 else "suite_sha256"
    identities = [
        (
            item["kind"],
            item["suite_version"],
            item["total_cases"],
            result.get(policy_field),
            result.get("selection"),
            tuple((case["id"], case["policy_sha256"], case["contract"]) for case in item["cases"]),
        )
        for item, result in zip(inspected, results, strict=True)
    ]
    if identities[0] != identities[1]:
        raise ParisonError("suite comparison requires matching scope and policy")
    cases = []
    for before, after in zip(inspected[0]["cases"], inspected[1]["cases"], strict=True):
        child = [inspect_bundle(path / case["bundle"]) for path, case in zip(bundles, (before, after), strict=True)]
        fields = ("outcome", "complete", "counts", "discrepancy_count")
        prior, later = ({name: value.get(name) for name in fields} for value in child)
        inputs_changed = child[0].get("input_sha256") != child[1].get("input_sha256")
        cases.append(
            {
                "id": before["id"],
                "changed": prior != later or inputs_changed,
                "inputs_changed": inputs_changed,
                "before": prior,
                "after": later,
            }
        )
    transitions: dict[str, int] = {}
    for case in cases:
        transition = f"{case['before']['outcome']}->{case['after']['outcome']}"
        transitions[transition] = transitions.get(transition, 0) + 1
    return {
        "suite_version": inspected[0]["suite_version"],
        policy_field: results[0][policy_field],
        "selection": results[0].get("selection"),
        "changed": any(case["changed"] for case in cases) or inspected[0]["outcome"] != inspected[1]["outcome"],
        "outcome": {"before": inspected[0]["outcome"], "after": inspected[1]["outcome"]},
        "transitions": dict(sorted(transitions.items())),
        "cases": cases,
    }


def _suite_report(result: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(case[field]))}</td>" for field in ("id", "outcome", "complete", "contract", "bundle")
        )
        + "</tr>"
        for case in result["cases"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Parison suite report</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:.5rem;text-align:left}}</style></head>
<body><h1>Parison suite report</h1><p><strong>{html.escape(result["outcome"])}</strong> — {result["completed_cases"]} of {result["total_cases"]} cases published.</p>
<table><thead><tr><th>Case</th><th>Outcome</th><th>Complete</th><th>Contract</th><th>Bundle</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""


def assemble_suite(plan: str | Path, inputs: list[str | Path], output: str | Path) -> dict[str, Any]:
    """Assemble a complete suite from an exact set of verified v2 shards."""
    suite = load_suite(plan)
    if suite["suite_version"] != 2:
        raise ParisonError("suite assembly requires suite_version 2")
    if not inputs or len(inputs) > 100:
        raise ParisonError("suite assembly requires 1..100 shard inputs")
    shard_results, indexes, common = [], set(), None
    for source in map(Path, inputs):
        manifest = verify_bundle(source)
        if manifest.get("kind") != "suite-shard":
            raise ParisonError(f"assembly input is not a suite shard: {source}")
        result = json.loads((source / "suite-result.json").read_text(encoding="utf-8"))
        selection = result["selection"]
        identity = {
            "case_ids": selection["case_ids"],
            "tags": selection["tags"],
            "shard_count": selection["shard_count"],
        }
        if common is None:
            common = identity
        elif identity != common:
            raise ParisonError("suite shards use different selections or shard counts")
        index = selection["shard_index"]
        if index in indexes:
            raise ParisonError(f"duplicate suite shard index: {index}")
        indexes.add(index)
        if result["suite_policy_sha256"] != suite["suite_policy_sha256"]:
            raise ParisonError("suite shard plan fingerprint does not match current plan")
        if not result["execution_complete"]:
            raise ParisonError(f"suite shard is not execution-complete: {source}")
        shard_results.append((source, result))
    assert common is not None
    if indexes != set(range(common["shard_count"])):
        raise ParisonError("suite shard indexes do not provide exact coverage")
    selected = select_suite_cases(suite, common["case_ids"], common["tags"])
    by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
    for source, result in shard_results:
        for case in result["cases"]:
            if case["id"] in by_id:
                raise ParisonError(f"duplicate assembled suite case: {case['id']}")
            by_id[case["id"]] = (source, case)
    expected_ids = [case["id"] for case in selected]
    if set(by_id) != set(expected_ids):
        raise ParisonError("suite shards do not provide exact selected-case coverage")
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(output.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        (stage / "cases").mkdir()
        cases = []
        for identifier in expected_ids:
            source, case = by_id[identifier]
            child_source = source / case["bundle"]
            child_target = stage / "cases" / identifier
            _copy_verified_child(child_source, child_target)
            copied = dict(case)
            copied["manifest_sha256"] = _digest(child_target / "manifest.json")
            cases.append(copied)
        effective = {"suite_version": 2, "cases": [case["portable"] for case in suite["cases"]]}
        (stage / "effective-suite.json").write_text(
            json.dumps(effective, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
        outcome = max((case["outcome"] for case in cases), key=precedence.get)
        selection = {"case_ids": common["case_ids"], "tags": common["tags"], "shard_index": None, "shard_count": None}
        result = {
            "schema_version": 2,
            "suite_version": 2,
            "kind": "suite",
            "outcome": outcome,
            "complete": all(case["complete"] for case in cases),
            "scope_complete": not common["case_ids"] and not common["tags"],
            "execution_complete": True,
            "runtime": _runtime_info(contract="suite-v2"),
            "total_cases": len(suite["cases"]),
            "selected_cases": len(cases),
            "completed_cases": len(cases),
            "outcome_counts": {name: sum(case["outcome"] == name for case in cases) for name in precedence},
            "selection": selection,
            "cases": cases,
            "suite_policy_sha256": suite["suite_policy_sha256"],
            "effective_suite_sha256": _digest(stage / "effective-suite.json"),
        }
        (stage / "suite-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_suite_report(result), encoding="utf-8")
        manifest = {
            "schema_version": 2,
            "kind": "suite",
            "complete": True,
            "outcome": outcome,
            "runtime": result["runtime"],
            "files": {
                name: _digest(stage / name) for name in ("suite-result.json", "effective-suite.json", "report.html")
            },
            "cases": {case["id"]: case["manifest_sha256"] for case in cases},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _rename_no_replace(stage, output)
        return result
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot assemble suite: {exc}") from exc
    except Exception:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def _copy_verified_child(source: Path, target: Path) -> None:
    manifest = verify_bundle(source)
    target.mkdir()
    shutil.copy2(source / "manifest.json", target / "manifest.json")
    for name in manifest["files"]:
        shutil.copy2(source / name, target / name)
    verify_bundle(target)


def _checkpoint_data(
    case: dict[str, Any], child: Path, suite_sha256: str, limits: dict[str, int], sample_limit: int
) -> dict[str, Any]:
    result = _read_bundle_result(child)
    return {
        "case_id": case["id"],
        "suite_policy_sha256": suite_sha256,
        "policy_sha256": case["policy_sha256"],
        "limits": limits,
        "sample_limit": sample_limit,
        "parison_version": _runtime_info()["parison_version"],
        "inputs": {side: result.get("inputs", {}).get(side, {}).get("sha256") for side in ("baseline", "candidate")},
        "manifest_sha256": _digest(child / "manifest.json"),
    }


def _write_checkpoint(path: Path, data: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent, text=True)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except OSError:
            pass


def _reusable_workspace_child(
    case: dict[str, Any],
    child: Path,
    checkpoint_path: Path,
    suite_sha256: str,
    limits: dict[str, int],
    sample_limit: int,
) -> bool:
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        expected = _checkpoint_data(case, child, suite_sha256, limits, sample_limit)
        verify_bundle(child)
        child_result = _read_bundle_result(child)
    except (OSError, json.JSONDecodeError, ParisonError):
        return False
    if checkpoint != expected:
        return False
    try:
        current_inputs = {"baseline": _source_digest(case["baseline"]), "candidate": _source_digest(case["candidate"])}
    except ParisonError:
        return False
    if checkpoint["inputs"] != current_inputs:
        return False
    resource_limits = child_result.get("resource_limits", {})
    expected_resources = {
        "max_input_bytes": limits["max_input_bytes"],
        "max_decoded_bytes": limits["max_decoded_bytes"],
        "max_rows_per_input": limits["max_rows"],
    }
    mode = load_recipe(case["recipe"])["comparison_mode"]
    if mode == "aggregate":
        expected_resources["max_groups_per_input"] = limits["max_groups"]
    elif mode == "multiset":
        expected_resources["max_distinct_rows_per_input"] = limits["max_distinct_rows"]
    if case.get("execution"):
        expected_resources["max_temp_bytes"] = case["execution"].get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES)
    return resource_limits == expected_resources


def preview_suite_recovery(
    plan: str | Path,
    workspace: str | Path,
    *,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
    sample_limit: int = 100,
) -> dict[str, Any]:
    """Report current reuse eligibility using the runner's exact child rule."""
    suite = load_suite(plan)
    if suite["suite_version"] != 2:
        raise ParisonError("suite recovery requires suite_version 2")
    selected = select_suite_cases(suite, case_ids, tags, shard_index, shard_count)
    root = Path(workspace)
    if (
        root.is_symlink()
        or not root.is_dir()
        or any(path.is_symlink() or not path.is_dir() for path in (root / "cases", root / "checkpoints"))
    ):
        raise ParisonError("suite recovery workspace is incomplete or unsafe")
    cases = []
    for case in selected:
        limits = case["limits"]
        reusable = _reusable_workspace_child(
            case,
            root / "cases" / case["id"],
            root / "checkpoints" / f"{case['id']}.json",
            suite["suite_policy_sha256"],
            limits,
            sample_limit,
        )
        cases.append({"id": case["id"], "reusable": reusable})
    return {"suite_policy_sha256": suite["suite_policy_sha256"], "cases": cases}


def _execute_suite_case(
    case: dict[str, Any], destination: Path, sample_limit: int, limits: dict[str, int]
) -> dict[str, Any]:
    """Execute and publish one isolated suite case."""
    recipe = load_recipe(case["recipe"])
    try:
        result = compare(
            case["recipe"],
            case["baseline"],
            case["candidate"],
            sample_limit,
            limits["max_input_bytes"],
            limits["max_rows"],
            case.get("expected_policy_sha256"),
            limits["max_decoded_bytes"],
            limits["max_groups"],
            limits["max_distinct_rows"],
            case.get("execution", {}).get("engine", "memory"),
            case.get("execution", {}).get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
            destination.parent if case.get("execution") else None,
        )
    except ParisonError as exc:
        if str(exc) == "workbench run cancelled":
            raise
        execution = case.get("execution", {})
        result = error_result(
            str(exc),
            recipe,
            execution.get("engine", "memory"),
            execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
        )
    publish(destination, result, recipe)
    return result


def _suite_worker(worker, sender, case, destination, sample_limit, limits) -> None:
    """Run one case without exposing worker failures or values to the parent."""
    try:
        sender.send(("ok", worker(case, destination, sample_limit, limits)))
    except Exception:
        sender.send(("error", None))
    finally:
        sender.close()


def _stop_suite_workers(active: dict, timeout: float = 2.0) -> None:
    """Bound shutdown of the small private process pool."""
    processes = [record[0] for record in active.values()]
    for process in processes:
        if process.is_alive():
            process.terminate()
    deadline = time.monotonic() + timeout
    for process in processes:
        process.join(max(0.0, deadline - time.monotonic()))
    survivors = [process for process in processes if process.is_alive()]
    for process in survivors:
        process.kill()
    deadline = time.monotonic() + timeout
    for process in survivors:
        process.join(max(0.0, deadline - time.monotonic()))
    if any(process.is_alive() for process in survivors):
        raise ParisonError("suite workers could not be stopped safely")


def _clean_interrupted_workspace_case(case: dict[str, Any], destination: Path) -> None:
    """Remove incomplete output and atomic-publish scratch left by termination."""
    try:
        verify_bundle(destination)
    except ParisonError:
        shutil.rmtree(destination, ignore_errors=True)
    for scratch in destination.parent.glob(f".{case['id']}-*"):
        if scratch.is_dir() and not scratch.is_symlink():
            shutil.rmtree(scratch, ignore_errors=True)
        else:
            try:
                scratch.unlink()
            except OSError:
                pass
    for spill in destination.parent.glob("parison-spill-*"):
        if spill.is_dir() and not spill.is_symlink():
            shutil.rmtree(spill, ignore_errors=True)


def run_suite(
    plan: str | Path,
    output: str | Path,
    sample_limit: int = 100,
    max_input_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_groups: int = 100_000,
    max_distinct_rows: int = 100_000,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
    workspace: str | Path | None = None,
    resume: bool = False,
    jobs: int = 1,
    cancelled=None,
    progress=None,
    input_bindings: bool = False,
) -> dict[str, Any]:
    """Run a validated ordered suite and atomically publish its child bundles."""
    if input_bindings:
        from .manifesting import canonical_input_bindings_bytes, capture_suite_input_bindings

    suite = load_suite(plan)
    selected = select_suite_cases(suite, case_ids, tags, shard_index, shard_count)
    if input_bindings and suite["suite_version"] != 2:
        raise ParisonError("input bindings require suite_version 2")
    captured_inputs = capture_suite_input_bindings(suite, selected) if input_bindings else None
    if not 1 <= jobs <= _MAX_SUITE_JOBS:
        raise ParisonError(f"jobs must be between 1 and {_MAX_SUITE_JOBS}")
    if cancelled is not None and jobs != 1:
        raise ParisonError("cooperative suite cancellation requires one job")
    if (workspace is not None or resume) and suite["suite_version"] != 2:
        raise ParisonError("suite workspaces require suite_version 2")
    if resume and workspace is None:
        raise ParisonError("--resume requires --workspace")
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    workspace_path = Path(workspace) if workspace is not None else None
    if workspace_path is not None:
        if workspace_path.absolute() == output.absolute():
            raise ParisonError("workspace and output must be different directories")
        if resume:
            if workspace_path.is_symlink() or not workspace_path.is_dir():
                raise ParisonError("resume workspace is not a regular directory")
            if any(
                path.is_symlink() or not path.is_dir()
                for path in (workspace_path / "cases", workspace_path / "checkpoints")
            ):
                raise ParisonError("resume workspace is incomplete or unsafe")
        elif workspace_path.exists():
            raise ParisonError(f"workspace already exists: {workspace_path}")
        else:
            try:
                (workspace_path / "cases").mkdir(parents=True)
                (workspace_path / "checkpoints").mkdir()
                os.chmod(workspace_path, 0o700)
            except OSError as exc:
                raise ParisonError(f"cannot prepare suite workspace: {exc}") from exc
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(output.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        (stage / "cases").mkdir()
        cases_by_id: dict[str, dict[str, Any]] = {}
        pending = []
        for case in selected:
            limits = case.get(
                "limits",
                {
                    "max_input_bytes": max_input_bytes,
                    "max_decoded_bytes": max_decoded_bytes,
                    "max_rows": max_rows,
                    "max_groups": max_groups,
                    "max_distinct_rows": max_distinct_rows,
                },
            )
            child = stage / "cases" / case["id"]
            workspace_child = workspace_path / "cases" / case["id"] if workspace_path is not None else None
            checkpoint = workspace_path / "checkpoints" / f"{case['id']}.json" if workspace_path is not None else None
            reused = bool(
                resume
                and workspace_child is not None
                and checkpoint is not None
                and _reusable_workspace_child(
                    case, workspace_child, checkpoint, suite["suite_policy_sha256"], limits, sample_limit
                )
            )
            if reused:
                _copy_verified_child(workspace_child, child)
                result = _read_bundle_result(child)
            else:
                if workspace_child is not None:
                    shutil.rmtree(workspace_child, ignore_errors=True)
                pending.append((case, child, workspace_child, checkpoint, limits))
                continue
            cases_by_id[case["id"]] = {
                "id": case["id"],
                "outcome": result["outcome"],
                "complete": result["complete"],
                "schema_version": result["schema_version"],
                "contract": result["runtime"]["contract"],
                "policy_sha256": result.get("policy_sha256"),
                "manifest_sha256": _digest(child / "manifest.json"),
                "bundle": f"cases/{case['id']}",
            }

        def finish(case, child, workspace_child, checkpoint, limits, result):
            if workspace_child is not None and checkpoint is not None:
                _write_checkpoint(
                    checkpoint,
                    _checkpoint_data(case, workspace_child, suite["suite_policy_sha256"], limits, sample_limit),
                )
                _copy_verified_child(workspace_child, child)
            cases_by_id[case["id"]] = {
                "id": case["id"],
                "outcome": result["outcome"],
                "complete": result["complete"],
                "schema_version": result["schema_version"],
                "contract": result["runtime"]["contract"],
                "policy_sha256": result.get("policy_sha256"),
                "manifest_sha256": _digest(child / "manifest.json"),
                "bundle": f"cases/{case['id']}",
            }

        interrupted = False
        if jobs == 1:
            if progress is not None:
                progress(0, len(selected))
            for index, (case, child, workspace_child, checkpoint, limits) in enumerate(pending):
                if cancelled is not None and cancelled():
                    raise ParisonError("workbench suite cancelled")
                try:
                    with InputCancellation(cancelled):
                        result = _execute_suite_case(case, workspace_child or child, sample_limit, limits)
                except ParisonError as exc:
                    if str(exc) == "workbench run cancelled":
                        raise ParisonError("workbench suite cancelled") from exc
                    raise
                except KeyboardInterrupt:
                    recipe = load_recipe(case["recipe"])
                    execution = case.get("execution", {})
                    result = terminal_result(
                        "INTERRUPTED",
                        "comparison interrupted by user",
                        recipe,
                        execution.get("engine", "memory"),
                        execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
                    )
                    publish(workspace_child or child, result, recipe)
                    interrupted = True
                finish(case, child, workspace_child, checkpoint, limits, result)
                if progress is not None:
                    progress(index + 1, len(selected))
                if interrupted:
                    break
            if cancelled is not None and cancelled():
                raise ParisonError("workbench suite cancelled")
        else:
            context = multiprocessing.get_context("spawn")
            waiting = iter(pending)
            active = {}

            def launch() -> bool:
                try:
                    item = next(waiting)
                except StopIteration:
                    return False
                case, child, workspace_child, _checkpoint, limits = item
                receiver, sender = context.Pipe(duplex=False)
                process = context.Process(
                    target=_suite_worker,
                    args=(_execute_suite_case, sender, case, workspace_child or child, sample_limit, limits),
                )
                process.start()
                sender.close()
                active[receiver] = (process, item)
                return True

            def recover(item, message):
                case, child, workspace_child, checkpoint, limits = item
                destination = workspace_child or child
                result = message[1] if message and message[0] == "ok" else None
                if result is None:
                    try:
                        verify_bundle(destination)
                        result = _read_bundle_result(destination)
                    except ParisonError:
                        shutil.rmtree(destination, ignore_errors=True)
                        recipe = load_recipe(case["recipe"])
                        execution = case.get("execution", {})
                        result = error_result(
                            "suite worker failed unexpectedly",
                            recipe,
                            execution.get("engine", "memory"),
                            execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
                        )
                        publish(destination, result, recipe)
                finish(case, child, workspace_child, checkpoint, limits, result)

            try:
                for _ in range(min(jobs, len(pending))):
                    launch()
                while active:
                    ready = set(wait(active, timeout=0.05))
                    ready.update(receiver for receiver, (process, _item) in active.items() if not process.is_alive())
                    for receiver in ready:
                        process, item = active.pop(receiver)
                        try:
                            message = receiver.recv() if receiver.poll() else None
                        except (EOFError, OSError):
                            message = None
                        receiver.close()
                        process.join()
                        recover(item, message)
                        launch()
            except KeyboardInterrupt:
                _stop_suite_workers(active)
                for receiver in active:
                    receiver.close()
                for case, _child, workspace_child, checkpoint, limits in pending:
                    if workspace_child is None or checkpoint is None:
                        continue
                    _clean_interrupted_workspace_case(case, workspace_child)
                    try:
                        verify_bundle(workspace_child)
                    except ParisonError:
                        continue
                    _write_checkpoint(
                        checkpoint,
                        _checkpoint_data(case, workspace_child, suite["suite_policy_sha256"], limits, sample_limit),
                    )
                raise
            except BaseException:
                _stop_suite_workers(active)
                for receiver in active:
                    receiver.close()
                raise

        cases = [cases_by_id[case["id"]] for case in selected if case["id"] in cases_by_id]
        precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
        outcome = max((case["outcome"] for case in cases), key=precedence.get)
        outcome_counts = {name: sum(case["outcome"] == name for case in cases) for name in precedence}
        effective = (
            {"suite_version": 2, "cases": [case["portable"] for case in suite["cases"]]}
            if suite["suite_version"] == 2
            else json.loads(Path(plan).read_text(encoding="utf-8"))
        )
        (stage / "effective-suite.json").write_text(
            json.dumps(effective, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        result = {
            "schema_version": 1,
            "suite_version": 1,
            "outcome": outcome,
            "complete": len(cases) == len(suite["cases"]) and all(case["complete"] for case in cases),
            "runtime": _runtime_info(contract="suite-v1"),
            "total_cases": len(suite["cases"]),
            "completed_cases": len(cases),
            "outcome_counts": outcome_counts,
            "cases": cases,
            "suite_sha256": _digest(stage / "effective-suite.json"),
        }
        kind = "suite"
        if suite["suite_version"] == 2:
            selection = {
                "case_ids": case_ids or [],
                "tags": tags or [],
                "shard_index": shard_index,
                "shard_count": shard_count,
            }
            scope_complete = not selection["case_ids"] and not selection["tags"] and shard_count is None
            execution_complete = len(cases) == len(selected) and all(case["complete"] for case in cases)
            kind = "suite-shard" if shard_count is not None else "suite"
            result = {
                "schema_version": 2,
                "suite_version": 2,
                "kind": kind,
                "outcome": outcome,
                "complete": execution_complete,
                "scope_complete": scope_complete,
                "execution_complete": execution_complete,
                "runtime": _runtime_info(contract="suite-v2"),
                "total_cases": len(suite["cases"]),
                "selected_cases": len(selected),
                "completed_cases": len(cases),
                "outcome_counts": outcome_counts,
                "selection": selection,
                "cases": cases,
                "suite_policy_sha256": suite["suite_policy_sha256"],
                "effective_suite_sha256": _digest(stage / "effective-suite.json"),
            }
        (stage / "suite-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_suite_report(result), encoding="utf-8")
        if input_bindings:
            if capture_suite_input_bindings(suite, selected) != captured_inputs:
                raise ParisonError("suite inputs changed during execution")
            recorded = {(item["id"], item["role"]): item for item in captured_inputs["bindings"]}
            for case in cases:
                child_result = _read_bundle_result(stage / case["bundle"])
                if not child_result.get("complete"):
                    continue
                for role in ("baseline", "candidate"):
                    if (
                        child_result.get("inputs", {}).get(role, {}).get("sha256")
                        != recorded[(case["id"], role)]["source_sha256"]
                    ):
                        raise ParisonError("suite child input digest does not match captured binding")
            (stage / "input-bindings.json").write_bytes(canonical_input_bindings_bytes(captured_inputs))
        members = ("suite-result.json", "effective-suite.json", "report.html") + (
            ("input-bindings.json",) if input_bindings else ()
        )
        files = {name: _digest(stage / name) for name in members}
        manifest = {
            "schema_version": 3 if input_bindings else result["schema_version"],
            "kind": kind,
            "complete": True,
            "outcome": outcome,
            "runtime": result["runtime"],
            "files": files,
            "cases": {case["id"]: case["manifest_sha256"] for case in cases},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _rename_no_replace(stage, output)
        return result
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot publish suite: {exc}") from exc
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise
