# Workbench Impeccable UI audit

Date: 20 October 2026

Status: audit recorded; production UI unchanged

## Purpose

Record the first reproducible design-system and rendered-browser review of the
unified Workbench before the next implementation window. This is design
evidence, not verification evidence, policy approval, or release approval.

## Audit setup

- Impeccable 4.7.0 was installed project-locally with automatic hooks disabled.
- The pinned detector engine was 0.1.16.
- The installation remains untracked under `.agents/`; it is not vendored by
  this checkpoint because it includes a roughly 19 MB detector binary.
- The source target was `src/parison/workbench_page.py`.
- The static detector reported no findings.
- The rendered detector inspected the default desktop viewport and a
  390 x 844 mobile viewport against a temporary loopback Workbench host.

## Findings

The audit scored the current interface 13/20 (acceptable): accessibility 3/4,
performance 4/4, theming 1/4, responsive behavior 2/4, and integrity 3/4.

Rendered desktop detection found four `undersized-ui-text` warnings for the
10.2 px **Planned** labels and one `kicker-above-heading` warning for the
**Verified evidence** label above **Results**. The 390 x 844 pass found only
the kicker warning because the Planned labels are hidden at that viewport.

The prioritized manual findings are:

1. **P1 — responsive loaded-plan controls.** The Plans editor footer and
   actions can crowd or overflow at 390 px once a plan is loaded.
2. **P2 — mobile targets.** Workbench navigation targets are approximately
   34 px high rather than the recommended 44 px touch target.
3. **P2 — planned-state contrast.** Planned navigation text uses `#667085` on
   `#101828`, approximately 3.57:1.
4. **P2 — theme structure.** The established palette is repeated as raw values
   instead of a compact set of semantic CSS custom properties.
5. **P3 — planned-state typography.** The desktop Planned labels render at
   10.2 px.
6. **P3 — generic eyebrow copy.** Labels such as **Verified evidence** add
   hierarchy weakly and should be removed or made specific.

Positive evidence: controls have labels, native controls and focus treatment
are retained, empty states are clear, and the UI adds no frontend dependency.

## Recommended implementation slice

Apply Impeccable's `adapt`, `layout`, `colorize`, and `polish` guidance as one
small UI-only checkpoint:

- make loaded Plans controls fit and remain legible at 390 px;
- raise mobile navigation and action targets to at least 44 px;
- improve Planned-label size and contrast without overstating unavailable
  activities;
- introduce a small semantic token layer for the existing palette rather than
  adding a theme system;
- remove or rewrite generic eyebrow labels while preserving the report-aligned
  Results and Plans hierarchy.

This slice must not introduce a framework or runtime dependency, widen local
filesystem access, add execution, or alter the Workbench security boundary.
Run source and rendered detection again, inspect desktop and 390 x 844 states,
run focused Workbench tests, and pass `make check` before committing.

## Copy-ready next-window prompt

```text
Continue Parison 2.0 Workbench development in /Users/raghav/projects/parity-repo on branch develop. Start with `make context` and preserve all unrelated work. The implemented code checkpoint is 4233c8542b80dbc07546a63dd7697607ac29bfa2; its quality gate and Python 3.11-3.14 macOS/Windows built-wheel matrix are green. The documentation checkpoint before this audit is 293199d. Read docs/2.0/206-workbench-impeccable-audit.md and the linked active 2.0 contracts before editing.

The project-local Impeccable 4.7.0 installation under `.agents/` is intentionally untracked and includes the pinned 0.1.16 detector. Do not commit or delete it. Use the installed `impeccable` skill and the `ponytail` skill. Run `.agents/skills/impeccable/scripts/impeccable context --target src/parison/workbench_page.py` once, then implement the smallest coherent UI refinement slice guided by adapt, layout, colorize, and polish: make the loaded Plans footer/actions robust at 390 px, provide at least 44 px mobile navigation/action targets, improve Planned-label size and contrast, introduce only a compact semantic CSS-variable layer for the existing palette, and remove or rewrite generic eyebrow labels while preserving Results/Plans semantics and the HTML-report visual baseline.

Do not add a frontend framework or dependency, network behavior, broader filesystem access, execution, persistence, or a new Workbench activity. Preserve the loopback capability boundary, strict routes, summary-safe output, native picker constraints, exact plan validation, and all released compatibility guarantees. Verify empty and loaded Results/Plans states in a browser at desktop and 390 x 844, rerun both source and rendered Impeccable detection, add narrowly scoped regression coverage where behavior changes, and run `make check`. Update active 2.0 documentation and CHANGELOG.md for user-visible behavior. Commit and push one coherent checkpoint on develop, then confirm exact-commit CI. Do not open a release candidate, tag, publish, or open a PR yet. Stop gracefully and return a fresh copy-ready handoff before only 5% of the active allocation remains.
```

