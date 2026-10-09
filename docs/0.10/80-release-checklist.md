# Parison 0.10 release checklist

Status: **in progress**

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
- [ ] Add self-consistent parent-tampering and publication-failure tests.
- [ ] Build and install a clean wheel, then run the mixed-suite workflow.
- [ ] Record final matrix, artifact checksums and downloaded-release verification.

Do not tag 0.10 until every unchecked item has reproducible evidence.
