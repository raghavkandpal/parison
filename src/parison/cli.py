from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import OUTCOME_CODES, ParisonError, compare, error_result, load_recipe, publish, terminal_result, verify_bundle


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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="parison", description="Compare data-pipeline outputs deterministically")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-recipe", help="validate a JSON recipe")
    validate.add_argument("recipe")
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
