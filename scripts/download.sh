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

# 2. Datenquelle laden (siehe sources/openskimap.env)
SOURCE_ENV="$SCRIPT_DIR/../sources/openskimap.env"
if [ ! -f "$SOURCE_ENV" ]; then
    log_error "Quellen-Definition nicht gefunden: $SOURCE_ENV"
    exit 1
fi
source "$SOURCE_ENV"

BASE_DIR="data"
SRC_DIR="$BASE_DIR/src"

# 3. Verzeichnis sicherstellen
# Wir arbeiten relativ zum Projekt-Root
cd "$SCRIPT_DIR/.."
mkdir -p "$SRC_DIR"

# 4. Download mit aria2c (Timestamp-Prüfung)
URL="$OPENSKIMAP_URL"
FILENAME="$OPENSKIMAP_FILENAME"
LOCAL_FILE="$SRC_DIR/$FILENAME"

if ! command -v aria2c >/dev/null 2>&1; then
    log_error "aria2c nicht gefunden. Bitte installieren."
    exit 1
fi

# Bei einem mehrfach segmentierten Download (-x/-s) kann eine parallele
# Serveraktualisierung mitten im Transfer dazu führen, dass einzelne
# Segmente aus unterschiedlichen Dateiversionen stammen. Das Ergebnis ist
# eine strukturell ungültige GeoPackage-Datei (SQLite: "malformed database
# schema"). ogrinfo kann das per Schema-Lesezugriff erkennen, ohne die
# komplette Datei einzulesen.
validate_gpkg() {
    local file="$1"
    if ! command -v ogrinfo >/dev/null 2>&1; then
        return 0
    fi
    # `|| status=$?` haelt den Fehlschlag in einer Bedingung, damit
    # `set -e` hier nicht sofort abbricht.
    local status=0
    ogrinfo -q "$file" >/dev/null 2>&1 || status=$?
    # ogrinfo/sqlite kann beim Öffnen einer WAL-Datenbank -wal/-shm
    # Begleitdateien anlegen; die gehören nicht zum Download-Ergebnis.
    rm -f "${file}-wal" "${file}-shm"
    return "$status"
}

download_gpkg() {
    aria2c --conditional-get=true -x16 -s16 -c -d "$SRC_DIR" -o "$FILENAME" "$URL"
}

log_info "Prüfe auf neue OpenSkimap-Daten..."

if ! download_gpkg; then
    log_error "Fehler beim Download von $URL"
    exit 1
fi

if ! validate_gpkg "$LOCAL_FILE"; then
    log_warn "Datei beschädigt (ungültiges GeoPackage-Schema). Starte Neu-Download..."
    rm -f "$LOCAL_FILE"
    if ! download_gpkg; then
        log_error "Fehler beim Download von $URL"
        exit 1
    fi
    if ! validate_gpkg "$LOCAL_FILE"; then
        log_error "GeoPackage weiterhin beschädigt auch nach Neu-Download: $LOCAL_FILE"
        exit 1
    fi
    log_success "Neu-Download erfolgreich, Datei ist valide."
else
    log_success "Download erfolgreich oder Datei bereits aktuell."
fi

log_info "Speicherort: $LOCAL_FILE"
