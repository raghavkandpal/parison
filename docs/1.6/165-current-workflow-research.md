# Current workflow and command-reference research

Date: 18 October 2026

Status: **accepted implementation direction**

## Question

What is the largest coherent adoption improvement Parison can ship from the
evidence already in the repository without expanding its trust boundary or
inventing demand for a new data format?

## Evidence

The post-1.0 direction requires adoption evidence before a new parser or a
generic extraction-receipt contract. Three unfamiliar-user proxy studies now
exercise recipe authoring, comparison, verification and investigation. They
show that the workflow is repeatable, while also recording friction around
discovering allowed values, interpreting comparison exit 1 and finding the
right artifact for investigation.

The public documentation has acquired a second, directly observable problem:
the authoritative consolidated guide is frozen at 0.19, while the supported
1.2--1.5 workflows live in separate version folders. The root README still
contains stale status and installation examples. A user must reconstruct the
current workflow from historical release records even though the CLI already
contains the complete command grammar.

Python's standard-library `argparse` owns Parison's command grammar and
provides `format_help()` for the registered parser. Therefore an exhaustive
reference can be rendered from the parser without a new dependency or a
second command model. JSON Schema annotations remain authoring assistance,
not validation behavior; schema-description improvements can follow only when
a concrete authoring gap is identified.

Primary sources, accessed 18 October 2026:

- [Python `argparse` reference](https://docs.python.org/3.12/library/argparse.html)
- [JSON Schema annotations](https://json-schema.org/understanding-json-schema/reference/annotations)

Repository evidence:

- [post-1.0 product direction](../0.20/134-post-1.0-direction-research.md)
- [0.19 consolidated guide](../0.19/131-user-guide.md)
- `studies/unfamiliar-user-01` through `studies/unfamiliar-user-03`

## Decision

Ship one 1.6 adoption slice with three inseparable parts:

1. a stable, task-oriented current guide covering the complete 1.x workflow;
2. an exhaustive command reference generated from the real parser, including
   nested catalog commands; and
3. drift checks for the generated reference and every repository-local command
   example in the current guide.

The guide explains decisions, trust boundaries and task sequence. The
generated reference owns syntax and options. Historical version guides remain
unchanged as release records.

## Design consequences

- Keep the stable entry points at `docs/user-guide.md` and
  `docs/command-reference.md`; future releases update them in place.
- Generate reference text only from the in-process parser. Do not scrape shell
  output, add a documentation framework or publish a machine-stable CLI schema.
- Make generation deterministic across supported Python versions by setting
  the parser program name and normalizing only trailing whitespace.
- Check the generated file in so installed-package or website tooling is not
  required to read it.
- Test documented commands against repository examples without executing
  expensive comparisons in the documentation check; existing focused tests
  continue to own runtime semantics.

## Threats

- `argparse` wrapping can vary with interpreter behavior. Fix the formatter
  width for reference generation and qualify it on Python 3.11--3.14.
- Generated syntax can be exhaustive but still fail to explain policy choices.
  Keep task guidance hand-written and explicitly separate.
- Copy-paste tests can become a second CLI parser. Limit them to checking that
  command names and repository paths resolve; let `argparse` and existing tests
  validate options.
- A stable current guide can accidentally rewrite historical guarantees. Link
  frozen contracts for normative details and edit no released contract.

## Non-goals

- changing comparison, evidence or exit-code semantics;
- adding interactive help, a web site or a documentation dependency;
- treating generated examples or schema annotations as policy approval;
- removing historical guides or contracts;
- adding a parser, connector or receipt interpretation.

## Completion gate

The slice is complete when one stable guide covers initialization, direct
comparison, suites, reconciliation, dataset evidence, rehearsal analysis and
authenticated handoff; every current CLI command appears in a deterministic
generated reference; drift fails a focused test; all linked repository-local
examples exist; the full check passes; and built wheels pass Python 3.11--3.14
on Linux, macOS and Windows before release.
