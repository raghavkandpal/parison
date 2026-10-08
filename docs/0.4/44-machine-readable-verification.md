# Machine-readable verification

Date: 8 October 2026

`parison verify RUN_DIRECTORY` retains its stable `valid` standard output for interactive use. Automation can request the integrity-checked manifest instead:

```sh
parison verify run --json
```

The command writes one JSON object containing the recorded outcome, sensitivity, runtime and file digests. Diagnostics remain on standard error, and successful integrity verification returns exit code `0` regardless of whether the recorded comparison outcome is PASS, FAIL, ERROR, INCONCLUSIVE or INTERRUPTED.

Consumers must inspect `outcome` separately. Integrity means the covered files still match the supplied manifest; it does not approve or reinterpret the comparison result.
