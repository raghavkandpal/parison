# Project initialization contract

Date: 12 October 2026

Status: **development contract**

## Interface

`parison init DIRECTORY` creates one minimal keyed CSV comparison project. `DIRECTORY` may be missing or an existing empty directory. A file, symlink or non-empty directory is rejected before any project file is written.

Successful JSON output reports the destination exactly as supplied and a sorted file list. Human-readable stderr names the next step. The command performs no input discovery, network access or environment inspection.

## Generated project

The four generated files are:

- `recipe.json`, a valid keyed recipe with exact string comparison and summary-only output;
- `baseline.csv` and `candidate.csv`, matching one-row synthetic smoke inputs; and
- `README.md`, containing validation, record-preflight, comparison and bundle-verification commands.

The recipe's snapshot and cutoff are conspicuous placeholders. They make the smoke example executable but are not claims about a user's extraction. The guide requires users to replace them and review keys, filters, completeness, types and comparisons before relying on a result.

## Safety and compatibility

Initialization never overwrites content and has no force mode. Generated files contain no absolute paths, credentials, host details or user data. Their names and content are deterministic for a given Parison version, but they are authoring aids rather than a versioned evidence format.

Partial filesystem failure is reported as a controlled error. A caller should treat the destination as untrusted after such a failure and inspect or remove it before retrying; the command does not delete user-selected paths during recovery.
