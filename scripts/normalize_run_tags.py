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

`downhill`/`nordic`/`skitour` have allowlists - `other` (a heterogeneous
catch-all: hike/sled/etc.) was not investigated and passes through
unchanged (see design doc, "Explizit zurückgestellt").

`skitour`'s allowlist was added after manually reviewing all 18 affected
OSM ways/relations against live OSM data (mogul/scooter/skating values,
2026-08-16 follow-up): unlike downhill/nordic's fusion artifacts, most of
these sit on *pure* skitour-only ways (no merge), but are simply
mistagged/unmaintained on OSM - ski-touring routes aren't machine-groomed,
so only `backcountry` is meaningful there.

Separately, `difficulty` is remapped (not just allowlisted) across ALL
four categories uniformly - unlike `grooming`, `difficulty` means the same
thing regardless of run category (one shared match expression colors it
identically everywhere). `expert`/`extreme` are folded into
`advanced`/`freeride` respectively: styles/openskimap-style.json's
difficulty match expression already assigns advanced/expert the identical
color (pure black) and freeride/extreme the identical color (orange) - the
raw 7-tier scale renders as only 5 distinct colors today, the legend just
hasn't caught up. Remapping at the data stage (this file) means the
style's match expression and the legend extractor need no special
"merge these two branches" logic later - they'll just never see the two
folded-away values again. (Style/legend cleanup itself is a deliberately
separate follow-up step, not part of this change.)
"""
import json
import os
import sys

GROOMING_ALLOWLIST = {
    "downhill": {"mogul", "backcountry"},
    "nordic": {"classic", "classic+skating", "skating", "scooter", "backcountry"},
    "skitour": {"backcountry"},
}

# Applied uniformly to all four run categories (see module docstring) -
# unlike GROOMING_ALLOWLIST, not category-dependent.
DIFFICULTY_REMAP = {
    "expert": "advanced",
    "extreme": "freeride",
}

# The four real run categories produced by scripts/convert.sh. Not the same
# set as GROOMING_ALLOWLIST.keys() - "skitour"/"other" are valid categories
# that intentionally have no allowlist entry (normalize_grooming passes them
# through unchanged), so validating against GROOMING_ALLOWLIST would wrongly
# reject them.
VALID_CATEGORIES = {"downhill", "nordic", "skitour", "other"}


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


def normalize_difficulty(properties):
    """
    Remap properties["difficulty"] per DIFFICULTY_REMAP if present there,
    leaving any other value (including None/missing) untouched. Mutates and
    returns `properties`. Category-agnostic - see module docstring.

    Args:
        properties (dict): a GeoJSON Feature's "properties" object

    Returns:
        dict: the same `properties` dict, mutated in place
    """
    current = properties.get("difficulty")
    if current in DIFFICULTY_REMAP:
        properties["difficulty"] = DIFFICULTY_REMAP[current]
    return properties


def normalize_file(path, category):
    """
    Rewrite the GeoJSONSeq file at `path` in place, applying
    normalize_grooming and normalize_difficulty to every feature's
    properties. One JSON object per line (ogr2ogr's GeoJSONSeq output in
    this pipeline has no RS/0x1e separator - verified against real output).

    Writes to a temp file in the same directory and atomically renames it
    over `path` (os.replace) rather than reopening `path` directly, so an
    interruption mid-write can't leave a truncated file in place.

    Args:
        path (str): path to a .jsonseq file, rewritten in place
        category (str): passed through to normalize_grooming
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            feature = json.loads(line)
            properties = feature.get("properties") or {}
            properties = normalize_grooming(properties, category)
            properties = normalize_difficulty(properties)
            feature["properties"] = properties
            f.write(json.dumps(feature, ensure_ascii=False) + "\n")
    os.replace(tmp_path, path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: normalize_run_tags.py <path.jsonseq> <category>", file=sys.stderr)
        sys.exit(1)
    if sys.argv[2] not in VALID_CATEGORIES:
        print(
            f"Error: unknown category {sys.argv[2]!r}, expected one of {sorted(VALID_CATEGORIES)}",
            file=sys.stderr,
        )
        sys.exit(1)
    normalize_file(sys.argv[1], sys.argv[2])
