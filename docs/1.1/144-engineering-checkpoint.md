# Parison 1.1 engineering checkpoint

Date: 15 October 2026

Status: **qualified on `develop`; publication intentionally bundled with 1.2**

## Qualified capability

`semantic-scalar-v1` is an opt-in, fingerprinted projection shared by CSV, TSV, JSON Lines, SQLite and Parquet. Legacy recipes that omit it retain their released parsing and policy identities. The projection remains local, strict and policy-directed; it performs no inference, repair, extraction or remote work.

The compatibility corpus proves:

- every semantic type and null/empty boundary across every supported input format;
- keyed, aggregate and multiset agreement under row-order permutations;
- signed 64-bit bounds, decimal scale and signed zero, finite float encoding, Unicode normalization, timezone-offset equivalence, pre-epoch timestamps and microsecond precision;
- every admitted Parquet integer width and scalar dtype family, including null columns and millisecond/microsecond aware datetimes;
- stable rejection of ambiguous scalar classes, overflow, non-finite numbers, excess precision, timezone-naive timestamps, nested, binary, time, duration, categorical and struct Parquet fields;
- identical pinned `typed-length-prefixed-v1` canonical row bytes across formats.

The corpus exposed and fixed two portability/correctness defects before qualification: Windows installations now receive the first-party IANA timezone fallback, and empty text remains valid for string projection while every non-string empty value fails closed.

## Evidence

- Local `make check` passed **270 tests with 11 optional-Polars skips** on the system interpreter.
- The same projection module passed with optional Polars installed in the alternate Python 3.12 environment.
- Exact commit `0b07f1cd1705020e7fe039089ea8f8f1e98ac47b` passed [built-wheel CI run 38693629443](https://github.com/raghavkandpal/parison/actions/runs/38693629443).
- Every Python 3.11, 3.12, 3.13 and 3.14 Linux lane and both Python 3.14 platform lanes on macOS and Windows ran **270 tests** successfully from the built wheel with pinned Polars 1.44.2.
- The release compatibility corpus and `git diff --check` remained green.

## Release disposition

No 1.1.0 release is cut from this checkpoint. The qualified projection ships as part of the larger active 1.2 arc together with `schema-evolution-v1` and `policy-diff-v1`. This avoids publishing another narrow increment while preserving the exact qualification evidence for the projection boundary.
