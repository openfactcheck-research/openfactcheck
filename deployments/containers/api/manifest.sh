#!/bin/bash

# ============================================================================
# API container manifest — defines what to assemble for the Lambda API build
# ============================================================================

# Source paths used for hash computation (change detection)
SOURCE_PATHS=(
    "${PROJECT_ROOT}/src/openfactcheck/__init__.py"
    "${PROJECT_ROOT}/src/openfactcheck/api"
    "${PROJECT_ROOT}/pyproject.toml"
    "${PROJECT_ROOT}/VERSION"
    "${CONTAINER_DIR}/Dockerfile"
    "${CONTAINER_DIR}/manifest.sh"
)

# Assemble the build directory with only what this container needs
assemble_target() {
    mkdir -p "$BUILD_DIR/src/openfactcheck"

    # Package source — only __init__.py (for __version__) and api/
    cp "${PROJECT_ROOT}/src/openfactcheck/__init__.py" "$BUILD_DIR/src/openfactcheck/"
    rsync -a --exclude='__pycache__' "${PROJECT_ROOT}/src/openfactcheck/api" "$BUILD_DIR/src/openfactcheck/"

    # Build metadata referenced by pyproject.toml
    cp "${PROJECT_ROOT}/pyproject.toml" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/VERSION" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/LICENSE" "$BUILD_DIR/" 2>/dev/null || true
    cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/" 2>/dev/null || true
}
