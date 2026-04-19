#!/bin/bash
set -euo pipefail

# 1. CI Utils laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    echo "❌ Fehler: scripts/ci/utils.sh nicht gefunden!"
    exit 1
fi

log_header "DOWNLOAD: OPENSKIMAP"

BASE_DIR="build"
SRC_DIR="$BASE_DIR/src"

# 2. Verzeichnis sicherstellen
# Wir arbeiten relativ zum Projekt-Root
cd "$SCRIPT_DIR/.."
mkdir -p "$SRC_DIR"

# 3. Download mit aria2c (Timestamp-Prüfung)
URL="https://tiles.openskimap.org/openskidata.gpkg"
FILENAME="openskidata.gpkg"

log_info "Prüfe auf neue OpenSkimap-Daten..."

if ! command -v aria2c >/dev/null 2>&1; then
    log_error "aria2c nicht gefunden. Bitte installieren."
    exit 1
fi

# --conditional-get prüft Last-Modified und lädt nur bei Updates
if aria2c --conditional-get=true -x16 -s16 -c -d "$SRC_DIR" -o "$FILENAME" "$URL"; then
    log_success "Download erfolgreich oder Datei bereits aktuell."
else
    log_error "Fehler beim Download von $URL"
    exit 1
fi

log_info "Speicherort: $SRC_DIR/$FILENAME"
