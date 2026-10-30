# Task-oriented 2.3 commands

Date: 30 October 2026
Status: additive command aliases released in 2.3.0 through PR #109

Use the existing `parison` command for the 2.3 PostgreSQL rehearsal workflow:

```text
parison postgres table --plan table-plan.json --output table-export
parison postgres pair --plan pair-plan.json --output pair-export
parison partitions discover --plan partition-plan.json --recipe recipe.json --baseline baseline.csv --candidate candidate.csv --output discovery
parison partitions investigate --plan investigation-plan.json --discovery discovery --recipe recipe.json --baseline baseline.csv --candidate candidate.csv --output investigation
parison rehearsal run --plan rehearsal-plan.json --baseline baseline-pair --candidate candidate-pair --orders-recipe orders.json --lines-recipe lines.json --reconciliation relationships.json --output rehearsal
parison dossier create --plan dossier-plan.json --rehearsal rehearsal --baseline baseline-pair --candidate candidate-pair --orders-recipe orders.json --lines-recipe lines.json --relationships relationships.json --output dossier
```

Each task also has its existing `verify` path. `parison partitions` retains
`verify-investigation`. See the generated [command reference](../command-reference.md)
for exact arguments and help. `parison-postgres`, `parison-postgres-pair`,
`parison-partitions` and `parison-rehearsal` remain installed aliases with their
existing behavior and exit codes. The [versioned migration contract](273-cli-command-alias-contract.md)
maps every old and new path. A future breaking release must decide any alias
retirement separately.

These commands operate under the same reviewed local-first evidence policies.
They do not approve extraction truth, migration or cutover.
