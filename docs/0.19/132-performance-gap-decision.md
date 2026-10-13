# Performance-gap decision for 1.0

Date: 13 October 2026

Status: **recommended acceptance pending maintainer decision**

## Decision proposed

Accept the remaining documented performance gaps for 1.0. Do not add cross-platform benchmarks or a raw-sensitivity capacity claim unless a concrete deployment requires them.

## Evidence now available

The [machine-qualified performance envelope](127-performance-envelope.md) records accuracy-verified keyed memory profiles through 250,000 rows, keyed SQLite and multiset memory/SQLite profiles through 100,000 rows, mixed-mode concurrent suites with nine 100,000-row cases, and suite orchestration through 100 cases.

Aggregate coverage has now been repeated at 100,000 rows on arm64 macOS with Python 3.14.7 and Parison 0.18.0:

| Profile | Groups | Median elapsed | Median peak RSS | Accuracy |
| --- | ---: | ---: | ---: | --- |
| global | 1 | 3.94 s | 36.0 MB | verified PASS |
| low cardinality | 10 | 4.12 s | 36.0 MB | verified PASS |
| high cardinality | 100,000 | 7.33 s | 484.8 MB | verified PASS |

The exact result is checked in at [the aggregate 100k benchmark](../../benchmarks/results-2026-10-13-aggregate-100k.json). Values are medians of three fresh subprocess runs after one warm-up and remain machine-specific evidence.

## Gaps accepted if approved

### Raw-sensitivity performance

Raw evidence is an optional diagnostic mode, not the default gate. Output sampling is bounded, its disclosure risk is explicit, and correctness is tested. Without a representative consumer and discrepancy distribution, a single raw benchmark would encourage a misleading capacity claim. Users selecting raw sensitivity should qualify it with their own protected data shape.

### Linux and Windows performance

Installed-wheel functional behavior is tested on Linux, macOS and Windows. Performance depends on hardware, filesystem, process limits, virtualization and workload shape; one hosted-runner number per operating system would not form a portable guarantee. Parison promises semantic portability, not equal throughput across hosts.

### Suite concurrency repetition

The mixed-mode concurrency record contains one measured run per worker count and demonstrates the time/memory tradeoff, not a throughput promise. Repeated concurrency medians are unnecessary until scheduling performance becomes a release or adoption decision.

## Consequence

If the maintainer accepts this decision, the performance gate for 1.0 is complete with the gaps kept visible in the user guide and readiness checklist. New measurements should answer a concrete deployment question rather than expand a generic benchmark matrix.
