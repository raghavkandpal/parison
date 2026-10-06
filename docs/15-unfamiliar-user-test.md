# Unfamiliar-user test 01

## Purpose

Determine whether an engineer who has not seen Parison can install it, run a comparison, interpret `FAIL`, `INCONCLUSIVE` and tolerance behavior correctly, and preserve verifiable evidence without coaching.

This is a usability test, not a product demonstration. Do not explain recipes, outcomes or report fields unless the participant asks. Record every intervention.

## Participant and setup

- Recruit a data engineer or software engineer who has not used Parison and has not read this repository's design documents.
- Allow 45 minutes.
- Provide a clean machine or temporary environment with Python 3.11 or newer, a built Parison wheel, the repository README and `studies/unfamiliar-user-01/participant-task.md`.
- Do not provide this document: it contains the answer key.
- Ask permission before recording the screen or collecting quotes. Do not use production data.

Start the timer when the participant opens the task. The facilitator may fix machine-specific problems unrelated to Parison, but must record the intervention and exclude that time.

## What to observe

Record timestamps, commands, files opened, incorrect interpretations, help requests and the participant's exact final explanations. In particular, watch whether the participant:

1. includes installation and recipe setup in their assessment of effort;
2. finds the generated HTML report without prompting;
3. understands that equal totals can hide row-level errors;
4. understands that duplicate keys make identity ambiguous rather than proving a mismatch;
5. understands that `PASS` with within-tolerance differences does not mean byte-for-byte equality;
6. verifies the result bundle and can identify the files that should be retained.

## Answer key

- The initial candidate must return `FAIL`. Orders `001` and `002` differ by `+1.00` and `-1.00`; their aggregate total is unchanged, but both keyed records are wrong under the initial `0.01` absolute tolerance.
- The duplicate candidate must return `INCONCLUSIVE`, because key `001` occurs twice and therefore cannot identify one record on that side.
- After changing the absolute tolerance to `1.00`, the original candidate must return `PASS` with two within-tolerance records. The files are still different, so an explanation that they are "identical" is incorrect.
- A completed bundle contains `result.json`, `effective-recipe.json`, `report.html` and `manifest.json`; `parison verify` should report it as valid.

## Scorecard

| Measure | Result |
| --- | --- |
| Installed and produced first result without help | pass / fail; minutes: |
| Correctly explained offsetting row errors | pass / fail |
| Correctly explained duplicate identity | pass / fail |
| Correctly explained tolerance PASS | pass / fail |
| Found and used the HTML report | pass / fail |
| Verified and identified the evidence bundle | pass / fail |
| Help requests | count and details: |
| Blocking usability findings | list: |
| Would use Parison for a second comparison | yes / no / unsure; why: |

Core-task success requires the first six measures to pass without outcome-related coaching.

## Decision rule

- **GO:** core task succeeds, there are no security/correctness concerns, and only cosmetic or optional improvements are observed.
- **FIX:** the task is completable, but setup, terminology, report discovery or interpretation causes a failure or material help request. Fix only the observed blockers, then repeat with a new participant.
- **STOP:** the participant cannot obtain trustworthy evidence, the workflow encourages a false conclusion, or the current approach is clearly worse than their normal method without a narrow fix.

Do not count the maintainer rehearsal below toward the release gate. After five genuine sessions, advance only if at least four participants complete the core task unassisted and at least three say they would use Parison for a second comparison.

## Maintainer rehearsal — 6 October 2026

Environment: clean Git archive, fresh Python 3.14 virtual environment on arm64 macOS, editable installation following the README, no optional Parquet dependency.

Observed:

- Installation, recipe validation, comparison and bundle verification all completed successfully.
- The example returned `PASS` with one within-tolerance record, as expected.
- The comparison command printed only the outcome and output directory. A participant must discover and open `report.html` themselves; the real session should test whether that is sufficient.
- `validate-recipe` and `verify` both printed only `valid`, which provides little orientation but did not block the rehearsal.
- `docs/04-workflows-and-usability.md` still described all flows as proposed and said no executable product existed, despite the implemented vertical slice.

Decision: **FIX before counting a human session.** Correct the stale workflow statement and use the participant pack in a genuine unfamiliar-user session. Do not build a UI or expand the engine based on this rehearsal alone.
