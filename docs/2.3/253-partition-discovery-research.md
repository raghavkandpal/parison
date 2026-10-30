# Exact partitioned difference discovery research

Date and primary-source access: 28 October 2026
Status: historical feature 3 research checkpoint; contract and implementation later integrated through PR #99

## Boundary and existing semantics

The [six-feature roadmap](246-six-feature-roadmap.md) asks for a bounded,
disk-backed strategy over reviewed key ranges. A full-scope PASS requires exact
completion of every range. Feature 4 will investigate verified suspect ranges
under the same policy and input identities. The selected migration target and
100k/250k-row gate are recorded in the [post-2.2 direction](../2.2/244-fast-diff-and-cutover-evidence-direction.md).

The released keyed comparator already owns normalization, null and duplicate
key rejection, row/field classifications, outcome and input digests
([`comparison.py`](../../src/parison/comparison.py),
[`policies.py`](../../src/parison/policies.py)). It reads local inputs through
one format-aware iterator, including strict CSV parsing and per-side null
tokens ([`inputs.py`](../../src/parison/inputs.py)). The SQLite engine stores
normalized keyed rows in a private `WITHOUT ROWID` table and enforces a page
limit; SQLite says that layout can save space or time in some cases, but is not
universally faster ([SQLite `WITHOUT ROWID`](https://www.sqlite.org/withoutrowid.html),
[SQLite PRAGMAs](https://www.sqlite.org/pragma.html)). A new strategy needs its
own versioned evidence and must leave released result and bundle bytes alone.

## Design consequences

1. Start with a narrow, reviewed keyed-local-input subset. A single integer
   key and CSV files make ordered half-open ranges unambiguous. Each partition
   plan must declare contiguous, nonoverlapping ranges covering the full
   integer domain, including open ends. Range boundaries are policy-sensitive
   selection data. Reject unsupported projections, formats and keys explicitly
   rather than silently falling back to a different claim.
2. Route every parsed source row exactly once using the same key parsing and
   normalization as the released comparator. A duplicate normalized key must
   reach the same range on its own side, preserving duplicate rejection.
   Zero-row ranges still need explicit completed records. One digest of an
   output partition does not prove that routing was exhaustive; the producer
   must bind source digests, source row totals, routing totals, range plan and
   all completed exact comparisons. A verifier with source bytes can reroute
   to prove the assignment; a source-free verifier can validate only the
   internal evidence and must state that narrower claim.
3. Enforce separate limits on source bytes/rows, total staged bytes, per-range
   rows and working memory. Skew can concentrate almost all rows in one range;
   do not label a strategy bounded merely because it has many ranges. On a
   limit breach, fail closed and remove sensitive staging. Python's
   [`TemporaryDirectory`](https://docs.python.org/3/library/tempfile.html)
   supplies context-managed cleanup; repository publication primitives still
   control no-overwrite, symlink safety and interruption handling.
4. Preserve the original recipe identity. The released comparator treats an
   empty side as INCONCLUSIVE unless the recipe explicitly sets
   `scope.expected_empty` ([`compare`](../../src/parison/comparison.py)). An
   empty *range* is not necessarily an empty *declared scope*. If an internal
   comparison permits empty ranges, its mechanically derived policy and digest
   must be explicit, and the original global empty rule must be applied once
   after all ranges complete. The derived policy cannot be presented as an
   operator approval. A narrower internal exact-classification primitive may
   avoid changing the recipe at all.
5. Keep raw keys, values, ranges, source paths and samples in private local
   evidence only. A summary-safe view may report aggregate counts, completion
   and bound digest identifiers, but cannot reveal which range is suspect.
   Feature 4 may then request sensitive detail from verified private evidence.

Python's [`csv` module](https://docs.python.org/3/library/csv.html) handles
quoted fields and delimiters, but does not automatically convert ordinary
fields to policy types. Routing therefore cannot compare raw CSV strings as
integer keys. The existing format-aware parse/normalize path is the semantic
authority.

## Threats and qualification work

- **False coverage:** gaps/overlaps, omitted rows, discarded empty ranges,
  changed input after routing, swapped sources, wrong recipe, or a missing
  child result must prevent a full-scope PASS. A digest-valid locally forged
  record is not proof of extraction truth or source authenticity.
- **False parity:** concatenating per-range outcomes or counts without the
  global `expected_empty`, null-key and duplicate rules can disagree with the
  released engine. Compare outcomes, all count fields and field classifications
  against it on low-difference, high-difference, skewed and all-different
  corpora, including missing-only ranges and a globally empty side.
- **Resource abuse:** an adversarial key distribution, very wide CSV fields,
  open file handles and interruption can exhaust memory, disk or descriptors.
  Measure peak process RSS, temporary bytes and elapsed time in fresh processes
  at 100k and 250k rows. Record source input bytes and read passes; local CSV
  tests have no PostgreSQL source-load observation. If paired PostgreSQL
  exports are used, source scans belong to their separate acquisition gate.
- **Race and substitution:** before/after source digests are the released
  comparator's mutation check, not an atomic source snapshot. The partition
  producer should bind the actual bytes it routed and verify all staged bytes
  before publication. Source-free verification cannot infer the original
  PostgreSQL snapshot from local bytes.

## Exploratory reference probe

On an Apple M1, macOS 27.0.1, Python 3.14.7, a disposable four-range CSV
prototype routed rows once and called the released memory comparator per
range. The reference was the released SQLite keyed engine. The policy had one
integer key and one exact decimal field. Each case was run once; these are
diagnostic observations, not the required fresh-process 100k/250k gate.

| Case | Rows per side | SQLite seconds | Prototype seconds | Eight counts equal? |
| --- | ---: | ---: | ---: | --- |
| Low difference | 20,000 | 0.559 | 0.213 | Yes |
| High difference | 20,000 | 0.552 | 0.204 | Yes |
| 95% in one range | 10,000 | 0.278 | 0.102 | Yes |
| Disjoint keys | 20,000 | 0.433 | 0.200 | Yes |

The prototype mechanically changed `expected_empty` for range-local calls.
This exposed the global-empty semantic issue and is **not** accepted as the
implementation. It did not measure peak RSS, peak disk, source load, null or
duplicate keys, input substitution or interruption. At 100k and 250k rows in
a separate low-difference probe, the released SQLite engine took 2.826 s and
7.141 s and used 29,630,464 and 78,442,496 temporary bytes; a five-range
prototype took 1.122 s and 2.722 s including routing. Those one-shot numbers
only justify investigating the narrow strategy.

## Non-goals for the first strategy

No sampling, hash-only parity, automatic range suggestion as policy approval,
remote partition workers, source queries, cross-instance coordination, raw
discrepancy export, or claim that local parity authorizes cutover. Generalizing
to composite or noninteger keys and every supported input format waits for an
exactness and resource gate on the narrow strategy.
