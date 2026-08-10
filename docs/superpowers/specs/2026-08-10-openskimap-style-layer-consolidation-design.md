# OpenSkiMap style adoption & layer consolidation

## Context

`geodata-openskimap`'s current `styles/openskimap-style.json` is a minimal, hand-rolled
MapLibre style: flat colors, no difficulty/status differentiation, and five
tippecanoe source-layers split purely by geometry type
(`ski_areas_point`/`ski_areas_multipolygon`, `runs_linestring`/`runs_multipolygon`,
`lifts_linestring`). The goal is to bring the visual language in line with the
"real" OpenSkiMap map (colored by piste difficulty, lift status, etc.) while
keeping our own sprite set, and to restructure the underlying vector-tile
layers so they map cleanly onto independent on/off toggles in a downstream
viewer — including, per explicit request, separately toggleable **alpine
("Ski") vs. nordic** ski areas and runs.

This is deliberately scoped to the cartography/data side only. Aligning the
repo's process scripts (`setup.sh`/`run.sh`/`update.sh`, `dist/layer-list.json`,
`run_logger.sh`) with the current `/mnt/geodata/GEODATA_PLUGIN_STANDARD.md`
(v1.4) is tracked as a separate follow-up spec, since it's an independent
concern with no dependency on this one (the reverse dependency does exist:
the v1.4 `layer-list.json` generator reads the *final* style file, so doing
this first is the right order).

**Source material used:**
- Upstream style JSON: hosted live at `https://tiles.openskimap.org/styles/terrain_v2.json`
  (not in the `russellporter/openskimap.org` GitHub repo — confirmed via
  `src/MapStyle.ts`, which only references the hosted URLs).
- Upstream difficulty/status color logic: `russellporter/openskidata-format`
  (`src/Run.ts`, `src/Lift.ts`) — the actual source of the `color`/`colorName`
  properties baked into upstream's internal tiles, MIT-licensed, reproduced
  here as static tables since we don't have their backend pipeline.
- Our actual data schema: verified directly against
  `data/src/openskidata.gpkg` via `ogrinfo`/`ogr2ogr -sql`, not assumed.

## Goals

- Adopt OpenSkiMap's visual language (colors, casing, dash conventions) for
  runs, lifts, ski areas, using **only** attributes present in our own
  GeoPackage and **only** icons present in `assets/sprites/openskimap/`.
- Consolidate tippecanoe source-layers from 5 (geometry-fragmented) to 6
  (concept-fragmented, activity-split where requested), so each is one
  meaningful on/off toggle.
- Add the previously-unused `spots_point` table (lift stations, halfpipes,
  avalanche checkpoints, crossings) as a new `ski_spots` layer, styled with
  generic markers (no matching sprite icons exist for these).

## Non-goals

- Upstream's multi-lane parallel-offset rendering for overlapping same-geometry
  runs with multiple uses (e.g. a shared downhill+nordic trail drawn as two
  parallel offset lines). That requires a backend-computed offset property
  (`downhill`/`nordic`/`skitour`/`other`, each the run's lane index) that only
  exists in OpenSkiMap's own processing pipeline, not in the public
  GeoPackage. Accepted simplification: overlapping uses render as
  coincident (non-offset) lines/casings.
- Upstream's `tappable-*`/`selected-*` layers — invisible wide-hit-area lines
  and hover/selection highlight states that exist only for their own React
  app's click/hover interactivity. Not applicable to a static overlay style.
- `oneway-run-icons` and the `unpatrolled` run-name icon — both need sprite
  icons we don't have; dropped rather than faked.
- Any change to `scripts/check_dependencies.sh`, `update.sh`'s phase
  structure, or `docs/plugin-standard.md` — that's the v1.4-alignment
  follow-up spec.

## Data layer consolidation (`scripts/convert.sh`)

Six `ogr2ogr` extractions (five existing tables + the new `spots_point`),
then merge GeoJSONSeq streams per target layer with `cat` (record order is
irrelevant for GeoJSONSeq, so concatenation is safe) before a single
`tippecanoe -L <name>:<merged-file>` per layer — mixing geometry types within
one vector-tile layer, same as upstream's own `runs`/`skiareas` layers do.

| new source-layer | built from (`ogr2ogr` output) | inclusion rule |
|---|---|---|
| `ski_areas_alpine` | `ski_areas_point` + `ski_areas_multipolygon` | `activities` contains `downhill`, OR does not contain `nordic` (fallback for empty/unknown) |
| `ski_areas_nordic` | same two tables | `activities` contains `nordic` |
| `ski_runs_alpine` | `runs_linestring` + `runs_multipolygon` | `uses` contains `downhill`, OR does not contain `nordic` (fallback catches skitour/connection/sled/hike/sleigh/ice_skate/snow_park/playground/fatbike-only runs) |
| `ski_runs_nordic` | same two tables | `uses` contains `nordic` |
| `ski_lifts` | `lifts_linestring` | unchanged (no activity field on lifts) |
| `ski_spots` *(new)* | `spots_point` | unchanged |

Both `activities` (ski areas) and `uses` (runs) are comma-delimited string
columns (verified via `ogr2ogr -sql "SELECT DISTINCT ..."`); the split can be
done with a `-where` clause on the `ogr2ogr` extraction (`LIKE '%nordic%'`
etc.) so each concept is extracted straight into its two GeoJSONSeq subsets —
no post-processing needed. A run/area tagged with both activities ends up in
both subsets (by design — this is what makes mixed-use features still appear
when either toggle is on).

Cleanup step (`rm -f *.jsonseq`) stays as-is, just covering more filenames.

## Style content (`styles/openskimap-style.json`)

Rewritten from scratch against the new source-layers, structured the same
way upstream groups things (casing layer + colored layer + label layer per
concept), but simplified to what our schema supports:

**Runs** (`ski_runs_alpine`, `ski_runs_nordic` — same paint logic, just
different source-layer/filter):
- Color by `difficulty` + `difficulty_convention` (`europe`/`north_america`/`japan`
  — all three values are present in our data), using OpenSkiMap's own table
  from `openskidata-format`:

  | difficulty | europe | japan | north_america |
  |---|---|---|---|
  | novice | green | green | green |
  | easy | blue | green | green |
  | intermediate | red | red | blue |
  | advanced / expert | black | black | black |
  | freeride / extreme | orange | orange | orange |
  | null / other | grey | grey | grey |

  Color values: green `hsl(125,100%,33%)`, blue `hsl(208,100%,33%)`, red
  `hsl(359,94%,53%)`, black `hsl(0,0%,0%)`, orange `hsl(34,100%,50%)`, grey
  `hsl(0,0%,35%)`.
- White casing beneath the colored line; casing turns
  `hsl(63,100%,76%)` (upstream's "lit" yellow) when `lit=true`.
- Dash pattern for `gladed=true` (dotted) and for ungroomed/backcountry runs
  (`grooming` in `backcountry`/`mogul`, or difficulty `expert`/`freeride`/`extreme`
  with no explicit grooming — matches the `openskidata-format` doc comment
  that ungroomed is assumed for those difficulties) — dashed, distinct
  pattern from gladed.
- Polygon geometry (wide/area runs) gets a translucent fill in the same
  difficulty color, no casing.
- Cyan overlay line where `snowmaking=true` or `snowfarming=true`.
- Name labels along the line (kept from current style, `minzoom 13`).

**Ski areas** (`ski_areas_alpine`, `ski_areas_nordic`):
- Polygon fill kept from current style (light green, low opacity).
- New: circle marker for point-geometry ski areas.
- Area/ski-area name labels (consolidating the current style's oddly-placed
  `ski-labels` layer, which points at `runs_linestring` instead of an areas
  layer).

**Lifts** (`ski_lifts` — unsplit):
- Color by `status`: bright red `hsl(0,82%,42%)` for `operating`/`proposed`/
  `planned`/`construction`; dim red `hsl(0,53%,42%)` for `disused`/`abandoned`.
- White casing; dashed when `access=private`.
- Existing `ski-lifts-icons` symbol layer (lift-type icon via our sprite,
  driven by `lift_type`/`occupancy`) carried over unchanged — it's already
  ours, already sprite-only, already correct.
- Name/ref labels kept from current style.

**Spots** (`ski_spots`, new):
- Generic circle markers, colored/sized by `spot_type` (`lift_station`,
  `halfpipe`, `crossing`, `avalanche_transceiver_training`,
  `avalanche_transceiver_checkpoint`) — no icons (none exist in our sprite
  set), per your call to include spots now with generic markers rather than
  deferring them.

`sprite`/`glyphs`/`sources` stay pointed at our own
`assets/sprites/openskimap` output and `pmtiles://{TILES_BASE_URL}/...` —
no change to how those are wired into `dist/`.

### Known limitations

`gladed`, `lit`, `snowmaking`, and `snowfarming` are uniformly `false`/absent
across the entire current OpenSkiMap GeoPackage (verified by direct SQLite
inspection) — an upstream data characteristic, not a bug here. The style
layers keyed off them (`ski-runs-*-gladed`, `ski-runs-*-snowmaking`, and the
`lit`-based yellow casing color in `ski-runs-*-casing`/`ski-lifts-casing`)
are correctly built and will start rendering automatically once upstream
populates these fields — they're just not visually exercisable with today's
data, so don't expect to see their effect during a manual visual check.

## Verification

- `bash scripts/convert.sh` end-to-end against the already-downloaded
  `data/src/openskidata.gpkg`, confirm `work/openskimap.pmtiles` contains
  exactly the 6 new source-layers (`tippecanoe` output / `pmtiles show`
  or `tile-join`/`ogrinfo` on the result) with plausible feature counts on
  both sides of each alpine/nordic split (sanity check: alpine run count
  should dominate globally, nordic count should be non-zero given Nordic
  countries are well represented in the dataset).
- Load `dist/styles/openskimap-style.json` + `dist/pmtiles/openskimap.pmtiles`
  in a local MapLibre viewer (e.g. `tools/viewer`-style static HTML or
  `maplibre-gl` CDN page) against a known ski region (e.g. an Austrian or
  Japanese resort, to exercise a non-`europe` difficulty convention) and
  visually confirm: difficulty colors render correctly, lit-run casing shows
  where expected, lift status coloring, alpine vs. nordic areas/runs toggle
  independently via `setLayoutProperty(id, "visibility", ...)` per layer.
- Confirm no style layer references an `icon-image` value absent from
  `assets/sprites/openskimap/sprite.json`.

## Out of scope / follow-up

A second spec will cover plugin-standard v1.4 alignment: the
`setup.sh`/`run.sh`/`update.sh` entry-point trifecta, `dist/layer-list.json`
generation (reusing `geodata-overlays`' `layer_metadata_extractor.py` /
`generate_layer_list.py` reference implementation, adapted for this repo's
single static style instead of a multi-template config), `run_logger.sh`
JSONL run-logging, and syncing `docs/` with the canonical
`/mnt/geodata/GEODATA_PLUGIN_STANDARD.md`.
