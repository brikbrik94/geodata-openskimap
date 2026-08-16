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

# Geografische Beschneidung: dieses Repo beliefert eine Deployment-Umgebung,
# deren Basiskarte nur Österreich + Nachbarländer abdeckt (siehe
# docs/ROADMAP.md-Kontext) - der weltweite OpenSkiMap-Datensatz wird auf
# Skigebiete/Pisten/Lifte/Spots mit Österreich-Bezug beschnitten.
# `country_codes` ist ein semikolon-getrenntes ISO-Alpha-2-Feld (z.B. "AT",
# "AT;CH", "AT;DE") - LIKE '%AT%' erfasst reine AT-Gebiete UND
# grenzüberschreitende (z.B. Ischgl/Samnaun AT;CH), verworfen wird nur, wo AT
# in keinem der Codes vorkommt. Gilt für ALLE Layer unten (Gebiete, Pisten,
# Lifte, Spots) - ein einzelner globaler Filter, kein Bounding-Box-Clip.
COUNTRY_WHERE="country_codes LIKE '%AT%'"

# Ski-Gebiete: nach 'activities' in Alpine/Nordic aufgeteilt.
# Gemischte Gebiete (activities="downhill,nordic") landen in beiden Layern.
# Punkt- und Polygon-Geometrie bleiben in getrennten Tippecanoe-Layern (wie vor
# der Konsolidierung) - Mischgeometrie in einem Layer war nie beauftragt und
# war die Ursache für zoomstufen-abhängig hüpfende Polygonkanten.
ALPINE_AREA_WHERE="(activities LIKE '%downhill%' OR activities NOT LIKE '%nordic%') AND $COUNTRY_WHERE"
NORDIC_AREA_WHERE="activities LIKE '%nordic%' AND $COUNTRY_WHERE"

ogr2ogr -f GeoJSONSeq ski_areas_alpine_point.jsonseq "$INPUT_FILE" ski_areas_point -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_alpine_poly.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$ALPINE_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_nordic_point.jsonseq "$INPUT_FILE" ski_areas_point -where "$NORDIC_AREA_WHERE"
ogr2ogr -f GeoJSONSeq ski_areas_nordic_poly.jsonseq  "$INPUT_FILE" ski_areas_multipolygon -where "$NORDIC_AREA_WHERE"

# Pisten/Loipen: nach 'uses' in Kategorien aufgeteilt. Downhill/Nordic/
# Skitour sind UNABHAENGIG/inklusiv wie bei den Ski-Gebieten oben - ein
# Feature mit uses="nordic,downhill" landet in BEIDEN Layern (identische
# Geometrie, dupliziert). Loest damit das Problem, dass eine "nur Loipen"-
# Ansicht sonst Mischnutzungs-Segmente komplett verliert. Ersetzt die
# vorherige feste Prioritaet downhill > nordic > skitour > other (siehe
# docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md, jetzt
# abgeloest durch docs/superpowers/specs/
# 2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md).
#
# "Other" wurde am 2026-08-16 (Follow-up) selbst in sechs eigene Kategorien
# aufgeteilt (hike/sled/connection/snow_park/playground/ice_skate), nach
# demselben unabhaengig/inklusiven Muster - alle 2608 bisherigen "Other"-
# Features sind durch diese sechs `uses`-Werte vollstaendig abgedeckt
# (verifiziert gegen die echten Daten). OTHER_RUN_WHERE bleibt als echtes
# Auffangbecken bestehen (schliesst jetzt zusaetzlich alle sechs neuen Typen
# aus) - aktuell 0 Features, aber Sicherheitsnetz fuer kuenftige/unbekannte
# uses-Werte. OTHER_RUN_WHERE deckt auch NULL/leeres 'uses' ab: OGR-SQL
# wertet "NULL LIKE '%x%'" als NULL/falsy - ohne den IS-NULL-Zweig wuerden
# Features ganz ohne uses-Wert herausfallen.
#
# Downhill/Nordic/Skitour bekommen eine grooming-Tag-Normalisierung
# (normalize_run_tags.py, siehe unten) - alle anderen Kategorien (auch die
# sechs neuen) noch nicht (siehe design doc "Explizit zurueckgestellt";
# Skitour kam am 2026-08-16 dazu, nach manueller Pruefung aller betroffenen
# OSM-Ways gegen die Live-Daten). ALLE Kategorien laufen trotzdem durch
# dieselbe normalize_run_tags.py fuer die difficulty-Remappierung
# (expert->advanced, extreme->freeride) - kategorie-unabhaengig, da
# difficulty ueberall gleich bedeutet; ihr grooming-Wert bleibt dabei fuer
# die Kategorien ohne Allowlist-Eintrag unveraendert.
DOWNHILL_RUN_WHERE="uses LIKE '%downhill%' AND $COUNTRY_WHERE"
NORDIC_RUN_WHERE="uses LIKE '%nordic%' AND $COUNTRY_WHERE"
SKITOUR_RUN_WHERE="uses LIKE '%skitour%' AND $COUNTRY_WHERE"
NOT_PISTE_WHERE="uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%'"
HIKE_RUN_WHERE="uses LIKE '%hike%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
SLED_RUN_WHERE="uses LIKE '%sled%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
CONNECTION_RUN_WHERE="uses LIKE '%connection%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
SNOW_PARK_RUN_WHERE="uses LIKE '%snow_park%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
PLAYGROUND_RUN_WHERE="uses LIKE '%playground%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
ICE_SKATE_RUN_WHERE="uses LIKE '%ice_skate%' AND $NOT_PISTE_WHERE AND $COUNTRY_WHERE"
OTHER_RUN_WHERE="(uses IS NULL OR ($NOT_PISTE_WHERE AND uses NOT LIKE '%hike%' AND uses NOT LIKE '%sled%' AND uses NOT LIKE '%connection%' AND uses NOT LIKE '%snow_park%' AND uses NOT LIKE '%playground%' AND uses NOT LIKE '%ice_skate%')) AND $COUNTRY_WHERE"

ogr2ogr -f GeoJSONSeq ski_runs_downhill_line.jsonseq "$INPUT_FILE" runs_linestring -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_downhill_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$DOWNHILL_RUN_WHERE"
log_info "Normalisiere grooming-Tags (downhill/nordic/skitour) und difficulty-Remap (alle Kategorien)..."
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_downhill_line.jsonseq downhill
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_downhill_poly.jsonseq downhill

ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_nordic_line.jsonseq nordic
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_nordic_poly.jsonseq nordic

ogr2ogr -f GeoJSONSeq ski_runs_skitour_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SKITOUR_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_skitour_line.jsonseq skitour
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_skitour_poly.jsonseq skitour

# "Other"-Subtypen: hike/connection sind zu 100% Linien, die anderen vier
# haben einen echten Poly-Anteil (verifiziert gegen die echten Daten).
ogr2ogr -f GeoJSONSeq ski_runs_hike_line.jsonseq "$INPUT_FILE" runs_linestring -where "$HIKE_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_hike_line.jsonseq hike

ogr2ogr -f GeoJSONSeq ski_runs_sled_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SLED_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_sled_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SLED_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_sled_line.jsonseq sled
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_sled_poly.jsonseq sled

ogr2ogr -f GeoJSONSeq ski_runs_connection_line.jsonseq "$INPUT_FILE" runs_linestring -where "$CONNECTION_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_connection_line.jsonseq connection

ogr2ogr -f GeoJSONSeq ski_runs_snow_park_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SNOW_PARK_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_snow_park_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SNOW_PARK_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_snow_park_line.jsonseq snow_park
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_snow_park_poly.jsonseq snow_park

ogr2ogr -f GeoJSONSeq ski_runs_playground_line.jsonseq "$INPUT_FILE" runs_linestring -where "$PLAYGROUND_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_playground_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$PLAYGROUND_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_playground_line.jsonseq playground
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_playground_poly.jsonseq playground

ogr2ogr -f GeoJSONSeq ski_runs_ice_skate_line.jsonseq "$INPUT_FILE" runs_linestring -where "$ICE_SKATE_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_ice_skate_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$ICE_SKATE_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_ice_skate_line.jsonseq ice_skate
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_ice_skate_poly.jsonseq ice_skate

# Rest-Auffangbecken (siehe Kommentar oben) - aktuell 0 Features erwartet.
# Wird NICHT mehr in die PMTiles/den Layer-List eingespeist (leerer Layer
# waere fuer die Konsumenten sichtbar, aber sinnlos) - die Extraktion bleibt
# trotzdem bestehen, rein als Sicherheitsnetz: wenn hier doch Features
# auftauchen, signalisiert das einen neuen/unbekannten uses-Wert, den keine
# der neun benannten Kategorien abdeckt.
ogr2ogr -f GeoJSONSeq ski_runs_other_line.jsonseq "$INPUT_FILE" runs_linestring -where "$OTHER_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$OTHER_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_other_line.jsonseq other
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_other_poly.jsonseq other

OTHER_COUNT=$(($(wc -l < ski_runs_other_line.jsonseq) + $(wc -l < ski_runs_other_poly.jsonseq)))
if [ "$OTHER_COUNT" -gt 0 ]; then
  log_warn "ski_runs_other: $OTHER_COUNT Feature(s) im Rest-Auffangbecken gefunden (erwartet: 0) - vermutlich ein neuer/unbekannter uses-Wert, der von keiner der neun benannten Kategorien abgedeckt wird. Nicht im PMTiles-Output enthalten (siehe Kommentar oben) - work/ski_runs_other_line.jsonseq / _poly.jsonseq pruefen."
fi

# Lifte: ein Layer, keine Kategorie-Aufteilung noetig
ogr2ogr -f GeoJSONSeq ski_lifts.jsonseq "$INPUT_FILE" lifts_linestring -where "$COUNTRY_WHERE"

# Spots: Liftstationen, Halfpipes, Lawinen-Checkpunkte, Kreuzungen
ogr2ogr -f GeoJSONSeq ski_spots.jsonseq "$INPUT_FILE" spots_point -where "$COUNTRY_WHERE"

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
  -L "ski_runs_downhill_line:ski_runs_downhill_line.jsonseq" \
  -L "ski_runs_downhill_poly:ski_runs_downhill_poly.jsonseq" \
  -L "ski_runs_nordic_line:ski_runs_nordic_line.jsonseq" \
  -L "ski_runs_nordic_poly:ski_runs_nordic_poly.jsonseq" \
  -L "ski_runs_skitour_line:ski_runs_skitour_line.jsonseq" \
  -L "ski_runs_skitour_poly:ski_runs_skitour_poly.jsonseq" \
  -L "ski_runs_hike_line:ski_runs_hike_line.jsonseq" \
  -L "ski_runs_sled_line:ski_runs_sled_line.jsonseq" \
  -L "ski_runs_sled_poly:ski_runs_sled_poly.jsonseq" \
  -L "ski_runs_connection_line:ski_runs_connection_line.jsonseq" \
  -L "ski_runs_snow_park_line:ski_runs_snow_park_line.jsonseq" \
  -L "ski_runs_snow_park_poly:ski_runs_snow_park_poly.jsonseq" \
  -L "ski_runs_playground_line:ski_runs_playground_line.jsonseq" \
  -L "ski_runs_playground_poly:ski_runs_playground_poly.jsonseq" \
  -L "ski_runs_ice_skate_line:ski_runs_ice_skate_line.jsonseq" \
  -L "ski_runs_ice_skate_poly:ski_runs_ice_skate_poly.jsonseq" \
  -L "ski_lifts:ski_lifts.jsonseq" \
  -L "ski_spots:ski_spots.jsonseq"

log_success "OpenSkimap PMTiles erfolgreich erstellt."
