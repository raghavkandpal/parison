# Portable decision dossier implementation checkpoint

Date: 29 October 2026
Status: feature 6 candidate; independent review and exact-head CI pending

`parison dossier create|verify` publishes a private, unsigned, self-contained
package of one verified feature 5 rehearsal. It includes exact pair receipts
and CSVs, recipes, relationship declaration, optional source-owned claim and
selected feature 4 investigations. Creation verifies the original evidence,
then verifies copied members under private staging; the final verifier uses
only package members and reruns source-backed local checks. Workbench Results
uses the same verified summary projector as the CLI/CI command. Sign-off and
exception digests remain opaque supplied references, never authorization.

The canonical fixture pins every package byte. The adversarial tests cover
PASS/FAIL/INCONCLUSIVE, portable replay after source removal, a selected
investigation, recomputed-digest outcome forgery, missing/symlinked members,
duplicate JSON names, non-finite JSON, bad schemas, no-overwrite publication,
interruption cleanup and CLI/Workbench summary safety. The controlled live
PostgreSQL 16.15→18.6 dump/restore gate creates a dossier after pair acquisition
and verifies it after server shutdown and original input removal. The final
report is retained locally at `/private/tmp/dossier-live-final.json`; it uses
synthetic ten-row data and does not establish production capacity.

The owner asked to consolidate standalone installed commands after the dossier
is done. This feature uses the existing `parison` command. See the
[follow-up](270-cli-consolidation-followup.md) for a separately versioned
migration of already shipped command contracts. The combined six-feature
release gate remains pending until dossier integration and full qualification.
