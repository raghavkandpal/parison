# 0.2 human-results checklist

Use synthetic or user-controlled data only. Do not commit production data, credentials or raw-sensitive reports.

- [ ] **Recipe authoring — person 1:** have an unfamiliar user run `draft-recipe`, complete every review choice, validate the recipe and run a comparison. Record completion, elapsed time, help needed, mistakes and whether drafting was easier than editing the example JSON.
- [ ] **Recipe authoring — person 2:** repeat independently with a second unfamiliar user and record the same results.
- [ ] **Report investigation:** run the counterbalanced [filtering protocol](../../studies/report-filtering-01/protocol.md) with an unfamiliar human. Record both timings, answers, corrections, controls used and confusion. Keep filtering only if answers are correct and the filtered condition is faster without help.
- [ ] **Real repeat use:** have one target user run the same reviewed recipe on a later candidate. Record whether the run and bundle verification completed, what help was needed and whether they would use it again.
- [ ] **Release decision:** review all four records and write a dated **GO**, **FIX** or **STOP** decision. A GO must confirm that no policy was inferred or self-approved and that the evidence bundle was understandable.
- [ ] **After GO only:** rebuild from the chosen commit in a clean environment, inspect the wheel and source archive, repeat the installed-wheel smoke test, then tag and publish `0.2.0`.

Store only consented, non-sensitive observations in `studies/`; keep private datasets and raw artifacts outside the repository.
