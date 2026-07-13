#!/bin/bash

# Source common helpers
source "taskfiles/common.helpers.sh" 2>/dev/null || source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Build Helper Functions
#
# Builds Lambda deployment zips, one per directory under deployments/artifacts/.
# Each target <name> has:
#   deployments/artifacts/<name>/Dockerfile    — assembles + zips in the runtime image
#   deployments/artifacts/<name>/run.sh         — handler startup script
#   deployments/artifacts/<name>/manifest.sh    — defines the build context
#   deployments/artifacts/<name>/build/         — build context + exported zip (gitignored)
#   deployments/artifacts/<name>/.hash          — source hash for skip logic
#
# Dependencies are installed inside the arm64 Lambda runtime image (their exact native
# builds) and zipped there deterministically; only the zip is exported.
#
# Usage:
#   source taskfiles/build.helpers.sh
#   build_all            # build every target (skips unchanged)
#   build_all force      # build every target, ignoring the change hash
#   clean_all            # remove every target's build/ and hash
# ============================================================================

PROJECT_ROOT=$(pwd)
ARTIFACTS_ROOT="${PROJECT_ROOT}/deployments/artifacts"

# ============================================================================
# Target setup
# ============================================================================

set_target() {
    local target="$1"

    if [[ -z "$target" ]]; then
        c_echo "$COLOR_RED" "Error: target is required"
        exit 1
    fi

    TARGET="$target"
    TARGET_DIR="${ARTIFACTS_ROOT}/${TARGET}"
    BUILD_DIR="${TARGET_DIR}/build"
    HASH_FILE="${TARGET_DIR}/.hash"
    MANIFEST="${TARGET_DIR}/manifest.sh"
    DOCKERFILE="${TARGET_DIR}/Dockerfile"

    for f in "${TARGET_DIR}/run.sh" "$DOCKERFILE" "$MANIFEST"; do
        if [[ ! -f "$f" ]]; then
            c_echo "$COLOR_RED" "Error: missing $f"
            exit 1
        fi
    done

    export TARGET TARGET_DIR BUILD_DIR HASH_FILE MANIFEST DOCKERFILE
}

# ============================================================================
# Hashing (change detection)
# ============================================================================

compute_source_hash() {
    # manifest.sh must define SOURCE_PATHS as an array
    local source_paths
    source_paths=$(source "$MANIFEST" && echo "${SOURCE_PATHS[@]}")

    # shellcheck disable=SC2086
    find $source_paths -type f 2>/dev/null \
        | sort \
        | xargs sha256sum \
        | sha256sum \
        | awk '{print $1}'
}

build_needed() {
    local new_hash old_hash
    new_hash=$(compute_source_hash)
    old_hash=$(cat "$HASH_FILE" 2>/dev/null)

    # Rebuild unless the source is unchanged and a zip is already present.
    if [[ "$new_hash" == "$old_hash" ]] && ls "$BUILD_DIR"/*.zip >/dev/null 2>&1; then
        return 1  # not needed
    fi
    return 0  # needed
}

write_hash() {
    mkdir -p "$(dirname "$HASH_FILE")"
    compute_source_hash > "$HASH_FILE"
    c_echo "$COLOR_GREEN" "[$TARGET] Hash written"
}

# ============================================================================
# Build one target — assemble the context, zip it in Docker, export the zip
# ============================================================================

assemble() {
    c_echo "$COLOR_GREEN" "[$TARGET] Assembling build context"
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # manifest.sh must define assemble_target()
    source "$MANIFEST"
    assemble_target
}

build_zip() {
    c_echo "$COLOR_GREEN" "[$TARGET] Building deployment zip in Docker (linux/arm64)"

    docker build \
        --platform linux/arm64 \
        --target export \
        --output "type=local,dest=${BUILD_DIR}" \
        -f "$DOCKERFILE" \
        "$BUILD_DIR" || {
        c_echo "$COLOR_RED" "[$TARGET] Docker build failed!"
        exit 1
    }

    if ! ls "$BUILD_DIR"/*.zip >/dev/null 2>&1; then
        c_echo "$COLOR_RED" "[$TARGET] No zip produced"
        exit 1
    fi

    # Keep only the exported zip; the assembled context was only Docker build input.
    find "$BUILD_DIR" -mindepth 1 -maxdepth 1 ! -name '*.zip' -exec rm -rf {} +

    c_echo "$COLOR_GREEN" "[$TARGET] Built $(du -h "$BUILD_DIR"/*.zip | awk '{print $2" ("$1")"}')"
}

build_one() {
    assemble
    build_zip
    write_hash
}

# ============================================================================
# Build / clean every target under deployments/artifacts/
# ============================================================================

build_all() {
    local force="$1" dir target built=0

    for dir in "$ARTIFACTS_ROOT"/*/; do
        [[ -d "$dir" ]] || continue
        target=$(basename "$dir")
        set_target "$target"

        if [[ "$force" == "force" ]] || build_needed; then
            build_one
            built=$((built + 1))
        else
            c_echo "$COLOR_YELLOW" "[$target] Skipping build — source unchanged"
        fi
    done

    if [[ "$built" -eq 0 ]]; then
        c_echo "$COLOR_YELLOW" "All targets up to date"
    fi
}

clean_all() {
    local dir target

    for dir in "$ARTIFACTS_ROOT"/*/; do
        [[ -d "$dir" ]] || continue
        target=$(basename "$dir")
        set_target "$target"
        rm -rf "$BUILD_DIR"
        rm -f "$HASH_FILE"
        c_echo "$COLOR_GREEN" "[$target] Cleaned build/ and hash"
    done
}

# ============================================================================
# Auto tfvars — writes build metadata for Terraform
# ============================================================================

write_tfvars() {
    local version
    version=$(cat "${PROJECT_ROOT}/VERSION" 2>/dev/null || echo "unknown")
    local commit
    commit=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    local tfvars_file="${PROJECT_ROOT}/deployments/base/ignore.build.auto.tfvars"

    {
        echo "#--------------------------------------------------------------"
        echo "# Auto-generated by build.helpers.sh — do not edit."
        echo "#--------------------------------------------------------------"
        echo "build_version = \"${version}\""
        echo "commit = \"${commit}\""
    } > "$tfvars_file"

    c_echo "$COLOR_GREEN" "Wrote $tfvars_file"
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
