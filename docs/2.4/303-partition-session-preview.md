# Bounded retained-session preview

Date: 1 November 2026
Status: feature4 reader/preview slice; retained execution and abandonment pending

Under [contract296](296-partition-recovery-contract.md), preview reads one
explicit private session without reading original source/recipe paths, running
comparisons or establishing current-source reuse eligibility:

```sh
parison partitions session preview DIRECTORY
# Compatible legacy alias:
parison-partitions session preview DIRECTORY
```

The command takes the existing nonblocking kernel lock, then recognizes the
committed primary journal and the fixed member namespaces. Metadata and cache
files must be regular and non-reparse/non-symlink. Directory capabilities/native
Windows delete-sharing pins bind their names; streamed byte/SHA verification
uses native metadata-change clocks and rechecks every member before returning.
No original pathname is retained, consulted or emitted. No session file is
written, discarded or promoted by preview.

All retained file contents count against the recorded storage budget: the lock,
primary journal, plan, bounded uncommitted next journal, source snapshots,
derived recipe, buckets and committed/uncommitted children. File and metadata
caps apply independently. The plan's cumulative staged-byte cap also applies to
partial routing, using v1 exclusions and v2 all-routing accounting. Spec review
found a missing initializing-state check; its regression failed before the fix. Streaming closes each file before opening the next;
only root/lock and the two nested directory capabilities remain held. A synthetic
N128 test uses a real64-descriptor process limit on POSIX. This is a bounded
resource check, not a capacity or performance promise.

Only a valid committed session.json supplies state. A bounded regular
session.next remains untouched regardless of whether it is truncated or appears
later. Missing/malformed primary metadata rejects even with a valid next file.
Initializing permits bounded partial known routing files. Comparing permits
bounded uncommitted known child slots; neither is reusable work. Missing, damaged
or inconsistent committed files reject outside abandonment.

Abandoning permits known files and whole emptied routing/results directories
to have disappeared. When plan.json has already gone, protocol ceilings and
recorded labels check surviving metadata shape; this does not reconstruct or
validate the original plan digest. If the derived recipe has gone, surviving
committed children still require their journal-bound exact bytes, engine/input
bindings, closed shape and result arithmetic, but unavailable effective-policy
and exact non-key field coverage cannot be re-established. These cleanup-only
recognition paths are restricted to abandoning and grant no reuse authority.
Unexpected members, damaged surviving committed bytes and substitutions still
reject. No deletion command is enabled in this slice.

The initial native matrix exposed a pre-existing ownership namespace miss on
Windows3.13. [Correction304](304-session-namespace-guard.md) was isolated,
independently reviewed and qualified through PR141 before this preview rebased.
The reader now reuses its bounded enumeration helper; native clocks remain.
The failed run is not treated as qualified or rerun away.

## Response and qualification

Successful preview returns the closed session-result-v1 response with action
preview, recorded state, execution_assurance:not-executed, zero work counters,
reused_routing:false, sensitive_retained:true and summary:null. This remains true
for ready/published state; preview neither verifies an output's existence nor
claims PASS. A coherently rehashed unsigned classification forgery can remain
integrity-valid. Full source-backed verification must still reconstruct the
entire derivation and reject forged claims.

Valid queries exit0; invalid/busy/unsafe state exits2 with fixed value-free text
and no JSON. Interruption exits130 with fixed value-free text and no JSON; all
session bytes remain unchanged and ownership releases. Existing ordinary
partition discover/verify responses and canonical bytes are unchanged.

Focused tests cover five profiles/six states, sole primary authority, partial
files, committed damage, unknown members, exact storage and individual caps,
interrupted abandonment, coherent forgery, foreign recorded context, competing
ownership, exception/interrupt release, transient file/directory changes,
symlinks, native Windows junctions and both CLI spellings. Independent review,
full local checks and exact-head quality/manual built-wheel native matrix remain
integration requirements; record results in the PR.

Features1–3 remain integrated (3/10). Feature4 still requires separate mutating
ownership, safe abandonment, retained discover/resume, exact clean/resumed byte
equality and the complete interruption/storage/forgery gate. All ten features
precede any2.4 candidate; worker feature5 follows recovery. No release or reset.
