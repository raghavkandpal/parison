from __future__ import annotations

import platform
from importlib import metadata
from typing import Any

OUTCOME_CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "INCONCLUSIVE": 3, "INTERRUPTED": 130}
_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "keys",
    "scope",
    "identity",
    "nulls_equal",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_AGGREGATE_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "group_by",
    "measures",
    "scope",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_MULTISET_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "scope",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_COLUMN_KEYS = {"type", "comparison", "tolerance", "timezone", "scale", "normalize"}
_MEASURE_KEYS = {"operator", "column", "nulls", "comparison", "tolerance"}
_TYPES = {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}
_NORMALIZATIONS = {"trim", "casefold", "unicode_nfc"}
_INPUT_PROJECTIONS = {"semantic-scalar-v1"}
_RAW_VALUE = object()
_FILE_FORMATS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".xlsx": "xlsx",
}
_SCHEMAS = {
    "recipe-authoring": "recipe-authoring.schema.json",
    "recipe": "recipe-v1.schema.json",
    "recipe-v2": "recipe-v2.schema.json",
    "recipe-v3": "recipe-v3.schema.json",
    "recipe-v4": "recipe-v4.schema.json",
    "recipe-v5": "recipe-v5.schema.json",
    "recipe-v6": "recipe-v6.schema.json",
    "result": "result-v1.schema.json",
    "result-v2": "result-v2.schema.json",
    "result-v3": "result-v3.schema.json",
    "manifest": "manifest-v1.schema.json",
    "preflight": "preflight-v1.schema.json",
    "preflight-v2": "preflight-v2.schema.json",
    "preflight-v3": "preflight-v3.schema.json",
    "preflight-v4": "preflight-v4.schema.json",
    "preflight-v5": "preflight-v5.schema.json",
    "preflight-v6": "preflight-v6.schema.json",
    "preflight-v7": "preflight-v7.schema.json",
    "preflight-v8": "preflight-v8.schema.json",
    "preflight-v9": "preflight-v9.schema.json",
    "preflight-v10": "preflight-v10.schema.json",
    "preflight-v11": "preflight-v11.schema.json",
    "preflight-v12": "preflight-v12.schema.json",
    "preflight-v13": "preflight-v13.schema.json",
    "preflight-v14": "preflight-v14.schema.json",
    "preflight-v15": "preflight-v15.schema.json",
    "preflight-v16": "preflight-v16.schema.json",
    "preflight-v17": "preflight-v17.schema.json",
    "preflight-v18": "preflight-v18.schema.json",
    "preflight-v19": "preflight-v19.schema.json",
    "preflight-v20": "preflight-v20.schema.json",
    "preflight-v21": "preflight-v21.schema.json",
    "preflight-v22": "preflight-v22.schema.json",
    "preflight-v23": "preflight-v23.schema.json",
    "preflight-v24": "preflight-v24.schema.json",
    "suite": "suite-v1.schema.json",
    "suite-authoring": "suite-authoring.schema.json",
    "suite-v2": "suite-v2.schema.json",
    "suite-result": "suite-result-v1.schema.json",
    "suite-result-v2": "suite-result-v2.schema.json",
    "suite-manifest": "suite-manifest-v1.schema.json",
    "suite-manifest-v2": "suite-manifest-v2.schema.json",
    "suite-manifest-v3": "suite-manifest-v3.schema.json",
    "statement": "statement-v1.schema.json",
    "statement-v2": "statement-v2.schema.json",
    "schema-evolution": "schema-evolution-v1.schema.json",
    "policy-diff": "policy-diff-v1.schema.json",
    "time-alignment": "time-alignment-v1.schema.json",
    "reconciliation": "reconciliation-v1.schema.json",
    "alignment-preflight": "alignment-preflight-v1.schema.json",
    "relationship-result": "relationship-result-v1.schema.json",
    "conservation-result": "conservation-result-v1.schema.json",
    "reconciliation-result": "reconciliation-result-v1.schema.json",
    "reconciliation-manifest-v2": "reconciliation-manifest-v2.schema.json",
    "dataset-manifest": "dataset-manifest-v1.schema.json",
    "dataset-manifest-v2": "dataset-manifest-v2.schema.json",
    "input-bindings-v1": "input-bindings-v1.schema.json",
    "manifest-result-v2": "manifest-result-v2.schema.json",
    "dataset-evidence-v2": "dataset-evidence-v2.schema.json",
    "reproducibility-diagnostic": "reproducibility-diagnostic-v1.schema.json",
    "reproducibility-diagnostic-v2": "reproducibility-diagnostic-v2.schema.json",
    "discrepancy-analysis": "discrepancy-analysis-v1.schema.json",
    "suite-series": "suite-series-v1.schema.json",
    "discrepancy-drilldown": "discrepancy-drilldown-v1.schema.json",
    "postgres-export-plan": "postgres-export-plan-v1.schema.json",
    "postgres-source-receipt": "postgres-source-receipt-v1.schema.json",
    "postgres-source-summary": "postgres-source-summary-v1.schema.json",
    "postgres-source-manifest": "postgres-source-manifest-v1.schema.json",
    "postgres-pair-plan": "postgres-pair-plan-v1.schema.json",
    "postgres-pair-receipt": "postgres-pair-receipt-v1.schema.json",
    "postgres-pair-summary": "postgres-pair-summary-v1.schema.json",
    "postgres-pair-manifest": "postgres-pair-manifest-v1.schema.json",
}

_SUITE_LIMIT_DEFAULTS = {
    "max_input_bytes": 1_000_000_000,
    "max_decoded_bytes": 1_000_000_000,
    "max_rows": 5_000_000,
    "max_groups": 100_000,
    "max_distinct_rows": 100_000,
}
_SUITE_LIMIT_KEYS = set(_SUITE_LIMIT_DEFAULTS)
_MAX_SUITE_JOBS = 16
DEFAULT_MAX_TEMP_BYTES = 5_000_000_000


class ParisonError(ValueError):
    pass


class _SafeParseError(ValueError):
    pass


def _runtime_info(paths: tuple[Any, Any] | None = None, contract: str = "keyed-v1") -> dict[str, Any]:
    try:
        version = metadata.version("parison")
    except metadata.PackageNotFoundError:
        version = "source-tree"
    runtime = {
        "contract": contract,
        "parison_version": version,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }
    if paths and any(_file_format(_source_path(path)) == "parquet" for path in paths):
        try:
            runtime["polars"] = metadata.version("polars")
        except metadata.PackageNotFoundError:
            runtime["polars"] = "unavailable"
    return runtime


def _raw_value(row: dict[Any, Any], name: str) -> Any:
    return _json_value(row.get((_RAW_VALUE, name), row[name]))


# Compatibility re-exports; implementation lives in parison.policies.
from .policies import (  # noqa: E402, I001
    _checked_policy_sha256 as _checked_policy_sha256,
    _effective_aggregate_policy as _effective_aggregate_policy,
    _effective_multiset_policy as _effective_multiset_policy,
    _effective_policy as _effective_policy,
    _load_aggregate_recipe as _load_aggregate_recipe,
    _load_multiset_recipe as _load_multiset_recipe,
    _normalize as _normalize,
    _parse as _parse,
    _parse_input as _parse_input,
    _parse_row as _parse_row,
    _portable_identifier as _portable_identifier,
    _source_name as _source_name,
    _unknown as _unknown,
    _validate_common_recipe as _validate_common_recipe,
    _validate_input_projection as _validate_input_projection,
    _validate_suite_limits as _validate_suite_limits,
    _validate_tolerance as _validate_tolerance,
    _with_input_projection as _with_input_projection,
    explain_recipe as explain_recipe,
    export_editor_schemas as export_editor_schemas,
    list_suite as list_suite,
    load_recipe as load_recipe,
    load_schema as load_schema,
    load_suite as load_suite,
    select_suite_cases as select_suite_cases,
)


# Compatibility re-exports; implementation lives in parison.comparison.
from .comparison import (  # noqa: E402
    _json_value as _json_value,
    _multiset_encoding as _multiset_encoding,
    _classify as _classify,
    compare as compare,
    _report as _report,
)


# Compatibility re-exports; implementation lives in parison.inputs.
from .inputs import (  # noqa: E402
    _LimitedText as _LimitedText,
    _aggregate_record_diagnostics as _aggregate_record_diagnostics,
    _decoded_sizes as _decoded_sizes,
    _digest as _digest,
    _file_format as _file_format,
    _input_columns as _input_columns,
    _iter_input_rows as _iter_input_rows,
    _iter_jsonl as _iter_jsonl,
    _jsonl_record as _jsonl_record,
    _multiset_record_diagnostics as _multiset_record_diagnostics,
    _open_text as _open_text,
    _read as _read,
    _record_diagnostics as _record_diagnostics,
    _schema_details as _schema_details,
    _source_bytes as _source_bytes,
    _source_digest as _source_digest,
    _source_metadata as _source_metadata,
    _source_path as _source_path,
    _source_paths as _source_paths,
    _sqlite_rows as _sqlite_rows,
    _sqlite_source as _sqlite_source,
    _suggest_keys as _suggest_keys,
    _suggest_type as _suggest_type,
    _validate_headers as _validate_headers,
    _validate_parquet_projection as _validate_parquet_projection,
    draft_recipe as draft_recipe,
    validate_inputs as validate_inputs,
)


# Compatibility re-exports; implementation lives in parison.evidence.
from .evidence import (  # noqa: E402
    _check_output_parent as _check_output_parent,
    _verify_manifest_files as _verify_manifest_files,
    _write_once as _write_once,
    bundle_integrity_matches as bundle_integrity_matches,
    error_result as error_result,
    evidence_statement as evidence_statement,
    export_evidence as export_evidence,
    export_statement as export_statement,
    inspect_bundle as inspect_bundle,
    publish as publish,
    report_ci as report_ci,
    report_cutover as report_cutover,
    terminal_result as terminal_result,
    verify_bundle as verify_bundle,
    verify_statement as verify_statement,
)


# Compatibility re-exports; implementation lives in parison.suites.
from .suites import (  # noqa: E402
    _execute_suite_case as _execute_suite_case,
    assemble_suite as assemble_suite,
    run_suite as run_suite,
)
