from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from . import __version__
from .catalog import add as catalog_add, diff as catalog_diff, history as catalog_history, list_runs as catalog_list, remove as catalog_remove, show as catalog_show
from .core import DEFAULT_MAX_TEMP_BYTES, OUTCOME_CODES, ParisonError, assemble_suite, compare, draft_recipe, error_result, explain_recipe, export_editor_schemas, export_evidence, export_statement, inspect_bundle, list_suite, load_recipe, load_schema, load_suite, publish, report_ci, report_cutover, run_suite, terminal_result, validate_inputs, verify_bundle, verify_statement
from .evolution import compile_evolution_mappings, diff_policies, explain_evolution, load_evolution, summarize_policy_diff
from .manifesting import capture_reproducibility_diagnostic, create_dataset_manifest, diff_reproducibility_diagnostics, explain_dataset_manifest, verify_dataset_manifest
from .project import init_project
from .reconciliation import check_conservation, check_identity_references, explain_reconciliation, explain_time_alignment, inspect_reconciliation_bundle, load_reconciliation, load_time_alignment, preflight_alignment, publish_reconciliation_bundle, run_reconciliation, summarize_reconciliation_result, verify_reconciliation_bundle


def _shell_command(parts: list[str]) -> str:
    return subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)


def _print_bundle_next(output: str) -> None:
    print("Next:", file=sys.stderr)
    print(f"  {_shell_command(['parison', 'verify', output])}", file=sys.stderr)
    print(f"  {_shell_command(['parison', 'inspect', output])}", file=sys.stderr)


def _print_suite_next(output: str) -> None:
    _print_bundle_next(output)
    print(f"  {_shell_command(['parison', 'report-ci', output, '--format', 'markdown', '--output', 'parison-summary.md'])}", file=sys.stderr)


def _print_summary(result: dict, output: str) -> None:
    counts = result["counts"]
    print(f"Parison {result['outcome']} (complete: {str(result['complete']).lower()})", file=sys.stderr)
    if result["schema_version"] == 3 and counts:
        print(
            "Rows: "
            f"baseline {counts['baseline_rows']}, candidate {counts['candidate_rows']}, common occurrences {counts['common_occurrences']}, "
            f"baseline-only {counts['baseline_only_occurrences']}, candidate-only {counts['candidate_only_occurrences']}",
            file=sys.stderr,
        )
    elif result["schema_version"] == 2 and counts:
        print(
            "Groups: "
            f"baseline {counts['baseline_groups']}, candidate {counts['candidate_groups']}, common {counts['common_groups']}, "
            f"baseline-only {counts['baseline_only_groups']}, candidate-only {counts['candidate_only_groups']}",
            file=sys.stderr,
        )
        print(
            "Measures: "
            f"exact {counts['exact_measures']}, within tolerance {counts['within_tolerance_measures']}, "
            f"different {counts['different_measures']}",
            file=sys.stderr,
        )
    elif counts:
        print(
            "Rows: "
            f"baseline {counts['baseline']}, candidate {counts['candidate']}, common {counts['common_keys']}, "
            f"baseline-only {counts['baseline_only']}, candidate-only {counts['candidate_only']}",
            file=sys.stderr,
        )
        print(
            "Matches: "
            f"exact {counts['matched_exact']}, within tolerance {counts['matched_within_tolerance']}, "
            f"different {counts['matched_with_required_difference']}",
            file=sys.stderr,
        )
    print(f"Sensitivity: {result['sensitivity']}", file=sys.stderr)
    print(f"Bundle: {output}", file=sys.stderr)
    if result["outcome"] == "FAIL":
        print("Exit 1 means the comparison completed and found required differences.", file=sys.stderr)
        _print_bundle_next(output)
        if result["sensitivity"] == "raw":
            print(f"  {_shell_command(['parison', 'export-evidence', output, '--output', 'evidence.jsonl'])}", file=sys.stderr)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="parison", description="Compare data-pipeline outputs deterministically")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a minimal keyed migration project")
    init.add_argument("directory")
    validate = commands.add_parser("validate-recipe", help="validate a JSON recipe")
    validate.add_argument("recipe")
    explain = commands.add_parser("explain", help="print the effective recipe policy without reading inputs")
    explain.add_argument("recipe")
    validate_evolution = commands.add_parser("validate-evolution", help="validate a schema evolution declaration")
    validate_evolution.add_argument("evolution")
    explain_evolution_parser = commands.add_parser("explain-evolution", help="print normalized schema evolution and its fingerprint")
    explain_evolution_parser.add_argument("evolution")
    compile_evolution = commands.add_parser("compile-evolution", help="compile identity-preserving evolution into column mappings")
    compile_evolution.add_argument("evolution")
    policy_diff = commands.add_parser("diff-policy", help="assess two effective policies under a schema evolution declaration")
    policy_diff.add_argument("--baseline-recipe", required=True)
    policy_diff.add_argument("--candidate-recipe", required=True)
    policy_diff.add_argument("--evolution", required=True)
    policy_diff.add_argument("--summary", action="store_true", help="omit schema names, paths and policy fragments")
    validate_alignment = commands.add_parser("validate-time-alignment", help="validate a time-alignment-v1 declaration")
    validate_alignment.add_argument("alignment")
    explain_alignment = commands.add_parser("explain-time-alignment", help="print normalized time alignment and its fingerprint")
    explain_alignment.add_argument("alignment")
    validate_reconciliation = commands.add_parser("validate-reconciliation", help="validate a reconciliation-v1 declaration")
    validate_reconciliation.add_argument("reconciliation")
    explain_reconciliation_parser = commands.add_parser("explain-reconciliation", help="print normalized reconciliation and its fingerprint")
    explain_reconciliation_parser.add_argument("reconciliation")
    alignment_preflight = commands.add_parser("preflight-alignment", help="scan event windows and evaluate coordination claims")
    alignment_preflight.add_argument("--alignment", required=True)
    alignment_preflight.add_argument("--reconciliation", required=True)
    alignment_preflight.add_argument("--receipt", required=True)
    alignment_preflight.add_argument("--dataset", action="append", nargs=4, metavar=("ID", "RECIPE", "BASELINE", "CANDIDATE"), required=True)
    alignment_preflight.add_argument("--max-input-bytes", type=int, default=1_000_000_000)
    alignment_preflight.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000)
    alignment_preflight.add_argument("--max-rows", type=int, default=5_000_000)
    relationships = commands.add_parser("check-identity-references", help="evaluate reconciliation identities and references on both sides")
    relationships.add_argument("--reconciliation", required=True)
    relationships.add_argument("--dataset", action="append", nargs=4, metavar=("ID", "RECIPE", "BASELINE", "CANDIDATE"), required=True)
    relationships.add_argument("--engine", choices=("memory", "sqlite"), default="memory")
    relationships.add_argument("--max-input-bytes", type=int, default=1_000_000_000)
    relationships.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000)
    relationships.add_argument("--max-rows", type=int, default=5_000_000)
    relationships.add_argument("--max-keys", type=int, default=100_000)
    relationships.add_argument("--max-temp-bytes", type=int, default=DEFAULT_MAX_TEMP_BYTES)
    relationships.add_argument("--temp-directory")
    conservation = commands.add_parser("check-conservation", help="evaluate reconciliation grouped-sum conservation on both sides")
    conservation.add_argument("--reconciliation", required=True)
    conservation.add_argument("--dataset", action="append", nargs=4, metavar=("ID", "RECIPE", "BASELINE", "CANDIDATE"), required=True)
    conservation.add_argument("--engine", choices=("memory", "sqlite"), default="memory")
    conservation.add_argument("--max-input-bytes", type=int, default=1_000_000_000)
    conservation.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000)
    conservation.add_argument("--max-rows", type=int, default=5_000_000)
    conservation.add_argument("--max-groups", type=int, default=100_000)
    conservation.add_argument("--max-temp-bytes", type=int, default=DEFAULT_MAX_TEMP_BYTES)
    conservation.add_argument("--temp-directory")
    reconcile = commands.add_parser("reconcile", help="run aligned per-dataset parity and all reconciliation checks")
    reconcile.add_argument("--alignment", required=True)
    reconcile.add_argument("--reconciliation", required=True)
    reconcile.add_argument("--receipt", required=True)
    reconcile.add_argument("--dataset", action="append", nargs=4, metavar=("ID", "RECIPE", "BASELINE", "CANDIDATE"), required=True)
    reconcile.add_argument("--engine", choices=("memory", "sqlite"), default="memory")
    reconcile.add_argument("--summary", action="store_true", help="omit dataset and relationship identifiers and detailed counts")
    reconcile.add_argument("--output", help="atomically publish a verified reconciliation bundle")
    reconcile.add_argument("--max-input-bytes", type=int, default=1_000_000_000)
    reconcile.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000)
    reconcile.add_argument("--max-rows", type=int, default=5_000_000)
    reconcile.add_argument("--max-keys", type=int, default=100_000)
    reconcile.add_argument("--max-groups", type=int, default=100_000)
    reconcile.add_argument("--max-distinct-rows", type=int, default=100_000)
    reconcile.add_argument("--max-temp-bytes", type=int, default=DEFAULT_MAX_TEMP_BYTES)
    reconcile.add_argument("--temp-directory")
    verify_reconciliation_parser = commands.add_parser("verify-reconciliation", help="verify a published reconciliation bundle")
    verify_reconciliation_parser.add_argument("bundle")
    inspect_reconciliation_parser = commands.add_parser("inspect-reconciliation", help="print summary-safe metadata from a verified reconciliation bundle")
    inspect_reconciliation_parser.add_argument("bundle")
    create_manifest = commands.add_parser("create-dataset-manifest", help="bind explicitly named local files to a deterministic manifest")
    create_manifest.add_argument("--root", required=True)
    create_manifest.add_argument("--collection-id", required=True)
    create_manifest.add_argument("--policy-kind", choices=("suite", "reconciliation"), required=True)
    create_manifest.add_argument("--policy-sha256", required=True)
    create_manifest.add_argument("--resource", action="append", nargs=4, metavar=("ID", "ROLE", "FORMAT", "PATH"), required=True)
    create_manifest.add_argument("--output", required=True)
    validate_manifest = commands.add_parser("validate-dataset-manifest", help="validate a dataset-manifest-v1 declaration")
    validate_manifest.add_argument("manifest")
    explain_manifest = commands.add_parser("explain-dataset-manifest", help="print a normalized dataset manifest and fingerprint")
    explain_manifest.add_argument("manifest")
    verify_manifest = commands.add_parser("verify-dataset-manifest", help="verify declared local membership and byte identity")
    verify_manifest.add_argument("--manifest", required=True)
    verify_manifest.add_argument("--root", required=True)
    verify_manifest.add_argument("--summary", action="store_true")
    capture_diagnostic = commands.add_parser("capture-reproducibility", help="record bounded runtime facts for one dataset manifest")
    capture_diagnostic.add_argument("--manifest", required=True)
    capture_diagnostic.add_argument("--output", required=True)
    diff_diagnostic = commands.add_parser("diff-reproducibility", help="compare two diagnostics for the same dataset manifest")
    diff_diagnostic.add_argument("left")
    diff_diagnostic.add_argument("right")
    schema = commands.add_parser("schema", help="print an installed JSON Schema")
    schema.add_argument("name", choices=("recipe", "recipe-authoring", "recipe-v2", "recipe-v3", "result", "result-v2", "result-v3", "manifest", "preflight", "preflight-v2", "preflight-v3", "suite", "suite-authoring", "suite-v2", "suite-result", "suite-result-v2", "suite-manifest", "suite-manifest-v2", "statement", "schema-evolution", "policy-diff", "time-alignment", "reconciliation", "alignment-preflight", "relationship-result", "conservation-result", "reconciliation-result", "dataset-manifest", "reproducibility-diagnostic"))
    schema_export = commands.add_parser("export-editor-schemas", help="export offline recipe and suite editor schemas")
    schema_export.add_argument("--output", required=True)
    suite = commands.add_parser("validate-suite", help="validate a comparison suite and its references")
    suite.add_argument("plan")
    suite_list = commands.add_parser("list-suite", help="list selected suite cases without reading inputs")
    suite_list.add_argument("plan")
    suite_list.add_argument("--case", action="append", default=[])
    suite_list.add_argument("--tag", action="append", default=[])
    suite_list.add_argument("--shard-index", type=int)
    suite_list.add_argument("--shard-count", type=int)
    suite_list.add_argument("--json", action="store_true")
    suite_run = commands.add_parser("run-suite", help="run an ordered comparison suite")
    suite_run.add_argument("--plan", required=True)
    suite_run.add_argument("--output", required=True)
    suite_run.add_argument("--sample-limit", type=int, default=100)
    suite_run.add_argument("--max-input-bytes", type=int, default=1_000_000_000)
    suite_run.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000)
    suite_run.add_argument("--max-rows", type=int, default=5_000_000)
    suite_run.add_argument("--max-groups", type=int, default=100_000)
    suite_run.add_argument("--max-distinct-rows", type=int, default=100_000)
    suite_run.add_argument("--case", action="append", default=[])
    suite_run.add_argument("--tag", action="append", default=[])
    suite_run.add_argument("--shard-index", type=int)
    suite_run.add_argument("--shard-count", type=int)
    suite_run.add_argument("--workspace")
    suite_run.add_argument("--resume", action="store_true")
    suite_run.add_argument("--jobs", type=int, default=1, help="maximum concurrent suite cases (default: 1; maximum: 16)")
    suite_assemble = commands.add_parser("assemble-suite", help="assemble verified suite shards")
    suite_assemble.add_argument("--plan", required=True)
    suite_assemble.add_argument("--input", action="append", required=True)
    suite_assemble.add_argument("--output", required=True)
    ci_report = commands.add_parser("report-ci", help="export a safe CI projection from a verified suite")
    ci_report.add_argument("bundle")
    ci_report.add_argument("--format", choices=("markdown", "junit"), required=True)
    ci_report.add_argument("--output", required=True)
    inputs = commands.add_parser("validate-inputs", help="validate input schemas and optionally records against a recipe")
    inputs.add_argument("--recipe", required=True)
    inputs.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    inputs.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    inputs.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    inputs.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000, help="maximum combined decoded gzip size (default: 1 GB)")
    inputs.add_argument("--records", action="store_true", help="scan all records for types and mode-specific identity")
    inputs.add_argument("--max-rows", type=int, default=5_000_000, help="maximum rows in either input (default: 5 million)")
    inputs.add_argument("--max-groups", type=int, default=100_000, help="maximum aggregate groups in either input (default: 100,000)")
    inputs.add_argument("--max-distinct-rows", type=int, default=100_000, help="maximum distinct rows in either multiset input (default: 100,000)")
    inputs.add_argument("--expected-policy-sha256", help="require this effective-policy fingerprint before reading inputs")
    draft = commands.add_parser(
        "draft-recipe",
        help="draft a JSON recipe with reviewable suggestions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Review the generated JSON before comparison:
  confirm the suggested keys, scope, null handling and column data types;
  map renamed baseline/candidate columns; adjust exclusions and tolerances.
Then run: parison validate-recipe DRAFT.json

Numeric comparison requires integer, decimal or float plus an explicit
symmetric-v1 tolerance. With --aggregate, confirm every suggested group,
operator and null policy. Suggestions are starting points, not approved policy.""",
    )
    draft.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    draft.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    draft.add_argument("--output", required=True)
    draft.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    draft.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000, help="maximum combined decoded gzip size (default: 1 GB)")
    draft_mode = draft.add_mutually_exclusive_group()
    draft_mode.add_argument("--aggregate", action="store_true", help="draft an aggregate-v1 recipe instead of a keyed recipe")
    draft_mode.add_argument("--multiset", action="store_true", help="draft a multiset-v1 recipe instead of a keyed recipe")
    verify = commands.add_parser("verify", help="verify a published run bundle")
    verify.add_argument("run_directory")
    verify.add_argument("--json", action="store_true", help="print verified manifest metadata as JSON")
    inspect = commands.add_parser("inspect", help="inspect safe metadata from a verified run bundle")
    inspect.add_argument("run_directory")
    statement = commands.add_parser("statement", help="export an unsigned in-toto Statement for a verified bundle")
    statement.add_argument("bundle")
    statement.add_argument("--output", required=True)
    statement_verify = commands.add_parser("verify-statement", help="match an authenticated Statement to a verified bundle")
    statement_verify.add_argument("bundle")
    statement_verify.add_argument("statement")
    cutover_report = commands.add_parser("report-cutover", help="export a safe Markdown cover sheet from verified evidence")
    cutover_report.add_argument("bundle")
    cutover_report.add_argument("--output", required=True)
    catalog = commands.add_parser("catalog", help="index safe metadata from verified bundles locally")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_add_parser = catalog_commands.add_parser("add", help="verify and index a bundle")
    catalog_add_parser.add_argument("bundle")
    catalog_add_parser.add_argument("--database", required=True)
    catalog_list_parser = catalog_commands.add_parser("list", help="list indexed bundles and their current state")
    catalog_list_parser.add_argument("--database", required=True)
    catalog_list_parser.add_argument("--outcome", choices=tuple(OUTCOME_CODES))
    catalog_list_parser.add_argument("--kind", choices=("run", "suite", "suite-shard"))
    catalog_list_parser.add_argument("--policy-sha256")
    catalog_list_parser.add_argument("--state", choices=("current", "modified", "missing"))
    catalog_show_parser = catalog_commands.add_parser("show", help="show one indexed bundle by path")
    catalog_show_parser.add_argument("bundle")
    catalog_show_parser.add_argument("--database", required=True)
    catalog_history_parser = catalog_commands.add_parser("history", help="show insertion-ordered runs and transitions for one policy")
    catalog_history_parser.add_argument("--database", required=True)
    catalog_history_parser.add_argument("--policy-sha256", required=True)
    catalog_diff_parser = catalog_commands.add_parser("diff", help="compare safe projections of two same-policy runs")
    catalog_diff_parser.add_argument("left_bundle")
    catalog_diff_parser.add_argument("right_bundle")
    catalog_diff_parser.add_argument("--database", required=True)
    catalog_remove_parser = catalog_commands.add_parser("remove", help="remove an indexed path without deleting its bundle")
    catalog_remove_parser.add_argument("bundle")
    catalog_remove_parser.add_argument("--database", required=True)
    export = commands.add_parser("export-evidence", help="export bounded raw evidence from a verified bundle")
    export.add_argument("run_directory")
    export.add_argument("--output", required=True)
    export.add_argument("--classification")
    export.add_argument("--kind", choices=("record", "field", "group", "measure", "row"))
    export.add_argument("--name", help="exact field or measure name")
    export.add_argument("--limit", type=int, default=100)
    run = commands.add_parser("compare", help="compare baseline and candidate files")
    run.add_argument("--recipe", required=True)
    run.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    run.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    run.add_argument("--output", required=True)
    run.add_argument("--sample-limit", type=int, default=100, help="maximum raw field differences to publish")
    run.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    run.add_argument("--max-decoded-bytes", type=int, default=1_000_000_000, help="maximum combined decoded gzip size (default: 1 GB)")
    run.add_argument("--max-rows", type=int, default=5_000_000, help="maximum rows in either input (default: 5 million)")
    run.add_argument("--max-groups", type=int, default=100_000, help="maximum groups in either aggregate input (default: 100,000)")
    run.add_argument("--max-distinct-rows", type=int, default=100_000, help="maximum distinct rows in either multiset input (default: 100,000)")
    run.add_argument("--engine", choices=("memory", "sqlite"), default="memory", help="execution engine; sqlite supports keyed and multiset recipes (default: memory)")
    run.add_argument("--max-temp-bytes", type=int, default=DEFAULT_MAX_TEMP_BYTES, help="maximum SQLite spill database size (default: 5 GB)")
    run.add_argument("--temp-directory", help="existing directory in which to create and clean up the private spill workspace")
    run.add_argument("--expected-policy-sha256", help="require this effective-policy fingerprint before reading inputs")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    recipe = None
    try:
        if args.command == "init":
            files = init_project(args.directory)
            print(json.dumps({"directory": args.directory, "files": files}))
            print(f"Created Parison project: {args.directory}", file=sys.stderr)
            print(f"Next: cd {args.directory} and follow README.md", file=sys.stderr)
            return 0
        if args.command == "verify":
            manifest = verify_bundle(args.run_directory)
            print(json.dumps(manifest, sort_keys=True) if args.json else "valid")
            detail = "suite" if manifest.get("kind") == "suite" else f"sensitivity: {manifest['sensitivity']}"
            print(f"Verified bundle integrity: {args.run_directory} (recorded outcome: {manifest['outcome']}, {detail})", file=sys.stderr)
            print("Integrity verification does not change the recorded comparison outcome.", file=sys.stderr)
            return 0
        if args.command == "inspect":
            print(json.dumps(inspect_bundle(args.run_directory), indent=2, sort_keys=True))
            return 0
        if args.command == "statement":
            print(json.dumps(export_statement(args.bundle, args.output), sort_keys=True))
            print("Exported unsigned Statement; authenticate it with an external signer.", file=sys.stderr)
            return 0
        if args.command == "verify-statement":
            print(json.dumps(verify_statement(args.bundle, args.statement), sort_keys=True))
            print("Statement semantics match the verified bundle; signature authentication is external.", file=sys.stderr)
            return 0
        if args.command == "report-cutover":
            print(json.dumps(report_cutover(args.bundle, args.output), sort_keys=True))
            print("Exported verified metadata cover sheet; cutover approval remains external.", file=sys.stderr)
            return 0
        if args.command == "catalog":
            if args.catalog_command == "add":
                result = catalog_add(args.database, args.bundle)
            elif args.catalog_command == "list":
                result = {"runs": catalog_list(
                    args.database, args.outcome, args.kind,
                    policy_sha256=args.policy_sha256, state=args.state,
                )}
            elif args.catalog_command == "show":
                result = catalog_show(args.database, args.bundle)
            elif args.catalog_command == "history":
                result = catalog_history(args.database, args.policy_sha256)
            elif args.catalog_command == "diff":
                result = catalog_diff(args.database, args.left_bundle, args.right_bundle)
            else:
                result = catalog_remove(args.database, args.bundle)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "export-evidence":
            print(json.dumps(export_evidence(args.run_directory, args.output, args.classification, args.limit, kind=args.kind, name=args.name), sort_keys=True))
            return 0
        if args.command == "draft-recipe":
            draft = draft_recipe(args.baseline, args.candidate, args.max_input_bytes, args.max_decoded_bytes, args.aggregate, args.multiset)
            output = Path(args.output)
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("x", encoding="utf-8") as handle:
                    json.dump(draft, handle, indent=2)
                    handle.write("\n")
            except OSError as exc:
                raise ParisonError(f"cannot write draft recipe: {exc}") from exc
            print(json.dumps({"output": args.output}))
            print(f"Drafted recipe with inferred suggestions: {args.output}", file=sys.stderr)
            print("Next: review the suggestions, then run parison validate-recipe on the draft.", file=sys.stderr)
            return 0
        if args.command == "explain":
            print(json.dumps(explain_recipe(args.recipe), indent=2, sort_keys=True))
            print(f"Explained effective policy: {args.recipe}", file=sys.stderr)
            return 0
        if args.command == "validate-evolution":
            load_evolution(args.evolution)
            print("valid")
            print(f"Validated schema evolution: {args.evolution}", file=sys.stderr)
            return 0
        if args.command == "explain-evolution":
            print(json.dumps(explain_evolution(args.evolution), indent=2, sort_keys=True))
            print(f"Explained schema evolution: {args.evolution}", file=sys.stderr)
            return 0
        if args.command == "compile-evolution":
            print(json.dumps(compile_evolution_mappings(args.evolution), indent=2, sort_keys=True))
            print("Compiled identity mappings only; review them before adding them to a recipe.", file=sys.stderr)
            return 0
        if args.command == "diff-policy":
            result = diff_policies(args.baseline_recipe, args.candidate_recipe, args.evolution)
            print(json.dumps(summarize_policy_diff(result) if args.summary else result, indent=2, sort_keys=True))
            print("Compatibility is a mechanical assessment, not policy approval or cutover authorization.", file=sys.stderr)
            return 0 if result["compatibility"] == "ACCEPT" else 1 if result["compatibility"] == "DENY" else 3
        if args.command == "validate-time-alignment":
            load_time_alignment(args.alignment)
            print("valid")
            print(f"Validated time alignment: {args.alignment}", file=sys.stderr)
            return 0
        if args.command == "explain-time-alignment":
            print(json.dumps(explain_time_alignment(args.alignment), indent=2, sort_keys=True))
            print(f"Explained time alignment: {args.alignment}", file=sys.stderr)
            return 0
        if args.command == "validate-reconciliation":
            load_reconciliation(args.reconciliation)
            print("valid")
            print(f"Validated reconciliation: {args.reconciliation}", file=sys.stderr)
            return 0
        if args.command == "explain-reconciliation":
            print(json.dumps(explain_reconciliation(args.reconciliation), indent=2, sort_keys=True))
            print(f"Explained reconciliation: {args.reconciliation}", file=sys.stderr)
            return 0
        if args.command == "preflight-alignment":
            if len({item[0] for item in args.dataset}) != len(args.dataset):
                raise ParisonError("--dataset IDs must be unique")
            inputs = {item[0]: {"recipe": item[1], "baseline": item[2], "candidate": item[3]} for item in args.dataset}
            result = preflight_alignment(
                args.alignment, args.reconciliation, args.receipt, inputs,
                args.max_input_bytes, args.max_decoded_bytes, args.max_rows,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            print("Alignment preflight checks supplied local evidence; it does not establish extraction truth or authorize cutover.", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "check-identity-references":
            if len({item[0] for item in args.dataset}) != len(args.dataset):
                raise ParisonError("--dataset IDs must be unique")
            inputs = {item[0]: {"recipe": item[1], "baseline": item[2], "candidate": item[3]} for item in args.dataset}
            result = check_identity_references(
                args.reconciliation, inputs, args.engine, args.max_input_bytes,
                args.max_decoded_bytes, args.max_rows, args.max_keys,
                args.max_temp_bytes, args.temp_directory,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            print("Relationship checks describe supplied local rows; they do not establish extraction truth or authorize repair or cutover.", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "check-conservation":
            if len({item[0] for item in args.dataset}) != len(args.dataset):
                raise ParisonError("--dataset IDs must be unique")
            inputs = {item[0]: {"recipe": item[1], "baseline": item[2], "candidate": item[3]} for item in args.dataset}
            result = check_conservation(
                args.reconciliation, inputs, args.engine, args.max_input_bytes,
                args.max_decoded_bytes, args.max_rows, args.max_groups,
                args.max_temp_bytes, args.temp_directory,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            print("Conservation checks supplied local sums only; they do not certify accounting, repair data or authorize cutover.", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "reconcile":
            if len({item[0] for item in args.dataset}) != len(args.dataset):
                raise ParisonError("--dataset IDs must be unique")
            inputs = {item[0]: {"recipe": item[1], "baseline": item[2], "candidate": item[3]} for item in args.dataset}
            result = run_reconciliation(
                args.alignment, args.reconciliation, args.receipt, inputs, args.engine,
                args.max_input_bytes, args.max_decoded_bytes, args.max_rows,
                args.max_keys, args.max_groups, args.max_distinct_rows,
                args.max_temp_bytes, args.temp_directory,
            )
            if args.output:
                publish_reconciliation_bundle(args.output, result, args.alignment, args.reconciliation)
            print(json.dumps(summarize_reconciliation_result(result) if args.summary else result, indent=2, sort_keys=True))
            if args.output:
                print(f"Bundle: {args.output}", file=sys.stderr)
            print("PASS means supplied artifacts agree under the declared policies; it is not extraction truth, approval or cutover authorization.", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "verify-reconciliation":
            manifest = verify_reconciliation_bundle(args.bundle)
            print(json.dumps({"kind": manifest["kind"], "outcome": manifest["outcome"], "complete": manifest["complete"], "bundle_sha256": hashlib.sha256((Path(args.bundle) / "manifest.json").read_bytes()).hexdigest()}, sort_keys=True))
            return 0
        if args.command == "inspect-reconciliation":
            print(json.dumps(inspect_reconciliation_bundle(args.bundle), indent=2, sort_keys=True))
            return 0
        if args.command == "create-dataset-manifest":
            result = create_dataset_manifest(args.root, args.collection_id, args.policy_kind, args.policy_sha256, args.resource, args.output)
            print(json.dumps({"output": args.output, "manifest_sha256": result["manifest_sha256"]}, sort_keys=True))
            print("Manifest PASS proves declared local byte identity only; it is not extraction truth or approval.", file=sys.stderr)
            return 0
        if args.command == "validate-dataset-manifest":
            explain_dataset_manifest(args.manifest)
            print("valid")
            return 0
        if args.command == "explain-dataset-manifest":
            print(json.dumps(explain_dataset_manifest(args.manifest), indent=2, sort_keys=True))
            return 0
        if args.command == "verify-dataset-manifest":
            result = verify_dataset_manifest(args.manifest, args.root, args.summary)
            print(json.dumps(result, indent=2, sort_keys=True))
            print("Manifest PASS proves declared local byte identity only; it is not extraction truth or approval.", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "capture-reproducibility":
            result = capture_reproducibility_diagnostic(args.manifest, args.output)
            print(json.dumps({"output": args.output, "diagnostic_sha256": result["diagnostic_sha256"]}, sort_keys=True))
            return 0
        if args.command == "diff-reproducibility":
            print(json.dumps(diff_reproducibility_diagnostics(args.left, args.right), indent=2, sort_keys=True))
            print("Runtime differences are informational and do not change verification outcomes.", file=sys.stderr)
            return 0
        if args.command == "schema":
            print(json.dumps(load_schema(args.name), indent=2, sort_keys=True))
            return 0
        if args.command == "export-editor-schemas":
            print(json.dumps(export_editor_schemas(args.output), sort_keys=True))
            return 0
        if args.command == "validate-suite":
            loaded = load_suite(args.plan)
            print(json.dumps({"status": "valid", "cases": len(loaded["cases"])}, sort_keys=True))
            print(f"Validated comparison suite: {args.plan}", file=sys.stderr)
            return 0
        if args.command == "list-suite":
            result = list_suite(args.plan, args.case, args.tag, args.shard_index, args.shard_count)
            if args.json:
                print(json.dumps(result, indent=2, sort_keys=True))
            else:
                for case in result["cases"]:
                    print(f"{case['id']}\t{case['comparison_mode']}\t{','.join(case.get('tags', []))}")
            print(f"Selected {result['selected_cases']} of {result['total_cases']} suite cases.", file=sys.stderr)
            return 0
        if args.command == "run-suite":
            result = run_suite(
                args.plan, args.output, args.sample_limit, args.max_input_bytes, args.max_rows,
                args.max_decoded_bytes, args.max_groups, args.max_distinct_rows,
                args.case, args.tag, args.shard_index, args.shard_count,
                args.workspace, args.resume,
                args.jobs,
            )
            print(json.dumps({"outcome": result["outcome"], "output": args.output, "cases": result["completed_cases"]}, sort_keys=True))
            subject = "suite shard" if result.get("kind") == "suite-shard" else "suite"
            denominator = result.get("selected_cases", result["total_cases"])
            print(f"Parison {subject} {result['outcome']}: {result['completed_cases']} of {denominator} selected cases published to {args.output}", file=sys.stderr)
            if result["outcome"] != "PASS":
                _print_suite_next(args.output)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "assemble-suite":
            result = assemble_suite(args.plan, args.input, args.output)
            print(json.dumps({"outcome": result["outcome"], "output": args.output, "cases": result["completed_cases"]}, sort_keys=True))
            print(f"Assembled Parison suite {result['outcome']}: {result['completed_cases']} selected cases published to {args.output}", file=sys.stderr)
            if result["outcome"] != "PASS":
                _print_suite_next(args.output)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "report-ci":
            print(json.dumps(report_ci(args.bundle, args.output, args.format), sort_keys=True))
            return 0
        if args.command == "validate-inputs":
            result = validate_inputs(
                args.recipe,
                args.baseline,
                args.candidate,
                args.max_input_bytes,
                args.expected_policy_sha256,
                args.max_decoded_bytes,
                args.records,
                args.max_rows,
                args.max_groups,
                args.max_distinct_rows,
            )
            print(json.dumps(result, sort_keys=True))
            if args.records:
                for side in ("baseline", "candidate"):
                    records = result["inputs"][side].get("records")
                    if records:
                        if result["comparison_mode"] == "aggregate":
                            print(
                                f"{side.title()} records: {records['rows']} rows, {records['groups']} groups, "
                                f"{records['invalid_rows']} invalid rows, {records['null_group_rows']} null-group rows, "
                                f"{records['rejected_null_measure_values']} rejected null measure values.", file=sys.stderr,
                            )
                        elif result["comparison_mode"] == "multiset":
                            print(
                                f"{side.title()} records: {records['rows']} rows, {records['distinct_rows']} distinct rows, "
                                f"{records['invalid_rows']} invalid rows, limit exceeded: {str(records['distinct_row_limit_exceeded']).lower()}.", file=sys.stderr,
                            )
                        else:
                            print(
                                f"{side.title()} records: {records['rows']} rows, "
                                f"{records['invalid_rows']} invalid rows, {records['null_key_rows']} null-key rows, "
                                f"{records['duplicate_keys']} duplicate keys.", file=sys.stderr,
                            )
            if result["status"] == "valid":
                print(
                    f"Validated input schemas: {result['inputs']['baseline']['columns']} baseline and "
                    f"{result['inputs']['candidate']['columns']} candidate columns.",
                    file=sys.stderr,
                )
                return 0
            subject = "Input schemas or records" if args.records else "Input schemas"
            print(f"{subject} do not match the recipe; inspect the JSON diagnostics.", file=sys.stderr)
            return 2
        recipe = load_recipe(args.recipe)
        if args.command == "validate-recipe":
            print("valid")
            print(f"Validated recipe: {args.recipe}", file=sys.stderr)
            return 0
        result = compare(
            args.recipe,
            args.baseline,
            args.candidate,
            args.sample_limit,
            args.max_input_bytes,
            args.max_rows,
            args.expected_policy_sha256,
            args.max_decoded_bytes,
            args.max_groups,
            args.max_distinct_rows,
            args.engine,
            args.max_temp_bytes,
            args.temp_directory,
        )
        publish(args.output, result, recipe)
        print(json.dumps({"outcome": result["outcome"], "output": args.output}))
        _print_summary(result, args.output)
        return OUTCOME_CODES[result["outcome"]]
    except ParisonError as exc:
        if args.command == "compare":
            result = error_result(str(exc), recipe, args.engine, args.max_temp_bytes)
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print(f"parison: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        if args.command == "compare":
            result = terminal_result("INTERRUPTED", "comparison interrupted by user", recipe, args.engine, args.max_temp_bytes)
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print("parison: interrupted", file=sys.stderr)
        return 130
