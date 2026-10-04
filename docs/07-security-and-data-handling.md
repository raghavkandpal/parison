# Parity security and data handling

## Security position

Local execution removes the need to upload datasets to us; it does not make processing automatically secure. Inputs, scratch files, report samples, identifiers, logs and CI artifacts can expose sensitive data. The first version should minimize what it stores and publish a clear threat model.

This proposal is not a security assessment or compliance claim. Build with independently created synthetic/public fixtures; support should not require users to send production files.

## Threats and proposed controls

| Threat | Proposed control | Verification |
| --- | --- | --- |
| Malicious recipe executes code | Strict declarative schema; safe YAML parsing; no eval or free-form SQL | Adversarial recipe corpus and dependency review |
| Crafted file exhausts resources/crashes parser | Separate constrained worker, size limits and tested time/disk/RAM limits | Oversized/malformed fixtures, cancellation and crash tests |
| Path traversal or symlink escape | Explicit local paths; canonicalization; reject disallowed special files; safe staging and permission checks | Traversal, symlink and concurrent-path-change tests |
| Dataset changes during comparison | Protected snapshot/staging or documented checked zero-copy mode | Mid-read mutation fixture |
| Data appears in logs | Log event codes and bounded metadata, not row values or credentials | Automated canary scan of logs and crash output |
| HTML/script injection | Escape all values, self-contained assets and restrictive rendering policy | Script-like values/column names in reports |
| Spreadsheet formula injection | Separate safe-for-spreadsheet export from exact-value evidence | Formula-prefix and delimiter/quote tests |
| CI artifact leaks | Private restricted artifact destination, explicit retention, safe summary default | Public PR/fork pipeline tests |
| Old recipe/report becomes silently modified | Immutable run bundle and content checksums with trusted references | Tamper/missing-file checks |
| Local UI is reachable by another page or host | Loopback binding, session token, Host/Origin checks, no wildcard CORS | Unauthorized browser/local request tests |

Native parsers may run with the process user's privileges. OS/container restrictions are required if accepting untrusted inputs beyond the documented supported trust boundary. Size limits are not a substitute for a sandbox. Publish what is and is not enforced on each supported OS.

If DuckDB is introduced, its own documentation warns that untrusted SQL and non-SQL parameters can trigger filesystem/network operations, and that settings alone are not a comprehensive sandbox. Disable unnecessary extensions/external access and restrict execution outside the engine. [Security guidance](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview), [security model](https://duckdb.org/security).

## Default privacy mode

Default report mode should contain counts, field classifications and coverage, with no raw row samples. Even column names and group labels may be sensitive; provide a policy for suppressing them. Debugging evidence is an explicit local opt-in and clearly marked in the manifest.

Masking is applied only at export/view boundaries after comparison, not before comparison where it could conceal differences. Simple hashes are not anonymization: predictable identifiers can be guessed, and equality patterns remain visible. Where correlated masked samples are needed, use scoped keyed pseudonyms and treat the key and output as sensitive.

The local UI may show raw values only after an explicit user choice. Exported summary mode must not contain hidden raw data in HTML attributes, embedded JSON or scripts. Test the bytes, not just the visible table.

## Export fidelity versus safety

CSV evidence opened in a spreadsheet can interpret attacker-controlled values as formulas. OWASP documents this risk. [CSV injection](https://community.owasp.org/attacks/CSV_Injection).

Offer two clearly different exports: exact-value structured evidence such as JSON/Parquet, and transformed spreadsheet-safe CSV. Preserve original value digests/metadata where appropriate and record which transformations were applied. Never silently prefix source values and claim the exported file is an exact reproduction. Test actual target spreadsheet behavior; quoting alone is not a universal defense.

## Retention and deletion

Use per-run scratch directories with restrictive permissions and cleanup on success/cancellation where possible. Detect abandoned task-owned scratch at startup and ask or apply the published cleanup policy. Never delete user source paths or broad directories during cleanup.

Evidence bundles are retained only in destinations the user selects. Show their sensitivity mode and sizes. Disk encryption is the user's OS responsibility unless we later implement reviewed artifact encryption; do not claim that Parity encrypts local files by default.

Deleting a file is not guaranteed secure erasure on SSDs or replicated backups. Document that limitation. Do not retain source copies merely to make reruns convenient without explicit permission.

## Provenance and authority

Checksums support integrity relative to a trusted manifest, but an attacker able to replace both can forge the bundle. Authenticated/signed provenance is a later capability requiring key management and trusted CI binding.

Prevent policy self-approval in CI: protected baseline/recipe, independent review for rule changes, candidate commit binding and checks on artifact completeness. A green exit code from an untrusted job alone is insufficient evidence. Untrusted fork builds must not receive production credentials or raw baselines.

## Dependency and distribution hygiene

Pin releases, inventory transitive dependencies, review license terms and publish supported Python/OS versions. Keep optional database/cloud packages out of the default install. Verify release artifacts, maintain a vulnerability-reporting channel and avoid automatic remote asset downloads during a run.

Do not promise an air-gapped product until installation, execution, reports and updates are verified offline. Runtime “no telemetry” should be tested with network egress blocked. Optional opt-in diagnostics must be value-free and previewable before submission.

## Independent-project boundary

Use original implementations, public specifications and fixtures with clear provenance. Do not import workplace parsers, production outputs, internal comparison rules or confidential workflow details. Any employment/IP obligations should be reviewed independently before commercialization; this dossier does not determine those rights.
