# Workbench Plans unfamiliar-agent proxy task

Use a fresh browser context with no implementation history. Before completing
the task, consult only this page and the Workbench UI at the supplied local URL.
Do not read repository source, tests, Git history, design notes or answer keys.
All data are synthetic. Do not submit a Run or stop the shared preview host.

1. Open `study.json` in Plans. Explain whether loading and validation approve
   the policy. Find the effective delimiter and normalization settings that
   were omitted from the imported JSON.
2. Use the policy controls to change the snapshot to `plans-trial`. Keep the
   exact string key `id`, the existing cutoff, full nonempty scope and summary
   output. Change `amount` to numeric comparison with a symmetric absolute
   tolerance of `0.10` and relative tolerance `0`, retaining decimal scale 2.
3. Validate the current draft and download it. Report whether validation or
   download establishes approval, and whether the original file was saved.
4. Try `../outside.csv` as baseline and `candidate.csv` as candidate. Recover by
   choosing `baseline.csv` and `candidate.csv`, then copy the locations to Run.
   Check which fields were copied and whether execution has begun.
5. Return to Plans, clear it, and explain what happened to the original recipe
   and any downloaded draft.

Report observed outcomes, confusion, recovery and a go/fix/stop decision.
Identify any unsupported conclusion. This is an agent proxy trial, not a human
participant study. After recording the trial, the Spec reviewer may inspect the
implementation against the feature contract.
