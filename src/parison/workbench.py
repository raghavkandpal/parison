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
from .core import ParisonError
from .evidence import inspect_bundle
from .policies import explain_recipe, load_recipe

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
    path = Path(recipe)
    loaded = load_recipe(path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ParisonError(f"cannot read recipe: {exc}") from exc
    policy = explain_recipe(path)
    return _publish_page(
        render_plan_builder(source, policy["policy_sha256"], loaded["comparison_mode"], loaded["recipe_version"]),
        output,
    )
