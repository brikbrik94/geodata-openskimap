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

log_section "CONVERT: OPENSKIMAP -> PMTILES (Original Layer Names)"

BASE_DIR="${SKIMAP_BUILD_DIR:-$OVERLAYS_BUILD_DIR/openskimap}"
SRC_DIR="$BASE_DIR/src"
TMP_DIR="$BASE_DIR/tmp"

# 2. Pfade definieren
INPUT_FILE="$SRC_DIR/openskidata.gpkg"
OUTPUT_PMTILES="$TMP_DIR/openskimap.pmtiles"

if [ ! -f "$INPUT_FILE" ]; then
    log_error "Eingabedatei nicht gefunden: $INPUT_FILE"
    exit 1
fi

# In den Arbeitsordner wechseln
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

# 3. Extraktion der Layer (GeoJSONSeq für Tippecanoe)
# Wir behalten hier kurze Dateinamen für das TMP-Verzeichnis,
# das Mapping auf die echten Namen erfolgt erst im nächsten Schritt.
log_info "Extrahiere Layer aus GeoPackage..."

ogr2ogr -f GeoJSONSeq areas_p.jsonseq    "$INPUT_FILE" ski_areas_point
ogr2ogr -f GeoJSONSeq areas_poly.jsonseq "$INPUT_FILE" ski_areas_multipolygon
ogr2ogr -f GeoJSONSeq lifts.jsonseq      "$INPUT_FILE" lifts_linestring
ogr2ogr -f GeoJSONSeq runs_poly.jsonseq  "$INPUT_FILE" runs_multipolygon
ogr2ogr -f GeoJSONSeq runs_line.jsonseq  "$INPUT_FILE" runs_linestring

# 4. Konvertierung mit Tippecanoe
# Hier nutzen wir -L "OriginalName:Datei", damit die Layer im PMTiles
# exakt so heißen wie im GPKG.
log_info "Erstelle PMTiles: $OUTPUT_PMTILES"

tippecanoe -o "$OUTPUT_PMTILES" --force \
  --minimum-zoom=0 --maximum-zoom=14 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  -L "ski_areas_point:areas_p.jsonseq" \
  -L "ski_areas_multipolygon:areas_poly.jsonseq" \
  -L "lifts_linestring:lifts.jsonseq" \
  -L "runs_multipolygon:runs_poly.jsonseq" \
  -L "runs_linestring:runs_line.jsonseq"

# 5. Aufräumen
log_info "Bereinige temporäre JSON-Dateien..."
rm -f *.jsonseq

log_success "OpenSkimap PMTiles erfolgreich erstellt (Layer-Namen beibehalten)."
