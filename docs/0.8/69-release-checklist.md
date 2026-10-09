# Parison 0.8 release checklist

Status: **release candidate**

## Contract and implementation

- [x] Multiset-v1 research and normative contract are checked in.
- [x] Recipe-v3 validation and effective policy fingerprinting are implemented.
- [x] Result-v3 comparison, duplicate conservation and hard distinct-row limits are implemented.
- [x] Preflight-v3 reports privacy-safe parse and distinct-row diagnostics.
- [x] Canonical tagged, length-prefixed evidence ordering is implemented.
- [x] Explicit multiset drafting is implemented; mode fallback remains forbidden.

## Evidence and safety

- [x] Cross-format CSV-to-JSON Lines example passes with duplicate rows.
- [x] Summary output contains no row values or canonical row keys.
- [x] Raw evidence is bounded and deterministically ordered.
- [x] Empty inputs, parsing failures, mutation checks and resource limits retain explicit outcomes.
- [x] Add golden encoding vectors for every scalar type, including timestamps and floats.
- [x] Add generated permutation and `PYTHONHASHSEED` determinism checks.
- [x] Record multiset benchmark profiles across duplicate skew and distinct-row ratios.

## CI and release rehearsal

- [x] CI prints recipe-v3, result-v3 and preflight-v3 schemas.
- [x] CI runs multiset preflight, compare and verify smoke commands.
- [x] Local suite passes with optional dependency skips recorded.
- [x] Rebuild clean wheel and source archive from the release candidate.
- [x] Install the wheel in a fresh Python 3.12 environment and run the 0.8 example through verify.
- [ ] Confirm Python and platform matrix, checksums and release assets after tagging.

Do not tag 0.8 until every unchecked item above has evidence attached to the engineering checkpoint.
