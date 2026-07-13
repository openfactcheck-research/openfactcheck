#!/bin/bash

# ============================================================================
# API Lambda manifest — defines what to assemble for the API deployment package.
#
# The build/ directory is the Docker build context. It holds a buildable copy of
# the project (so the image can install the openfactcheck wheel with its api +
# cloud extras) plus the run.sh startup script. The streaming run endpoint
# executes a pipeline in-process, so the wheel carries the whole library, not
# just api/.
# ============================================================================

# Source paths used for hash computation (change detection). The whole source tree
# is a build input, along with the lock file, project metadata, and the container spec.
SOURCE_PATHS=(
    "${PROJECT_ROOT}/src/openfactcheck"
    "${PROJECT_ROOT}/pyproject.toml"
    "${PROJECT_ROOT}/uv.lock"
    "${PROJECT_ROOT}/VERSION"
    "${TARGET_DIR}/run.sh"
    "${TARGET_DIR}/Dockerfile"
    "${TARGET_DIR}/manifest.sh"
)

# Assemble the Docker build context: a buildable project snapshot plus the run.sh
# startup script.
assemble_target() {
    cp "${PROJECT_ROOT}/pyproject.toml" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/uv.lock" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/VERSION" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/LICENSE" "$BUILD_DIR/" 2>/dev/null || true
    cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/" 2>/dev/null || true
    cp "${TARGET_DIR}/run.sh" "$BUILD_DIR/run.sh"
    rsync -a --exclude='__pycache__' "${PROJECT_ROOT}/src" "$BUILD_DIR/"
}
