# Parison 0.10 release checklist

Status: **released**

## Suite contract and implementation

- [x] Suite-v1 research, roadmap and normative contract are checked in.
- [x] Strict plan, result and parent-manifest schemas are installed.
- [x] Relative references, unique portable IDs and optional policy locks are validated.
- [x] Cases run sequentially through existing comparison and child-publication paths.
- [x] Outcome precedence and continued execution are tested.
- [x] Parent publication is atomic and refuses existing destinations.
- [x] Verification recursively checks child integrity and parent/child semantic agreement.
- [x] Inspection remains summary-safe and parent evidence export is rejected.

## Evidence and release gates

- [x] Mixed keyed, aggregate and multiset example passes locally.
- [x] Python 3.11–3.14, macOS and Windows suite smoke passes.
- [x] Add self-consistent parent-tampering and publication-failure tests.
- [x] Build and install a clean wheel, then run the mixed-suite workflow.
- [x] Record the candidate matrix and artifact checksums before publication.
- [x] Rebuild from the tag and verify downloaded release assets.

Do not tag 0.10 until every unchecked item has reproducible evidence.

Released as [0.10.0](https://github.com/raghavkandpal/parison/releases/tag/0.10.0) from commit `437068e6edc1ca2c6593d4ce980c87816a153ef3`.
