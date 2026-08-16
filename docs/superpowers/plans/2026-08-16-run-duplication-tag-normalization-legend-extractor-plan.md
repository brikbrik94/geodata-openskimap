# Run Duplication, Tag Normalization & Legend Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `convert.sh` duplicate multi-use runs into every matching category (like ski areas already are), normalize category-inappropriate `grooming` values at the source, and add a manual analysis script that reports real per-category value frequencies from the post-fix pipeline output.

**Architecture:** Two small stdlib-only Python scripts (`normalize_run_tags.py`, `analyze_legend_categories.py`) sit around the existing `ogr2ogr`-based extraction in `scripts/convert.sh` — normalization runs on the `.jsonseq` intermediates right after extraction and before the `tippecanoe` build; the analyzer is a separate, non-pipeline dev tool that reads those same (now-persistent) intermediates after a build.

**Tech Stack:** Bash (`convert.sh`), Python 3 stdlib only (no dependencies — matches this repo's existing `scripts/*.py` convention), `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`

## Global Constraints

- Python code is stdlib-only, no third-party dependencies (matches `scripts/layer_metadata_extractor.py`/`scripts/generate_layer_list.py`).
- Git: stage files explicitly (never `git add -A`); commit messages use Conventional Commits prefixes.
- `CHANGELOG.md` entries use the `## [Unreleased] - YYYY-MM-DD HH:mm` journal format (Keep a Changelog style, German prose, matching this file's existing entries).
- `GROOMING_ALLOWLIST` only covers `downhill` and `nordic` — `skitour`/`other` were not investigated this session and must pass through **unchanged** (no silent guessing at their allowlists).
- `work/` is fully gitignored (per `CLAUDE.md`) — leaving `.jsonseq` intermediates there between builds is intentional and safe.
- Verification command for the existing (unrelated but must-stay-green) suite: `cd scripts && python3 -m unittest test_validate_style test_layer_metadata_extractor test_generate_layer_list -v`

---

### Task 1: `scripts/normalize_run_tags.py` — grooming normalization core + CLI

**Files:**
- Create: `scripts/normalize_run_tags.py`
- Test: `scripts/test_normalize_run_tags.py`

**Interfaces:**
- Produces: `normalize_grooming(properties: dict, category: str) -> dict` — mutates and returns `properties` with `properties["grooming"]` set to `None` if its current value isn't in `GROOMING_ALLOWLIST[category]`; returns `properties` unchanged if `category` has no allowlist entry. Consumed by Task 2 (via the script's CLI) and reused directly by Task 1's own tests.
- Produces: `GROOMING_ALLOWLIST: dict[str, set[str]]` — `{"downhill": {"mogul", "backcountry"}, "nordic": {"classic", "classic+skating", "skating", "scooter", "backcountry"}}`.
- Produces: `normalize_file(path: str, category: str) -> None` — rewrites the GeoJSONSeq file at `path` in place, applying `normalize_grooming` to every feature's `properties`. Consumed by Task 2's `convert.sh` wiring and Task 5's end-to-end run.

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_normalize_run_tags.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from normalize_run_tags import normalize_grooming, GROOMING_ALLOWLIST


class NormalizeGroomingTests(unittest.TestCase):
    def test_downhill_allowed_value_passes_through(self):
        props = {"grooming": "mogul"}
        self.assertEqual(normalize_grooming(props, "downhill")["grooming"], "mogul")

    def test_downhill_backcountry_passes_through(self):
        props = {"grooming": "backcountry"}
        self.assertEqual(normalize_grooming(props, "downhill")["grooming"], "backcountry")

    def test_downhill_classic_is_nulled(self):
        # "classic" on a downhill piste is redundant (groomed is the
        # default assumption) and/or a merge artifact from OpenSkiMap
        # fusing an adjacent nordic way - see the design doc.
        props = {"grooming": "classic"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_classic_plus_skating_is_nulled(self):
        props = {"grooming": "classic+skating"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_skating_is_nulled(self):
        props = {"grooming": "skating"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_downhill_scooter_is_nulled(self):
        props = {"grooming": "scooter"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_nordic_classic_passes_through(self):
        props = {"grooming": "classic"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "classic")

    def test_nordic_classic_plus_skating_passes_through(self):
        props = {"grooming": "classic+skating"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "classic+skating")

    def test_nordic_backcountry_passes_through(self):
        props = {"grooming": "backcountry"}
        self.assertEqual(normalize_grooming(props, "nordic")["grooming"], "backcountry")

    def test_nordic_mogul_is_nulled(self):
        # mogul (Buckelpiste) is downhill-specific, doesn't apply to nordic.
        props = {"grooming": "mogul"}
        self.assertIsNone(normalize_grooming(props, "nordic")["grooming"])

    def test_missing_grooming_key_stays_none(self):
        props = {"name": "Some Run"}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_null_grooming_value_stays_none(self):
        props = {"grooming": None}
        self.assertIsNone(normalize_grooming(props, "downhill")["grooming"])

    def test_category_without_allowlist_entry_passes_through_unchanged(self):
        # skitour/other were not investigated this session - see design doc
        # "Explizit zurückgestellt". Must NOT be silently normalized.
        props = {"grooming": "classic+skating"}
        result = normalize_grooming(props, "skitour")
        self.assertEqual(result["grooming"], "classic+skating")

    def test_allowlist_has_only_downhill_and_nordic(self):
        self.assertEqual(set(GROOMING_ALLOWLIST.keys()), {"downhill", "nordic"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_normalize_run_tags -v`
Expected: `ModuleNotFoundError: No module named 'normalize_run_tags'` (the module doesn't exist yet).

- [ ] **Step 3: Implement `scripts/normalize_run_tags.py`**

```python
#!/usr/bin/env python3
"""
Normalizes the `grooming` property on run features per category, right
after ogr2ogr extraction and before the tippecanoe build (scripts/convert.sh).

Two independent reasons a run's `grooming` value can be inappropriate for
its category (see docs/superpowers/specs/
2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md):

1. OpenSkiMap fuses geometrically adjacent OSM ways of different piste
   types into one feature, inheriting a combined `uses` and a single
   `grooming` value from whichever source way happened to carry it - e.g.
   a downhill segment fused with a nordic segment inherits the nordic
   way's "classic+skating" grooming value onto the whole feature.
2. "classic" is real, common OSM tagging practice on pure downhill ways
   too (not a merge artifact - verified against live OSM way tags), but
   is semantically redundant there: a downhill piste is assumed groomed
   unless marked otherwise (mogul/backcountry).

Only `downhill` and `nordic` have allowlists - `skitour`/`other` were not
investigated this session and pass through unchanged (see design doc,
"Explizit zurückgestellt").
"""
import json
import sys

GROOMING_ALLOWLIST = {
    "downhill": {"mogul", "backcountry"},
    "nordic": {"classic", "classic+skating", "skating", "scooter", "backcountry"},
}


def normalize_grooming(properties, category):
    """
    Null out properties["grooming"] if its value isn't meaningful for
    `category`. Mutates and returns `properties`.

    Args:
        properties (dict): a GeoJSON Feature's "properties" object
        category (str): one of "downhill", "nordic", "skitour", "other"

    Returns:
        dict: the same `properties` dict, mutated in place
    """
    allowlist = GROOMING_ALLOWLIST.get(category)
    if allowlist is None:
        return properties
    if properties.get("grooming") not in allowlist:
        properties["grooming"] = None
    return properties


def normalize_file(path, category):
    """
    Rewrite the GeoJSONSeq file at `path` in place, applying
    normalize_grooming to every feature's properties. One JSON object per
    line (ogr2ogr's GeoJSONSeq output in this pipeline has no RS/0x1e
    separator - verified against real output).

    Args:
        path (str): path to a .jsonseq file, rewritten in place
        category (str): passed through to normalize_grooming
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            feature = json.loads(line)
            feature["properties"] = normalize_grooming(feature.get("properties", {}), category)
            f.write(json.dumps(feature, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: normalize_run_tags.py <path.jsonseq> <category>", file=sys.stderr)
        sys.exit(1)
    normalize_file(sys.argv[1], sys.argv[2])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_normalize_run_tags -v`
Expected: all 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_run_tags.py scripts/test_normalize_run_tags.py
git commit -m "$(cat <<'EOF'
feat(convert): add grooming tag normalization per run category

New normalize_run_tags.py: nulls out a run's grooming value when it isn't
meaningful for its category (downhill: mogul/backcountry only; nordic:
classic/classic+skating/skating/scooter/backcountry). Not yet wired into
convert.sh.
EOF
)"
```

---

### Task 2: Wire duplication + normalization into `scripts/convert.sh`

**Files:**
- Modify: `scripts/convert.sh`

**Interfaces:**
- Consumes: `scripts/normalize_run_tags.py`'s CLI (`python3 normalize_run_tags.py <path.jsonseq> <category>`) from Task 1.
- Produces: `work/ski_runs_nordic_line.jsonseq`/`_poly.jsonseq` and `work/ski_runs_skitour_line.jsonseq`/`_poly.jsonseq` now include every feature whose `uses` matches that category, even if `uses` also contains `downhill` (previously excluded). `work/ski_runs_downhill_*`/`_nordic_*.jsonseq` have normalized `grooming` values. No more `rm -f *.jsonseq` at the end — consumed by Task 3/Task 5.

- [ ] **Step 1: Update `NORDIC_RUN_WHERE`/`SKITOUR_RUN_WHERE` and the comment block above them**

In `scripts/convert.sh`, replace:

```bash
# Pisten/Loipen: nach 'uses' in vier Kategorien aufgeteilt, mit fester
# Prioritaet downhill > nordic > skitour > other (siehe
# docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md).
# Jedes Feature bekommt genau eine Kategorie - keine Mehrfachzuordnung wie
# bei den Ski-Gebieten oben. Das echte OpenSkiMap-Stylesheet zeichnet bei
# Mehrfachnutzung mehrere parallel versetzte Linien (line-offset); das ist
# als Roadmap-Punkt zurueckgestellt, siehe docs/ROADMAP.md. Linien- und
# Polygon-Geometrie bleiben getrennt, siehe Kommentar oben.
# OTHER_RUN_WHERE deckt auch NULL/leeres 'uses' ab: OGR-SQL wertet
# "NULL LIKE '%x%'" als NULL/falsy - ohne den IS-NULL-Zweig wuerden
# Features ganz ohne uses-Wert aus allen vier Kategorien herausfallen.
DOWNHILL_RUN_WHERE="uses LIKE '%downhill%' AND $COUNTRY_WHERE"
NORDIC_RUN_WHERE="uses LIKE '%nordic%' AND uses NOT LIKE '%downhill%' AND $COUNTRY_WHERE"
SKITOUR_RUN_WHERE="uses LIKE '%skitour%' AND uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND $COUNTRY_WHERE"
OTHER_RUN_WHERE="(uses IS NULL OR (uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%')) AND $COUNTRY_WHERE"
```

with:

```bash
# Pisten/Loipen: nach 'uses' in vier Kategorien aufgeteilt. Downhill/Nordic/
# Skitour sind jetzt UNABHAENGIG/inklusiv wie bei den Ski-Gebieten oben -
# ein Feature mit uses="nordic,downhill" landet in BEIDEN Layern (identische
# Geometrie, dupliziert). Loest damit das Problem, dass eine "nur Loipen"-
# Ansicht sonst Mischnutzungs-Segmente komplett verliert. Ersetzt die
# vorherige feste Prioritaet downhill > nordic > skitour > other (siehe
# docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md, jetzt
# abgeloest durch docs/superpowers/specs/
# 2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md).
# OTHER_RUN_WHERE bleibt exklusiv - repraesentiert weiterhin "keine der drei
# spezifischen uses trifft zu", unveraendert durch die Duplizierung oben.
# OTHER_RUN_WHERE deckt auch NULL/leeres 'uses' ab: OGR-SQL wertet
# "NULL LIKE '%x%'" als NULL/falsy - ohne den IS-NULL-Zweig wuerden
# Features ganz ohne uses-Wert aus allen vier Kategorien herausfallen.
# Downhill/Nordic bekommen zusaetzlich eine grooming-Tag-Normalisierung
# (normalize_run_tags.py, siehe unten) - Skitour/Other nicht, siehe
# design doc "Explizit zurueckgestellt".
DOWNHILL_RUN_WHERE="uses LIKE '%downhill%' AND $COUNTRY_WHERE"
NORDIC_RUN_WHERE="uses LIKE '%nordic%' AND $COUNTRY_WHERE"
SKITOUR_RUN_WHERE="uses LIKE '%skitour%' AND $COUNTRY_WHERE"
OTHER_RUN_WHERE="(uses IS NULL OR (uses NOT LIKE '%downhill%' AND uses NOT LIKE '%nordic%' AND uses NOT LIKE '%skitour%')) AND $COUNTRY_WHERE"
```

- [ ] **Step 2: Wire `normalize_run_tags.py` calls after the downhill/nordic `ogr2ogr` extractions**

Replace:

```bash
ogr2ogr -f GeoJSONSeq ski_runs_downhill_line.jsonseq "$INPUT_FILE" runs_linestring -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_downhill_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_line.jsonseq "$INPUT_FILE" runs_linestring -where "$OTHER_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$OTHER_RUN_WHERE"
```

with:

```bash
ogr2ogr -f GeoJSONSeq ski_runs_downhill_line.jsonseq "$INPUT_FILE" runs_linestring -where "$DOWNHILL_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_downhill_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$DOWNHILL_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_downhill_line.jsonseq downhill
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_downhill_poly.jsonseq downhill

ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_nordic_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$NORDIC_RUN_WHERE"
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_nordic_line.jsonseq nordic
python3 "$SCRIPT_DIR/normalize_run_tags.py" ski_runs_nordic_poly.jsonseq nordic

ogr2ogr -f GeoJSONSeq ski_runs_skitour_line.jsonseq "$INPUT_FILE" runs_linestring -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_skitour_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$SKITOUR_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_line.jsonseq "$INPUT_FILE" runs_linestring -where "$OTHER_RUN_WHERE"
ogr2ogr -f GeoJSONSeq ski_runs_other_poly.jsonseq "$INPUT_FILE" runs_multipolygon -where "$OTHER_RUN_WHERE"
```

(`$SCRIPT_DIR` is already defined at the top of `convert.sh` as the absolute path to `scripts/` — reuse it rather than a relative path, since the `ogr2ogr` calls run from inside `cd "$TMP_DIR"`.)

- [ ] **Step 3: Remove the `rm -f *.jsonseq` cleanup**

Replace:

```bash
log_info "Bereinige temporäre JSON-Dateien..."
rm -f *.jsonseq

log_success "OpenSkimap PMTiles erfolgreich erstellt."
```

with:

```bash
log_success "OpenSkimap PMTiles erfolgreich erstellt."
```

(No replacement cleanup step: `work/` is fully gitignored, per `CLAUDE.md` — the `.jsonseq` files are harmless scratch that the next `convert.sh` run overwrites. Leaving them lets `scripts/analyze_legend_categories.py` (Task 3) read them after a build. Also delete the now-orphaned `log_info "Bereinige..."` line above the `rm -f` — shown already removed above.)

- [ ] **Step 4: Verify the WHERE-clause and normalization changes with a fast partial dry run**

Don't run the full `convert.sh` yet (that includes the multi-minute `tippecanoe` build — saved for Task 5's full end-to-end check). Instead verify just the changed extraction logic directly against the real GeoPackage:

```bash
cd /tmp && mkdir -p convert-task2-verify && cd convert-task2-verify
INPUT_FILE=/mnt/geodata/geodata-openskimap/data/src/openskidata.gpkg
COUNTRY_WHERE="country_codes LIKE '%AT%'"
NORDIC_RUN_WHERE="uses LIKE '%nordic%' AND $COUNTRY_WHERE"

ogr2ogr -f GeoJSONSeq ski_runs_nordic_line.jsonseq "$INPUT_FILE" runs_linestring -where "$NORDIC_RUN_WHERE"
python3 /mnt/geodata/geodata-openskimap/scripts/normalize_run_tags.py ski_runs_nordic_line.jsonseq nordic

# "Rundloipe Steyersberger Schwaig" (feature_id 3965815c...) should now be
# present here too, not just in the downhill layer:
grep -c '3965815c0c4a096f9506ebca22dba89f8a89fd6d' ski_runs_nordic_line.jsonseq
# Expected: 1

cd / && rm -rf /tmp/convert-task2-verify
```

Expected: the `grep -c` prints `1` (the feature is now present in the nordic extraction, confirming the duplication fix — before this task it was excluded by the old `uses NOT LIKE '%downhill%'` clause).

- [ ] **Step 5: Commit**

```bash
git add scripts/convert.sh
git commit -m "$(cat <<'EOF'
feat(convert): duplicate multi-use runs into every matching category

NORDIC_RUN_WHERE/SKITOUR_RUN_WHERE drop their mutual-exclusion clauses,
mirroring the existing ski-area duplication pattern - a run with
uses="nordic,downhill" now appears in both layers instead of only
downhill (previously lost entirely from a "nordic only" view). Wires in
normalize_run_tags.py for downhill/nordic grooming cleanup. Drops the
final jsonseq cleanup so scripts/analyze_legend_categories.py can read
the intermediates after a build (work/ is gitignored either way).

BREAKING: ski_runs_nordic_*/ski_runs_skitour_* pmtiles layers now include
features previously assigned only to ski_runs_downhill - consumers
counting on strict single-category membership must account for overlap.
EOF
)"
```

---

### Task 3: `scripts/analyze_legend_categories.py` — frequency-table analysis tool

**Files:**
- Create: `scripts/analyze_legend_categories.py`
- Test: `scripts/test_analyze_legend_categories.py`

**Interfaces:**
- Consumes: `.jsonseq` files left behind in `work/` by Task 2's updated `convert.sh` (not wired into the pipeline itself — this is a standalone manual tool, per the design doc's explicit "kein Pipeline-Schritt" decision).
- Produces: `count_values(properties_list: list[dict], prop: str) -> list[tuple]` — `[(value, count), ...]` sorted by count descending, ties broken by `str(value)` ascending for determinism. Consumed only within this script (Task 5 runs it as a CLI, doesn't import it).

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_analyze_legend_categories.py`:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from analyze_legend_categories import count_values


class CountValuesTests(unittest.TestCase):
    def test_counts_and_sorts_descending(self):
        props = [{"difficulty": "easy"}, {"difficulty": "easy"}, {"difficulty": "advanced"}]
        self.assertEqual(
            count_values(props, "difficulty"),
            [("easy", 2), ("advanced", 1)],
        )

    def test_ties_broken_by_value_string_ascending(self):
        props = [{"grooming": "backcountry"}, {"grooming": "classic"}]
        self.assertEqual(
            count_values(props, "grooming"),
            [("backcountry", 1), ("classic", 1)],
        )

    def test_missing_property_counts_as_none(self):
        props = [{"name": "x"}, {"grooming": "classic"}]
        result = count_values(props, "grooming")
        self.assertIn((None, 1), result)
        self.assertIn(("classic", 1), result)

    def test_empty_list_returns_empty(self):
        self.assertEqual(count_values([], "difficulty"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scripts && python3 -m unittest test_analyze_legend_categories -v`
Expected: `ModuleNotFoundError: No module named 'analyze_legend_categories'`.

- [ ] **Step 3: Implement `scripts/analyze_legend_categories.py`**

```python
#!/usr/bin/env python3
"""
Standalone, manually-run analysis tool - NOT wired into run.sh/update.sh
(see docs/superpowers/specs/
2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md,
Baustein 3). Reads the .jsonseq intermediates scripts/convert.sh leaves
in work/ after a build (duplication + grooming normalization already
applied there - see normalize_run_tags.py) and prints, per group and per
legend-relevant property, a frequency table sorted by count descending.

Usage: python3 scripts/analyze_legend_categories.py [work_dir]
(defaults to the repo's work/ directory)
"""
import json
import os
import sys

GROUPS = {
    "ski_areas_alpine": {
        "files": ["ski_areas_alpine_point.jsonseq", "ski_areas_alpine_poly.jsonseq"],
        "properties": [],
    },
    "ski_areas_nordic": {
        "files": ["ski_areas_nordic_point.jsonseq", "ski_areas_nordic_poly.jsonseq"],
        "properties": [],
    },
    "ski_runs_downhill": {
        "files": ["ski_runs_downhill_line.jsonseq", "ski_runs_downhill_poly.jsonseq"],
        "properties": ["difficulty", "grooming"],
    },
    "ski_runs_nordic": {
        "files": ["ski_runs_nordic_line.jsonseq", "ski_runs_nordic_poly.jsonseq"],
        "properties": ["difficulty", "grooming"],
    },
    "ski_runs_skitour": {
        "files": ["ski_runs_skitour_line.jsonseq", "ski_runs_skitour_poly.jsonseq"],
        "properties": ["difficulty", "grooming"],
    },
    "ski_runs_other": {
        "files": ["ski_runs_other_line.jsonseq", "ski_runs_other_poly.jsonseq"],
        "properties": ["difficulty", "grooming"],
    },
    "ski_lifts": {"files": ["ski_lifts.jsonseq"], "properties": ["status"]},
    "ski_spots": {"files": ["ski_spots.jsonseq"], "properties": ["spot_type"]},
}


def count_values(properties_list, prop):
    """
    Pure function: list of GeoJSON Feature "properties" dicts -> sorted
    [(value, count), ...], count descending, ties broken by str(value)
    ascending for determinism.
    """
    counts = {}
    for properties in properties_list:
        value = properties.get(prop)
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))


def read_jsonseq_properties(path):
    """Yield each feature's "properties" dict from a GeoJSONSeq file."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line).get("properties", {})


def print_report(work_dir):
    for group, cfg in GROUPS.items():
        if not cfg["properties"]:
            continue
        properties_list = []
        for filename in cfg["files"]:
            path = os.path.join(work_dir, filename)
            if not os.path.exists(path):
                print(f"(skipping {group}: {filename} not found in {work_dir})", file=sys.stderr)
                continue
            properties_list.extend(read_jsonseq_properties(path))

        print(f"=== {group} ({len(properties_list)} features) ===")
        for prop in cfg["properties"]:
            print(f"-- {prop} --")
            for value, count in count_values(properties_list, prop):
                print(f"  {value!r}: {count}")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        WORK_DIR = sys.argv[1]
    else:
        WORK_DIR = os.path.join(os.path.dirname(__file__), "..", "work")
    print_report(WORK_DIR)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_analyze_legend_categories -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_legend_categories.py scripts/test_analyze_legend_categories.py
git commit -m "$(cat <<'EOF'
feat(analyze): add manual legend-category frequency extractor

Standalone dev tool (not wired into run.sh/update.sh) that reads
convert.sh's post-normalization .jsonseq intermediates from work/ and
prints per-group, per-property value frequency tables - informs the
still-open decision on how far a data-driven legend/style should go.
EOF
)"
```

---

### Task 4: `CHANGELOG.md` entry

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:** None — documentation only.

- [ ] **Step 1: Get the current UTC timestamp**

Run: `date -u '+%Y-%m-%d %H:%M'`

- [ ] **Step 2: Add the journal entry**

Insert a new entry at the top of `CHANGELOG.md`, immediately after the header block, using the timestamp from Step 1 in place of `<TIMESTAMP>`:

```markdown
## [Unreleased] - <TIMESTAMP>

### Added
- `scripts/normalize_run_tags.py`: normalisiert `grooming`-Werte pro Pisten-/Loipen-Kategorie
  (Downhill: nur `mogul`/`backcountry` bleiben erhalten; Nordic: `classic`/`classic+skating`/
  `skating`/`scooter`/`backcountry`) — behebt sowohl OpenSkiMap-Merge-Artefakte (Loipe+Piste zu
  einem Feature fusioniert) als auch die semantisch redundante `classic`-Markierung auf reinen
  Downhill-Pisten. Siehe
  `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`.
- `scripts/analyze_legend_categories.py`: manuelles Analyse-Tool (kein Pipeline-Schritt), das aus
  den `.jsonseq`-Zwischendateien in `work/` Häufigkeitstabellen pro Gruppe/Property erzeugt.

### Changed
- **Breaking:** `scripts/convert.sh` dupliziert Pisten/Loipen mit Mehrfachnutzung jetzt in jede
  zutreffende Kategorie (analog zu Ski-Gebieten) statt fester Priorität
  `downhill > nordic > skitour > other` — ein Feature mit `uses="nordic,downhill"` erscheint jetzt
  in beiden Layern. Betrifft `ski_runs_nordic_*`/`ski_runs_skitour_*`. Löst das Problem, dass eine
  "nur Loipen"-Ansicht Mischnutzungs-Segmente sonst komplett verliert.
- `scripts/convert.sh` löscht die `.jsonseq`-Zwischendateien am Ende nicht mehr (`work/` ist
  bereits vollständig gitignored) — Voraussetzung für `analyze_legend_categories.py`.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog entry for run duplication + tag normalization work"
```

---

### Task 5: End-to-end verification

**Files:** None modified — this task runs the pipeline and reports results.

**Interfaces:** Consumes everything from Tasks 1-3.

- [ ] **Step 1: Verify dependencies are present**

Run: `bash scripts/check_dependencies.sh`
Expected: all three (`aria2c`, `ogr2ogr`, `tippecanoe`) report found.

- [ ] **Step 2: Run the full `convert.sh`**

Run: `bash scripts/convert.sh`
Expected: completes with `✔ OpenSkimap PMTiles erfolgreich erstellt.` and no errors. This is the same real `data/src/openskidata.gpkg` (~400 MB, already present) used throughout this session's manual exploration — takes a few minutes (`tippecanoe` build).

- [ ] **Step 3: Confirm the `.jsonseq` intermediates survived**

Run: `ls work/*.jsonseq | wc -l`
Expected: `14` (the same 14 files convert.sh has always produced — `rm -f *.jsonseq` no longer deletes them).

- [ ] **Step 4: Run the analyzer**

Run: `python3 scripts/analyze_legend_categories.py`
Expected: prints frequency tables for `ski_runs_downhill` (`difficulty`, `grooming`), `ski_runs_nordic` (`difficulty`, `grooming`), `ski_runs_skitour`, `ski_runs_other`, `ski_lifts` (`status`), `ski_spots` (`spot_type`) — no Python tracebacks.

- [ ] **Step 5: Compare against this session's manual `sqlite3` findings**

Check two things the manual exploration established directly against `data/src/openskidata.gpkg`, to confirm the new pipeline output matches expectations:

1. **`ski_runs_downhill`'s `difficulty` distribution** should closely match the manually-found
   distribution (novice 259, easy 5255, intermediate 3870, advanced 901, expert 57, freeride 308,
   extreme 7, `None` 233 — total 10890). `difficulty` isn't touched by Task 1's normalization, so
   these counts should match closely (small deltas possible only from `AT` cross-border overlap
   with `runs_multipolygon`, which the manual check queried separately as
   `runs_linestring` alone — the analyzer combines `_line` + `_poly`, so totals will be a bit
   higher; the *shape* of the distribution, in particular that all 7 tiers are present and rare
   tiers stay rare, is the thing to confirm).
2. **`ski_runs_downhill`'s `grooming` distribution** should now show **only** `mogul`,
   `backcountry`, and `None` as values — no `classic`, `classic+skating`, `skating`, or `scooter`
   (previously 3995 `classic` + 13 `classic+skating`/`skating`/`scooter` combined, per this
   session's manual cross-tab). This is the concrete, checkable proof that Task 1's normalization
   worked end-to-end through the real pipeline.
3. **`ski_runs_nordic`'s feature count** should be higher than before this plan (previously
   excluded any `uses` containing `downhill`) — spot-check that `grep -c
   '3965815c0c4a096f9506ebca22dba89f8a89fd6d' work/ski_runs_nordic_line.jsonseq`
   returns `1` (the "Rundloipe Steyersberger Schwaig" feature investigated manually this
   session, now present in the nordic layer too).

- [ ] **Step 6: Report results**

Summarize what the analyzer printed for `ski_runs_downhill`'s `grooming` values and the
`feature_id` spot-check from Step 5, so the user can see the before/after concretely (this was
the explicit ask: "noch einmal den Test von zuvor mit den Typen"). No commit needed for this
task — nothing new was created, only verified.
