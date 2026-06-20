#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

# Validate required environment variables
: "${INFISICAL_MACHINE_CLIENT_ID:?Environment variable INFISICAL_MACHINE_CLIENT_ID is required}"
: "${INFISICAL_MACHINE_CLIENT_SECRET:?Environment variable INFISICAL_MACHINE_CLIENT_SECRET is required}"
: "${PROJECT_ID:?Environment variable PROJECT_ID is required}"
: "${INFISICAL_SECRET_ENV:?Environment variable INFISICAL_SECRET_ENV is required}"
: "${INFISICAL_API_URL:?Environment variable INFISICAL_API_URL is required}"

# Additional validation: check for command injection patterns
if [[ "$INFISICAL_MACHINE_CLIENT_ID" =~ [\$\`\;\|\&\<\>] ]] || \
   [[ "$INFISICAL_MACHINE_CLIENT_SECRET" =~ [\$\`\;\|\&\<\>] ]] || \
   [[ "$PROJECT_ID" =~ [\$\`\;\|\&\<\>] ]] || \
   [[ "$INFISICAL_SECRET_ENV" =~ [\$\`\;\|\&\<\>] ]] || \
   [[ "$INFISICAL_API_URL" =~ [\$\`\;\|\&\<\>] ]]; then
    echo "ERROR: Invalid characters detected in environment variables" >&2
    exit 1
fi

# Authenticate with Infisical (properly quoted to prevent command injection)
INFISICAL_TOKEN=$(infisical login \
    --method=universal-auth \
    --client-id="$INFISICAL_MACHINE_CLIENT_ID" \
    --client-secret="$INFISICAL_MACHINE_CLIENT_SECRET" \
    --plain \
    --silent)
export INFISICAL_TOKEN

# Execute the application with properly quoted variables
exec infisical run \
    --token "$INFISICAL_TOKEN" \
    --projectId "$PROJECT_ID" \
    --env "$INFISICAL_SECRET_ENV" \
    --domain "$INFISICAL_API_URL" \
    -- /commands