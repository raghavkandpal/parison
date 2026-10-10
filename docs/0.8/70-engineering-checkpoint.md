# Parison 0.8 engineering checkpoint

Date: 9 October 2026

The 0.8 candidate implements the third comparison proof mode: exact keyless, duplicate-aware multiset reconciliation.

## Verification

- 153 local tests pass with six optional dependency skips.
- Golden scalar encoding tests cover Boolean, integer, decimal, float, date, timestamp and string tags.
- Raw evidence remains stable under row reordering and is ordered by typed length-prefixed encoding bytes.
- Cross-format CSV-to-JSON Lines example passes with duplicate rows.
- Python 3.12 fresh-wheel smoke passes version discovery, multiset record preflight, compare, publish and verify.

## Reference measurements

Fresh-process local measurements on arm64 macOS, Python 3.12.5, source tree:

| Rows | Distinct rows | Outcome | Elapsed seconds |
| ---: | ---: | --- | ---: |
| 1,000 | 10 | PASS | 0.005415 |
| 1,000 | 500 | PASS | 0.004956 |
| 10,000 | 100 | PASS | 0.038993 |

These are engineering measurements, not supported scale claims. The implementation remains bounded by the configured distinct-row limit and does not claim spill-to-disk support.

## Candidate artifacts

- Wheel SHA-256: `187b127d6a4b1944968049c39c6bcb3ca669e0f7147527944f1b441c59bb15ca`
- Source archive SHA-256: `7466b5897d26842f206d1cd368769c23a99afe412c9e3866e936243857596aad`

The artifacts were built from the 0.8.0 candidate and installed/tested in a fresh Python 3.12 environment. Final release assets must be rebuilt from the tagged commit.
