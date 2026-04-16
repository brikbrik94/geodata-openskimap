#!/bin/bash
set -euo pipefail

# 1. Utils & Config laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/utils.sh" ]; then
    source "$SCRIPT_DIR/utils.sh"
else
    echo "❌ Fehler: utils.sh nicht gefunden!"
    exit 1
fi

log_header "DOWNLOAD: OPENSKIMAP"

BASE_DIR="${SKIMAP_BUILD_DIR:-$OVERLAYS_BUILD_DIR/openskimap}"
SRC_DIR="$BASE_DIR/src"

# 2. Verzeichnis sicherstellen
mkdir -p "$SRC_DIR"
cd "$SRC_DIR"

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
