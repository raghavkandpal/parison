# JSON field-projection engineering checkpoint

Status: **qualified feature checkpoint**

The first feature in the 1.9 release train is implemented. Recipe versions
4--6 add explicit per-side field projection to the released keyed, aggregate
and multiset semantics. JSON document fields use bounded RFC 6901 pointers;
every other supported source uses exact direct field names. Selectors are part
of the effective policy and fingerprint, while summary results continue to
exclude source names and paths.

Strict installed recipe schemas v4--v6 and preflight schemas v16--v18 cover
the new boundary without changing released schemas. Direct comparisons run
under both memory and SQLite engines, and portable suite-v2 execution is
verified under SQLite. Mixed JSON/direct input and mixed JSON/XML preflight
exercise all three comparison modes.

Fresh blind Standards and Spec review found and corrected three blockers:
schema-only preflight now enforces the same selector/source pairing as
execution; preflight v16--v18 admit and constrain released XML metadata; and
lone-surrogate selectors now produce a controlled policy error instead of an
encoding traceback. Regression coverage also pins selector depth and byte
limits, policy-fingerprint changes, missing/container/index failures, strict
schemas, suite execution and summary safety. Both reviewers cleared the
corrected gate.

Local completion gate: `make check` passes 386 tests on Python 3.14, with 11
optional dependency skips. Exact checkpoint
`c657fb2c3afefa6e2fb495cab59020a0b60bf3b7` passed the full
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39233529242)
on Python 3.11--3.14 across Linux, macOS and Windows, plus the independent
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39233529210).

This completes one of three required 1.9 features. It is not a release
candidate and must not be tagged or published independently. Review and test
evidence qualifies repository development only; it does not establish
extraction truth, policy approval, migration approval or cutover authorization.
