#!/bin/bash

# ============================================================================
# Common Helper Functions
# ============================================================================

# Color Codes
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_CYAN='\033[0;36m'
COLOR_RESET='\033[0m'

# Color Echo Function
c_echo () {
    local color=$1
    local txt=$2

    echo -e "${color}${txt}${COLOR_RESET}"
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
