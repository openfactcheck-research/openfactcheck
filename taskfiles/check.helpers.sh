#!/bin/bash

source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Check Helper Functions
# ============================================================================

# Force Root Directory
force_root () {
    DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
    PARENT_DIR=$(dirname $DIR)

    if [ "$(pwd)" != $PARENT_DIR ]
    then
        c_echo $COLOR_RED "You must be in $PARENT_DIR to run"
        exit 1
    fi
}

# Check for required dependencies
check_dependencies () {
    local missing_deps=()
    for dep in "$@"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    if [ ${#missing_deps[@]} -ne 0 ]; then
        c_echo $COLOR_RED "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
