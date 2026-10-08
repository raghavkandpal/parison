from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import OUTCOME_CODES, ParisonError, compare, draft_recipe, error_result, explain_recipe, load_recipe, load_schema, publish, terminal_result, validate_inputs, verify_bundle


def _print_summary(result: dict, output: str) -> None:
    counts = result["counts"]
    print(f"Parison {result['outcome']} (complete: {str(result['complete']).lower()})", file=sys.stderr)
    if counts:
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
    schema.add_argument("name", choices=("recipe", "result", "manifest"))
    inputs = commands.add_parser("validate-inputs", help="validate input schemas against a recipe")
    inputs.add_argument("--recipe", required=True)
    inputs.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    inputs.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    inputs.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
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
symmetric-v1 tolerance. Suggestions are starting points, not approved policy.""",
    )
    draft.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    draft.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    draft.add_argument("--output", required=True)
    draft.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    verify = commands.add_parser("verify", help="verify a published run bundle")
    verify.add_argument("run_directory")
    verify.add_argument("--json", action="store_true", help="print verified manifest metadata as JSON")
    run = commands.add_parser("compare", help="compare baseline and candidate files")
    run.add_argument("--recipe", required=True)
    run.add_argument("--baseline", required=True, help="baseline file, SQLite locator or partition directory")
    run.add_argument("--candidate", required=True, help="candidate file, SQLite locator or partition directory")
    run.add_argument("--output", required=True)
    run.add_argument("--sample-limit", type=int, default=100, help="maximum raw field differences to publish")
    run.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    run.add_argument("--max-rows", type=int, default=5_000_000, help="maximum rows in either input (default: 5 million)")
    run.add_argument("--expected-policy-sha256", help="require this effective-policy fingerprint before reading inputs")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    recipe = None
    try:
        if args.command == "verify":
            manifest = verify_bundle(args.run_directory)
            print(json.dumps(manifest, sort_keys=True) if args.json else "valid")
            print(
                f"Verified bundle integrity: {args.run_directory} "
                f"(recorded outcome: {manifest['outcome']}, sensitivity: {manifest['sensitivity']})",
                file=sys.stderr,
            )
            print("Integrity verification does not change the recorded comparison outcome.", file=sys.stderr)
            return 0
        if args.command == "draft-recipe":
            draft = draft_recipe(args.baseline, args.candidate, args.max_input_bytes)
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
        if args.command == "validate-inputs":
            result = validate_inputs(args.recipe, args.baseline, args.candidate, args.max_input_bytes, args.expected_policy_sha256)
            print(json.dumps(result, sort_keys=True))
            if result["status"] == "valid":
                print(
                    f"Validated input schemas: {result['inputs']['baseline']['columns']} baseline and "
                    f"{result['inputs']['candidate']['columns']} candidate columns.",
                    file=sys.stderr,
                )
                return 0
            print("Input schemas do not match the recipe; inspect the JSON diagnostics.", file=sys.stderr)
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
        )
        publish(args.output, result, recipe)
        print(json.dumps({"outcome": result["outcome"], "output": args.output}))
        _print_summary(result, args.output)
        return OUTCOME_CODES[result["outcome"]]
    except ParisonError as exc:
        if args.command == "compare":
            result = error_result(str(exc))
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print(f"parison: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        if args.command == "compare":
            result = terminal_result("INTERRUPTED", "comparison interrupted by user")
            try:
                publish(args.output, result, recipe)
                _print_summary(result, args.output)
            except ParisonError:
                pass
        print("parison: interrupted", file=sys.stderr)
        return 130
