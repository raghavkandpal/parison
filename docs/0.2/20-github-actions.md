# GitHub Actions reference

The reference workflow at [`examples/github-actions/parison.yml`](../../examples/github-actions/parison.yml) runs Parison inside the repository's GitHub-hosted runner. Inputs remain in that runner; Parison does not send them to a Parison-operated service.

Copy the workflow into `.github/workflows/parison.yml`, then replace the recipe, baseline and candidate paths with files produced by your pipeline jobs. The install URL is deliberately pinned to the 0.2.0 GitHub Release asset. It will become runnable when that release is published; development checkouts should install the local project instead.

## Outcome and artifact behavior

The comparison step captures Parison's exit code but temporarily returns success so the evidence upload can run. The last step restores the captured code: `0` PASS, `1` FAIL, `2` ERROR, `3` INCONCLUSIVE or `130` interrupted. The output directory includes the GitHub run ID and attempt, preventing an old bundle from satisfying a later upload. A missing bundle makes the upload step fail.

Download an artifact and verify it before review:

```sh
parison verify path/to/downloaded-bundle
```

Verification proves that the files still match their manifest. It does not change or approve the recorded comparison outcome.

## Data handling

The reference job refuses recipes whose output sensitivity is not `summary`. Summary bundles contain counts and policy metadata, not source keys or raw field values. Recipes, schema-like column names and provenance can still be sensitive, so review the bundle contents and repository visibility before enabling uploads.

Do not weaken this guard for workflows triggered by pull requests from forks. Fork-authored code can alter extraction and logging behavior, and uploaded raw artifacts can expose production data to anyone with artifact access. If raw evidence is necessary, use a separately reviewed workflow with trusted inputs, restricted permissions and an explicit retention policy.

GitHub stores the uploaded bundle as a repository Actions artifact. That is customer-controlled storage, not Parison custody; the repository owner remains responsible for access and retention.
