#!/bin/bash

source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Setup Helper Functions
# ============================================================================

# Install a package using the appropriate package manager for the OS.
# Currently supports macOS (brew). Exits with error on unsupported platforms.
# Usage: pkg_install <package>
pkg_install () {
    local package=$1

    if [[ "$(uname)" == "Darwin" ]]; then
        brew install "$package"
    else
        c_echo "$COLOR_RED" "  ✗ Unsupported platform. Install $package manually."
        exit 1
    fi
}

# Check if a tool is installed; install if missing, print status if present.
# Usage: ensure_tool <name> [<install_command>]
#   If no install command is provided, falls back to pkg_install.
ensure_tool () {
    local name=$1
    shift
    local install_cmd="${*:-pkg_install $name}"

    if command -v "$name" &> /dev/null; then
        local version
        version=$("$name" --version 2>/dev/null | head -1)
        c_echo "$COLOR_GREEN" "  ✓ $name ($version)"
    else
        c_echo "$COLOR_YELLOW" "  ⟳ Installing $name..."
        eval "$install_cmd"
        if command -v "$name" &> /dev/null; then
            local version
            version=$("$name" --version 2>/dev/null | head -1)
            c_echo "$COLOR_GREEN" "  ✓ $name ($version)"
        else
            c_echo "$COLOR_RED" "  ✗ Failed to install $name"
            exit 1
        fi
    fi
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
