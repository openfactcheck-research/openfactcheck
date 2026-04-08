#!/bin/bash

# Source common helpers
source "taskfiles/common.helpers.sh" 2>/dev/null || source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Build Helper Functions
#
# Generic container build system. Each target has:
#   deployments/containers/<target>/Dockerfile
#   deployments/containers/<target>/manifest.sh   — defines what to assemble
#   deployments/containers/<target>/build/         — assembled output (gitignored)
#   deployments/containers/<target>/.hash          — source hash for skip logic
#
# Usage:
#   source taskfiles/build.helpers.sh
#   set_target "api"
#   set_workspace "devhasan"     # optional — enables ECR push
#   assemble
#   build_image
#   push_image                   # only if workspace is set
#   write_hash
# ============================================================================

PROJECT_ROOT=$(pwd)
ENVIRONMENTS_DIR="${PROJECT_ROOT}/deployments/environments"

# Collected image refs for parallel push
declare -a IMAGE_REFS=()

# ============================================================================
# Target setup
# ============================================================================

set_target() {
    local target="$1"

    if [[ -z "$target" ]]; then
        c_echo "$COLOR_RED" "Error: TARGET is required"
        exit 1
    fi

    TARGET="$target"
    CONTAINER_DIR="${PROJECT_ROOT}/deployments/containers/${TARGET}"
    BUILD_DIR="${CONTAINER_DIR}/build"
    HASH_FILE="${CONTAINER_DIR}/.hash"
    MANIFEST="${CONTAINER_DIR}/manifest.sh"

    if [[ ! -f "${CONTAINER_DIR}/Dockerfile" ]]; then
        c_echo "$COLOR_RED" "Error: No Dockerfile found at ${CONTAINER_DIR}/Dockerfile"
        exit 1
    fi

    if [[ ! -f "$MANIFEST" ]]; then
        c_echo "$COLOR_RED" "Error: No manifest.sh found at ${MANIFEST}"
        exit 1
    fi

    # Default image tag (overridden if workspace is set)
    IMAGE_TAG="openfactcheck-${TARGET}:latest"

    export TARGET CONTAINER_DIR BUILD_DIR HASH_FILE MANIFEST IMAGE_TAG
}

set_workspace() {
    local workspace="$1"

    if [[ -z "$workspace" ]]; then
        c_echo "$COLOR_RED" "Error: WORKSPACE is required"
        exit 1
    fi

    local env_tfvars="${ENVIRONMENTS_DIR}/${workspace}.tfvars.json"
    if [[ ! -f "$env_tfvars" ]]; then
        c_echo "$COLOR_RED" "Error: Missing workspace tfvars: $env_tfvars"
        exit 1
    fi

    WORKSPACE="$workspace"
    AWS_ACCOUNT="$(jq -r '.aws_account' "$env_tfvars")"
    AWS_REGION="$(jq -r '.aws_region' "$env_tfvars")"
    AWS_PROFILE="$(jq -r '.aws_profile' "$env_tfvars")"

    ECR_REPO_NAME="openfactcheck-${TARGET}-${WORKSPACE}"
    ECR_REPO_URL="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
    IMAGE_TAG="${ECR_REPO_URL}:latest"

    export WORKSPACE AWS_ACCOUNT AWS_REGION AWS_PROFILE ECR_REPO_NAME ECR_REPO_URL IMAGE_TAG
}

# ============================================================================
# Hashing
# ============================================================================

hash_dir() {
    local dir="$1"
    (
        cd "$dir"
        find . -type f -print0 \
            | sort -z \
            | xargs -0 sha256sum \
            | sha256sum \
            | awk '{print $1}'
    )
}

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
    local new_hash
    new_hash=$(compute_source_hash)

    if [[ -f "$HASH_FILE" ]]; then
        local old_hash
        old_hash=$(cat "$HASH_FILE")
        if [[ "$new_hash" == "$old_hash" ]]; then
            return 1  # not needed
        fi
    fi

    return 0  # needed
}

write_hash() {
    mkdir -p "$(dirname "$HASH_FILE")"
    compute_source_hash > "$HASH_FILE"
    c_echo "$COLOR_GREEN" "[$TARGET] Hash written"
}

# ============================================================================
# Assemble
# ============================================================================

assemble() {
    c_echo "$COLOR_GREEN" "[$TARGET] Assembling build/"

    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Clean caches before assembly
    find "${PROJECT_ROOT}/src" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}/src" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

    # manifest.sh must define assemble_target()
    source "$MANIFEST"
    assemble_target

    c_echo "$COLOR_GREEN" "[$TARGET] Assembled ($(du -sh "$BUILD_DIR" | awk '{print $1}'))"
}

# ============================================================================
# Docker build
# ============================================================================

build_image() {
    c_echo "$COLOR_GREEN" "[$TARGET] Building Docker image: $IMAGE_TAG"

    docker build \
        --platform linux/amd64 \
        --provenance=false \
        -f "${CONTAINER_DIR}/Dockerfile" \
        -t "$IMAGE_TAG" \
        "$BUILD_DIR"

    if [[ $? -eq 0 ]]; then
        c_echo "$COLOR_GREEN" "[$TARGET] Build success!"
        IMAGE_REFS+=("$IMAGE_TAG")
    else
        c_echo "$COLOR_RED" "[$TARGET] Build failed!"
        exit 1
    fi
}

# ============================================================================
# ECR login + push
# ============================================================================

ecr_login() {
    local account="${1:-$AWS_ACCOUNT}"
    local region="${2:-$AWS_REGION}"

    c_echo "$COLOR_GREEN" "Logging into AWS ECR ($account / $region / $AWS_PROFILE)"
    aws ecr get-login-password --region "$region" --profile "$AWS_PROFILE" \
        | docker login --username AWS --password-stdin \
          "${account}.dkr.ecr.${region}.amazonaws.com"
}

push_image() {
    local image_ref="$1"
    local retries="${2:-1}"
    local attempt=0

    while true; do
        if docker push "$image_ref"; then
            c_echo "$COLOR_GREEN" "[$TARGET] Pushed: $image_ref"
            return 0
        fi

        attempt=$((attempt + 1))
        if (( attempt > retries )); then
            c_echo "$COLOR_RED" "[$TARGET] Push failed after $attempt attempt(s): $image_ref"
            return 1
        fi

        c_echo "$COLOR_YELLOW" "[$TARGET] Push failed; re-login and retry ($attempt/$retries)"
        ecr_login
    done
}

push_all() {
    if [[ ${#IMAGE_REFS[@]} -eq 0 ]]; then
        c_echo "$COLOR_YELLOW" "No images to push"
        return 0
    fi

    c_echo "$COLOR_GREEN" "Pushing ${#IMAGE_REFS[@]} image(s)"

    for ref in "${IMAGE_REFS[@]}"; do
        push_image "$ref" 3
    done

    c_echo "$COLOR_GREEN" "All images pushed!"
}

# ============================================================================
# Clean
# ============================================================================

clean() {
    rm -rf "$BUILD_DIR"
    rm -f "$HASH_FILE"
    c_echo "$COLOR_GREEN" "[$TARGET] Cleaned build/ and hash"
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
