# Portable decision dossier operator notes

Date: 29 October 2026
Status: feature 6 released in 2.3.0 through PR #106

The dossier packages one verified PostgreSQL 16→18 rehearsal, both acquisition
pairs, policies, optional source-owned coordination claim and selected exact
investigations into a private local directory. Another machine can verify it
without the original paths, PostgreSQL or the optional driver. A PASS remains
agreement under reviewed policy and source-owned claims, not extraction truth,
exception approval, human sign-off authentication or cutover authorization.

Prepare a strict `dossier-plan-v1` JSON file. Pin the exact rehearsal
`manifest.json` SHA-256 and each selected investigation manifest. Declare at
most 32 exception references and 16 sign-off references as stable IDs/roles
plus SHA-256 digests of external records. Exceptions have `open`, `accepted`
or `rejected` dispositions. These are opaque supplied metadata; the dossier
never loads, authenticates or approves the external records. The
[frozen contract](268-decision-dossier-contract.md) defines the full wire format.
Installed schemas are available through `parison schema dossier-plan`,
`dossier-receipt`, `dossier-summary` and `dossier-manifest`.

```sh
parison dossier create --plan dossier-plan.json --rehearsal rehearsal --baseline pg16-pair --candidate pg18-pair --orders-recipe orders.json --lines-recipe order_lines.json --relationships relationships.json --claim claim.txt --output decision-dossier
parison dossier verify decision-dossier
```

Omit `--claim` only when the rehearsal has `unestablished` coordination. Optional
`--orders-investigation` and `--lines-investigation` must match the plan's
non-null selected digests. Creation verifies the original evidence, copies it
under private staging, replays verification on those copies, checks the
original inputs again, and publishes atomically without overwrite. Handle the
entire directory as sensitive: it contains source rows and may contain raw
cases. Interruption removes staging. Verification uses only packaged members
and prints the same summary-safe JSON shown in Workbench Results. CLI/CI exit
codes remain 0 PASS, 1 FAIL, 2 invalid or incomplete, 3 INCONCLUSIVE.

The summary reports outcome, coverage, coordination, reference counts and
`authorization: "external-required"`. It never includes reference digests,
source names, paths, keys, values or cases. Sign-off references and exception
dispositions cannot improve the outcome. A human reviewer must assess external
claim truth, exceptions and authority independently.

`python scripts/check_postgres_rehearsal_live.py --pg16-bin ... --pg18-bin ...
--rows 10 --repeats 1 --dossier --report report.json` runs a disposable source
gate: PostgreSQL 18 dump/restore of a synthetic PostgreSQL 16 order/line pair,
acquisition from both, then dossier verification after both clusters stop and
the original local inputs are removed. This gate uses only synthetic data.
The six 2.3 capabilities remain one release train; combined release
qualification follows feature 6 integration under RELEASING.md.
