# Parison 0.10 roadmap

Date: 9 October 2026

Status: **release candidate**

## Focus: local comparison suites

0.10 will let one reviewed plan run an ordered set of existing keyed, aggregate and multiset comparisons and publish one recursively verifiable suite bundle. This expands Parison from one-output proof to migration-level evidence without adding a fourth comparison mode or changing any case outcome.

## Ordered implementation

1. Freeze suite-v1 plan, result, outcome-reduction and privacy contracts. **Implemented.**
2. Add installed suite schemas, strict loading, reference resolution and `validate-suite`. **Implemented.**
3. Run cases sequentially through existing compare/publish paths and continue after ordinary case outcomes. **Implemented.**
4. Publish one atomic parent bundle containing ordinary child bundles and safe suite summaries. **Implemented.**
5. Add recursive verification and suite-aware safe inspection. **Implemented.**
6. Add a checked-in mixed-mode example and cross-platform installed-wheel smoke. **Implemented.**
7. Complete adversarial tests, release evidence and 0.10.0 publication. **In progress.**

## Boundaries

- No parallel workers, retries, resume or cache reuse.
- No globs, recursive discovery, environment interpolation or arbitrary commands.
- No suite-wide raw evidence export; target a raw child bundle explicitly.
- No change to keyed-v1, aggregate-v1 or multiset-v1 recipes and results.
- No runtime dependency, server, remote input or hosted history.

The design evidence and rejected alternatives are recorded in [the comparison-suite research](76-suite-research.md). The normative target is [the suite-v1 contract](78-suite-contract.md).
