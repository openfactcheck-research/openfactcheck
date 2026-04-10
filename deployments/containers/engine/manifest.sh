#!/bin/bash

# ============================================================================
# Engine container manifest — defines what to assemble for the Lambda Engine build
# Engine is pure — no API or database dependencies
# ============================================================================

# Source paths used for hash computation (change detection)
SOURCE_PATHS=(
    "${PROJECT_ROOT}/src/openfactcheck/__init__.py"
    "${PROJECT_ROOT}/src/openfactcheck/engine"
    "${PROJECT_ROOT}/pyproject.toml"
    "${PROJECT_ROOT}/VERSION"
    "${CONTAINER_DIR}/Dockerfile"
    "${CONTAINER_DIR}/manifest.sh"
)

# Assemble the build directory with only what this container needs
assemble_target() {
    mkdir -p "$BUILD_DIR/src/openfactcheck"

    # Package source — __init__.py (for __version__) and engine/ only
    cp "${PROJECT_ROOT}/src/openfactcheck/__init__.py" "$BUILD_DIR/src/openfactcheck/"
    rsync -a --exclude='__pycache__' "${PROJECT_ROOT}/src/openfactcheck/engine" "$BUILD_DIR/src/openfactcheck/"

    # Build metadata referenced by pyproject.toml
    cp "${PROJECT_ROOT}/pyproject.toml" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/VERSION" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/LICENSE" "$BUILD_DIR/" 2>/dev/null || true
    cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/" 2>/dev/null || true
}
