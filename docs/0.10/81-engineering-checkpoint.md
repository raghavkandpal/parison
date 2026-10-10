# Parison 0.10 engineering checkpoint

Date: 9 October 2026

Candidate commit: `d521941d6c0a7dff03cac4ffc44ebd9eeecafafe`

## Verification

- 165 local tests pass with six optional dependency skips.
- The candidate [GitHub Actions run](https://github.com/raghavkandpal/parison/actions/runs/37947924646) passes Python 3.11, 3.12, 3.13 and 3.14 on Linux plus Python 3.14 smoke tests on macOS and Windows.
- Every platform validates and runs the locked three-case keyed/aggregate/multiset example, recursively verifies the suite, and safely inspects it.
- A clean Python 3.12 environment installed the candidate wheel and passed version discovery, installed suite-schema output, plan validation, mixed-suite execution, recursive verification and inspection.
- Adversarial coverage includes duplicate and unsafe IDs, unknown fields, policy drift, missing references, case ERROR continuation, interruption, existing output refusal, child tampering, self-consistent parent-summary tampering and injected parent-publication failure cleanup.

## Candidate artifacts

- Wheel SHA-256: `6ccda07f7fecedf59ab6a1680a8e41aa8b6af5ab79d00920b6fc028ae180771a`
- Source archive SHA-256: `1a875a431d4476319b974462a1eedeaba3db4b5e338029847c1d92339fa16259`

These hashes identify the candidate rehearsal artifacts. Release assets must be rebuilt from the tagged commit and published with their own checksums.

## Published release

The final commit [passed the full matrix](https://github.com/raghavkandpal/parison/actions/runs/37948079699), was tagged `0.10.0`, and was published with these verified assets:

- Wheel SHA-256: `1d57b2f7f08fe869f8dc9ed436d6c1cac6cedf48338eecf9b0d36940d4c4f21b`
- Source archive SHA-256: `97051c1e8951b07784a2b68fc304b83748529689c02333b82305970d58efa9e8`

Both assets were downloaded from the GitHub release, checked against the published checksum file, and the downloaded wheel repeated the Python 3.12 mixed-suite workflow.

## Scope decision

0.10 freezes sequential local suite orchestration, suite-v1 plan/result/manifest schemas, atomic parent publication, recursive child verification and summary-safe inspection. Parallelism, retries, resume, discovery, per-case limits, suite-wide evidence export and cross-suite history remain deferred.
