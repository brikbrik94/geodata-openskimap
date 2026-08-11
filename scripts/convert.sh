#!/bin/bash
set -euo pipefail

# 1. CI Utils laden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$SCRIPT_DIR/ci/utils.sh" ]; then
    source "$SCRIPT_DIR/ci/utils.sh"
else
    echo "❌ Fehler: scripts/ci/utils.sh nicht gefunden!"
    exit 1
fi

log_header "CONVERT: OPENSKIMAP -> PMTILES"

BASE_DIR="$REPO_DIR"
SRC_DIR="$BASE_DIR/data/src"
TMP_DIR="$BASE_DIR/work"

INPUT_FILE="$SRC_DIR/openskidata.gpkg"
OUTPUT_PMTILES="$TMP_DIR/openskimap.pmtiles"

if [ ! -f "$INPUT_FILE" ]; then
    log_error "Eingabedatei nicht gefunden: $INPUT_FILE"
    exit 1
fi

mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

log_info "Extrahiere Layer aus GeoPackage..."

# Ski-Gebiete: nach 'activities' in Alpine/Nordic aufgeteilt.
# Gemischte Gebiete (activities="downhill,nordic") landen in beiden Layern.
# Punkt- und Polygon-Geometrie bleiben in getrennten Tippecanoe-Layern (wie vor
# der Konsolidierung) - Mischgeometrie in einem Layer war nie beauftragt und
# war die Ursache für zoomstufen-abhängig hüpfende Polygonkanten.
ALPINE_AREA_WHERE="activities LIKE '%downhill%' OR activities NOT LIKE '%nordic%'"
NORDIC_AREA_WHERE="activities LIKE '%nordic%'"

ogr2ogr -f GeoJSONSeq ski_areas_alpine_point.jsonseq "$INPUT_FILE" ski_areas_point -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_alpine_poly.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_nordic_point.jsonseq "$INPUT_FILE" ski_areas_point -where "$NORDIC_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_nordic_poly.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$NORDIC_AREA_WHERE"

# Pisten/Loipen: nach 'uses' in Alpine/Nordic aufgeteilt.
# Gemischte Nutzung (uses="downhill,nordic") landet in beiden Layern; alles was
# nicht explizit nordic ist (downhill, skitour, connection, sled, hike, ...)
# faellt in den Alpine-Layer. Linien- und Polygon-Geometrie bleiben getrennt,
# siehe Kommentar oben.
ALPINE_RUN_WHERE="uses LIKE '%downhill%' OR uses NOT LIKE '%nordic%'"
NORDIC_RUN_WHERE="uses LIKE '%nordic%'"

ogr2ogr -f GeoJSONSeq ski_runs_alpine_line.jsonseq "$INPUT_FILE" runs_linestring -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_alpine_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$ALPINE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"

# Lifte: unveraendert, ein Layer
ogr2ogr -f GeoJSONSeq ski_lifts.jsonseq "$INPUT_FILE" lifts_linestring

# Spots: neu (Liftstationen, Halfpipes, Lawinen-Checkpunkte, Kreuzungen)
ogr2ogr -f GeoJSONSeq ski_spots.jsonseq "$INPUT_FILE" spots_point

log_info "Erstelle PMTiles: $(get_rel_path "$OUTPUT_PMTILES" "$REPO_DIR")"

tippecanoe -o "$OUTPUT_PMTILES" --force \
  --minimum-zoom=0 --maximum-zoom=14 \
  --drop-densest-as-needed \
  --extend-zooms-if-still-dropping \
  -x elevation_profile_heights \
  -x elevation_profile_resolution \
  -x sources \
  -x websites \
  -x wikidata_id \
  -x ref_fr_cairn \
  -L "ski_areas_alpine_point:ski_areas_alpine_point.jsonseq" \
  -L "ski_areas_alpine_poly:ski_areas_alpine_poly.jsonseq" \
  -L "ski_areas_nordic_point:ski_areas_nordic_point.jsonseq" \
  -L "ski_areas_nordic_poly:ski_areas_nordic_poly.jsonseq" \
  -L "ski_runs_alpine_line:ski_runs_alpine_line.jsonseq" \
  -L "ski_runs_alpine_poly:ski_runs_alpine_poly.jsonseq" \
  -L "ski_runs_nordic_line:ski_runs_nordic_line.jsonseq" \
  -L "ski_runs_nordic_poly:ski_runs_nordic_poly.jsonseq" \
  -L "ski_lifts:ski_lifts.jsonseq" \
  -L "ski_spots:ski_spots.jsonseq"

log_info "Bereinige temporäre JSON-Dateien..."
rm -f *.jsonseq

log_success "OpenSkimap PMTiles erfolgreich erstellt."
