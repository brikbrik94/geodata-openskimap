#!/bin/bash
# Kompletter Build-Durchlauf, erzwingt Update (Standard v1.4 §1, Einstiegspunkt
# 2 von 3 neben setup.sh/update.sh). Kann eigenständig laufen (voller
# Download+Build) oder von update.sh nach einem bereits erkannten
# Datenwechsel mit GEODATA_SKIP_DOWNLOAD=1 aufgerufen werden, um den
# Download-Schritt nicht doppelt auszuführen.
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
source "$SCRIPT_DIR/ci/run_logger.sh"

SLUG="geodata_openskimap"
run_log_init "$(run_log_file "${SLUG}_build_history.jsonl")" \
             "$(run_log_file "${SLUG}_build_status.json")"

if [ "${GEODATA_SKIP_DOWNLOAD:-0}" = "1" ]; then
    run_log_str source "external"
else
    run_log_str source "custom"
fi
RUN_LOG_STATUS="error"
RUN_LOG_MESSAGE="Build abgebrochen."
RUN_LOG_ERROR="Unerwarteter Abbruch."

STAGES=()

# --- PHASE 1: PRE-FLIGHT ---
log_header "PHASE 1: PRE-FLIGHT CHECK"
log_step 1 4 "Checking dependencies..."
if ! bash "$SCRIPT_DIR/check_dependencies.sh"; then
    RUN_LOG_MESSAGE="Voraussetzungen nicht erfüllt."
    RUN_LOG_ERROR="check_dependencies.sh fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi

mkdir -p "$PROJECT_ROOT/data/src" "$PROJECT_ROOT/work" "$PROJECT_ROOT/dist" "$PROJECT_ROOT/logs"

# --- PHASE 2: INGEST ---
if [ "${GEODATA_SKIP_DOWNLOAD:-0}" = "1" ]; then
    log_header "PHASE 2: INGEST (DOWNLOAD) — übersprungen, bereits aktuell via update.sh"
else
    log_header "PHASE 2: INGEST (DOWNLOAD)"
    log_step 2 4 "Downloading OpenSkiMap data..."
    if ! bash "$SCRIPT_DIR/download.sh"; then
        RUN_LOG_MESSAGE="Download fehlgeschlagen."
        RUN_LOG_ERROR="download.sh fehlgeschlagen."
        log_error "$RUN_LOG_MESSAGE"
        exit 1
    fi
fi
STAGES+=("download")

# --- PHASE 3: PROCESSING ---
log_header "PHASE 3: PROCESSING (CONVERT)"
log_step 3 4 "Converting to PMTiles..."
if ! bash "$SCRIPT_DIR/convert.sh"; then
    RUN_LOG_MESSAGE="Konvertierung fehlgeschlagen."
    RUN_LOG_ERROR="convert.sh fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi
STAGES+=("convert")

# --- PHASE 4: FINALIZE ---
log_header "PHASE 4: FINALIZE (MANIFEST)"
log_step 4 4 "Generating manifest and deploying to dist/..."
if ! python3 "$SCRIPT_DIR/generate_manifest.py"; then
    RUN_LOG_MESSAGE="Manifest-Generierung fehlgeschlagen."
    RUN_LOG_ERROR="generate_manifest.py fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi
STAGES+=("manifest")

# Merkt sich den mtime des für diesen erfolgreichen Build verwendeten GPKG,
# damit update.sh einen fehlgeschlagenen/abgebrochenen Build erkennt (sonst
# hielte es die Daten für "unverändert" und würde nie erneut bauen, siehe
# GPKG_STATE_FILE in update.sh).
GPKG_FILE="$PROJECT_ROOT/data/src/openskidata.gpkg"
if [ -f "$GPKG_FILE" ]; then
    stat -c %Y "$GPKG_FILE" > "$PROJECT_ROOT/data/.last_build_source_mtime" 2>/dev/null || true
fi

datasets=0
if [ -f "$PROJECT_ROOT/dist/manifest.json" ]; then
    datasets="$(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    print(len(json.load(f).get('datasets', [])))
" "$PROJECT_ROOT/dist/manifest.json" 2>/dev/null || echo 0)"
fi

stages_json="["
for i in "${!STAGES[@]}"; do
    [ "$i" -gt 0 ] && stages_json+=","
    stages_json+="\"${STAGES[$i]}\""
done
stages_json+="]"

run_log_raw stages "$stages_json"
run_log_num datasets "$datasets"
run_log_raw clean false

RUN_LOG_STATUS="ok"
RUN_LOG_MESSAGE="Build erfolgreich."
RUN_LOG_ERROR=""

log_success "Build erfolgreich abgeschlossen. Ergebnis in dist/"
log_header "BUILD ERFOLGREICH ABGESCHLOSSEN"
