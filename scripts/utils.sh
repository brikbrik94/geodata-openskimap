#!/bin/bash

# 1. Zentrale Konfiguration laden
# Wir suchen config.env im gleichen Ordner wie dieses Skript
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.env" ]; then
    source "$SCRIPT_DIR/config.env"
fi

# 2. Farben definieren
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 3. Logging Funktionen
log_header() {
    echo -e "\n${BLUE}==========================================================${NC}"
    echo -e "${BLUE}   $1${NC}"
    echo -e "${BLUE}==========================================================${NC}"
}

log_section() {
    echo -e "\n${BLUE}👉 $1${NC}"
}

log_success() {
    echo -e "${GREEN}   ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}   ❌ $1${NC}" >&2
}

log_info() {
    echo -e "   ℹ️  $1"
}

log_warn() {
    echo -e "${YELLOW}   ⚠️  $1${NC}"
}
