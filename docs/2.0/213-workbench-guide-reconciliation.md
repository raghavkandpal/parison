# Workbench guide reconciliation

Date: 21 October 2026

Status: **development documentation updated; release review remains**

The root quickstart now installs the released 1.9.0 wheel and uses only
released commands. A separate source-checkout path introduces the unreleased
unified `parison workbench --workspace .` application and its six activities.
The guide distinguishes recipe validation from approval and bundle verification
from extraction truth. It does not present the earlier generated evidence and
plan applications as the 2.0 interface.

The three substantial Workbench train features are present on `develop`:
verified Results/Investigation, schema-driven Plans, and bounded Run with
History/Compare. Exact merge `be1b872` passed the [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39605729250)
and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39605728982).

Before a 2.0 candidate, complete an informed human usability review of the
full Plans workflow and a combined Workbench review covering rejected paths,
tampered evidence, cancellation, shutdown and publication/catalog failures.
Recheck the exact candidate head on the required matrix. These development
checks do not authorize a user's policy, migration or cutover.
