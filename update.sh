#!/bin/bash
# Intelligenter Orchestrator: prüft auf neue OpenSkiMap-Daten und stößt bei
# Änderung run.sh an (Standard v1.4 §1, Einstiegspunkt 3 von 3 neben
# setup.sh/run.sh). Läuft ohne Änderung minimal-invasiv durch (nur
# Pre-Flight + Download-Check) und triggert den vollen Build nicht
# unnötig.
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
run_log_init "$(run_log_file "${SLUG}_update_history.jsonl")" \
             "$(run_log_file "${SLUG}_update_status.json")"
RUN_LOG_STATUS="error"
RUN_LOG_MESSAGE="Update-Check abgebrochen."
RUN_LOG_ERROR="Unerwarteter Abbruch."

log_header "UPDATE-CHECK: OPENSKIMAP"

# --- PRE-FLIGHT ---
log_step 1 2 "Pre-Flight: Abhängigkeiten prüfen..."
if ! bash "$SCRIPT_DIR/check_dependencies.sh"; then
    RUN_LOG_MESSAGE="Voraussetzungen nicht erfüllt."
    RUN_LOG_ERROR="check_dependencies.sh fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi

mkdir -p "$PROJECT_ROOT/data/src" "$PROJECT_ROOT/work" "$PROJECT_ROOT/dist" "$PROJECT_ROOT/logs"

# --- CHANGE-DETECTION ---
# download.sh nutzt aria2c --conditional-get: Ist die Serverdatei unverändert,
# lässt aria2c die lokale Datei (inkl. mtime) unangetastet. Verglichen wird
# nicht der mtime vor/nach diesem einen Download-Aufruf, sondern gegen den
# mtime, den run.sh beim letzten *erfolgreichen* Build in GPKG_STATE_FILE
# hinterlegt hat — sonst würde ein fehlgeschlagener/abgebrochener Build nie
# erneut versucht, weil die lokale GPKG-Datei seither unverändert bliebe.
GPKG_FILE="$PROJECT_ROOT/data/src/openskidata.gpkg"
GPKG_STATE_FILE="$PROJECT_ROOT/data/.last_build_source_mtime"
last_built_mtime=""
if [ -f "$GPKG_STATE_FILE" ]; then
    last_built_mtime="$(cat "$GPKG_STATE_FILE" 2>/dev/null || true)"
fi

log_step 2 2 "Prüfe auf neue OpenSkiMap-Daten..."
if ! bash "$SCRIPT_DIR/download.sh"; then
    RUN_LOG_MESSAGE="Download fehlgeschlagen."
    RUN_LOG_ERROR="download.sh fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi

current_mtime="$(stat -c %Y "$GPKG_FILE" 2>/dev/null || true)"

if [ -n "$last_built_mtime" ] && [ "$last_built_mtime" = "$current_mtime" ]; then
    log_success "Keine neuen Daten seit dem letzten erfolgreichen Build. Build wird übersprungen."
    RUN_LOG_STATUS="up_to_date"
    RUN_LOG_MESSAGE="Keine neuen Daten, Build übersprungen."
    RUN_LOG_ERROR=""
    log_header "UPDATE-CHECK ABGESCHLOSSEN (KEIN BUILD NÖTIG)"
    exit 0
fi

log_info "Neue Daten erkannt, starte Build (run.sh)..."

if ! GEODATA_SKIP_DOWNLOAD=1 bash "$PROJECT_ROOT/run.sh"; then
    RUN_LOG_STATUS="error"
    RUN_LOG_MESSAGE="Build fehlgeschlagen."
    RUN_LOG_ERROR="run.sh fehlgeschlagen."
    log_error "$RUN_LOG_MESSAGE"
    exit 1
fi

RUN_LOG_STATUS="build_triggered"
RUN_LOG_MESSAGE="Neue Daten erkannt, Build erfolgreich durchgeführt."
RUN_LOG_ERROR=""

log_header "UPDATE ERFOLGREICH ABGESCHLOSSEN"
