from __future__ import annotations

import json
from pathlib import Path

from .core import ParisonError


_RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "replace-with-shared-snapshot",
        "cutoff": "1970-01-01T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "string", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}

_README = """# Parison migration check

This starter compares two keyed CSV outputs locally and publishes summary-only evidence.

1. Replace `baseline.csv` and `candidate.csv` with outputs captured at the same logical point.
2. Review `recipe.json`: set the shared snapshot, cutoff, filters, keys, types and comparison rules.
3. Validate and run:

```sh
parison validate-recipe recipe.json
parison validate-inputs --recipe recipe.json --baseline baseline.csv --candidate candidate.csv --records
parison compare --recipe recipe.json --baseline baseline.csv --candidate candidate.csv --output run
parison verify run
```

The generated data is only a smoke test. Parison records the scope assertions but cannot prove
that upstream extraction honored them. Do not treat a PASS as proof of coordinated snapshots
until your extraction process provides that guarantee.
"""


def init_project(directory: str | Path) -> list[str]:
    destination = Path(directory)
    if destination.is_symlink():
        raise ParisonError(f"project destination must not be a symlink: {destination}")
    if destination.exists():
        if not destination.is_dir():
            raise ParisonError(f"project destination is not a directory: {destination}")
        if any(destination.iterdir()):
            raise ParisonError(f"project destination is not empty: {destination}")
    else:
        try:
            destination.mkdir(parents=True)
        except OSError as exc:
            raise ParisonError(f"cannot create project directory: {exc}") from exc

    files = {
        "README.md": _README,
        "baseline.csv": "id,value\nexample,same\n",
        "candidate.csv": "id,value\nexample,same\n",
        "recipe.json": json.dumps(_RECIPE, indent=2) + "\n",
    }
    try:
        for name, contents in files.items():
            with (destination / name).open("x", encoding="utf-8") as handle:
                handle.write(contents)
    except OSError as exc:
        raise ParisonError(f"cannot write project: {exc}") from exc
    return sorted(files)
