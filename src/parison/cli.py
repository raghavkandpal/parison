from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import OUTCOME_CODES, ParisonError, assemble_suite, compare, draft_recipe, error_result, explain_recipe, export_evidence, inspect_bundle, list_suite, load_recipe, load_schema, load_suite, publish, run_suite, terminal_result, validate_inputs, verify_bundle


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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="parison", description="Compare data-pipeline outputs deterministically")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-recipe", help="validate a JSON recipe")
    validate.add_argument("recipe")
    explain = commands.add_parser("explain", help="print the effective recipe policy without reading inputs")
    explain.add_argument("recipe")
    schema = commands.add_parser("schema", help="print an installed JSON Schema")
    schema.add_argument("name", choices=("recipe", "recipe-v2", "recipe-v3", "result", "result-v2", "result-v3", "manifest", "preflight", "preflight-v2", "preflight-v3", "suite", "suite-v2", "suite-result", "suite-result-v2", "suite-manifest", "suite-manifest-v2"))
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
    suite_assemble = commands.add_parser("assemble-suite", help="assemble verified suite shards")
    suite_assemble.add_argument("--plan", required=True)
    suite_assemble.add_argument("--input", action="append", required=True)
    suite_assemble.add_argument("--output", required=True)
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
    run.add_argument("--expected-policy-sha256", help="require this effective-policy fingerprint before reading inputs")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    recipe = None
    try:
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
        if args.command == "schema":
            print(json.dumps(load_schema(args.name), indent=2, sort_keys=True))
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
            )
            print(json.dumps({"outcome": result["outcome"], "output": args.output, "cases": result["completed_cases"]}, sort_keys=True))
            subject = "suite shard" if result.get("kind") == "suite-shard" else "suite"
            denominator = result.get("selected_cases", result["total_cases"])
            print(f"Parison {subject} {result['outcome']}: {result['completed_cases']} of {denominator} selected cases published to {args.output}", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
        if args.command == "assemble-suite":
            result = assemble_suite(args.plan, args.input, args.output)
            print(json.dumps({"outcome": result["outcome"], "output": args.output, "cases": result["completed_cases"]}, sort_keys=True))
            print(f"Assembled Parison suite {result['outcome']}: {result['completed_cases']} selected cases published to {args.output}", file=sys.stderr)
            return OUTCOME_CODES[result["outcome"]]
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
        )
        publish(args.output, result, recipe)
        print(json.dumps({"outcome": result["outcome"], "output": args.output}))
        _print_summary(result, args.output)
        return OUTCOME_CODES[result["outcome"]]
    except ParisonError as exc:
        if args.command == "compare":
            result = error_result(str(exc), recipe)
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print(f"parison: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        if args.command == "compare":
            result = terminal_result("INTERRUPTED", "comparison interrupted by user", recipe)
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print("parison: interrupted", file=sys.stderr)
        return 130
