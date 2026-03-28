#!/bin/bash

source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Release Helper Functions
# ============================================================================

# Validate version format
validate_version() {
  local version="$1"
  local rx='^v[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$'

  if ! [[ $version =~ $rx ]]; then
    c_echo $COLOR_RED "Version must match vX.Y.Z or vX.Y.ZaX, vX.Y.ZbX, vX.Y.ZrcX"
    return 1
  fi
}

# Check if on main branch
check_main_branch() {
  local branch=$(git rev-parse --abbrev-ref HEAD)

  if [ "$branch" != "main" ]; then
    c_echo $COLOR_RED "Must be on main branch (currently on $branch)"
    return 1
  fi
}

# Check for uncommitted changes
check_clean_tree() {
  if [[ -n $(git status -s) ]]; then
    c_echo $COLOR_RED "Uncommitted changes detected:"
    git status -s
    return 1
  fi
}

# Update VERSION file
update_version_file() {
  local version="$1"
  local version_num="${version#v}"

  echo "$version_num" > VERSION
}

# Check if version is pre-release
is_prerelease() {
  local version="$1"

  if [[ $version =~ (a|b|rc)[0-9]+$ ]]; then
    return 0
  fi
  return 1
}

# Sync with remote
sync_with_remote() {
  git fetch -q || return 1
  git pull origin main -q || return 1
}

# Check if in sync with remote
check_sync_with_remote() {
  local branch=$(git rev-parse --abbrev-ref HEAD)
  local local_commit=$(git rev-parse $branch)
  local remote_commit=$(git rev-parse origin/$branch)

  if [ "$local_commit" != "$remote_commit" ]; then
    c_echo $COLOR_RED "Out of sync with remote"
    git status
    return 1
  fi
}

# Check if tag already exists
check_tag_exists() {
  local version="$1"

  if git tag -l | grep -q "^${version}$"; then
    c_echo $COLOR_RED "Tag $version already exists"
    echo "Existing tags:"
    git tag
    return 1
  fi
}

# Get changelog since last tag
get_changelog() {
  local previous_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

  if [ -z "$previous_tag" ]; then
    git log --pretty=oneline
  else
    git log --pretty=oneline "${previous_tag}.."
  fi
}

# Confirmation prompt
confirm_release() {
  local version="$1"
  local changelog="$2"

  c_echo $COLOR_YELLOW "
────────────────────────────────────────────────────────────────────────────────
                           Confirmation
────────────────────────────────────────────────────────────────────────────────
"
  c_echo $COLOR_YELLOW "You are about to release $version"
  echo
  c_echo $COLOR_YELLOW "Changes:"
  echo "$changelog" | head -20
  if [ $(echo "$changelog" | wc -l) -gt 20 ]; then
    c_echo $COLOR_YELLOW "... and $(( $(echo "$changelog" | wc -l) - 20 )) more commits"
  fi
  echo
  c_echo $COLOR_YELLOW "Are you sure? (y/n, default: n)"
  read -r CONFIRMATION

  if [[ "$CONFIRMATION" != "y" ]]; then
    c_echo $COLOR_RED "Cancelled."
    return 1
  fi
}

# Get commit message for release
get_commit_message() {
  local version="$1"
  local changelog="$2"

  cat << EOF
🚀 Release $version

Changes:

$changelog
EOF
}

# Commit and tag release
commit_and_tag() {
  local version="$1"
  local changelog="$2"

  local message=$(get_commit_message "$version" "$changelog")

  git add VERSION
  git commit -m "$message"
  git tag -a "$version" -m "Release $version"
}

# Push to remote
push_to_remote() {
  local version="$1"

  git push origin main
  git push origin "$version"
}

# Create GitHub release
create_github_release() {
  local version="$1"
  local prerelease_flag=""

  if is_prerelease "$version"; then
    prerelease_flag="--prerelease"
    c_echo $COLOR_YELLOW "Creating pre-release on GitHub..."
  else
    c_echo $COLOR_CYAN "Creating release on GitHub..."
  fi

  gh release create "$version" --generate-notes $prerelease_flag
}

# Run all pre-release checks
run_all_checks() {
  local version="$1"
  local failed=0

  run_check "Version format" "bash taskfiles/release.helpers.sh validate_version $version 2>/dev/null" || failed=1
  run_check "Main branch" "bash taskfiles/release.helpers.sh check_main_branch 2>/dev/null" || failed=1
  run_check "Remote sync" "bash taskfiles/release.helpers.sh sync_with_remote 2>/dev/null" || failed=1
  run_check "Sync check" "bash taskfiles/release.helpers.sh check_sync_with_remote 2>/dev/null" || failed=1
  run_check "Clean tree" "bash taskfiles/release.helpers.sh check_clean_tree 2>/dev/null" || failed=1
  run_check "Tag unique" "bash taskfiles/release.helpers.sh check_tag_exists $version 2>/dev/null" || failed=1

  if [ $failed -eq 1 ]; then
    printf '\n'
    c_echo $COLOR_RED "✗ Pre-release checks failed"
    return 1
  fi
}

# Run check and display result
run_check() {
  local check_name="$1"
  local check_cmd="$2"

  printf "  • $check_name "

  if eval "$check_cmd" > /dev/null 2>&1; then
    c_echo $COLOR_GREEN "✓"
    return 0
  else
    c_echo $COLOR_RED "✗"
    return 1
  fi
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi
