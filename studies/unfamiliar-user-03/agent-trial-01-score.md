# Parison 0.2 blind agent-proxy trial 01

Date: 6 October 2026

The participant was a fresh agent with no inherited conversation and was prohibited from reading implementation, tests, versioned docs, Git history or answer keys. This is proxy evidence and does not satisfy a human usability gate.

| Measure | Result |
| --- | --- |
| Used documented source-tree fallback after no installed CLI was found | pass |
| Generated and completed a draft recipe | pass |
| Chose every supplied policy without adding inferred policy | pass |
| Validated the reviewed recipe | pass |
| Interpreted comparison exit `1` as completed FAIL | pass, initial friction noted |
| Verified summary and raw bundles | pass |
| Reported all headline and field counts | pass |
| Identified status keys `0042`, `0137` | pass |
| Identified note key `0088` | pass |
| Identified baseline-only `0077` and candidate-only `9001` | pass |
| Counted 20 tolerated amount differences | pass |
| Interactive use of report controls | not tested; local `file://` browser access was unavailable |
| Could repeat workflow | yes |

Independent scoring verified both manifests, the completed recipe and canonical raw discrepancy sample. The participant's answers match the committed study answer key exactly.

## Observed friction

- The study generator has no real `--help`; it treats that token as an output directory.
- Draft completion still requires manual JSON editing, while subcommand help does not explain allowed recipe values.
- A meaningful comparison FAIL uses process exit `1`, which initially resembles command failure despite the terminal summary.
- The participant's browser would not open the local report, so it inspected HTML/result artifacts directly.
- Filters expose no visible count of currently matching rows.

## Decision

- **GO** for agent-mediated recipe draft, validation, comparison and bundle verification.
- **FIX/RETEST** interactive report filtering: add a visible match count and run the committed counterbalanced protocol with a real browser and human reviewer.
- **STOP** is not warranted; no correctness, privacy or evidence-integrity failure occurred.

## Engineering follow-up

The report now shows live visible-row counts for field-summary and raw-evidence filters. A browser retest against this trial's 200-row dataset confirmed `2 of 3` fields for required differences, `2 of 25` sampled items for the `status` field, and `1 of 25` for `baseline_only`, with no browser console errors. This closes the agent-proxy filtering defect; the human-reviewer gate remains open.
