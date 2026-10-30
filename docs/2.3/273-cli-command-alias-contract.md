# 2.3 additive CLI command aliases

Date: 30 October 2026
Status: frozen before implementation; additive aliases integrated through PR #109

## Decision

The 2.3 CLI adds a task-oriented path beneath the existing `parison` command:

| New command | Shipped equivalent |
| --- | --- |
| `parison postgres table --plan P --output O` | `parison-postgres --plan P --output O` |
| `parison postgres pair --plan P --output O` | `parison-postgres-pair --plan P --output O` |
| `parison partitions discover ...` | `parison-partitions discover ...` |
| `parison partitions verify ...` | `parison-partitions verify ...` |
| `parison partitions investigate ...` | `parison-partitions investigate ...` |
| `parison partitions verify-investigation ...` | `parison-partitions verify-investigation ...` |
| `parison rehearsal run ...` | `parison-rehearsal run ...` |
| `parison rehearsal verify ...` | `parison-rehearsal verify ...` |
| `parison dossier create|verify ...` | Already under `parison`; unchanged |

The first four shipped project scripts remain installed and retain their
argument parsing, exit codes, stdout JSON, runtime error text, and `--help`
behavior. New paths call the same underlying command implementation with the
same arguments. New help and parser usage name the new command path; malformed
arguments return a generic value-free error and exit code 2. The new root and namespace help and generated
command reference list the task paths. No default, recipe, schema, bundle, canonical byte,
verification or policy meaning changes. A future retirement of aliases needs
a separately versioned breaking decision and migration window.

This is a command-name migration within 2.3, not a seventh feature. It follows
the owner-requested [consolidation follow-up](270-cli-consolidation-followup.md)
and does not weaken the six-feature release boundary.

## Gate

Freeze exact old/new equivalence fixtures for each command path: accepted
arguments, stdout JSON, exit code and runtime error stderr match. Check malformed
arguments and `--help` for every namespace. Run narrow CLI tests and
`make check`, independent Standards/Spec review, exact-head quality CI and the
full built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix before merging
to `develop`. Then rerun the combined 2.3 candidate qualification on the new
head. Do not describe command aliases as policy approval or migration cutover.
