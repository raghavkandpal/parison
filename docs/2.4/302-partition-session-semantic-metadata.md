# Recorded session metadata validation

Date: 1 November 2026
Status: private reader prerequisite; feature4 remains incomplete

This deepens the existing session module under [contract296](296-partition-recovery-contract.md)
and [continuation301](301-partition-session-reader-continuation.md). Features1–3
remain integrated (3/10). All ten features precede a2.4 candidate.

The private validators check bounded strict canonical LF journal/child bytes,
exact integer tokens, closed fields, state requirements, plan digest/profile and
slot count, physical column declarations, original descriptors, complete routing
file maps, labels and row/byte arithmetic. Derived recipe bytes are canonical
without LF and bound separately from the effective derived comparison policy.
The original policy fingerprint must match one of the two possible original
expected_empty values; mechanical derivation changes only that value to true.
Child records bind their index, effective policy, recorded engine and routed
inputs, with field coverage, count/discrepancy arithmetic and outcomes checked.

Spec review corrected an abandonment-state gap: retaining a ready manifest hash
also retains every committed result descriptor, even after owned cache files
disappear during cleanup. The focused regression failed before the correction.

Recorded well-formed foreign package/runtime identities remain readable. These
checks neither compare them with the running package/runtime nor establish
current-source reuse eligibility. A coherently rehashed classification forgery
still passes claimed arithmetic/bindings: this is unsigned integrity, never
execution authentication. Existing fresh source-backed verification retains its
full reconstruction requirement. No original source or recipe path is opened.

These are pure metadata checks, not a filesystem session recognizer. They must
be called only on bytes pinned after ownership by the next reader gate; invoking
them does not verify retained file contents, member namespaces, total storage or
absence of substitution. Preview, abandonment and retained execution remain
disabled. Released discovery, aliases, schemas and canonical output are unchanged.

## Qualification and next gate

Focused tests exercise all five canonical range/hash profiles and six states,
structural/semantic negatives, exact-token substitutions, malformed canonical
JSON, foreign recorded identities and the coherent-forgery boundary. Targeted
built-wheel platform coverage includes these tests alongside wire/ownership.
Record exact reviewed head and CI in the PR before integration.

Next implement bounded locked filesystem reading and summary-safe preview:
fixed-member recognition, streamed digest/byte checks with bounded descriptors,
namespace/native change-time guards, cumulative storage, primary-over-next
journal authority and interrupted initializing/abandoning layouts. No successful
preview may imply reuse eligibility or claim execution. Follow with separate
mutation/abandonment ownership, retained execution and the complete feature4
gate. Do not count this prerequisite as feature4 completion.
