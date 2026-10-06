# 0.1 human-results checklist

Version 0.1.0 is already published. This checklist records which human decisions supported that release and which direct-human evidence remains open; it does not retroactively gate the existing artifact.

## Decision record

- [x] **Agent execution:** two unfamiliar agents produced correct interpretations and verifiable bundles from separate synthetic tasks.
- [x] **Human review:** a human accepted the second agent's evidence and recommendation without a blocking concern.
- [x] **Release decision:** the maintainer accepted the bounded agent-mediated workflow and published the verified 0.1.0 prerelease.
- [ ] **Direct-human CLI use:** run the [unfamiliar-user protocol](15-unfamiliar-user-test.md) with five unfamiliar engineers. Record completion, time, help, interpretation errors, report discovery and bundle verification; target at least four unassisted core-task completions.
- [ ] **Reuse decision:** record whether at least three of those five participants would use Parison for a second comparison, including why or why not.
- [ ] **Normal-method comparison:** ask each participant what they would otherwise use and whether Parison improved correctness or total effort. Do not claim a usability advantage without this result.
- [ ] **Retrospective decision:** after the sessions, write a dated **GO**, **FIX** or **STOP** decision for continued 0.1 support. Fix correctness, false-PASS or sensitive-data failures immediately; carry nonblocking product changes into a later version.

Use synthetic data only, obtain consent for recordings or quotes, and keep generated bundles outside the repository.

## Code runbook

Give each participant a fresh environment, the published wheel, the README and [`participant-task.md`](../../studies/unfamiliar-user-01/participant-task.md). Do not provide the protocol or answer key.

```sh
python -m venv /tmp/parison-01-human
. /tmp/parison-01-human/bin/activate
python -m pip install \
  https://github.com/raghavkandpal/parison/releases/download/0.1.0/parison-0.1.0-py3-none-any.whl
parison --version

parison compare --recipe studies/unfamiliar-user-01/recipe.json \
  --baseline studies/unfamiliar-user-01/baseline.csv \
  --candidate studies/unfamiliar-user-01/candidate.csv \
  --output /tmp/parison-01-run-fail

parison compare --recipe studies/unfamiliar-user-01/recipe.json \
  --baseline studies/unfamiliar-user-01/baseline.csv \
  --candidate studies/unfamiliar-user-01/candidate-duplicate.csv \
  --output /tmp/parison-01-run-inconclusive

# The participant copies the recipe, changes only absolute tolerance to 1.00,
# and uses that copy for a new run of the original candidate.
parison compare --recipe /tmp/parison-01-tolerant.recipe.json \
  --baseline studies/unfamiliar-user-01/baseline.csv \
  --candidate studies/unfamiliar-user-01/candidate.csv \
  --output /tmp/parison-01-run-pass
parison verify /tmp/parison-01-run-pass
```

Expected process exits are `1` for the first completed comparison, `3` for ambiguous duplicate identity and `0` for the tolerance run. The participant must explain the meanings without seeing the answer key.
