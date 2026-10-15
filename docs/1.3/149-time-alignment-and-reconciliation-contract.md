# `time-alignment-v1` and `reconciliation-v1` contract

Date: 15 October 2026

Status: **frozen contract; alignment preflight implemented; relationship execution pending**

## Purpose and boundary

These opt-in declarations define the policy boundary for a future local multi-dataset verification run. `time-alignment-v1` fixes one event-time interval and binds source-owned coordination claims. `reconciliation-v1` names the logical datasets and the only relationship checks v1 may execute.

Authoring validation and fingerprints do not read datasets or receipts. Alignment preflight separately scans supplied local rows and binds receipt bytes, but does not prove that an extraction is complete, that a receipt is authentic, or that a cutover is approved. Released recipe, suite, result, bundle and exit-code meanings remain unchanged.

## Canonical form

Both declarations are strict JSON. Duplicate members, unknown members, unknown enum values, malformed identifiers and unsupported versions are controlled errors. Stable identifiers match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Digests are 64 lowercase hexadecimal characters.

Normalization uses UTF-8 JSON with sorted object members and no insignificant whitespace. Dataset arrays sort by dataset ID. Reconciliation checks sort by kind (`identity`, `reference`, `conservation`) and then check ID. Column arrays remain ordered because tuple position is semantic. Timestamps normalize to UTC with exactly six fractional digits. SHA-256 over those canonical bytes produces `alignment_sha256` or `reconciliation_sha256`.

Runtime file locators, receipt paths and baseline/candidate labels are intentionally absent. Later execution binds their content digests without making machine-specific paths part of policy identity.

## `time-alignment-v1`

```json
{
  "alignment_version": 1,
  "event_window": {
    "start": "2026-09-01T00:00:00Z",
    "end": "2026-10-01T00:00:00Z",
    "bounds": "start-inclusive-end-exclusive"
  },
  "coordination": {
    "mode": "source-snapshot",
    "claim_id": "september-close-4",
    "receipt_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "datasets": [
    {
      "id": "orders",
      "event_time_column": "occurred_at",
      "snapshot_token": "snapshot-42",
      "token_domain": "orders-db"
    }
  ]
}
```

`start` and `end` must be valid RFC 3339 UTC timestamps ending in `Z`, with no more than microsecond precision, and `start` must precede `end`. The only interval is `[start, end)`. Every declared dataset has one semantic timestamp column; execution will reject missing, null, unparsable, naive or out-of-window values rather than infer another timestamp.

Every mode carries a stable `claim_id` and the SHA-256 identity of a source-owned receipt. A digest identifies supplied bytes; it does not authenticate or endorse their contents.

### Source snapshot

Each dataset supplies a nonempty opaque `snapshot_token` and `token_domain`. Tokens in one domain must be byte-equal; different domains may use different token formats or values. Parison never parses a token or translates it across source systems. With valid receipt binding and in-window rows, this mode may produce alignment `PASS`.

### Watermark

The coordination object additionally declares:

- `watermark_kind`: `closed-world` or `heuristic`;
- `idle_partition_policy`: `not-applicable` or `documented`.

Each dataset supplies a UTC `watermark` and nonnegative integer `allowed_lateness_seconds`. Execution uses the minimum watermark as the effective claim and requires every watermark to reach the window end. Lateness is bound policy metadata; it is never added to the window end and Parison never waits on the clock. A mechanically sufficient `closed-world` claim may produce alignment `PASS`; a sufficient `heuristic` claim remains `INCONCLUSIVE`.

### Declared cutoff

Datasets add no mode-specific fields. The source receipt claims intended coverage, but local mechanics cannot establish coordinated extraction. Alignment is therefore always `INCONCLUSIVE` with `coordination-not-machine-established`, even when all supplied rows are in range.

Malformed timestamps, missing receipt bytes, digest mismatch, inconsistent token domains and negative lateness are input errors. An out-of-window row or insufficient watermark is `FAIL`, not `INCONCLUSIVE`.

## `reconciliation-v1`

```json
{
  "reconciliation_version": 1,
  "alignment_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "datasets": [
    {
      "id": "orders",
      "policy_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "columns": [
        {"name": "order_id", "type": "string"},
        {"name": "amount", "type": "decimal"}
      ]
    }
  ],
  "checks": [
    {"id": "order-id", "kind": "identity", "dataset": "orders", "columns": ["order_id"], "nulls": "forbid"}
  ]
}
```

The installed v1 schema and semantic validator require at least one dataset and one check. Dataset IDs are unique. Each dataset binds one reviewed effective recipe fingerprint and an ordered, unique set of semantic columns using the existing closed scalar types: `string`, `integer`, `decimal`, `float`, `boolean`, `date`, and `timestamp`. The alignment declaration used at execution must contain exactly the same dataset IDs and match `alignment_sha256`.

Every check ID is unique. References must resolve to declared datasets, columns and identities. Tuple arity and semantic types must match positionally. The directed child-to-parent relationship graph must be acyclic. Checks run independently on baseline and candidate dataset sets; rows never cross sides.

### Identity

```json
{"id":"order-id","kind":"identity","dataset":"orders","columns":["order_id"],"nulls":"forbid"}
```

The ordered tuple must be unique under canonical scalar encoding. `nulls` is `forbid` or `equal`; there is no ignore mode. Identity runs before dependent checks so a duplicate parent cannot satisfy a reference.

### Reference

```json
{"id":"line-order","kind":"reference","child_dataset":"lines","child_columns":["order_id"],"parent_identity":"order-id","nulls":"forbid"}
```

Every non-exempt child tuple must match exactly one parent identity tuple. `nulls` is `forbid`, `all-null-exempt`, or `match-null`. Under `all-null-exempt`, only an entirely null tuple is exempt; partial-null composites fail.

### Conservation

```json
{
  "id": "order-total",
  "kind": "conservation",
  "parent_dataset": "orders",
  "parent_identity": "order-id",
  "parent_group_columns": ["order_id"],
  "child_dataset": "lines",
  "child_group_columns": ["order_id"],
  "parent_measure": "amount",
  "child_measure": "amount",
  "operator": "sum",
  "nulls": "forbid",
  "comparison": "exact",
  "tolerance": null
}
```

Parent group columns must exactly equal the named parent identity tuple. Child group columns must match its arity and semantic types. Both measures must use the same `integer` or `decimal` type; float sums are excluded, matching aggregate-v1's deterministic accumulation boundary. The only operator is `sum`; nulls are `forbid` or `zero`. Exact comparison requires a null tolerance. Tolerant comparison requires nonnegative finite `absolute` and `relative` values under `symmetric-v1`, reusing aggregate-v1's comparison formula. Currency conversion, allocation, rounding selection and expressions are outside v1.

## Result precedence and disclosure

Future execution reduces results conservatively: controlled input errors abort; otherwise any alignment, parity or relationship `FAIL` makes the result `FAIL`; otherwise any component `INCONCLUSIVE` makes it `INCONCLUSIVE`; otherwise it is `PASS`. PASS means only agreement under these bound policies.

Full evidence may bind dataset IDs, column names, opaque snapshot tokens and bounded canonical key digests. Summary-safe evidence must exclude paths, physical table names, dataset and column names, tokens, receipt contents, keys, groups, values and samples. It may expose fingerprints, statuses, reason codes and aggregate counts.

## Commands and schemas

```console
parison validate-time-alignment alignment.json
parison explain-time-alignment alignment.json
parison validate-reconciliation reconciliation.json
parison explain-reconciliation reconciliation.json
parison preflight-alignment --alignment alignment.json --reconciliation reconciliation.json --receipt receipt.json \
  --dataset orders orders.recipe.json old-orders.csv new-orders.csv
parison check-identity-references --reconciliation reconciliation.json \
  --dataset orders orders.recipe.json old-orders.csv new-orders.csv \
  --dataset lines lines.recipe.json old-lines.csv new-lines.csv
parison check-conservation --reconciliation reconciliation.json \
  --dataset orders orders.recipe.json old-orders.csv new-orders.csv \
  --dataset lines lines.recipe.json old-lines.csv new-lines.csv
parison schema time-alignment
parison schema reconciliation
parison schema alignment-preflight
```

The validation commands establish authoring validity only. The explain commands print normalized declarations and their fingerprints without reading data or receipts. Draft 2020-12 schemas provide structural validation; the commands additionally enforce cross-object uniqueness, referential resolution, type/arity matching, token-domain equality and acyclicity.

`preflight-alignment` requires one `--dataset ID RECIPE BASELINE CANDIDATE` group for every declared dataset. It requires exact agreement among alignment, reconciliation and runtime dataset IDs; verifies the receipt, alignment and effective-policy fingerprints before scanning; enforces the combined byte, decoded-byte and per-input row limits; and rejects inputs changed during the scan. Its strict `alignment-preflight-v1` result contains only bound fingerprints, the fixed window, stable dataset IDs and aggregate event-time counts—never paths or timestamp values. Exit codes retain the released outcome mapping: 0 PASS, 1 FAIL, 2 input error and 3 INCONCLUSIVE.

`check-identity-references` evaluates every declared identity and reference independently on baseline and candidate. It emits aggregate counts only: rows, distinct and duplicate identities, null-key failures, exemptions, matches, orphans and ambiguous-parent rows. `--engine memory|sqlite` has identical semantics and deterministic result ordering; SQLite uses a private temporary database, a hard `--max-temp-bytes` ceiling and interruption-safe cleanup. The command also binds effective-policy fingerprints, enforces input and distinct-key limits, and rejects changed inputs. Conservation and per-dataset parity remain separate pending gates and are not implied by this command's PASS.

`check-conservation` evaluates every declared grouped sum independently on baseline and candidate. Measures are restricted to matching integer or scaled-decimal domains, matching aggregate-v1's deterministic sum boundary; float accumulation is not admitted. Results distinguish exact, within-tolerance and different groups, child-only groups, parents without children, duplicate parents and rejected null measures without exposing keys or values. Memory and bounded SQLite engines are semantically equivalent. Per-dataset parity and the overall reconciliation reduction remain separate pending gates.

## Compatibility

These contracts are additive and opt-in. `alignment_version: 1` and `reconciliation_version: 1` are immutable meanings. New modes, checks, operators, null rules, tolerance formulas or timestamp semantics require a versioned contract. Implementing execution must not reinterpret recipes 1–3 or any released bundle.
