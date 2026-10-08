# Bundle verification hardening

Date: 8 October 2026

`parison verify RUN_DIRECTORY` now checks both file integrity and the minimum structure needed to interpret a bundle safely:

- the manifest identifies schema version 1 and a completed publication;
- outcome, sensitivity and runtime metadata have valid shapes;
- `result.json` and `report.html` are both covered by lowercase SHA-256 digests;
- every listed regular file still matches its digest; and
- the integrity-checked result's outcome, sensitivity and runtime match the manifest.

This remains an integrity check relative to the supplied manifest. Someone able to replace an entire bundle can still forge a new internally consistent manifest, so verification is not authentication or proof of authorship.
