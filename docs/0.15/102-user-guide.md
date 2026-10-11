# Rehearsal history guide

Use catalog history when the same reviewed policy is run repeatedly during a migration, backfill or pipeline rewrite.

## Record each rehearsal

Obtain the exact policy fingerprint and lock it during comparison:

```sh
POLICY=$(parison explain recipe.json | python -c 'import json,sys; print(json.load(sys.stdin)["policy_sha256"])')
parison compare --recipe recipe.json --expected-policy-sha256 "$POLICY" \
  --baseline baseline.csv --candidate candidate.csv --output runs/rehearsal-01
parison catalog add --database .parison/catalog.sqlite runs/rehearsal-01
```

Use a new bundle path for every rehearsal. Re-adding the same path updates that entry instead of retaining a previous version.

## Review progress

```sh
parison catalog history --database .parison/catalog.sqlite --policy-sha256 "$POLICY"
parison catalog diff --database .parison/catalog.sqlite \
  runs/rehearsal-01 runs/rehearsal-02
```

The JSON can be archived or queried with standard tools. A decreasing discrepancy count and eventual PASS are useful signals only because the policy fingerprint is identical. Review `state` before relying on an entry; `modified` and `missing` refer to the live path while the other fields remain the stored, last-verified projection.

## What this workflow proves

It shows how verified result summaries changed for supplied inputs under one exact policy. Input digests reveal whether either snapshot changed between runs.

It does not prove that baseline and candidate exports shared a transaction boundary or CDC watermark. Capture that source-specific evidence in the extraction workflow, and keep catalog databases protected: even summary metadata and equality-revealing digests can be sensitive.
