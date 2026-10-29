# Exact partition discovery budget checkpoint

Date: 29 October 2026
Status: feature 3 local qualification evidence; machine-specific

Machine: Apple M1, 8 logical CPUs, 16 GiB RAM, macOS 27.0.1. Runtime:
Python 3.14.7 in a local virtual environment. Input: two synthetic CSV files
with one integer key and one exact decimal amount. Candidate differs at every
10,000th key. The reviewed five-range plan used `max_input_bytes: 1,000,000,000`,
`max_rows_per_input: 500,000`, `max_rows_per_partition_side: 50,000`,
`max_staged_bytes: 2,000,000,000`, and `max_partition_bytes: 1,000,000,000`.
Each run used a fresh adapter process and a new output path; three
runs per size. The reference engine was released SQLite keyed comparison.

| Total rows per side | Producer wall seconds, three runs | Peak producer RSS bytes, three runs | Peak logical temporary bytes | Final evidence bytes | Reference SQLite wall seconds, three runs | Peak reference RSS bytes, three runs | Reference SQLite temp bytes |
| ---: | --- | --- | ---: | ---: | --- | --- | ---: |
| 100,000 | 1.888, 1.886, 1.884 | 65,355,776; 65,355,776; 65,339,392 | 2,558,432 | 4,810 | 2.991, 2.898, 2.898 | 35,799,040; 35,667,968; 35,749,888 | 29,630,464 |
| 250,000 | 4.661, 4.537, 4.612 | 65,339,392; 65,486,848; 65,437,696 | 6,728,462 | 4,921 | 7.390, 7.359, 7.498 | 36,438,016; 36,585,472; 36,421,632 | 78,442,496 |

The 100k inputs were 1,278,906 baseline and 1,278,926 candidate bytes; the
250k inputs were 3,363,906 baseline and 3,363,956 candidate bytes. Both
producer sizes returned the released reference counts: 100k had 99,990
exact rows and 10 required differences; 250k had 249,975 exact and 25
required differences. Both outcomes were FAIL. The producer read each local
source four times: pre-route digest, routing, post-route digest, and
post-comparison digest. Source-backed verification repeats those four local
passes. The peak logical temporary bytes sum staged CSV files and the 512-byte
mechanically derived recipe. The producer checks CSV bytes as each row is
written. The final evidence directory contains only four JSON
files. The reviewed staged-file rehash was included in these runs. The
partition strategy used more process memory but less temporary disk and wall
time than the SQLite reference on these inputs. The benchmark did not measure
filesystem allocator overhead, a
PostgreSQL source scan, source-backed verifier time, or a complete migration
rehearsal. These observations are not universal capacity claims.

The [small reference corpus](253-partition-discovery-research.md#exploratory-reference-probe)
also matched all eight keyed count fields for low/high difference, 95% skew
and disjoint-key cases. The automated adversarial tests additionally compare
global empty, duplicate-key, complete PASS and substitution cases against
the released SQLite engine. The full acceptance gate still includes the
exact-head wheel matrix and independent review before integration.
