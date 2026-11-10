# Parison tool audit, product review and recommendations

Date/access date: 10 November 2026
Status: **independent audit, findings and recommendations only**. No code, contract, schema, index or changelog was changed. Nothing here approves a scope change; every recommendation needs an owner decision.
Audited base: `develop` at `a88f286` (2.3.0 released, 2.4 in progress).

Priority scale used throughout: **P1** = do now, blocks trust or progress. **P2** = do next, real cost if left. **P3** = worth doing, low urgency.

## What Parison is, and the load assumed

Parison compares a baseline and a candidate dataset on one machine under an explicit, reviewed policy, then publishes a tamper-evident evidence bundle. One operator or one CI job runs it at a time. Inputs (files, SQLite databases, XLSX, XML, a PostgreSQL server) can come from another team, so they are treated as possibly hostile. Scale was judged against that: single process, large files, no concurrent users.

## Top five, in order

1. **P1** Decide whether Parison is for users. There is no external adoption evidence, and the roadmap is written not to need any (finding G1).
2. **P1** Unblock 2.4. Three of ten features are done; the release is stuck behind feature 4 research (G2).
3. **P1** Fix the SQLite virtual-table hole (V1). It is the one confirmed break of an input contract.
4. **P1** Publish to PyPI. The name `parison` is free today (G3).
5. **P2** Close the two smaller invariant gaps: `search_path` (V2) and no-overwrite on other POSIX systems (V3).

## 1. Vulnerabilities

### P1

**V1. A SQLite virtual table passes the "ordinary table" check** (`src/parison/inputs.py:626-642`)

- **What this is:** The SQLite reader accepts only objects whose `sqlite_schema.type` is `table`, then runs `SELECT *` on it.
- **Problem:** SQLite stores virtual tables (for example FTS5) with type `table` too. Verified on this machine: an FTS5 table reports `('t', 'table')`, and `PRAGMA trusted_schema` is `1` on the read connection. A database file from another party can therefore make Parison run virtual-table module code over attacker-shaped shadow tables. This class of input has a history of memory-safety bugs in SQLite, and it breaks the documented "ordinary table" rule.
- **Fix:** After connecting, run `PRAGMA trusted_schema=OFF`. Reject the object when its `sql` starts with `CREATE VIRTUAL` (or use `PRAGMA table_list` and require type `table`). Add one hostile fixture test in `tests/test_sqlite.py`.
- **If we skip it:** The strongest input-safety claim in the product has a known exception.

### P2

**V2. Two PostgreSQL entry points do not pin `search_path`** (`src/parison/postgres_ingress.py:291-293`, `src/parison/postgres_pair.py:68-70`)

- **What this is:** The collection path runs `SET LOCAL search_path TO pg_catalog` (`postgres_collection.py:427`). Single-table ingress and pair export do not.
- **Problem:** A role or database setting such as `search_path = evil, pg_catalog` makes unqualified functions and operators (`has_table_privilege`, `=`) resolve to attacker objects first. The privilege preflight can then be made to lie. It needs a hostile database administrator, so this is not P1.
- **Fix:** Move the `SET LOCAL search_path TO pg_catalog` line into `_configure_transaction`, which all three paths can share.
- **If we skip it:** The same rule is applied in one path and not in the other two.

**V3. No-overwrite publish is not guaranteed on other POSIX systems** (`src/parison/_safe_fs.py:44-47`)

- **What this is:** `rename_no_replace` uses `renameat2` on Linux and `renamex_np` on macOS. Everything else falls to `os.rename`, with a comment that Windows fails when the target exists.
- **Problem:** FreeBSD and other POSIX systems also reach that branch. There `os.rename` silently replaces an existing empty directory, and replaces files. The "atomic, no-overwrite" invariant does not hold.
- **Fix:** Make the fallback `elif sys.platform == "win32"`, and raise `ParisonError("unsupported platform for safe publication")` otherwise.
- **If we skip it:** A raced target can be replaced on an unqualified platform with no error.

**V4. No security policy and no dependency update watch** (repository root, `.github/`)

- **What this is:** Extras pin exact versions (`polars==1.44.2`, `openpyxl==3.1.5`, `psycopg[binary]==3.3.6`). Actions are pinned by commit, which is good.
- **Problem:** There is no `SECURITY.md` and no Dependabot or equivalent. A parser CVE in a pinned extra will not surface, and a reporter has no private channel.
- **Fix:** Add `SECURITY.md` (private report address, supported versions) and a `dependabot.yml` for `pip` and `github-actions`.
- **If we skip it:** Pins that exist for determinism turn into stale parsers.

### P3

**V5. Session token compared with `==`** (`src/parison/workbench_host.py:428`). Use `hmac.compare_digest`. Loopback only, 256-bit token, so the timing risk is small. One line.

**V6. Catalog file is created before it is restricted** (`src/parison/catalog.py:44-57`). `sqlite3.connect` creates the file with the default umask, and `chmod 0o600` runs after the schema is written. Another local user can open it in that window. Create it first with `os.open(path, O_CREAT | O_EXCL, 0o600)`.

**V7. Output-parent symlink check is check-then-use** (`src/parison/_safe_fs.py:16-27`). A local user who can write to the output parent can swap a component for a symlink between the check and `mkdtemp`. Needs local write access to the same directory, so low. Opening the parent with `O_NOFOLLOW` and staging by `dir_fd` closes it; several newer modules already do this.

### What held up

Worth saying, because most of the attack surface was checked and found sound: the Workbench server binds `127.0.0.1` on a random port, checks `Host`, `Origin` and a 256-bit capability, caps request size, threads and read time, and sets a strict CSP with `frame-ancestors 'none'`. The page uses no `innerHTML`. XML rejects DTD and entity declarations. JSON rejects duplicate keys and `NaN`. SQL uses parameters and quoted identifiers. PostgreSQL reads run `REPEATABLE READ READ ONLY` with timeouts. Workspace paths reject `..`, absolute paths and symlinks. CI actions are pinned to commits with `contents: read`.

## 2. Gaps in the code

### P2

**C1. The stage-and-publish block is copied 19 times in 15 modules**

- **What this is:** `tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent)`, `chmod 0o700`, work, `rename_no_replace`, `rmtree` on failure. It appears in `analysis`, `evidence`, `manifesting` (2), `suites` (2), `partition_discovery` (2), `policies`, `reconciliation`, `workbench`, `decision_dossier`, `partition_investigation`, `postgres_ingress`, `postgres_pair`, `postgres_collection`, `postgres_rehearsal`, `representation_assessment`.
- **Problem:** The copies have already drifted. Most clean up with `ignore_errors=True`; `decision_dossier.py:401`, `postgres_collection.py:550` and `representation_assessment.py:532` do not, so a cleanup failure there hides the original error. The publication invariant in AGENTS.md lives in 19 places.
- **Fix:** One context manager in `_safe_fs.py` (`with staged_publication(target) as stage:`). Move callers one module per pull request.
- **If we skip it:** Fixes such as V3 and V7 must be checked against 19 call sites every time.

**C2. SQLite spill setup is copied five times** (`comparison.py:242, 793, 1161`; `reconciliation.py:582, 764`). Same temp directory, same `PRAGMA max_page_count`. Merge into one helper. Same reason as C1.

**C3. The command surface is very large for one maintainer.** `cli.py` registers 66 subcommands, and the package installs five executables (`parison`, `parison-postgres`, `parison-postgres-pair`, `parison-rehearsal`, `parison-partitions`). Every one is a released contract that must stay stable. Fold the four extra executables under `parison` as subcommands in the next major, and mark rarely used commands as advanced in help.

### P3

**C4. Exact pins in optional extras block co-installation.** `polars==1.44.2` will conflict with any project that needs another Polars. Keep exact pins in the CI constraint file and publish a tested range in `pyproject.toml`.

**C5. The largest modules mix several jobs.** `manifesting.py` (2,231 lines), `inputs.py` (1,777), `reconciliation.py` (1,553), `comparison.py` (1,547). `inputs.py` holds every format reader plus recipe drafting. Split by format only when a reader is next changed; do not split for line count.

## 3. Gaps in the product

### P1

**G1. There is no evidence that anyone outside the project uses Parison.**

- **What was found:** The 2.3.0 release assets show 2 downloads each, which matches the release smoke test. The first commit is dated 4 October 2026. In 37 days the project has 799 commits, 46 tagged versions (0.1 to 2.3) and 392 documents. The accepted direction says feature selection "does not wait for real-world approval, customer authorization or production adoption" and commits to this cycle "through at least v5.0".
- **Problem:** Version 2.x and a "stable compatibility baseline" signal maturity that has not been tested by a user. The compatibility promises (old bundles readable, canonical bytes fixed, exit codes fixed) are a real, growing cost paid to nobody. Internal review cannot find the wrong-product risk; only users can.
- **Recommendation:** Add one rule to the decision test: a new feature needs one named external user who asked for it or was observed needing it. Aim for five real migrations verified by people who are not the author before any 2.5 planning.

**G2. Release 2.4 is blocked by its own boundary.**

- **What was found:** Features 1 to 3 of 10 are integrated. Feature 4 (retained partition sessions) has about twenty research documents (295 to 315) on cross-platform destructive cleanup and no qualified protocol. The roadmap says all ten features ship together or not at all.
- **Problem:** Three finished features are held back by one unsolved research problem. The owner decision of 6 November kept the v1 preservation guarantee; that decision is respected here.
- **Recommendation:** Change the release boundary, not the guarantee. Ship features 1 to 3 as 2.4.0. Ship feature 4 later, first as non-destructive only (Parison never deletes a session; it prints the path and the user removes it). That needs no mutation protocol and weakens no guarantee.

**G3. Parison cannot be installed with `pip install parison`.**

- **What was found:** Distribution is GitHub Release assets only; "PyPI remains opt-in". `https://pypi.org/pypi/parison/json` returned 404 on the access date, so the name is free.
- **Problem:** This is the largest single adoption cost, and the name can be taken by someone else.
- **Recommendation:** Publish 2.3.0 to PyPI with trusted publishing. This is a packaging change, so the full-matrix gate applies.

### P2

**G4. A newcomer cannot find the front door.** The README opens with forty lines of release history. There are 66 commands and 392 documents, most of them development records. Put a 60-second quickstart at the top (`pip install`, `parison init`, one compare, one PASS and one FAIL). Move release history to the changelog. Keep `docs/user-guide.md` and `docs/command-reference.md` as the user docs and label the numbered folders as the engineering journal.

**G5. The stated users are on warehouses; live acquisition is PostgreSQL only.** The direction names warehouse migrations first. Connectors would break zero-custody, so do not add them. Write three tested "export then compare" guides instead (Snowflake, BigQuery, Databricks to Parquet, then Parison). This costs documentation, not code.

**G6. Parquet, the most likely warehouse exchange format, needs an extra.** The default install cannot read it. Say so in the first install line of the README (`pip install 'parison[parquet]'`).

### P3

**G7. The Workbench folder picker does not work on Linux** (`workbench_host.py:297-303` raises). Typing a workspace-relative path still works. Say this in the page instead of failing after the click.

**G8. `docs/CURRENT.md` is an agent handoff file in the public docs root.** It is useful, but a reader takes it for product status. Move the one user-relevant line (current version) into the README.

## 4. Feature research

Access date for all sources: 10 November 2026.

**The field.** Datafold archived the open-source `data-diff` in May 2024 and now sells migration validation as a service. The community fork `reladiff` keeps the engine but dropped the dbt integration, and no 2026 release was found. Google's Data Validation Tool is active and does count, aggregate and row-hash checks across warehouses, but it needs live credentials on both sides and produces reports, not portable evidence.

**Design consequence.** Diffing is a commodity. What nobody else offers is the combination Parison already has: no credentials, an explicit reviewed policy, and an evidence bundle a third party can verify. New work should make that combination easy to reach, not add more kinds of evidence.

**Threat to the thesis.** If users do not need portable evidence, Parison is a slower, narrower `reladiff`. G1 is how to find out.

**Non-goals confirmed.** Hosted service, embedded credentials, CDC monitoring, automatic repair, fuzzy matching. The existing boundaries are right.

| Priority | Candidate | Why | Cost |
| --- | --- | --- | --- |
| P1 | PyPI release and `uvx parison` one-line trial | Removes the first adoption step | Small, packaging only |
| P1 | Warehouse export guides (G5) | Reaches the stated users without a connector | Docs and three fixtures |
| P2 | dbt recipe: compare a model built in dev against prod exports | `data-diff` users lost this when the project was archived | One guide plus `parison init` template |
| P2 | Published GitHub Action wrapping `compare` and the summary-safe output | Evidence in a pull request is the easiest demo | Small; examples already exist |
| P2 | Cheap-first triage: counts and aggregates before keyed compare, as one command | Matches the verification ladder; DVT users expect it | Composes existing commands |
| P3 | Second live source pair (MySQL to PostgreSQL) | Common migration; only after a user asks | Large, new dependency |
| P3 | Arrow/ADBC file ingress | Wider reach without credentials | Medium; wait for demand |

## 5. Future direction

**P1. Replace the "through v5.0" feature train with an adoption loop.** The research, build, review cycle has produced a careful tool very fast. More cycles of it will not answer whether the tool is wanted. For the next two months: freeze the surface, fix what this audit found, publish, and put the tool in front of people doing real migrations.

**P1. Slow the version numbers.** Two majors in five weeks makes "stable" hard to believe. Stay on 2.x until a user-reported break forces 3.0.

**P2. Position against the gap `data-diff` left.** One honest article: what Parison does that `reladiff` and DVT do not (evidence, policy, no credentials), and what it does not do (cross-database live diff). That is the launch.

**P3. Keep zero-custody as the identity.** Every candidate in section 4 was chosen to hold it. If a user asks for a live connector, the answer is an export guide first.

## 6. Next steps, in order

1. **P1** Fix V1 on a `fix/` branch with a hostile SQLite fixture test.
2. **P1** Owner decision on G2: ship features 1 to 3 as 2.4.0, feature 4 later as non-destructive.
3. **P1** Publish to PyPI (G3) and rewrite the top of the README (G4).
4. **P1** Find five external users and record what they needed (G1).
5. **P2** Fix V2 and V3 (one line each), add `SECURITY.md` and Dependabot (V4).
6. **P2** Write the warehouse export guides and the dbt recipe (G5, section 4).
7. **P2** Introduce one staged-publication helper and migrate callers (C1), then C2.
8. **P3** V5, V6, V7, C4, G7, G8 as small follow-ups.

## Verdict

The engineering is careful and the security posture is well above normal for a project this size; one confirmed input-contract break (V1) and two small invariant gaps (V2, V3). The main risk is not in the code. It is that a large, stable-labelled product has been built without a user. Fix V1, ship what is finished, publish, and go find users.

Lean: one staging helper and one spill helper would remove roughly 300 lines. No dependency can be dropped.

## Not checked

- The full test suite was **not** run to completion. With Python 3.12 and no test extras installed, 431 tests ran: 32 errored on missing `jsonschema`/`openpyxl`, 1 failed (`test_github_actions.test_native_suites_preserve_regressions_and_discover_feature_tests`, cause not investigated, may be environmental), 18 skipped. `ruff` lint and format passed. No dependencies were installed, to honour "do not edit anything".
- Read in depth: `_safe_fs.py`, the Workbench host and page, SQLite/XML/JSON input paths, PostgreSQL connection setup, CI workflows, product direction and the 2.4 roadmap. Read by search only: `manifesting.py`, `comparison.py`, `reconciliation.py`, `partition_*.py`, `evidence.py`, `suites.py`, `policies.py`.
- Not exercised: Windows paths, a live PostgreSQL server, Parquet and XLSX readers, benchmarks, comparison correctness (keys, tolerances, multiset semantics), released-bundle compatibility.
- V1 was confirmed by probing SQLite directly, not by running a hostile file through `parison compare`. V2, V3, V6 and V7 are from reading the code.
- `docs/README.md` and `CHANGELOG.md` were not updated for this document, as instructed. The documentation index test may flag the new file until it is indexed.

## Sources

- [Datafold: open source data-diff](https://www.datafold.com/blog/open-source-data-diff/)
- [reladiff documentation](https://reladiff.readthedocs.io/en/latest/)
- [reladiff on PyPI](https://pypi.org/project/reladiff/0.4.0)
- [Google Data Validation Tool on PyPI](https://pypi.org/project/google-pso-data-validator)
- [Introducing the Data Validation Tool, Google Open Source Blog](https://opensource.googleblog.com/2021/08/introducing-data-validation-tool.html)
