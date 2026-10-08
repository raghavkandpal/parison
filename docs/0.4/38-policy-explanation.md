# Effective policy explanation

Date: 8 October 2026

`parison explain RECIPE.json` validates a recipe and writes its complete effective policy as JSON without opening baseline or candidate inputs.

The representation resolves defaults and relationships that otherwise require reading several recipe sections together. Each canonical column includes:

- whether it participates in the key;
- its effective baseline and candidate physical column names;
- its type and effective comparison mode;
- its ordered normalization rules, including an explicit empty list; and
- any configured scale, timezone or numeric tolerance.

The output also includes scope, identity, null equality, exclusions and output sensitivity. It contains no local recipe path, input metadata or record values. Recipe and schema names may themselves be sensitive.

`schema_version` versions the explanation representation independently from `recipe_version`. The same representation is intended for terminal automation and future report views; consumers should reject unsupported schema versions.
