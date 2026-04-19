#!/bin/bash
# Zentrales Update-Skript für OpenSkiMap (Standard v1.1)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/scripts"

# 1. CI Utils laden
if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    echo "❌ Fehler: scripts/ci/utils.sh nicht gefunden!"
    exit 1
fi

# --- PHASE 1: PRE-FLIGHT ---
log_header "PHASE 1: PRE-FLIGHT CHECK"
log_step 1 4 "Checking dependencies..."
if ! bash "$SCRIPT_DIR/check_dependencies.sh"; then
    log_error "Voraussetzungen nicht erfüllt. Abbruch."
    exit 1
fi

# Verzeichnisse initialisieren
mkdir -p build/tmp dist

# --- PHASE 2: INGEST ---
log_header "PHASE 2: INGEST (DOWNLOAD)"
log_step 2 4 "Downloading OpenSkiMap data..."
if ! bash "$SCRIPT_DIR/download.sh"; then
    log_error "Download fehlgeschlagen."
    exit 1
fi

# --- PHASE 3: PROCESSING ---
log_header "PHASE 3: PROCESSING (CONVERT)"
log_step 3 4 "Converting to PMTiles..."
if ! bash "$SCRIPT_DIR/convert.sh"; then
    log_error "Konvertierung fehlgeschlagen."
    exit 1
fi

# --- PHASE 4: FINALIZE ---
log_header "PHASE 4: FINALIZE (MANIFEST)"
log_step 4 4 "Generating manifest and deploying to dist/..."
if python3 "$SCRIPT_DIR/generate_manifest.py"; then
    log_success "Build erfolgreich abgeschlossen. Ergebnis in dist/"
else
    log_error "Manifest-Generierung fehlgeschlagen."
    exit 1
fi

log_header "UPDATE ERFOLGREICH ABGESCHLOSSEN"
