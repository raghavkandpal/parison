# Unfamiliar-user test 01

## Purpose

Determine whether an engineer who has not seen Parison can install it, run a comparison, interpret `FAIL`, `INCONCLUSIVE` and tolerance behavior correctly, and preserve verifiable evidence without coaching.

This is a usability test, not a product demonstration. Do not explain recipes, outcomes or report fields unless the participant asks. Record every intervention.

The expected workflow may be agent-mediated: an engineer delegates installation, execution and first-pass interpretation to a coding agent, then reviews the recipe, evidence and recommendation. Evaluate agent execution and human acceptance separately; neither should be presented as evidence for the other.

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

Do not count the maintainer rehearsal below toward the release gate. For direct use, advance after at least four of five unfamiliar engineers complete the core task unassisted and at least three would reuse Parison. For agent-mediated use, require successful execution by an unfamiliar agent plus human review that confirms the recommendation is understandable, trustworthy and preferable to the reviewer’s alternative workflow.

## Maintainer rehearsal — 6 October 2026

Environment: clean Git archive, fresh Python 3.14 virtual environment on arm64 macOS, editable installation following the README, no optional Parquet dependency.

Observed:

- Installation, recipe validation, comparison and bundle verification all completed successfully.
- The example returned `PASS` with one within-tolerance record, as expected.
- The comparison command printed only the outcome and output directory. A participant must discover and open `report.html` themselves; the real session should test whether that is sufficient.
- `validate-recipe` and `verify` both printed only `valid`, which provides little orientation but did not block the rehearsal.
- `docs/04-workflows-and-usability.md` still described all flows as proposed and said no executable product existed, despite the implemented vertical slice.

Decision: **FIX before counting a human session.** Correct the stale workflow statement and use the participant pack in a genuine unfamiliar-user session. Do not build a UI or expand the engine based on this rehearsal alone.

## Agent-mediated workflow trial 01 — 6 October 2026

This session used a fresh agent with no conversation history. It was told not to read this answer key and initially received only the repository README and participant task. Because the intended user may delegate this work to an agent, this is direct evidence that Parison is agent-legible: its CLI contract, artifacts and semantics supported correct independent execution and interpretation. It does not establish the separate human-review half of that workflow.

Environment: fresh Python 3.14 temporary environment and output directory. No wheel was supplied, so the agent ran the checkout with `PYTHONPATH=src`; this installation deviation must be avoided in the human session.

| Measure | Result |
| --- | --- |
| Installed and produced first result without help | deviation: no wheel supplied; first result completed without help |
| Correctly explained offsetting row errors | pass |
| Correctly explained duplicate identity | pass |
| Correctly explained tolerance PASS | pass |
| Found and used the HTML report | pass |
| Verified and identified the evidence bundle | pass |
| Help requests | would have requested the missing wheel |
| Blocking usability findings | none after the execution-path deviation |
| Would use Parison for a second comparison | yes |

Observed:

- The agent correctly classified the three runs as `FAIL` (exit 1), `INCONCLUSIVE` (exit 3) and `PASS` (exit 0).
- It explained that unchanged aggregate totals hid two keyed differences, duplicate identity prevented an equivalence decision, and a tolerance PASS did not make the files identical.
- It chose `report.html` for initial investigation, retained all four bundle files and noted that raw-sensitivity artifacts require protection.
- The only interpretive pause was `discrepancy_count: 2` in a passing result; `matched_within_tolerance` and the sample classification resolved it.
- Its stated fallback was a custom keyed Python/pandas merge with duplicate checks, explicit tolerance and manually preserved output.

Decision: **GO for the agent-execution half of an agent-mediated workflow.** The unfamiliar agent completed the core task and produced a correct, reviewable recommendation. Next, give its result bundle and recommendation to an unfamiliar engineer and test whether they can approve or challenge it without rerunning the work. Supply a built wheel in future execution trials. Release validation remains blocked until the human-review half is recorded.
