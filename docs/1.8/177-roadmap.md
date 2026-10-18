# Parison 1.8 roadmap

Status: **active**

Theme: explicit structured-record projection

## Release train

1. JSON document projection: select one array of flat record objects with an
   RFC 6901 JSON Pointer. Gate: all comparison modes, drafting, suites,
   preflight/evidence and hostile-input cases pass. **Complete locally; exact-commit CI pending.**
2. XML record projection: select repeated records with a bounded element path
   and explicit namespaces. Gate: scalar mapping, structural ambiguity,
   security limits and all existing workflows pass. **Complete locally; exact-commit CI and review pending.**
3. XLSX named-table projection: select one exact worksheet table by name and
   reuse the released cell-value policy. Gate: table identity, bounds,
   formulas, suites, evidence and all comparison modes pass. **Next.**

After each gate, run `make check`, commit coherently and push for exact-commit
CI. Do not open a candidate or release any subset. Candidate review begins only
after the combined train passes its full qualification gate.

## Compatibility

All selectors are local, explicit and bounded. They feed existing typed rows
under `semantic-scalar-v1`. Recipe versions 1--3, comparison semantics,
canonical values, result schemas, exit codes and historical bundle readers are
unchanged. New strict preflight schemas preserve all released schema files.
