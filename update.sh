#!/bin/bash
# Zentrales Update-Skript für OpenSkiMap
# Wird vom Hauptsystem aufgerufen.
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# 1. Config & Utils laden
if [ -f "scripts/utils.sh" ]; then
    source "scripts/utils.sh"
else
    echo "❌ Fehler: scripts/utils.sh nicht gefunden!"
    exit 1
fi

log_header "OpenSkiMap Update"

# 2. Download der Daten
bash scripts/download.sh

# 3. Konvertierung zu PMTiles
bash scripts/convert.sh

# 4. Finalisierung für das Deployment (dist/ Ordner)
log_section "DEPLOYMENT: Finalisierung..."

# Config erneut laden für Pfade
if [ -f "scripts/config.env" ]; then
    source "scripts/config.env"
fi
BASE_DIR="${SKIMAP_BUILD_DIR:-build}"
TMP_DIR="$BASE_DIR/tmp"

# PMTiles in den dist-Ordner schieben
mkdir -p dist/pmtiles
if [ -f "$TMP_DIR/openskimap.pmtiles" ]; then
    log_info "Kopiere PMTiles nach dist/pmtiles/..."
    cp "$TMP_DIR/openskimap.pmtiles" dist/pmtiles/openskimap.pmtiles
else
    log_error "PMTiles nicht gefunden: $TMP_DIR/openskimap.pmtiles"
    exit 1
fi

# Stylesheet kopieren
log_info "Kopiere Styles nach dist/styles/..."
mkdir -p dist/styles
cp styles/openskimap-style.json dist/styles/openskimap-style.json

# Sprites kopieren
log_info "Kopiere Sprites nach dist/assets/sprites/openskimap/..."
mkdir -p dist/assets/sprites/openskimap
cp assets/sprites/openskimap/* dist/assets/sprites/openskimap/

log_success "OpenSkiMap Plugin erfolgreich aktualisiert und in dist/ bereitgestellt."
