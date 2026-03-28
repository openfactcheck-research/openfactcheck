#!/bin/bash

# Source common helpers
source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Dev Helper Functions
# ============================================================================

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
