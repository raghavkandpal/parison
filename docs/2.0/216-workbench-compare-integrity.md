# Workbench Compare requires current evidence

Date: 21 October 2026

Status: **fix under qualification**

The released catalog diff may compare stored summary-safe projections after a
bundle becomes modified or missing. Workbench Compare promises a current
verified rehearsal view, so it now rejects either non-current side before
displaying a comparison. The released catalog command and its stored-history
semantics remain unchanged. Users can inspect each live state in History and
open a current bundle in Results for verification.

Regression coverage exercises a modified manifest member and a missing bundle
after two exact-policy runs have been cataloged. The Workbench rejects both.
