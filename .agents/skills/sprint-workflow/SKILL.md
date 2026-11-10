---
name: sprint-workflow
description: Plan an idea into a product spec, implement one selected sprint, or independently evaluate its acceptance criteria using the planner, generator and evaluator workflow. Use when this staged workflow is requested.
---

# Planner → generator → evaluator

Use the requested phase: `plan`, `generate`, `evaluate`, or `run` for one selected
sprint's implementation/evaluation loop. Read only its role prompt:

- `plan`: [planner.md](references/planner.md).
- `generate`: [generator.md](references/generator.md).
- `evaluate`: [evaluator.md](references/evaluator.md).
- `run`: generator, then a fresh independent evaluator; return evaluator defects
  to the generator before new work. Run roles sequentially; one writer at a time.

Identify the spec path and sprint ID from the request or existing task context.
If either is ambiguous, resolve it before implementation. Planning alone does
not authorize implementation. A `run` request covers only the selected sprint;
stop after it passes, is blocked, or reaches two fix-and-reevaluate rounds.
At that limit, report remaining defects and evidence rather than starting another
sprint or claiming success. The user can explicitly authorize more rounds.

Use native subagents for independent evaluation when available. Give the
evaluator the frozen spec, sprint ID, exact commit, launch/test instructions and
raw test resources, not the generator's conclusions. If independent execution
is unavailable, report that limitation; a self-check is not independent clearance.

Handoff each phase with the spec path/hash, sprint ID, commit (or planning-only),
criteria IDs, evidence, unresolved decisions and next phase. Persist the concise
result in the task's existing versioned note; changing state goes in
docs/CURRENT.md. Follow repository instructions for branch, tests and delivery.
The workflow verdict measures sprint acceptance, not approval of a user's data
policy, migration or cutover, and does not replace review or CI gates.

These Markdown roles guide behavior; they do not restrict actual tool permissions.
No model, MCP server, sandbox setting or dependency is configured by this skill.
