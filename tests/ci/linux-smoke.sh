#!/usr/bin/env bash
# Historical qualification scenarios; new feature coverage belongs in tests.
set -euo pipefail
: "${PARISON_CI_TEMP:?set a new private output directory}"
mkdir -- "$PARISON_CI_TEMP"

parison --version

parison schema recipe

parison schema recipe-authoring

parison schema result

parison schema manifest

parison schema preflight

parison schema recipe-v2

parison schema recipe-v3

parison schema recipe-v4

parison schema recipe-v5

parison schema recipe-v6

parison schema preflight-v2

parison schema preflight-v3

parison schema preflight-v4

parison schema preflight-v5

parison schema preflight-v6

parison schema preflight-v16

parison schema preflight-v17

parison schema preflight-v18

parison schema preflight-v19

parison schema preflight-v20

parison schema preflight-v21

parison schema preflight-v22

parison schema preflight-v23

parison schema preflight-v24

parison schema result-v2

parison schema result-v3

parison schema partition-plan

parison schema partition-receipt

parison schema partition-summary

parison schema partition-manifest

parison schema investigation-plan

parison schema investigation-receipt

parison schema investigation-cases

parison schema investigation-summary

parison schema investigation-manifest

parison schema suite

parison schema suite-authoring

parison schema suite-v2

parison schema suite-result

parison schema suite-result-v2

parison schema suite-manifest

parison schema suite-manifest-v2

parison schema statement

parison schema schema-evolution

parison schema policy-diff

parison schema time-alignment

parison schema reconciliation

parison schema alignment-preflight

parison schema relationship-result

parison schema conservation-result

parison schema reconciliation-result

parison schema dataset-manifest

parison schema reproducibility-diagnostic

parison verify-dataset-manifest --manifest examples/1.4/payout-dataset-manifest.json --root . --policy-file examples/1.3/reconciliation.json --summary

parison reconcile --alignment examples/1.3/alignment.json --reconciliation examples/1.3/reconciliation.json --receipt examples/1.3/extraction-receipt.json --dataset payments examples/1.3/payments.recipe.json examples/1.3/payments-baseline.csv examples/1.3/payments-candidate.jsonl --dataset payouts examples/1.3/payouts.recipe.json examples/1.3/payouts-baseline.csv examples/1.3/payouts-candidate.jsonl --engine sqlite --output "${PARISON_CI_TEMP}"/parison-1.3-reconciliation --summary

parison publish-dataset-evidence --manifest examples/1.4/payout-dataset-manifest.json --root . --policy-file examples/1.3/reconciliation.json --result-bundle "${PARISON_CI_TEMP}"/parison-1.3-reconciliation --output "${PARISON_CI_TEMP}"/parison-1.4-dataset-evidence

parison verify "${PARISON_CI_TEMP}"/parison-1.4-dataset-evidence

parison inspect "${PARISON_CI_TEMP}"/parison-1.4-dataset-evidence

parison validate-evolution examples/1.2/orders.schema-evolution.json

parison compile-evolution examples/1.2/orders.schema-evolution.json

parison diff-policy --baseline-recipe examples/1.2/baseline.recipe.json --candidate-recipe examples/1.2/candidate.recipe.json --evolution examples/1.2/orders.schema-evolution.json --summary

parison validate-time-alignment examples/1.3/alignment.json
parison validate-reconciliation examples/1.3/reconciliation.json
parison verify "${PARISON_CI_TEMP}"/parison-1.3-reconciliation
parison inspect "${PARISON_CI_TEMP}"/parison-1.3-reconciliation

parison export-editor-schemas --output "${PARISON_CI_TEMP}"/parison-editor-schemas

parison validate-recipe examples/orders.recipe.json

parison validate-inputs --recipe examples/orders.recipe.json --baseline examples/baseline.csv --candidate examples/candidate.csv

parison compare --recipe examples/orders.recipe.json --baseline examples/baseline.csv --candidate examples/candidate.csv --output "${PARISON_CI_TEMP}"/parison-smoke

parison verify "${PARISON_CI_TEMP}"/parison-smoke

parison workbench --help

python -c "from parison.workbench_host import create_workbench_server; server, url = create_workbench_server('.'); assert server.server_address[0] == '127.0.0.1' and url.startswith('http://127.0.0.1:'); server.server_close()"

parison statement "${PARISON_CI_TEMP}"/parison-smoke --output "${PARISON_CI_TEMP}"/parison-statement.json
parison verify-statement "${PARISON_CI_TEMP}"/parison-smoke "${PARISON_CI_TEMP}"/parison-statement.json
parison report-cutover "${PARISON_CI_TEMP}"/parison-smoke --output "${PARISON_CI_TEMP}"/parison-cutover.md

parison init "${PARISON_CI_TEMP}"/parison-quickstart
parison validate-recipe "${PARISON_CI_TEMP}"/parison-quickstart/recipe.json
parison validate-inputs --recipe "${PARISON_CI_TEMP}"/parison-quickstart/recipe.json --baseline "${PARISON_CI_TEMP}"/parison-quickstart/baseline.csv --candidate "${PARISON_CI_TEMP}"/parison-quickstart/candidate.csv --records
parison compare --recipe "${PARISON_CI_TEMP}"/parison-quickstart/recipe.json --baseline "${PARISON_CI_TEMP}"/parison-quickstart/baseline.csv --candidate "${PARISON_CI_TEMP}"/parison-quickstart/candidate.csv --output "${PARISON_CI_TEMP}"/parison-quickstart/run
parison verify "${PARISON_CI_TEMP}"/parison-quickstart/run

parison compare --recipe examples/orders.recipe.json --baseline examples/baseline.csv --candidate examples/candidate.csv --output "${PARISON_CI_TEMP}"/parison-smoke-2
parison catalog add --database "${PARISON_CI_TEMP}"/parison-catalog.sqlite "${PARISON_CI_TEMP}"/parison-smoke
parison catalog add --database "${PARISON_CI_TEMP}"/parison-catalog.sqlite "${PARISON_CI_TEMP}"/parison-smoke-2
parison catalog list --database "${PARISON_CI_TEMP}"/parison-catalog.sqlite --outcome PASS --kind run
policy=$(parison explain examples/orders.recipe.json | python -c 'import json, sys; print(json.load(sys.stdin)["policy_sha256"])')
parison catalog history --database "${PARISON_CI_TEMP}"/parison-catalog.sqlite --policy-sha256 "$policy"
parison catalog diff --database "${PARISON_CI_TEMP}"/parison-catalog.sqlite "${PARISON_CI_TEMP}"/parison-smoke "${PARISON_CI_TEMP}"/parison-smoke-2

parison validate-inputs --recipe examples/0.3/migration.recipe.json --baseline examples/0.3/baseline --candidate examples/0.3/candidate.jsonl

parison compare --recipe examples/0.3/migration.recipe.json --baseline examples/0.3/baseline --candidate examples/0.3/candidate.jsonl --output "${PARISON_CI_TEMP}"/parison-0.3-smoke

parison validate-inputs --recipe examples/0.5/migration.recipe.json --baseline examples/0.5/baseline.tsv.gz --candidate examples/0.5/candidate.csv

parison validate-inputs --records --recipe examples/0.5/migration.recipe.json --baseline examples/0.5/baseline.tsv.gz --candidate examples/0.5/candidate.csv

parison compare --recipe examples/0.5/migration.recipe.json --baseline examples/0.5/baseline.tsv.gz --candidate examples/0.5/candidate.csv --output "${PARISON_CI_TEMP}"/parison-0.5-smoke

parison validate-inputs --records --recipe examples/0.7/revenue.recipe.json --baseline examples/0.7/baseline.csv --candidate examples/0.7/candidate.jsonl

parison compare --recipe examples/0.7/revenue.recipe.json --baseline examples/0.7/baseline.csv --candidate examples/0.7/candidate.jsonl --output "${PARISON_CI_TEMP}"/parison-0.7-smoke

parison verify "${PARISON_CI_TEMP}"/parison-0.7-smoke

parison validate-inputs --records --recipe examples/0.8/multiset.recipe.json --baseline examples/0.8/baseline.csv --candidate examples/0.8/candidate.jsonl

parison compare --recipe examples/0.8/multiset.recipe.json --baseline examples/0.8/baseline.csv --candidate examples/0.8/candidate.jsonl --output "${PARISON_CI_TEMP}"/parison-0.8-smoke

parison verify "${PARISON_CI_TEMP}"/parison-0.8-smoke

parison inspect "${PARISON_CI_TEMP}"/parison-0.8-smoke

parison compare --recipe examples/0.8/multiset-raw.recipe.json --baseline examples/0.8/baseline.csv --candidate examples/0.8/candidate.jsonl --output "${PARISON_CI_TEMP}"/parison-0.8-raw-smoke

parison export-evidence "${PARISON_CI_TEMP}"/parison-0.8-raw-smoke --limit 10 --output "${PARISON_CI_TEMP}"/parison-0.8-evidence.jsonl

set +e
parison compare --recipe examples/0.9/multiset-raw.recipe.json --baseline examples/0.9/baseline.csv --candidate examples/0.9/candidate.jsonl --output "${PARISON_CI_TEMP}"/parison-0.9-raw-smoke
code=$?
set -e
test "$code" -eq 1

parison inspect "${PARISON_CI_TEMP}"/parison-0.9-raw-smoke

parison export-evidence "${PARISON_CI_TEMP}"/parison-0.9-raw-smoke --classification baseline_surplus --limit 10 --output "${PARISON_CI_TEMP}"/parison-0.9-evidence.jsonl

parison validate-suite examples/0.10/mixed-suite.json

parison run-suite --plan examples/0.10/mixed-suite.json --output "${PARISON_CI_TEMP}"/parison-0.10-suite

parison verify "${PARISON_CI_TEMP}"/parison-0.10-suite

parison inspect "${PARISON_CI_TEMP}"/parison-0.10-suite

parison list-suite examples/0.11/scalable-suite.json --tag critical --json
parison run-suite --plan examples/0.11/scalable-suite.json --shard-index 0 --shard-count 2 --output "${PARISON_CI_TEMP}"/parison-0.11-shard-0
parison run-suite --plan examples/0.11/scalable-suite.json --shard-index 1 --shard-count 2 --output "${PARISON_CI_TEMP}"/parison-0.11-shard-1
parison assemble-suite --plan examples/0.11/scalable-suite.json --input "${PARISON_CI_TEMP}"/parison-0.11-shard-0 --input "${PARISON_CI_TEMP}"/parison-0.11-shard-1 --output "${PARISON_CI_TEMP}"/parison-0.11-suite
parison verify "${PARISON_CI_TEMP}"/parison-0.11-suite
parison report-ci "${PARISON_CI_TEMP}"/parison-0.11-suite --format markdown --output "${PARISON_CI_TEMP}"/parison-0.11-summary.md

parison validate-suite examples/0.14/backfill-suite.json
parison run-suite --plan examples/0.14/backfill-suite.json --output "${PARISON_CI_TEMP}"/parison-0.14-suite
parison verify "${PARISON_CI_TEMP}"/parison-0.14-suite

parison validate-suite examples/0.15/payout-suite.json
parison run-suite --plan examples/0.15/payout-suite.json --output "${PARISON_CI_TEMP}"/parison-0.15-suite
parison verify "${PARISON_CI_TEMP}"/parison-0.15-suite

parison verify-postgres-export tests/fixtures/postgres_ingress

parison verify-postgres-pair tests/fixtures/postgres_pair

parison-postgres --help

parison-postgres-pair --help

parison-partitions --help

parison postgres --help

parison postgres table --help

parison postgres pair --help

parison postgres collection --help

parison partitions --help

parison rehearsal --help

parison dossier --help

parison-partitions discover --plan tests/fixtures/partition_discovery/plan.json --recipe tests/fixtures/partition_discovery/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_discovery/candidate.csv --output "${PARISON_CI_TEMP}"/parison-partition-smoke

parison-partitions verify "${PARISON_CI_TEMP}"/parison-partition-smoke --recipe tests/fixtures/partition_discovery/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_discovery/candidate.csv

parison partitions verify "${PARISON_CI_TEMP}"/parison-partition-smoke --recipe tests/fixtures/partition_discovery/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_discovery/candidate.csv

parison-partitions discover --plan tests/fixtures/partition_discovery/plan.json --recipe tests/fixtures/partition_investigation/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_investigation/candidate.csv --output "${PARISON_CI_TEMP}"/parison-investigation-discovery

parison-partitions investigate --plan tests/fixtures/partition_investigation/plan.json --discovery "${PARISON_CI_TEMP}"/parison-investigation-discovery --recipe tests/fixtures/partition_investigation/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_investigation/candidate.csv --output "${PARISON_CI_TEMP}"/parison-investigation-smoke

parison-partitions verify-investigation "${PARISON_CI_TEMP}"/parison-investigation-smoke --discovery "${PARISON_CI_TEMP}"/parison-investigation-discovery --recipe tests/fixtures/partition_investigation/recipe.json --baseline tests/fixtures/partition_discovery/baseline.csv --candidate tests/fixtures/partition_investigation/candidate.csv

python benchmarks/generate_cases.py --output "${PARISON_CI_TEMP}"/parison-bench --rows 1000
python benchmarks/run_cases.py --repeats 1 --max-memory-per-row 6000 "${PARISON_CI_TEMP}"/parison-bench/rows-1000
python benchmarks/generate_aggregate_cases.py --output "${PARISON_CI_TEMP}"/parison-aggregate-bench --rows 1000
python benchmarks/run_cases.py --repeats 1 --max-memory-per-row 6000 "${PARISON_CI_TEMP}"/parison-aggregate-bench/aggregate-global-1000 "${PARISON_CI_TEMP}"/parison-aggregate-bench/aggregate-low-1000 "${PARISON_CI_TEMP}"/parison-aggregate-bench/aggregate-high-1000

python benchmarks/generate_spill_cases.py --output "${PARISON_CI_TEMP}"/parison-spill-bench --rows 1000
python benchmarks/run_spill_cases.py --repeats 1 "${PARISON_CI_TEMP}"/parison-spill-bench/multiset-1000
python benchmarks/generate_spill_cases.py --output "${PARISON_CI_TEMP}"/parison-spill-bench --mode keyed --rows 1000
python benchmarks/run_spill_cases.py --repeats 1 "${PARISON_CI_TEMP}"/parison-spill-bench/keyed-1000
