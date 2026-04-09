#!/bin/bash

# Source common helpers
source "${BASH_SOURCE%/*}/common.helpers.sh"

# ============================================================================
# Deploy Helper Functions
# ============================================================================

# Directories (relative to workspace root)
DEPLOYMENTS_DIR=$(pwd)/deployments
ENVIRONMENTS_DIR="${DEPLOYMENTS_DIR}/environments"
ACCOUNTS_DIR="${DEPLOYMENTS_DIR}/accounts"

# Parse TARGET variable 
parse_target() {
  local target="$1"
  
  # Check if TARGET is provided
  if [ -z "$target" ]; then
    c_echo $COLOR_RED "Error: TARGET is required" >&2
    return 1
  fi
  
  # Parse TARGET format (env:*, acc:*, or shorthand)
  if echo "$target" | grep -q "^env:"; then
    TARGET_TYPE="env"
    TARGET_NAME=$(echo "$target" | sed 's/^env://')
  elif echo "$target" | grep -q "^acc:"; then
    TARGET_TYPE="acc"
    TARGET_NAME=$(echo "$target" | sed 's/^acc://')
  else
    # Shorthand - treat as env
    TARGET_TYPE="env"
    TARGET_NAME="$target"
  fi
  
  export TARGET_TYPE
  export TARGET_NAME
}

# Resolve DEP based on TARGET_TYPE and rules
parse_dep() {
  local dep="$1"
  
  # Apply DEP rules
  if [ "$TARGET_TYPE" = "env" ]; then
    # For env: default to base if DEP not specified
    if [ -z "$dep" ]; then
      RESOLVED_DEP="base"
    else
      RESOLVED_DEP="$dep"
    fi
  elif [ "$TARGET_TYPE" = "acc" ]; then
    # For acc: DEP is required
    if [ -z "$dep" ]; then
      c_echo $COLOR_RED "Error: DEP is required when TARGET is an account (acc:*)" >&2
      return 1
    fi
    RESOLVED_DEP="$dep"
  fi
  
  export RESOLVED_DEP
}

# Compute workspace name (same as TARGET_NAME)
compute_workspace() {
  WORKSPACE="$TARGET_NAME"
  export WORKSPACE
}

# Compute var file path (relative to deployment directory)
compute_varfile() {
  if [ "$TARGET_TYPE" = "env" ]; then
    VAR_FILE="${ENVIRONMENTS_DIR}/${TARGET_NAME}.tfvars.json"
  else
    VAR_FILE="${ACCOUNTS_DIR}/${TARGET_NAME}.tfvars.json"
  fi
  
  export VAR_FILE
}

# Compute backend config path (relative to deployment directory)
compute_backendconf() {
  if [ "$TARGET_TYPE" = "env" ]; then
    # For environments, read aws_account_name from tfvars
    local aws_account_name
    aws_account_name=$(cat "${ENVIRONMENTS_DIR}/${TARGET_NAME}.tfvars.json" 2>/dev/null | jq -r .aws_account_name 2>/dev/null)
    
    if [ -z "$aws_account_name" ] || [ "$aws_account_name" = "null" ]; then
      c_echo $COLOR_RED "Error: Failed to read aws_account_name from ${TARGET_NAME}.tfvars.json" >&2
      return 1
    fi
    
    BACKEND_CONF_ABS="${ACCOUNTS_DIR}/${aws_account_name}.backend.conf"
    BACKEND_CONF="$BACKEND_CONF_ABS"
  else
    BACKEND_CONF_ABS="${ACCOUNTS_DIR}/${TARGET_NAME}.backend.conf"
    BACKEND_CONF="$BACKEND_CONF_ABS"
  fi
  
  export BACKEND_CONF
  export BACKEND_CONF_ABS
}

prepare() {
  local target="$1"
  local dep="$2"
  
  # Parse TARGET
  parse_target "$target" || return 1
  
  # Resolve DEP
  parse_dep "$dep" || return 1
  
  # Compute all configuration values
  compute_workspace
  compute_varfile
  compute_backendconf || return 1
  
  return 0
}

# Display parsed values (for validation/debugging)
info() {
  c_echo $COLOR_CYAN "Target Type: $TARGET_TYPE"
  c_echo $COLOR_CYAN "Target Name: $TARGET_NAME"
  c_echo $COLOR_CYAN "Deployment: $RESOLVED_DEP"
}

# List deployments all
list_deployments() {
  c_echo $COLOR_YELLOW "Available Environments:"
  for file in "${ENVIRONMENTS_DIR}"/*.tfvars.json; do
    [ -e "$file" ] || continue
    env_name=$(basename "$file" .tfvars.json)
    c_echo $COLOR_GREEN "  env:$env_name"
  done
  
  c_echo $COLOR_YELLOW "Available Accounts:"
  for file in "${ACCOUNTS_DIR}"/*.tfvars.json; do
    [ -e "$file" ] || continue
    acc_name=$(basename "$file" .tfvars.json)
    c_echo $COLOR_GREEN "  acc:$acc_name"
  done
}

# ============================================================================
# Terraform Operations
# ============================================================================

TF_BIN="${TF_BIN:-tofu}"

# Check deployment is initialized
tf_check_init() {
  if [ ! -d "${DEPLOYMENTS_DIR}/${RESOLVED_DEP}/.terraform" ]; then
    c_echo "$COLOR_RED" "Error: Deployment not initialized. Run: task deploy:init TARGET=$1"
    return 1
  fi
}

# Prepare, check init, cd into deployment, select workspace
tf_enter() {
  local target="$1"
  local dep="$2"

  prepare "$target" "$dep" || return 1
  tf_check_init "$target" || return 1

  cd "${DEPLOYMENTS_DIR}/${RESOLVED_DEP}" || return 1

  c_echo "$COLOR_YELLOW" "Selecting workspace: ${WORKSPACE}"
  $TF_BIN workspace select -or-create "$WORKSPACE" || return 1
}

tf_init() {
  local target="$1"
  local dep="$2"

  prepare "$target" "$dep" || return 1

  if [ ! -d "${DEPLOYMENTS_DIR}/${RESOLVED_DEP}" ]; then
    c_echo "$COLOR_RED" "Error: Deployment \"${RESOLVED_DEP}\" does not exist"
    return 1
  fi

  if [ ! -f "$BACKEND_CONF_ABS" ]; then
    c_echo "$COLOR_RED" "Error: Backend config not found: ${BACKEND_CONF_ABS}"
    return 1
  fi

  cd "${DEPLOYMENTS_DIR}/${RESOLVED_DEP}" || return 1

  c_echo "$COLOR_YELLOW" "Initializing TF..."
  $TF_BIN init -reconfigure -backend-config="$BACKEND_CONF" || return 1
  c_echo "$COLOR_GREEN" "✓ Terraform initialized"
}

tf_plan() {
  tf_enter "$1" "$2" || return 1
  c_echo "$COLOR_CYAN" "Running plan..."
  $TF_BIN plan -var-file="$VAR_FILE" || return 1
  c_echo "$COLOR_GREEN" "✓ Plan completed"
}

tf_apply() {
  local auto_approve="$3"
  tf_enter "$1" "$2" || return 1

  local flags=""
  [ "$auto_approve" = "true" ] && flags="-auto-approve"

  c_echo "$COLOR_CYAN" "Running apply..."
  $TF_BIN apply -var-file="$VAR_FILE" $flags || return 1
  c_echo "$COLOR_GREEN" "✓ Apply completed: ${RESOLVED_DEP} → ${WORKSPACE}"
}

tf_destroy() {
  tf_enter "$1" "$2" || return 1
  c_echo "$COLOR_RED" "Running destroy..."
  $TF_BIN destroy -var-file="$VAR_FILE" || return 1
  c_echo "$COLOR_GREEN" "✓ Destroy completed"
}

tf_validate() {
  tf_enter "$1" "$2" || return 1
  c_echo "$COLOR_CYAN" "Validating configuration..."
  $TF_BIN validate || return 1
  c_echo "$COLOR_GREEN" "✓ Configuration is valid"
}

tf_output() {
  local target="$1"
  local dep="$2"

  prepare "$target" "$dep" || return 1
  tf_check_init "$target" || return 1

  cd "${DEPLOYMENTS_DIR}/${RESOLVED_DEP}" || return 1

  c_echo "$COLOR_YELLOW" "Workspace: ${WORKSPACE}"
  $TF_BIN workspace select "$WORKSPACE" 2>/dev/null

  c_echo "$COLOR_CYAN" "Outputs:"
  $TF_BIN output
}

# Execute function if script is run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    "$@"
fi