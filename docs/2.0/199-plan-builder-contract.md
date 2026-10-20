# Workbench plan-builder contract

Date: 20 October 2026

Status: **active 2.0 feature contract; first slice**

## Purpose

The Workbench plan builder edits the existing Parison recipe language. It does
not create a second plan format, infer approval, or replace authoritative
Python validation.

```sh
parison workbench plan RECIPE --output APPLICATION_DIRECTORY [--open]
```

Before publishing, Parison loads the recipe through the released runtime
loader and computes its effective policy fingerprint. Invalid or unsupported
recipes publish nothing. The generated application contains the caller's exact
UTF-8 JSON text, an explicit recipe version and comparison mode, the effective
policy fingerprint, and equivalent validation and execution commands. It does
not expose the recipe's source path.

## Editing and export

The first slice uses one visible CLI-native JSON editor so every policy choice
remains explicit and every released recipe version remains representable. The
browser checks JSON syntax and downloads `plan.json` locally. It labels the
result an unapproved draft and directs the user to `parison validate-recipe`.
Syntactic browser feedback is never described as Parison validation.

The application is self-contained. Its Content Security Policy blocks remote
content; the only script parses the text and creates the user-requested local
download. It does not start a listener, access source inputs, execute a plan,
or make a network request.

## Preservation rules

- Initial editor bytes equal the selected recipe bytes after HTML decoding.
- Download adds only one terminal newline when the edited text lacks one.
- All recipe content is HTML-escaped before embedding.
- Existing output paths and symlinks are rejected.
- Publication remains atomic and interruption-clean.
- Generated suggestions, visual field controls, continuous authoritative
  validation, and execution are deferred rather than silently approximated.

## Completion gate for the full feature

This slice establishes safe import, explicit editing, draft export, policy
identity and CLI equivalence. The complete plan-builder feature still requires:

- schema-derived controls for all policy-affecting fields;
- authoritative validation of edits without shell-command execution;
- explicit local input locator selection;
- hostile-input coverage for every control family;
- round-trip tests across recipe versions 1--6; and
- unfamiliar-user review proving that suggestions and drafts are not mistaken
  for approved policy.
