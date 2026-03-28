#!/bin/bash
# Output formatting library for consistent script styling
# Source this file in your scripts with: source "$(dirname "$0")/../.lib/output.sh"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m' # No Color

# Unicode symbols (work in most modern terminals)
readonly CHECK='✓'
readonly CROSS='✗'
readonly ARROW='→'
readonly INFO='ℹ'
readonly WARNING='⚠'
readonly ROCKET='🚀'
readonly PACKAGE='📦'
readonly WRENCH='🔧'
readonly SPARKLES='✨'
readonly BUG='🐛'
readonly BOOKS='📚'

# Formatted output functions
log_header() {
    printf "\n%b==> %b%b\n" "$BOLD$BLUE" "$1" "$NC"
}

log_success() {
    printf "%b%s %b%b\n" "$GREEN" "$CHECK" "$1" "$NC"
}

log_error() {
    printf "%b%s %b%b\n" "$RED" "$CROSS" "$1" "$NC" >&2
}

log_warning() {
    printf "%b%s %b%b\n" "$YELLOW" "$WARNING" "$1" "$NC"
}

log_info() {
    printf "%b%s %b%b\n" "$CYAN" "$INFO" "$1" "$NC"
}

log_step() {
    printf "    %b%s%b %b\n" "$DIM" "$ARROW" "$NC" "$1"
}

log_result() {
    local status=$1
    shift
    if [[ $status -eq 0 ]]; then
        printf "    %b%s %s%b\n" "$GREEN" "$CHECK" "$*" "$NC"
    else
        printf "    %b%s %s%b\n" "$RED" "$CROSS" "$*" "$NC"
    fi
}

# Separator lines
log_separator() {
    printf "%b%s%b\n" "$DIM" "────────────────────────────────────────────────────────────" "$NC"
}

# Exit with error message
die() {
    log_error "$1"
    exit "${2:-1}"
}

# Check command availability
require_command() {
    local cmd=$1
    local install_hint=${2:-""}

    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Required command not found: $cmd"
        if [[ -n $install_hint ]]; then
            log_info "Install with: $install_hint"
        fi
        exit 1
    fi
}
