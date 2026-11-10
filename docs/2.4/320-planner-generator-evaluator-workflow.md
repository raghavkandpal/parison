# Planner, generator and evaluator workflow

Date: 10 November 2026
Status: repository skill; no product sprint selected by this setup

The [sprint-workflow skill](../../.agents/skills/sprint-workflow/SKILL.md) packages
the requested planner.md, generator.md and evaluator.md prompts as supporting
role files. One discoverable Codex skill routes to the requested phase, so the
three roles need no extra orchestration framework or unsupported tool metadata.

```text
idea → planner → spec + sprint criteria
selected sprint → generator → local checks + commit → independent evaluator
                                                    ↑                 |
                                                    └── defects ──────┘
all criteria pass → existing review, CI and authorized delivery
```

## Role additions

| Role | Added to the supplied prompt |
| --- | --- |
| Planner | User journeys, non-goals, assumptions, unresolved decisions, dependencies, risks, measurable criterion IDs, negative cases, evidence and rollback; ambitious proposals stay separate from selected scope. |
| Generator | Frozen spec/sprint identity, owner-edit preservation, regression tests, required checks before scoped commit, exact-head handoff and rejection-first fixes; incompatible fixes block rather than weaken the spec. |
| Evaluator | Independent exact-head execution, every criterion reported with evidence, reproducible bug IDs/severity, negative paths, explicit missing-tool blockers, no source/spec fixes and reevaluation after changes. |

Only one sprint is generated at a time. Default `run` stops after success, a
blocker or two fix/evaluation rounds; more rounds need a new user instruction.
Planning alone never starts generation. Evaluation PASS means the selected
criteria were checked, not permission to push, merge or release.

## Usage

Use a known task spec path and a stable sprint ID. Example prompts:

```text
Use $sprint-workflow plan: expand IDEA into a spec and testable sprints. Do not implement.
Use $sprint-workflow generate: implement sprint S1 from PATH/spec.md; commit locally.
Use $sprint-workflow evaluate: check sprint S1 from PATH/spec.md at COMMIT.
Use $sprint-workflow run: implement and independently evaluate only sprint S1 from PATH/spec.md.
```

The entrypoint reads only the needed role. In `run`, native subagents provide a
fresh evaluator when available; roles run sequentially so there is one writer.
The spec path/hash, sprint ID, commit, criteria and evidence connect each handoff.
If independent execution is unavailable, report it rather than claim independence.
New skills may require discovery in a fresh session; the entrypoint can also be
read explicitly by path in the current session.

## Browser capability and enforcement

Playwright MCP is required for UI criteria as requested. No direct Playwright
MCP tool was exposed in this session's tool inventory on 10 November 2026;
the available browser/computer-use tools do not by themselves establish that
integration. UI evaluation is BLOCKED until it is available or the user explicitly
approves an alternative. This setup installs no browser dependency or MCP server.
CLI/evidence criteria use their own runnable checks without a browser requirement.

Role Markdown is advisory, not a sandbox or tool allowlist. Evaluator instructions
forbid implementation/spec edits, but actual permissions come from the harness.
Reuse the existing [development setup](../../CONTRIBUTING.md) and
[CI gates](305-tiered-ci-qualification.md). No Codex security settings change.

## Product status and continuity

This workflow does not select a new product feature or relax contract296. Features
1–3 remain integrated; feature4 needs a new concrete protocol satisfying every
audit314 row. FSRef routes remain rejected by318, profile315 remains unselected,
and destructive session operations/retained execution remain disabled. All ten
features, audit307 and gate317 still precede a 2.4 candidate. Reuse existing
versioned contracts as the spec when appropriate rather than replacing them
with a competing root-level spec.md. Keep changing state in docs/CURRENT.md.

## Validation and rollback

Validate skill metadata with the bundled skill-creator validator and check all
role links. Exercise the role instructions with isolated synthetic scenarios
before claiming a product sprint was evaluated. Record actual outcomes here;
metadata validation alone does not establish workflow behavior or browser access.

Local validation on 10 November 2026:

- Bundled skill metadata validation passed; role/documentation links resolve.
- Documentation suite passed 3 tests; lint, format, generated-reference and
  whitespace checks passed with the project interpreter.
- Before the authorized commit/push/PR/merge, full `make check` passed on Python
  3.14.7: 756 tests ran with 7 skips. Independent review and exact-head CI evidence
  belong in the sprint-workflow PR to develop.
- A fresh evaluator executed a synthetic three-criterion fixture: C1 passed its
  exact command/output check, C2 failed its contradictory output requirement and
  C3 was blocked on missing Playwright MCP and app launch information. Overall
  FAIL was reported, with the criterion conflict classified as a spec problem.
  The synthetic unresolved commit was separately reported as an identity blocker.
- The evaluator made no edits or installations. Its feedback clarified that
  identity/spec blockers cannot yield overall acceptance, while independently
  executable checks should still run. This is evaluator behavior evidence only:
  no product UI test or complete planner/generator product run was performed.

The owner's continuation297 diff was hash-checked unchanged. No product code,
test, package metadata, CI workflow or security setting was modified.

Rollback removes only this skill's directory and its scoped documentation/index
changes through a reviewed revert. Preserve the ignored impeccable skill and the
owner's continuation297 edit. No package, external connection or runtime behavior
is installed by this change.

Official [Build skills](https://learn.chatgpt.com/docs/build-skills), accessed
10 November 2026, describes SKILL.md metadata and supporting references.
Design consequence: one focused skill with three role prompts. Threats: scope
inflation, stale-head evidence, self-certification, criteria weakening and false
browser-pass claims. Non-goals: automatic release, new product scope, another
agent framework and security-policy changes.
