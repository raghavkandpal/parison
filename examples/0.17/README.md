# Evidence Statement fixture

`parison-statement.json` is the canonical unsigned Statement for the checked-in verified bundle at [`../output`](../output). Tests regenerate it byte for byte, including its single trailing newline, on every supported platform.

The fixture is intentionally unsigned. A signature would bind an external identity and time-dependent transparency material, neither of which belongs in a deterministic cross-platform fixture. Follow the [evidence handoff guide](../../docs/0.17/116-evidence-handoff-guide.md) to authenticate a freshly exported Statement.
