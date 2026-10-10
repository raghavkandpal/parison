# Parison boundaries and 0.12 direction

Date: 10 October 2026

Status: **accepted planning decision**

## Correction to the current boundary list

Suite sharding and resume are no longer deferred. Parison 0.11 ships deterministic external sharding, independently verifiable shard bundles, exact assembly, and digest-validated resume from an explicit workspace. The remaining concurrency boundary is narrower: Parison does not yet execute multiple suite cases concurrently inside one local process invocation.

## Why the other boundaries exist

These are sequencing decisions, not claims that the features are universally undesirable.

| Boundary | Why it remains outside the current product | Evidence that would justify reopening it |
| --- | --- | --- |
| Interactive local UI | The self-contained HTML report already provides a portable, zero-service reading interface. A live workbench adds a localhost server, session and origin security, filesystem mediation, browser-state limits, and another packaging/test surface. | Repeated user evidence that CLI plus static reports materially slows recipe authoring or investigation, with a concrete workflow the static report cannot support. |
| YAML recipes | Strict JSON has one installed schema, predictable parsing, and stable canonical fingerprinting. YAML adds implicit scalar typing, aliases, tags, parser limits, another dependency, and two equivalent authoring syntaxes without adding comparison capability. | Users repeatedly reject JSON authoring and a safe YAML subset can round-trip to the exact existing effective policy without ambiguity. |
| Remote connectors | A connector must define credentials, network egress, retries, snapshot consistency, mutation detection, pagination, SDK versions, and redaction. Reading a local export keeps extraction under the user's existing platform controls. | A named source is a demonstrated adoption blocker and its snapshot semantics can be made at least as strong as local-input mutation checks. |
| Internal parallel execution | Before 0.11, Parison lacked isolated case limits, stable selection, resumable workspaces, and a partial-scope result model. A worker pool would have multiplied memory and complicated interruption without a safe recovery path. | This gate is now met. It is the recommended 0.12 slice. |
| Fuzzy matching | Fuzzy entity resolution replaces declared identity with an algorithmic assignment. Multiple plausible matches, threshold changes, and order-dependent tie-breaking make PASS mean something fundamentally different. | A separate, versioned proof mode with deterministic assignment, ambiguity reporting, and independently testable golden cases. |
| Automatic data repair | Parison is a read-only evidence tool. Mutating or generating replacement data would mix diagnosis with remediation, introduce loss and rollback risk, and create incentives to “repair until PASS.” | A separately named output-only transformation product with provenance, preview, approval, and rollback—not a hidden comparison option. |
| Hosted history | Hosting conflicts with the current zero-custody promise and requires authentication, authorization, tenant isolation, encryption, retention, deletion, incident response, and a sustainable service model. Even summary metadata can be sensitive. | Proven team demand, a metadata classification policy, signed submissions, and an explicit operating/security commitment. |

## Product rule

Parison should cross one trust boundary at a time. A release may deepen local deterministic comparison, or add remote/hosted/mutating behavior, but should not combine those changes. That keeps the meaning of a result reviewable and makes failures attributable to one new seam.

## 0.12 choice

Build **bounded local suite concurrency**. It directly deepens the released suite interface and reuses existing case execution, workspace, verification, and publication behavior. It does not add a fourth comparison mode, a new recipe syntax, network access, or a runtime dependency.

The external interface stays small:

```text
parison run-suite --plan PLAN --output DIRECTORY --jobs N
```

`--jobs 1` preserves current behavior. Values greater than one bound the number of active cases; they do not claim automatic CPU or memory optimization. Final results, reports, and manifests remain in plan order regardless of start or completion order.

