#!/bin/bash
set -euo pipefail

# CI Utils laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    echo "❌ Fehler: $SCRIPT_DIR/ci/utils.sh nicht gefunden!"
    exit 1
fi

log_header "ABHÄNGIGKEITS-CHECK"

MISSING_DEPS=0

check_command() {
    local cmd=$1
    local name=$2
    if command -v "$cmd" >/dev/null 2>&1; then
        log_success "$name ($cmd) gefunden."
    else
        log_error "$name ($cmd) fehlt!"
        MISSING_DEPS=1
    fi
}

# Erforderliche Programme prüfen
check_command "aria2c" "aria2"
check_command "ogr2ogr" "GDAL/ogr2ogr"
check_command "tippecanoe" "Tippecanoe"

if [ $MISSING_DEPS -ne 0 ]; then
    log_error "Einige Abhängigkeiten fehlen. Bitte die Dokumentation unter docs/dependencies.md lesen."
    exit 1
else
    log_success "Alle erforderlichen Abhängigkeiten sind installiert."
fi
