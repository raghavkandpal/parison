# Authoring and local catalog guide

## Configure offline editor validation

Export the installed union schemas into your workspace:

```sh
mkdir -p .parison .vscode
parison export-editor-schemas --output .parison
cp examples/editor/vscode-settings.json .vscode/settings.json
```

The export atomically writes two union schemas and their five versioned siblings without remote base identifiers, so all references resolve inside `.parison` without network access. It refuses to overwrite an existing directory. The checked-in settings example associates `*.recipe.json` and common suite filenames with those local files. Editor diagnostics are assistance; keep `validate-recipe` and `validate-suite` as execution gates.

## Index a verified run explicitly

```sh
parison catalog add --database runs/catalog.sqlite runs/orders
parison catalog list --database runs/catalog.sqlite
parison catalog list --database runs/catalog.sqlite --outcome FAIL --kind run
parison catalog list --database runs/catalog.sqlite --policy-sha256 HASH --state current
parison catalog show --database runs/catalog.sqlite runs/orders
parison catalog remove --database runs/catalog.sqlite runs/orders
```

`add` recursively verifies the bundle. `list` is compact path-ordered JSON and rechecks whether each entry is current, modified or missing. `show` uses the bundle path rather than a mutable nickname and returns its full safe projection. `remove` deletes only the index entry.

Copying a bundle and adding both paths is allowed; each entry reports the shared digest count. Moving a bundle deliberately appears as a missing old entry until the new path is added. Delete the SQLite file whenever the index is no longer useful—the source bundles are untouched.

Do not treat the catalog as an evidence archive. It stores safe inspection metadata and paths, while the original verified bundle remains the evidence source.
