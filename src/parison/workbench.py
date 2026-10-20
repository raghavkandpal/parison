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


def publish_workbench(bundle: str | Path, output: str | Path) -> Path:
    """Publish a verified static workbench atomically without overwriting."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ParisonError(f"output already exists: {output}")
    page = render_workbench(workbench_projection(bundle))
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
