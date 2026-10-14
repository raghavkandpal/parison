# Performance-gap decision for 1.0

Date: 13 October 2026

Status: **accepted with targeted evidence added**

## Decision

Close the actionable raw-sensitivity and concurrency-repeat gaps with machine-qualified measurements. Accept cross-platform throughput as deployment-specific rather than treating hosted CI numbers as a portable performance guarantee.

## Evidence now available

The [machine-qualified performance envelope](127-performance-envelope.md) records accuracy-verified keyed memory profiles through 250,000 rows, keyed SQLite and multiset memory/SQLite profiles through 100,000 rows, mixed-mode concurrent suites with nine 100,000-row cases, and suite orchestration through 100 cases.

Aggregate coverage has now been repeated at 100,000 rows on arm64 macOS with Python 3.14.7 and Parison 0.18.0:

| Profile | Groups | Median elapsed | Median peak RSS | Accuracy |
| --- | ---: | ---: | ---: | --- |
| global | 1 | 3.94 s | 36.0 MB | verified PASS |
| low cardinality | 10 | 4.12 s | 36.0 MB | verified PASS |
| high cardinality | 100,000 | 7.33 s | 484.8 MB | verified PASS |

The exact result is checked in at [the aggregate 100k benchmark](../../benchmarks/results-2026-10-13-aggregate-100k.json). Values are medians of three fresh subprocess runs after one warm-up and remain machine-specific evidence.

Raw high-mismatch profiles now cover 10,000 and 100,000 rows with sample limits 10, 100 and 1,000. At 100,000 rows, raw mode recorded about 996 MB median peak RSS versus 288 MB for summary mode; sample-limit growth primarily affected result size. See [raw high-mismatch evidence](../../benchmarks/results-2026-10-13-raw-high-mismatch.json).

The nine-case mixed keyed/aggregate/multiset suite now has three timed runs after a warm-up for each worker count. Medians were 11.05 s, 6.55 s and 4.07 s for one, two and four workers. See [repeated concurrency evidence](../../benchmarks/results-2026-10-13-suite-concurrency-repeated.json).

## Accepted boundary

Installed-wheel functional behavior is tested on Linux, macOS and Windows. Performance depends on hardware, filesystem, process limits, virtualization and workload shape; one hosted-runner number per operating system would not form a portable guarantee. Parison promises semantic portability, not equal throughput across hosts.

## Consequence

The performance gate for 1.0 is complete. New measurements should answer a concrete deployment question rather than expand a generic benchmark matrix.
