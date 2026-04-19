#!/bin/bash

# --- GEODATA-OSM CORPORATE IDENTITY UTILS ---

# Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_DIM="\033[2m"
C_PURPLE="\033[1;35m"
C_BLUE="\033[1;34m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_CYAN="\033[0;36m"

# Symbols
S_HEADER="▶▶▶"
S_INFO="  ℹ"
S_SUCCESS="  ✔"
S_WARN="  ⚠"
S_ERROR="  ✖"

# Logging Functions
log_header() {
    echo -e "\n${C_PURPLE}${S_HEADER} $1${C_RESET}"
}

log_info() {
    echo -e "${C_BLUE}${S_INFO}${C_RESET} $1"
}

log_success() {
    echo -e "${C_GREEN}${S_SUCCESS}${C_RESET} $1"
}

log_warn() {
    echo -e "${C_YELLOW}${S_WARN}${C_RESET} $1"
}

log_error() {
    echo -e "${C_RED}${S_ERROR}${C_RESET} $1"
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${C_CYAN}  [DEBUG] $1${C_RESET}"
    fi
}

# Progress Helper
log_step() {
    local current=$1
    local total=$2
    local msg=$3
    echo -e "${C_BOLD}[$current/$total]${C_RESET} $msg"
}

# Path Helper (Relative to Project Root)
get_rel_path() {
    local full_path="$1"
    local root_path="$2"
    echo "${full_path#$root_path/}"
}
