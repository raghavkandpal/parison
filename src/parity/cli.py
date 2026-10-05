from __future__ import annotations

import argparse
import json
import sys

from .core import OUTCOME_CODES, ParityError, compare, error_result, load_recipe, publish, verify_bundle


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="parity", description="Compare data-pipeline outputs deterministically")
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
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    recipe = None
    try:
        if args.command == "verify":
            verify_bundle(args.run_directory)
            print("valid")
            return 0
        recipe = load_recipe(args.recipe)
        if args.command == "validate-recipe":
            print("valid")
            return 0
        result = compare(args.recipe, args.baseline, args.candidate, args.sample_limit)
        publish(args.output, result, recipe)
        print(json.dumps({"outcome": result["outcome"], "output": args.output}))
        return OUTCOME_CODES[result["outcome"]]
    except ParityError as exc:
        if args.command == "compare":
            try:
                publish(args.output, error_result(str(exc)), recipe)
            except ParityError:
                pass
        print(f"parity: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
