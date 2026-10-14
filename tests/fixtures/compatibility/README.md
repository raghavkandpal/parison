# Historical compatibility fixtures

These immutable synthetic bundles were emitted by the exact source at the named release tag. Generation ran the tagged CLI with matching installed-distribution version metadata; current Parison only reads the resulting files.

| Fixture | Producer | Artifact family |
| --- | --- | --- |
| `aggregate-0.7.0` | tag `0.7.0` | aggregate-v1 run, result schema 2 |
| `multiset-0.8.0` | tag `0.8.0` | multiset-v1 run, result schema 3 |
| `suite-v1-0.10.0` | tag `0.10.0` | suite-v1 with keyed, aggregate and multiset children |
| `suite-v2-0.11.0` | tag `0.11.0` | suite-v2 with keyed, aggregate and multiset children |

Do not regenerate these fixtures with current code. Add a new directory when a new artifact family or version creates a compatibility obligation. `tests.test_compatibility` pins each top-level manifest digest so any byte change requires explicit review.
