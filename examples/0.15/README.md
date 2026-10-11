# Payout reconciliation gate

This synthetic workflow compares exported processor balance transactions with a ledger representation for one payout. The aggregate case conserves exact scaled-decimal net amounts and transaction counts by currency and reporting category. The keyed case then requires every transaction identifier and field to match exactly.

```sh
parison run-suite --plan examples/0.15/payout-suite.json --output runs/payout-gate
parison verify runs/payout-gate
```

`ledger-with-error.csv` is an intentionally failing fixture: substitute it for `ledger.csv` to see both the fee-category conservation check and transaction diagnosis fail.

Before adapting this example, the extractor must provide a stable settlement snapshot, select the correct payout and status, preserve signed minor-unit meaning, normalize currency consistently and account for reversals. A PASS proves equality only for the supplied synthetic exports and reviewed recipes. It is not a certified accounting control and does not establish that the upstream ledger or processor is correct.
