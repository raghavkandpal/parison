from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import OUTCOME_CODES, ParisonError, compare, draft_recipe, error_result, load_recipe, publish, terminal_result, verify_bundle


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
    draft = commands.add_parser(
        "draft-recipe",
        help="draft an intentionally incomplete JSON recipe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Review the generated JSON before comparison:
  choose keys; fill scope snapshot, cutoff, completeness='full' and expected_empty;
  choose nulls_equal; replace each REVIEW_REQUIRED type with string, integer,
  decimal, float, boolean, date or timestamp; explain every excluded column.
Then run: parison validate-recipe DRAFT.json

Numeric comparison requires integer, decimal or float plus an explicit
symmetric-v1 tolerance. Drafting never approves inferred policy.""",
    )
    draft.add_argument("--baseline", required=True)
    draft.add_argument("--candidate", required=True)
    draft.add_argument("--output", required=True)
    draft.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    verify = commands.add_parser("verify", help="verify a published run bundle")
    verify.add_argument("run_directory")
    run = commands.add_parser("compare", help="compare baseline and candidate files")
    run.add_argument("--recipe", required=True)
    run.add_argument("--baseline", required=True)
    run.add_argument("--candidate", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--sample-limit", type=int, default=100, help="maximum raw field differences to publish")
    run.add_argument("--max-input-bytes", type=int, default=1_000_000_000, help="maximum combined input size (default: 1 GB)")
    run.add_argument("--max-rows", type=int, default=5_000_000, help="maximum rows in either input (default: 5 million)")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    recipe = None
    try:
        if args.command == "verify":
            manifest = verify_bundle(args.run_directory)
            print("valid")
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
            print(f"Drafted unresolved recipe: {args.output}", file=sys.stderr)
            print("Next: resolve every review choice, then run parison validate-recipe on the draft.", file=sys.stderr)
            return 0
        recipe = load_recipe(args.recipe)
        if args.command == "validate-recipe":
            print("valid")
            print(f"Validated recipe: {args.recipe}", file=sys.stderr)
            return 0
        result = compare(args.recipe, args.baseline, args.candidate, args.sample_limit, args.max_input_bytes, args.max_rows)
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
