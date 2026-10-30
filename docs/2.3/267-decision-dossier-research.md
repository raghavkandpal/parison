# Portable decision dossier: primary-source research

Date and source access: 29 October 2026
Status: historical feature 6 research checkpoint; contract and implementation later integrated through PR #106

## Question and decision

How can a reviewer move the PostgreSQL 16→18 rehearsal evidence to another
machine, reproduce its derived status without the databases, and see exceptions
and external human sign-off references without mistaking either for Parison
approval? The [six-feature roadmap](246-six-feature-roadmap.md) calls for a
separately versioned, unsigned local artifact with the same summary-safe result
in Workbench and CI. The existing [rehearsal verifier](../../src/parison/postgres_rehearsal.py)
needs both original pair bundles, both recipes, the relationship declaration
and the optional source-owned claim. The consequence is architectural: a
self-contained offline dossier must carry those exact inputs (including private
CSV bytes) alongside the rehearsal artifact, then invoke the existing verifier
on the packaged copies. Merely copying its summary or manifest would establish
only integrity of a past assertion, not reproducibility. This is a reading of
the current repository code, not an external standard.

The dossier should be a private, deterministic package with an independent
closed summary projection. It should preserve the unchanged pair and rehearsal
bundles as nested members rather than inventing a second parser or comparison
engine. A verifier must first validate exact members and digests, then
recursively verify the pair bundles and replay the rehearsal from packaged
inputs. It should recompute status from those checks and compare canonical
bytes, fail closed on missing/mutated/unexpected members, and never use a
network connection or optional PostgreSQL driver. The private package is
sensitive even when its summary is safe to print.

## Primary-source findings and consequences

1. **A digest binds bytes, not the authority of their producer.** The
   [in-toto Statement v1 specification](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md)
   identifies a subject by digest and a predicate by type. Its separate
   [Envelope layer](https://github.com/in-toto/attestation/blob/main/spec/v1/envelope.md)
   handles authentication and serialization. Parison already publishes a
   released unsigned typed Statement; the [existing verifier and export
   functions](../../src/parison/evidence.py) match it to a verified bundle.
   A dossier can reuse that vocabulary and export seam, but it must not imply
   that a digest or an unsigned reference authenticates a database, operator
   or signatory. Do not retrofit released Statement v1/v2 wire bytes; any new
   Statement support needs its own versioned predicate.

2. **Canonicalization is a protocol boundary.** [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)
   explains why repeatable hashes require a defined serialization and rejects
   duplicate JSON names and non-I-JSON values. Parison's released canonical
   encoding is its own compact sorted-key UTF-8 protocol, not RFC 8785 JCS:
   changing it to match JCS could change existing bundle bytes. The dossier
   must pin its exact canonical bytes, reject duplicate names and non-finite
   numbers, and version any semantic or byte change. It should reuse the
   repository's canonical helper and strict readers; do not claim JCS
   compatibility without a separate conformance gate.

3. **Human authorization is a separate accountable decision.** The
   [NIST Risk Management Framework Authorize step](https://csrc.nist.gov/Projects/risk-management/about-rmf/authorize-step)
   makes a senior official's risk decision distinct from the assessment
   package. This is an analogy, not a requirement that Parison or a database
   migration follow federal authorization rules. For Parison it reinforces
   the existing product boundary: a human sign-off reference is an opaque
   pointer or reviewed digest supplied by an operator, not a verified approval
   or automatic cutover gate. The verifier may check its local bytes or strict
   syntax but cannot authenticate the named person, authority or intent.
   Do not expose signatory names, URLs, ticket text or signatures in the
   summary-safe projection.

4. **Existing Workbench and CI seams differ.** The released
   [Workbench handoff](../2.1/223-workbench-handoff-contract.md) first verifies
   a bundle, compares the manifest digest seen at preview with the export-time
   digest, then atomically exports an unsigned Statement or Markdown cover
   sheet. The [CI report path](../../src/parison/evidence.py) emits bounded
   summary-only Markdown or JUnit from verified suite bundles. Feature 6
   should give both surfaces one pure summary projector over the same verified
   dossier result. Workbench must use workspace-relative non-symlink paths and
   a fresh verification on export; CI must not independently interpret private
   files or render exception/sign-off text. No browser-only status logic.

5. **Existing source claims stay source-owned.** Feature 5's
   [rehearsal contract](262-postgresql-rehearsal-contract.md) and
   [integration checkpoint](266-postgresql-rehearsal-integration.md) distinguish
   complete local evaluation, independently reviewed expected counts and an
   opaque cross-instance coordination claim. Packaging may reproduce the
   local outcome, but it cannot elevate a source-owned claim into extraction
   truth. A package with matching omissions and unauthenticated sign-off
   references must still show the original INCONCLUSIVE coverage/coordination
   meaning. The dossier should keep coverage, parity, relationships,
   conservation, exceptions and external references as separate fields and
   never collapse them to a single authorization boolean.

## Proposed contract and adversarial gate

Freeze a strict `decision-dossier-v1` input declaration with exact bound
rehearsal identity, bounded exception entries and bounded external sign-off
references. Prefer enumerated exception classifications and opaque IDs/digests
over free-text descriptions or URLs. An exception is a human review item; it
cannot change PASS, FAIL or INCONCLUSIVE produced by verified evidence.
Absent sign-off is not evidence failure. If the product wants to display
readiness, use a separate descriptive label such as `review_pending` whose
meaning explicitly excludes authorization; keeping just verification status
and reference counts is simpler.

Freeze the full member list and canonical plan/receipt/summary/manifest bytes
before runtime changes. Publish in a private no-overwrite directory through
existing atomic primitives, with sensitive staging cleanup on exceptions and
interrupts. Cap nested file bytes, total bytes and count of exception/reference
entries before copying. Check symlinks and exact membership at every nested
boundary. Verify twice around copying and compare bytes/digests to reject
transient substitution. A source-free verifier must reproduce the same
rehearsal status from contained pairs, recipes, relationship declaration and
claim, then derive the dossier projection from that verified result only.

The adversarial corpus should include: golden portable verification after
removing external source directories and stopping PostgreSQL; PASS, FAIL and
INCONCLUSIVE rehearsals; same-side omission or absent coordination; incomplete
or wrong-bound pair/rehearsal, missing child/partition/recipe/claim, swapped
source/target, changed policy or snapshot; digest-only and digest-recomputed
forgery; path traversal/symlink/membership attacks; transient file replacement
while packaging; oversized nested input; interruption, no-overwrite and
sensitive stage cleanup; exception count/classification substitution; absent,
duplicate, changed and forged sign-off references; and raw names/paths/keys/
values or signatory text in Workbench, CI and CLI summary/error output. Every
derived status must equal a fresh replay of the contained evidence. The
existing feature 5 live gate already tests PostgreSQL acquisition; the dossier
gate must prove portable source-free verification of that real fixture, not
redefine database correctness.

## Threats and non-goals

Threats include a locally forged but digest-consistent package, altered input
after preview, partial copy, symlink escape, accidental publication of private
CSV, status laundering by suppressing a failing component, and a reference
label interpreted as human approval. Hashing detects mutation relative to
reviewed bytes but does not authenticate those bytes. No signing, key custody,
network verification, remote document fetch, approval workflow, policy
generation, migration execution or automatic cutover belongs in feature 6.
The dossier is a transfer and review artifact, not a release of source data to
an untrusted recipient; the operator chooses its custody. Keep all six 2.3
features together before release qualification.
