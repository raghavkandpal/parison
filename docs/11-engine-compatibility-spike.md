# Engine compatibility spike

Date: 5 October 2026. Tested package: DataComPy 1.1.0 with its Polars backend in an isolated environment.

## Decision

Do not add DataComPy as a Parity runtime dependency for the keyed-v1 contract. Keep the current contract-specific implementation and use DataComPy only as an optional differential reference where semantics overlap.

This is a semantic decision, not a claim that DataComPy is incorrect. Its documented behavior is useful for general dataframe comparison but differs from Parity's deliberately stricter identity and tolerance rules.

## Executed cases

| Case | DataComPy 1.1.0 observation | Parity requirement | Compatibility |
| --- | --- | --- | --- |
| Duplicate join keys | Reported duplicates, paired the rows and returned a match | Reject duplicate keys before joining and return INCONCLUSIVE | No |
| Relative tolerance, inputs `100` and `111` at `0.1` | Matched in one input direction and failed after swapping inputs | Symmetric allowance based on the larger magnitude | No |
| Decimal `10.00` versus `10.01` at absolute tolerance `0.01` | Matched, but reported maximum delta as `0.009999999999999787` | Preserve Decimal arithmetic and publish exact decimal delta | No |
| Missing/extra rows and field summaries | Exposed unique rows, intersecting rows and per-column statistics | Complete counts and bounded evidence | Partial |
| String normalization | Case/space behavior is configurable | Exact strings by default; normalization only when explicitly reviewed | Configurable overlap |

The directional tolerance result agrees with the maintained API documentation, which defines the allowance using the second dataframe's magnitude. The duplicate-key result agrees with the maintained usage guide, which says duplicate join rows are paired rather than rejected. See [DataComPy API](https://capitalone.github.io/datacompy/api/datacompy.html) and [Pandas usage](https://capitalone.github.io/datacompy/pandas_usage.html).

## Consequences

- Do not add pandas, NumPy, Jinja or DataComPy to the default installation.
- Keep Polars optional for Parquet parsing; CSV comparison remains standard-library-only.
- Retain independent Decimal and typed-key tests as the source of truth.
- A future differential test may compare exact, unique-key cases with zero tolerance. It must not treat disagreement outside that overlap as an implementation defect.
- Revisit an adapter only if DataComPy adds configurable duplicate rejection, symmetric tolerance and Decimal-preserving evidence, or if Parity changes its contract.

