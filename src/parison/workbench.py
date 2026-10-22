"""Deterministic, summary-safe local workbench publication."""

from __future__ import annotations

import html
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import analyze_bundle
from .catalog import add as catalog_add
from .catalog import diff as catalog_diff
from .catalog import list_runs
from .comparison import compare
from .core import ParisonError
from .evidence import inspect_bundle, publish
from .inputs import InputCancellation, validate_inputs
from .policies import explain_recipe_text, load_recipe
from .suites import compare_suites, run_suite
from .workbench_plans import plan_controls

_COMMON_FIELDS = (
    "kind",
    "schema_version",
    "suite_version",
    "outcome",
    "complete",
    "scope_complete",
    "execution_complete",
    "sensitivity",
    "runtime",
    "counts",
    "outcome_counts",
    "total_cases",
    "completed_cases",
    "discrepancy_count",
    "discrepancy_sample_size",
    "discrepancy_sample_limit",
    "resource_limits",
    "input_sha256",
    "policy_sha256",
    "bundle_sha256",
    "manifest_files",
)


def workbench_projection(bundle: str | Path) -> dict[str, Any]:
    """Verify a bundle and return the closed summary-safe workbench view."""
    inspected = inspect_bundle(bundle)
    return {name: inspected[name] for name in _COMMON_FIELDS if name in inspected}


def plan_projection(recipe: str | Path) -> dict[str, Any]:
    """Validate a recipe and return its exact source plus policy identity."""
    path = Path(recipe)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParisonError(f"cannot read recipe: {exc}") from exc
    return {"source": source, **plan_text_projection(source)}


def plan_text_projection(source: str) -> dict[str, Any]:
    """Validate edited recipe text without persisting it."""
    policy = explain_recipe_text(source)
    return {
        "policy_sha256": policy["policy_sha256"],
        "comparison_mode": policy["comparison_mode"],
        "recipe_version": policy["recipe_version"],
        **_plan_control_projection(source),
        "effective_policy": json.dumps(policy, indent=2, ensure_ascii=True),
    }


def _plan_control_projection(source: str) -> dict[str, Any]:
    try:
        return {"controls": plan_controls(source), "controls_notice": ""}
    except ParisonError as exc:
        return {"controls": None, "controls_notice": str(exc)}


def _catalog_path(workspace: str | Path) -> Path:
    directory = Path(workspace).resolve() / ".parison"
    if directory.is_symlink():
        raise ParisonError("workbench catalog directory must not be a symlink")
    return directory / "catalog.sqlite3"


def execute_run(
    workspace: str | Path,
    recipe: str | Path,
    baseline: str | Path,
    candidate: str | Path,
    output: str | Path,
    cancelled=None,
    progress=None,
) -> dict[str, Any]:
    """Preflight, execute, publish, verify and catalog one local comparison."""
    emit = progress or (lambda phase: None)
    with InputCancellation(cancelled):
        emit("preflight")
        preflight = validate_inputs(recipe, baseline, candidate, validate_records=True)
        if preflight["status"] != "valid":
            raise ParisonError("workbench preflight rejected the selected inputs")
        loaded = load_recipe(recipe)
        emit("comparing")
        result = compare(recipe, baseline, candidate, expected_policy_sha256=preflight["policy_sha256"])
        if cancelled is not None and cancelled():
            raise ParisonError("workbench run cancelled")
    emit("publishing")
    publish(output, result, loaded)
    emit("verifying")
    projection = workbench_projection(output)
    emit("cataloging")
    indexed = catalog_add(_catalog_path(workspace), output)
    emit("complete")
    return {"evidence": projection, "catalog_status": indexed["status"]}


def execute_suite_run(
    workspace: str | Path,
    plan: str | Path,
    output: str | Path,
    case_ids: list[str],
    tags: list[str],
    shard_index: int | None,
    shard_count: int | None,
    cancelled=None,
    progress=None,
) -> dict[str, Any]:
    """Execute one selected local suite, then verify and catalog its bundle."""
    run_suite(
        plan,
        output,
        case_ids=case_ids,
        tags=tags,
        shard_index=shard_index,
        shard_count=shard_count,
        jobs=1,
        cancelled=cancelled,
        progress=progress,
    )
    projection = workbench_projection(output)
    indexed = catalog_add(_catalog_path(workspace), output)
    return {"evidence": projection, "catalog_status": indexed["status"]}


def history_projection(workspace: str | Path) -> list[dict[str, Any]]:
    """Return workspace-relative summary-safe history from the local catalog."""
    root = Path(workspace).resolve()
    database = _catalog_path(root)
    if not database.exists():
        return []
    runs = [
        run for run in list_runs(database, insertion_order=True) if run.get("kind") in {"run", "suite", "suite-shard"}
    ]
    projected = []
    for run in runs:
        try:
            bundle = str(Path(run.pop("path")).resolve().relative_to(root))
        except ValueError as exc:
            raise ParisonError("workbench catalog contains a bundle outside its workspace") from exc
        projected.append({"bundle": bundle, **run})
    return projected


def compare_projection(workspace: str | Path, left: str | Path, right: str | Path) -> dict[str, Any]:
    """Return a same-policy summary-safe catalog comparison with relative bundle names."""
    root = Path(workspace).resolve()
    try:
        comparison = catalog_diff(_catalog_path(root), left, right)
    except ParisonError as catalog_error:
        try:
            kinds = {inspect_bundle(path).get("kind") for path in (left, right)}
        except ParisonError:
            raise catalog_error from None
        if kinds & {"suite", "suite-shard"}:
            return compare_suites(left, right)
        raise
    if any(comparison[side]["state"] != "current" for side in ("left", "right")):
        raise ParisonError("workbench comparison requires current bundle integrity")
    for side in ("left", "right"):
        comparison[side]["bundle"] = str(Path(comparison[side].pop("path")).resolve().relative_to(root))
    return comparison


def investigate_projection(bundle: str | Path) -> dict[str, Any]:
    """Return exhaustive summary-safe discrepancy groups for one verified run."""
    analysis = analyze_bundle(bundle)
    return {
        name: analysis[name]
        for name in (
            "analysis_version",
            "kind",
            "bundle_sha256",
            "policy_sha256",
            "comparison_mode",
            "sensitivity",
        )
    } | {
        "scope_sections": sorted({reference["path"].rsplit("/", 1)[0] for reference in analysis["scope_references"]}),
        "groups": [
            {
                "group_id": group["group_id"],
                "descriptor": {name: value for name, value in group["descriptor"].items() if name != "logical_name"},
                "count": group["count"],
                "reason_codes": group["reason_codes"],
                "policy_sections": sorted(
                    {"/" + reference["path"].strip("/").split("/", 1)[0] for reference in group["policy_references"]}
                ),
            }
            for group in analysis["groups"]
        ],
    }


def _rows(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, dict):
        rows = []
        for name in sorted(value):
            label = f"{prefix}.{name}" if prefix else str(name)
            rows.extend(_rows(value[name], label))
        return rows
    if isinstance(value, list):
        return [(prefix, ", ".join(str(item) for item in value))]
    return [(prefix, json.dumps(value, ensure_ascii=False) if value is not None else "null")]


def render_workbench(projection: dict[str, Any]) -> str:
    """Render one deterministic, script-free workbench page."""
    rows = "".join(
        f'<tr><th scope="row">{html.escape(name)}</th><td><code>{html.escape(value)}</code></td></tr>'
        for name, value in _rows(projection)
    )
    outcome = html.escape(str(projection.get("outcome", "UNKNOWN")))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Parison Workbench — {outcome}</title>
<style>
:root{{color-scheme:light dark;font:16px/1.5 system-ui,sans-serif}}body{{max-width:72rem;margin:auto;padding:2rem}}
header{{border-bottom:.25rem solid currentColor;margin-bottom:2rem}}.notice{{padding:1rem;border:1px solid;border-radius:.4rem}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:.55rem;text-align:left;vertical-align:top;border-bottom:1px solid #8888}}
th{{width:34%}}code{{overflow-wrap:anywhere}}footer{{margin-top:2rem;color:#666}}
</style></head><body><header><p>Parison Workbench</p><h1>{outcome}</h1></header>
<p class="notice"><strong>Verified local evidence.</strong> PASS means agreement under the displayed policy; it is not extraction truth, approval, or cutover authorization.</p>
<main><h2>Summary-safe evidence</h2><table><tbody>{rows}</tbody></table></main>
<footer>No source paths, keys, values, or discrepancy samples are included in this view.</footer></body></html>
"""


def _publish_page(page: str, output: str | Path) -> Path:
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ParisonError(f"output already exists: {output}")
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        check_output_parent(output.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        (stage / "index.html").write_text(page, encoding="utf-8")
        rename_no_replace(stage, output)
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot publish workbench: {exc}") from exc
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise
    return output / "index.html"


def publish_workbench(bundle: str | Path, output: str | Path) -> Path:
    """Publish a verified static workbench atomically without overwriting."""
    return _publish_page(render_workbench(workbench_projection(bundle)), output)


def render_plan_builder(source: str, policy_sha256: str, comparison_mode: str, recipe_version: int) -> str:
    """Render an explicit JSON plan editor with local-only draft download."""
    escaped_source = html.escape(source)
    escaped_digest = html.escape(policy_sha256)
    escaped_mode = html.escape(comparison_mode)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>Parison Workbench — plan builder</title>
<style>
:root{{color-scheme:light dark;font:16px/1.5 system-ui,sans-serif}}body{{max-width:72rem;margin:auto;padding:2rem}}
textarea{{box-sizing:border-box;width:100%;min-height:32rem;font:14px/1.4 ui-monospace,monospace;padding:1rem}}
.notice{{padding:1rem;border:1px solid;border-radius:.4rem}}button{{font:inherit;padding:.6rem 1rem}}code{{overflow-wrap:anywhere}}
</style></head><body><header><p>Parison Workbench</p><h1>Verification plan builder</h1></header>
<p class="notice"><strong>Policy review required.</strong> This editor never approves keys, tolerances, scope, exclusions, sensitivity, or repairs.</p>
<p>Loaded recipe v{recipe_version} · {escaped_mode} · effective policy <code>{escaped_digest}</code></p>
<label for="plan"><strong>CLI-native JSON plan</strong></label>
<textarea id="plan" spellcheck="false">{escaped_source}</textarea>
<p id="status" role="status">Loaded plan passed authoritative Python validation. Changes are not yet validated.</p>
<button id="save" type="button">Download unapproved draft</button>
<h2>Equivalent execution</h2>
<pre><code>parison validate-recipe plan.json
parison compare --recipe plan.json --baseline BASELINE --candidate CANDIDATE --output RUN_DIRECTORY</code></pre>
<script>
const plan=document.getElementById('plan'),status=document.getElementById('status'),save=document.getElementById('save');
plan.addEventListener('input',()=>{{try{{const value=JSON.parse(plan.value);if(!value||Array.isArray(value)||typeof value!=='object')throw Error('top level must be an object');status.textContent='Valid JSON; authoritative Parison validation is still required.';}}catch(error){{status.textContent='Invalid JSON: '+error.message;}}}});
save.addEventListener('click',()=>{{try{{JSON.parse(plan.value);const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([plan.value.endsWith('\\n')?plan.value:plan.value+'\\n'],{{type:'application/json'}}));link.download='plan.json';link.click();URL.revokeObjectURL(link.href);status.textContent='Downloaded unapproved draft. Run parison validate-recipe before use.';}}catch(error){{status.textContent='Cannot download invalid JSON: '+error.message;}}}});
</script></body></html>
"""


def publish_plan_builder(recipe: str | Path, output: str | Path) -> Path:
    """Validate and publish an editor for one explicit CLI-native recipe."""
    plan = plan_projection(recipe)
    return _publish_page(
        render_plan_builder(plan["source"], plan["policy_sha256"], plan["comparison_mode"], plan["recipe_version"]),
        output,
    )
