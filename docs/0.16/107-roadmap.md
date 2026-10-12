# Parison 0.16 roadmap

Status: **release candidate**

## Theme: fast project adoption

Parison 0.15 made repeated rehearsal results easier to interpret. Version 0.16 reduces the work required to adopt that verification loop in a real project without weakening its explicit-policy or local-first model.

## Planned slices

1. Create a minimal, runnable migration project with `parison init`. **Implemented.**
2. Improve failed-run terminal guidance with exact safe investigation commands. **Implemented.**
3. Add tested reference integrations for generic CI, dbt, Airflow and Dagster without making those tools runtime dependencies. **Implemented.**
4. Prove the documented quickstart from a clean installed wheel. **Implemented in Python 3.14 Linux, macOS and Windows CI lanes.**

## Acceptance gates

- Initialization never overwrites existing project content and introduces no dependency or network access.
- Generated recipes remain explicit starting points, not inferred approval policy.
- Every integration example runs Parison as an external CLI and keeps credentials and input acquisition outside Parison.
- Suggested investigation commands disclose no source keys or values and apply only when their prerequisites are satisfied.
- The complete quickstart passes from the built wheel on every supported platform.

## Non-goals

- Interactive prompting or a template engine.
- Embedded orchestrator, warehouse or database clients.
- Hidden policy inference, automatic repair or production-data fixtures.
- YAML recipes or a Parison-managed deployment service.
