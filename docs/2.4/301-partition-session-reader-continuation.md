# Session reader continuation after qualified prerequisites

Date: 1 November 2026
Status: structures and read ownership integrated; feature4 incomplete

Continue from current develop after reading AGENTS.md, ignored AGENTS.local.md,
CURRENT, [contract296](296-partition-recovery-contract.md) and this checkpoint.
Start with `make context`. Preserve the owner's existing local spacing edit in
continuation297 if still present; it was excluded from every change below.
No release or reset was consumed. Features1–3 remain integrated (3/10); feature4
is not counted until retained execution and its full adversarial gate qualify.
All ten features must integrate and qualify before a2.4 candidate.

## Qualified integration records

| Gate | Exact reviewed head | Develop integration | Quality | Full wheel/native matrix |
| --- | --- | --- | --- | --- |
| Native metadata change-time correction, PR136 | `5c8fa2f76e8b1206700f2dc19e20522cb8e70294` | `661374e1ecaa91c4ad9730334a73015bc907ab27` | [41284318063](https://github.com/raghavkandpal/parison/actions/runs/41284318063) | [41284315785](https://github.com/raghavkandpal/parison/actions/runs/41284315785) |
| Session structures, PR135 | `aaa9d43fba5f895c19686710f6e9eae52c5d7fe2` | `07b71b2ab41ea23da67ae0a153ae17fb3335a10a` | [41285167137](https://github.com/raghavkandpal/parison/actions/runs/41285167137) | [41285164896](https://github.com/raghavkandpal/parison/actions/runs/41285164896) |
| Read ownership, PR137 | `d58ffdf4bb230c76098710c039c88bdbce58cb87` | `a1ee30874f6ec094118fe6b2c4b9b22a4a078236` | [41287121209](https://github.com/raghavkandpal/parison/actions/runs/41287121209) | [41287118842](https://github.com/raghavkandpal/parison/actions/runs/41287118842) |

Every head above received independent Standards and Spec clearance and passed
Python3.11–3.14 Linux/macOS/Windows built-wheel qualification. Local full suites
passed686,695 and703 tests respectively. Latest ownership checks also pass on
all four local minors; native CI exercises actual Windows locking, directory
change clocks, competing processes and kernel lock release after process kill.

The wire gate originally exposed a pre-existing Windows3.14 namespace-ABA miss.
It was not rerun away: [correction299](299-native-hash-change-time-guard.md) was
isolated, qualified and integrated first, then wire work rebased/requalified.
Hash-only guards now use native FILE_BASIC_INFO.ChangeTime rather than assuming
Python ctime always denotes metadata change. No timestamp is serialized.

Spec review also corrected child policy binding: checkpoint policy_sha256 is
the effective mechanically derived comparison-policy fingerprint, while
identity.derived_recipe_sha256 hashes the derived recipe's file bytes. Those
identities differ. Golden children, journal descriptors and coherent-forgery
examples now bind correctly and compare directly against the exact engine.

## What exists and what does not

Standalone session-v1 journal, checkpoint-v1 child and session-result-v1 schemas
are exposed through existing `parison schema`. The synthetic corpus covers both
legacy physical column orders, hash PASS/FAIL/INCONCLUSIVE, six persisted states,
safe responses, canonical final-file references and structural/semantic/forgery
counterexamples. Fixture directories are collections of examples, not directly
valid session roots: materialize only fixed root members and one selected journal.

`partition_sessions._read_owner` supplies nonblocking exclusive ownership over
an existing regular NUL lock, guarded root/lock identities and a borrowed
directory capability plus recheck callback. It creates or rewrites nothing and
must not be used for mutation/abandonment. Entering it does not recognize a
session, validate metadata/cache contents, grant reuse permission or perform a
comparison. Existing metadata files still need their own pinned read guards.
It is an advisory protocol for cooperating invocations, not authentication.

Public session commands, preview, abandonment and retained discover/resume flags
are still disabled. There is no retained execution or new project script.
Released range-v1/hash-v2 behavior and canonical bytes are unchanged.

## Exact next implementation gate

Implement bounded locked semantic reading and summary-safe preview before any
retained execution. Use the frozen schemas/fixtures as structures, not a runtime
jsonschema dependency. Deepen existing private validators and file guards rather
than introducing another comparator or orchestration layer.

- Acquire ownership first, then pin/revalidate metadata; pre-lock data never
  authorizes reuse. Check fixed root members, regular files, symlink/reparse/
  namespace substitution, byte caps and cumulative session storage. Use actual
  handle metadata consistently; do not mix pathname birth time with handle
  metadata change time or drop ctime checks.
- Parse strict canonical LF journals/children and the canonical no-LF derived
  recipe. Enforce exact JSON tokens in semantic validation: JSON Schema's
  mathematical integer model can accept1.0. Verify plan/profile/N-slot bindings,
  original input descriptors, derived-file versus effective-policy fingerprints,
  engine/runtime descriptor relationships, physical layout, side rows/bytes/SHA,
  staged arithmetic, child classification counts and state transitions.
- Read-only preview must not open original source paths, compare rows, establish
  current-source reuse eligibility or authenticate past execution. Return only
  contract296's query response: not-executed, zero counters, false reused_routing,
  sensitive_retained:true and summary:null, even for a recorded published state.
  Original inputs/recipe/actual package/runtime admission belong to resume later.
- Honor sole committed session.json authority over bounded uncommitted next
  files; never promote a later-looking replacement. Recognize known uncommitted
  child slots and interrupted initializing/abandoning layouts without granting
  reuse authority. Malformed committed metadata and unexpected members reject.
- Keep file descriptor use bounded at N128: holding all2N+3 routing files plus
  N children simultaneously can exceed ordinary descriptor limits. Preserve
  file/directory identity and digest checks while streaming bounded members.
- Keep unsigned-cache assurance honest. A coherent, rehashed classification
  forgery is integrity evidence only; full source-backed verification must still
  reconstruct the derivation and reject it. Do not infer execution truth from
  stronger hashing, ownership or journal validation.

Run focused reader tests, all local checks, independent Standards/Spec review
and exact-head quality/manual full built-wheel native CI before integrating the
reader/preview gate. Then implement separate mutation/abandonment ownership,
retained execution and the complete interruption/forgery/storage gate. Do not
weaken the read-only context to silently permit journal replacement.

Resume ordinary scope sequencing after feature4: feature5 workers depend on
recovery. Preserve released contracts, aliases, local-first boundaries and the
through-v5.0 direction. Check the five-hour usage window and stop near95% with
reviewed pushed work or an explicit handoff; never reset automatically.
