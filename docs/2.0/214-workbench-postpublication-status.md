# Workbench post-publication status

Date: 21 October 2026

Status: **qualified at `57224cb`; merged through PR #59**

Run may receive a cancellation request after immutable bundle publication has
started. A later verification or catalog error can leave an output bundle that
must be checked before the path is reused. The Workbench now reports an error
for that failure and directs the user to open the output in Results, which
verifies it before display. Only the explicit pre-publication cancellation
exception receives the `cancelled` phase. The output remains immutable and
is not silently removed or registered after a failure.

The regression gate covers cancellation during comparison, cancellation
requested during a simulated catalog failure, an actual published and verified
bundle left outside history when cataloging fails, and the browser's failure copy.
It leaves recipe, bundle, exit-code and CLI contracts unchanged.

Exact head `57224cb` passed the complete [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39607547089)
and pull request quality gate before merge.
