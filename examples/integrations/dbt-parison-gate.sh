#!/usr/bin/env sh
set -eu

# Materialize and test the candidate model first. Exporting both model versions
# at one coordinated snapshot remains adapter- and project-specific.
dbt build --select "${DBT_SELECTION:?set DBT_SELECTION}"
"${EXPORT_PARITY_INPUTS:?set EXPORT_PARITY_INPUTS to your extraction executable}"

set +e
parison compare \
  --recipe "${PARISON_RECIPE:?set PARISON_RECIPE}" \
  --baseline "${PARISON_BASELINE:?set PARISON_BASELINE}" \
  --candidate "${PARISON_CANDIDATE:?set PARISON_CANDIDATE}" \
  --output "${PARISON_OUTPUT:?set PARISON_OUTPUT}"
comparison_code=$?
set -e
parison verify "$PARISON_OUTPUT"
exit "$comparison_code"
