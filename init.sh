#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/scripts"

if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    log_header() { echo -e "\n=== $1 ===\n"; }
    log_info() { echo -e "  ℹ $1"; }
    log_success() { echo -e "  ✔ $1"; }
    log_error() { echo -e "  ✖ $1"; }
fi

log_header "INITIALISIERUNG: GEODATA-OPENSKIMAP"

log_info "Erstelle Verzeichnisstruktur..."
mkdir -p "$PROJECT_ROOT/data/src" "$PROJECT_ROOT/work" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/dist/pmtiles" "$PROJECT_ROOT/dist/styles" "$PROJECT_ROOT/dist/assets/sprites"
log_success "Struktur ist bereit."

log_info "Prüfe System-Abhängigkeiten..."
# OpenSkiMap braucht zusätzlich gdal (für ogr2ogr)
MISSING=()
for tool in curl aria2c tippecanoe ogr2ogr python3; do
    if ! command -v "$tool" &> /dev/null; then
        MISSING+=("$tool")
    fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
    log_error "Folgende Tools fehlen: ${MISSING[*]}"
    log_info "Bitte installiere diese via: sudo apt install curl aria2 tippecanoe gdal-bin python3-venv"
    exit 1
fi
log_success "Alle Basis-Tools gefunden."

log_info "Richte Python Umgebung ein..."
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    python3 -m venv "$PROJECT_ROOT/.venv"
fi
log_success "Python Umgebung ist bereit."

log_info "Setze Ausführungsrechte..."
chmod +x "$PROJECT_ROOT/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/"*.py 2>/dev/null || true

log_header "SETUP ERFOLGREICH ABGESCHLOSSEN"
