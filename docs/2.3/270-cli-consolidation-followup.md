# CLI consolidation after the portable dossier

Date: 29 October 2026
Status: owner requested completion before the 2.3 release; additive command-alias contract frozen in [273](273-cli-command-alias-contract.md)

The five standalone project entry points added across the 2.3 train now make
installation and documentation harder to navigate:

```text
parison-postgres
parison-postgres-pair
parison-partitions
parison-rehearsal
parison-dossier (proposed, removed before feature 6 release)
```

Feature 6 uses `parison dossier create|verify` under the existing `parison`
command. After the dossier is complete, design one task-oriented `parison`
subcommand structure for PostgreSQL acquisition, partition discovery and
investigation, rehearsal, and dossier work. Consolidate parsing, safe errors,
help and generated command reference; avoid a new project script per feature.

The first four entry points are already shipped contracts. Changing or retiring
them requires a separately versioned CLI migration decision, explicit old/new
command equivalence tests, documentation and a transition path. Preserve their
existing behavior and exit codes while introducing any unified command. Do not
remove an old entry point or reinterpret its JSON merely because a new alias
exists. A future intentional breaking release may retire aliases only under the
repo's compatibility and release process, with a documented replacement and
migration window. Keep recipe, schema and evidence wire compatibility separate
from command-name changes.

This is not a seventh 2.3 feature credit, not part of the dossier's acceptance
gate, and not permission to weaken the six-feature release boundary. The next
concrete step after feature 6 integration is to inventory shipped usage and
freeze a versioned CLI migration contract before editing existing entry points.
