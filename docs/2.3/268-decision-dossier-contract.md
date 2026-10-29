# Portable decision dossier contract

Date: 29 October 2026
Status: frozen for feature 6 implementation; not release authorization

## Claim and boundary

A `decision-dossier-v1` is a private, unsigned, self-contained local directory
for one verified feature 5 PostgreSQL 16→18 rehearsal. It packages exact source
and target acquisition pairs, both recipes, the relationship declaration, the
optional opaque source-owned coordination claim, the rehearsal evidence, and
optionally one feature 4 investigation per table. This makes verification
possible without the original paths or databases. Its summary is a closed
safe projection suitable for CLI/CI and Workbench Results. The dossier does not
authenticate extraction, upstream coordination, exception disposition, a
signer, or cutover approval. It cannot promote a rehearsal status.

The reviewed `dossier-plan-v1` has exactly `dossier_plan_version: 1`,
`rehearsal_manifest_sha256`, `investigations`, `exceptions`, and `signoffs`.
`investigations` has exactly `orders` and `order_lines`, each null or a lowercase
SHA-256 of a selected investigation's canonical manifest bytes. At most one
investigation per table; selected cases remain bounded by feature 4. Each
non-null investigation must be reverified source-backed against the packaged
rehearsal discovery, recipe and CSV inputs. `exceptions` is an array of at most
32 explicit records with exactly `id` (stable `[A-Za-z0-9._-]` identifier),
`reference_sha256` (digest of a source-owned external exception record), and
`disposition` (`open`, `accepted`, `rejected`). `signoffs` is an array of at most
16 records with exactly `role` (stable identifier) and `reference_sha256`
(digest of an external human sign-off record). IDs and roles are unique within
their arrays. No names, URIs, signatures, credentials, paths, raw values or
unbounded prose enter the plan. Digests identify references only; existence,
authenticity, issuer and authorization remain outside Parison. Sign-offs and
exception dispositions cannot change `outcome`, `coverage` or `complete`.
No generated reference or disposition is treated as policy approval.

The create command takes explicit plan and directory paths for feature 5
rehearsal, two pair bundles, two recipes, relationship declaration, optional
coordination claim and selected investigations. It calls existing verifiers
before copying. It requires the plan to pin the exact rehearsal manifest and
each selected investigation manifest; no implicit discovery or source search.
All inputs must be regular, non-symlink local files/directories. Cap the
package at 4 GiB total, 1 GiB per member file, 128 files, 256 total entries and depth 8; JSON
metadata files cap at 4 MiB and the claim at 256 KiB. The complete
portable package remains private because it contains acquired rows and possibly
raw discrepancy cases. The output must be outside every input directory. A no-overwrite target is installed atomically from a
mode-0700 stage; any failure/interruption removes sensitive staging.

## Wire format and verification

The output has exactly `plan.json`, `receipt.json`, `summary.json`,
`manifest.json`, and `members/`. `members/` contains exactly `rehearsal/`,
`baseline/`, `candidate/`, `orders-recipe.json`, `lines-recipe.json`,
`relationships.json`, optional `claim.txt`, and optional `investigations/` with
only `orders/` and/or `order_lines/`. The three pair/rehearsal directories and
investigations retain their unchanged released/feature wire formats and bytes.
The receipt has exactly `dossier_receipt_version: 1`, `rehearsal_manifest_sha256`,
`pair_manifests` (baseline/candidate SHA-256), `investigation_manifests`
(orders/order_lines null or SHA-256), `outcome`, `coverage`, `coordination`,
`complete: true`, `exception_count`, `open_exception_count`, `signoff_count`,
and `verification: "source-backed-local"`. It binds only verified derived
results and reviewed reference counts. The summary has exactly
`dossier_summary_version: 1`, `kind: "decision-dossier"`, `outcome`, `coverage`,
`coordination`, `complete: true`, `exception_count`, `open_exception_count`,
`signoff_count`, `authorization: "external-required"`, and `receipt_sha256`.
It contains no source names, paths, keys, values, snapshot tokens or reference
digests. `manifest.json` has `dossier_manifest_version: 1` and a closed `files`
map binding all top-level JSON members and every package member by relative
path and SHA-256. Manifest membership is exact; no links, extra files or
unbounded traversal. Each JSON artifact is compact sorted-key UTF-8 with one
newline; identity hashes of objects omit that newline.

Offline `verify` checks strict schema, canonical bytes, exact membership,
digests and symlink safety, reruns feature 5 verification using only packaged
members, reruns each selected investigation source-backed, and recomputes the
receipt, summary and manifest. Tampered outcomes, recomputed digest-valid
forgery, missing inputs, changed sign-off/exception counts and substituted
sources fail closed. Verification returns exactly the stored summary. It does
not access PostgreSQL or remote references and cannot prove the truth of
source-owned claims. A summary-safe `inspect` path in Workbench Results and
the CLI/CI verifier must return identical summary fields and values.

`parison dossier create --plan FILE --rehearsal DIR --baseline DIR --candidate
DIR --orders-recipe FILE --lines-recipe FILE --relationships FILE [--claim FILE]
[--orders-investigation DIR] [--lines-investigation DIR] --output DIR` publishes
one dossier. `parison dossier verify DIR` verifies from packaged members only.
Both print only the summary JSON; exit codes follow established 0 PASS, 1 FAIL,
2 invalid/incomplete, 3 INCONCLUSIVE. Errors are fixed summary-safe text.
Workbench Results may open a dossier by workspace-relative path and call the
same offline verifier; it does not expose private members in the UI.

## Adversarial gate

Pin complete canonical bytes for a small fixture and verify after removing all
original inputs. Exercise PASS, FAIL and INCONCLUSIVE rehearsal outcomes;
missing/changed pair, policy, claim or investigation; altered raw case, result
status, exception/sign-off reference and counts; duplicate reference IDs;
unknown fields, duplicate JSON members and non-finite numbers; symlinks at
all levels; target collision; mid-copy interruption and cleanup; bounded
member sizes; and summary/CLI/Workbench leakage. Recompute all local digests
on a forged PASS and show the verifier still rejects derived status changes.
Use one complete controlled 16→18 rehearsal output as a source fixture, then
verify its dossier after shutting both clusters down. Keep source/claim truth
and reference authentication explicitly external. Run narrow tests,
`make check`, independent Standards/Spec review and exact-head quality plus
Python 3.11–3.14 Linux/macOS/Windows built-wheel CI before integration.

The six-feature train remains one 2.3 release boundary. Only after feature 6
integration may combined release qualification begin under RELEASING.md; no
PASS, sign-off reference or test run itself authorizes a cutover or release.
