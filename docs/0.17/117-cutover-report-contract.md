# Cutover evidence report contract

Status: **implementation contract**

## Command

```text
parison report-cutover BUNDLE --output REPORT.md
```

The command recursively verifies the bundle, then writes a concise deterministic Markdown projection for a human cutover review. It supports run, suite and suite-shard bundles.

## Contents

Every report identifies the bundle kind, top-level manifest SHA-256, outcome, completeness, result schema and producing Parison version. A run report adds its comparison contract, effective-policy fingerprint, sensitivity, result counts and discrepancy count. A suite report adds its suite version, suite-policy fingerprint when available, scope completeness, case completion, outcome counts and ordered case outcomes.

The report contains no local bundle path, source path, source value, discrepancy sample, execution timestamp or host identity. It is a safe metadata projection, not a substitute for the complete bundle.

## Publication and interpretation

The report creates missing parent directories, publishes atomically and refuses to overwrite an existing output. Identical verified bundle content produces identical report bytes across platforms.

The report always names the remaining independent checks: signer authentication, reviewed gate policy and upstream extraction guarantees. It never labels a PASS as approval, proves extraction truth or claims the Markdown itself is signed. Sign the canonical Parison Statement and retain the complete verified bundle; use the report as the review cover sheet.
