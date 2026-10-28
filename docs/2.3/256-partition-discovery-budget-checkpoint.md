# Exact partition discovery budget checkpoint

Date: 28 October 2026  
Status: feature 3 local qualification evidence; machine-specific

Machine: Apple M1, 8 logical CPUs, 16 GiB RAM, macOS 27.0.1. Runtime:
Python 3.14.7 in a local virtual environment. Input: two synthetic CSV files
with one integer key and one exact decimal amount. Candidate differs at every
10,000th key. The reviewed five-range plan capped each side at 50,000 rows
per range. Each run used a fresh adapter process and a new output path; three
runs per size. The reference engine was released SQLite keyed comparison.

| Total rows per side | Producer wall seconds, three runs | Peak producer RSS bytes, three runs | Peak staged CSV bytes | Final evidence bytes | Reference SQLite seconds, one run | Reference SQLite temp bytes |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 100,000 | 2.036, 1.920, 1.928 | 65,339,392; 65,355,776; 65,470,464 | 2,557,920 | 4,810 | 2.826 | 29,630,464 |
| 250,000 | 4.631, 4.557, 4.535 | 65,404,928; 65,421,312; 65,421,312 | 6,727,950 | 4,921 | 7.141 | 78,442,496 |

Both producer sizes returned the released reference counts: 100k had 99,990
exact rows and 10 required differences; 250k had 249,975 exact and 25
required differences. Both outcomes were FAIL. The producer read each local
source four times: pre-route digest, routing, post-route digest, and
post-comparison digest. Source-backed verification repeats those four local
passes. The staged-byte number is the final sum of temporary CSV files; the
producer checks it as each row is written, so this run's peak staged CSV
bytes equal that sum. The final evidence directory contains only four JSON
files. The benchmark did not measure filesystem allocator overhead, a
PostgreSQL source scan, source-backed verifier time, or a complete migration
rehearsal. These observations are not universal capacity claims.

The [small reference corpus](253-partition-discovery-research.md#exploratory-reference-probe)
also matched all eight keyed count fields for low/high difference, 95% skew
and disjoint-key cases. The automated adversarial tests additionally compare
global empty, duplicate-key, complete PASS and substitution cases against
the released SQLite engine. The full acceptance gate still includes the
exact-head wheel matrix and independent review before integration.
