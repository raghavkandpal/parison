# Parison 1.6 engineering checkpoint

Date: 18 October 2026

Status: **candidate qualified**

## Delivered capability

- `docs/user-guide.md` is the stable task-oriented entry point for direct
  comparison, suites, schema evolution, reconciliation, dataset evidence,
  rehearsal analysis and authenticated evidence handoff.
- `docs/command-reference.md` contains every command, nested catalog command,
  positional and option registered by the real CLI parser.
- A standard-library generator omits interpreter-dependent usage wrapping and
  produces identical reference bytes on Python 3.11--3.14.
- The local and CI gate rejects stale generated help, malformed guide commands
  and missing repository-local guide links.
- The README and documentation index now route users to maintained current
  pages while released version guides remain unchanged.

## Qualification

- `make check` passes 345 tests with 11 expected optional-Polars skips.
- Exact implementation checkpoint `891f377bf70cc13e3a80e7982c62e4f6ea547d29`
  passed [built-wheel CI run 39100830901](https://github.com/raghavkandpal/parison/actions/runs/39100830901)
  on Python 3.11--3.14, Linux, macOS and Windows; the separate
  [quality run 39100830905](https://github.com/raghavkandpal/parison/actions/runs/39100830905)
  also passed.
- The first checkpoint exposed interpreter-dependent `argparse` usage wrapping
  on Python 3.11 and 3.12. The corrected generator removes only that unstable
  presentation layer while retaining parser-owned argument documentation.

## Preserved boundaries

This slice does not change recipes, schemas, comparison semantics, bundles,
canonical bytes, CLI JSON or exit codes. Generated guidance does not approve
policy, establish extraction truth or authorize cutover.
