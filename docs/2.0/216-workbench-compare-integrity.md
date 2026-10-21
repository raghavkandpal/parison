# Workbench Compare requires current evidence

Date: 21 October 2026

Status: **integrated; independent Spec re-review clear**

The released catalog diff may compare stored summary-safe projections after a
bundle becomes modified or missing. Workbench Compare promises a current
verified rehearsal view, so it now rejects either non-current side before
displaying a comparison. The released catalog command and its stored-history
semantics remain unchanged. Users can inspect each live state in History and
open a current bundle in Results for verification.

Regression coverage exercises a modified manifest member and a missing bundle
after two exact-policy runs have been cataloged. The Workbench rejects both.
The fix merged through PR #61 at `caf1e6d`; its exact merge passed the
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39610651284)
and [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39610651251).
