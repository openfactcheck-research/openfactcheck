#!/bin/bash

# ============================================================================
# Engine container manifest — defines what to assemble for the Lambda Engine build
# Ships the engine plus the library layers its block handlers call (chat,
# prompts, messages). Reads the user's encrypted secrets at run time (cloud
# extra), but never imports the api/ package.
# ============================================================================

# Subpackages the engine imports at run time (engine/__init__ registers the
# handlers, which pull chat, prompts, and messages). Kept in sync with the
# rsync list in assemble_target below.
ENGINE_PACKAGES=(engine chat prompts messages)

# Source paths used for hash computation (change detection)
SOURCE_PATHS=(
    "${PROJECT_ROOT}/src/openfactcheck/__init__.py"
    "${PROJECT_ROOT}/pyproject.toml"
    "${PROJECT_ROOT}/VERSION"
    "${CONTAINER_DIR}/Dockerfile"
    "${CONTAINER_DIR}/manifest.sh"
)
for pkg in "${ENGINE_PACKAGES[@]}"; do
    SOURCE_PATHS+=("${PROJECT_ROOT}/src/openfactcheck/${pkg}")
done

# Assemble the build directory with only what this container needs
assemble_target() {
    mkdir -p "$BUILD_DIR/src/openfactcheck"

    # Package source — __init__.py (for __version__) and the engine's runtime layers.
    cp "${PROJECT_ROOT}/src/openfactcheck/__init__.py" "$BUILD_DIR/src/openfactcheck/"
    for pkg in "${ENGINE_PACKAGES[@]}"; do
        rsync -a --exclude='__pycache__' "${PROJECT_ROOT}/src/openfactcheck/${pkg}" "$BUILD_DIR/src/openfactcheck/"
    done

    # Build metadata referenced by pyproject.toml
    cp "${PROJECT_ROOT}/pyproject.toml" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/VERSION" "$BUILD_DIR/"
    cp "${PROJECT_ROOT}/LICENSE" "$BUILD_DIR/" 2>/dev/null || true
    cp "${PROJECT_ROOT}/README.md" "$BUILD_DIR/" 2>/dev/null || true
}
