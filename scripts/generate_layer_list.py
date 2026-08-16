#!/usr/bin/env python3
"""
Builds dist/layer-list.json per GEODATA_PLUGIN_STANDARD.md §5.

Unlike geodata-overlays (many per-file datasets, each becoming its own
group, always exactly one source-layer per group), geodata-openskimap's
groups can span multiple source-layers: each real-world concept (e.g.
"ski areas, alpine") is stored as separate geometry-pure PMTiles
source-layers (a _point and a _poly layer) so tippecanoe never has to
tile mixed geometry types in one layer — but its style layers (fill,
circle marker, label) still belong together as one togglable unit for
the frontend, which is the actual "labels + polygons + lines that
logically belong together" grouping the spec's legend/toggle automation
is for. Groups are therefore defined explicitly by style-layer id in
GROUP_MAP below, not derived from `source-layer` equality.

`template` and `original_file` have no direct equivalent without a
per-group dataset config or source file: `template` is set to the
group key itself (each of our 8 groups is its own category),
`original_file` points at the shared GeoPackage source. `source_layer`
holds the group's first (file-order) source-layer for spec compliance.
`source_layers` (plural) is the sole remaining locally-proposed extension,
not part of the standard — it lists every distinct source-layer the group
spans, since collapsing to a single string would lose information for
groups split across point/poly or line/poly PMTiles layers. `variants`
(including its `axis` field) IS part of GEODATA_PLUGIN_STANDARD.md as of
v2.1.0 §5.3 (formerly tracked as geodata-plugin-standard#4, now resolved);
the `axis` naming/grouping and the shared-vs-variant split themselves
remain a reference-implementation judgment call the standard explicitly
leaves open. `variants` describes filter-based style-layer groupings per
MapLibre `filter` — not "mutually-exclusive": the standard explicitly
asserts no exclusivity semantics.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "ci"))
from utils import log_warn
from layer_metadata_extractor import (
    determine_part_kind,
    extract_part_color,
    extract_categorized_items,
    extract_part_opacity,
    extract_part_width,
    extract_part_dasharray,
    extract_part_radius,
    extract_part_icon,
    extract_part_stroke_color,
    extract_part_stroke_width,
)

SOURCE_GPKG_REL_PATH = "data/src/openskidata.gpkg"

# style layer id -> logical group key. Every layer in styles/openskimap-style.json
# must appear here — build_layer_list() raises if one doesn't, so a future layer
# added to the style without updating this map fails loudly instead of silently
# missing the frontend's layer-list.json.
GROUP_MAP = {
    "ski-areas-alpine-fill": "ski-areas-alpine",
    "ski-areas-alpine-circle": "ski-areas-alpine",
    "ski-areas-alpine-labels": "ski-areas-alpine",
    "ski-areas-nordic-fill": "ski-areas-nordic",
    "ski-areas-nordic-circle": "ski-areas-nordic",
    "ski-areas-nordic-labels": "ski-areas-nordic",
    "ski-runs-downhill-fill": "ski-runs-downhill",
    "ski-runs-downhill-casing": "ski-runs-downhill",
    "ski-runs-downhill-line": "ski-runs-downhill",
    "ski-runs-downhill-gladed": "ski-runs-downhill",
    "ski-runs-downhill-ungroomed": "ski-runs-downhill",
    "ski-runs-downhill-snowmaking": "ski-runs-downhill",
    "ski-runs-downhill-labels": "ski-runs-downhill",
    "ski-runs-nordic-fill": "ski-runs-nordic",
    "ski-runs-nordic-casing": "ski-runs-nordic",
    "ski-runs-nordic-line": "ski-runs-nordic",
    "ski-runs-nordic-ungroomed": "ski-runs-nordic",
    "ski-runs-nordic-snowmaking": "ski-runs-nordic",
    "ski-runs-nordic-labels": "ski-runs-nordic",
    "ski-runs-skitour-fill": "ski-runs-skitour",
    "ski-runs-skitour-line": "ski-runs-skitour",
    "ski-runs-skitour-labels": "ski-runs-skitour",
    "ski-runs-other-fill": "ski-runs-other",
    "ski-runs-other-line": "ski-runs-other",
    "ski-runs-other-labels": "ski-runs-other",
    "ski-spots": "ski-spots",
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-other": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-line-private-other": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
}

# group key -> German display name shown in downstream legend UIs. Every key
# in GROUP_MAP's values must appear here (build_layer_list raises KeyError
# via direct dict indexing if one doesn't, same fail-fast convention as
# GROUP_MAP itself).
GROUP_NAMES = {
    "ski-areas-alpine": "Skigebiete (Alpin)",
    "ski-areas-nordic": "Skigebiete (Nordisch)",
    "ski-runs-downhill": "Pisten",
    "ski-runs-nordic": "Loipen",
    "ski-runs-skitour": "Skitouren",
    "ski-runs-other": "Sonstige Strecken",
    "ski-spots": "Ski-Spots",
    "ski-lifts": "Lifte",
}

# group key -> shared legend_scale_id (GEODATA_PLUGIN_STANDARD.md v2.1.0
# §5.5). All four run-category groups render categorized colors from the
# same difficulty match expression (verified byte-identical against
# styles/openskimap-style.json — see design doc 2026-08-14), so they share
# one central legend. ski-lifts (status) and ski-spots (spot_type) each
# get their own scale, newly introduced with the v2.0 migration (v1.1 only
# had ungrouped per-group legend_items for these two).
GROUP_LEGEND_SCALE = {
    "ski-runs-downhill": "ski-difficulty-v1",
    "ski-runs-nordic": "ski-difficulty-v1",
    "ski-runs-skitour": "ski-difficulty-v1",
    "ski-runs-other": "ski-difficulty-v1",
    "ski-lifts": "ski-lift-status-v1",
    "ski-spots": "ski-spot-type-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
    "ski-lift-status-v1": "Lift-Status",
    "ski-spot-type-v1": "Spot-Typ",
}

# group key -> list of {"axis": ..., "label": ..., "style_layer_ids": [...]}
# — filter-based variants within the group, grouped by a named `axis` per
# GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3 (design docs: 2026-08-14
# legend-variants for the original shared/variant split, 2026-08-16 for this
# axis retaxonomy — geodata-plugin-standard#4, part of the standard as of
# v2.1.0). Style layers not listed in ANY variant here stay in the group's
# shared `render`. Groups not listed here at all get `variants: None` and
# unchanged `render` behavior.
#
# §5.3 requires that a style layer land in `render` or in EXACTLY ONE
# `variants[]` entry, never in both and never in more than one entry — the
# standard does NOT permit cross-entry duplication. ski-lifts is fully
# conformant (each of its 4 variant-bearing style layers appears in exactly
# one axis entry — see the design doc's paint-coupling investigation for how
# it was split into orthogonal "status"/"access" axes without duplication).
# ski-runs-downhill is a KNOWN, DELIBERATE DEVIATION from this rule:
# ski-runs-downhill-gladed and ski-runs-downhill-ungroomed each appear in
# TWO variants[] entries — their own single-condition entry AND the combined
# "Waldabfahrt, nicht präpariert" entry of the grooming-terrain axis. A
# conformant orthogonal-axis decomposition (splitting into a "terrain" axis
# and a "grooming" axis, eliminating the combined entry) was investigated
# and found tractable — see
# docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md's
# "Verworfene Alternative" section — but was deliberately deferred to avoid
# a second breaking variants[] shape change for the website-v3 consumer so
# soon after this migration. This is accepted, documented technical debt,
# tracked in docs/TODO.md, not a standard-permitted pattern.
GROUP_VARIANTS = {
    "ski-runs-nordic": [
        {"axis": "grooming", "label": "Gespurt", "style_layer_ids": ["ski-runs-nordic-line"]},
        {"axis": "grooming", "label": "Ungespurt", "style_layer_ids": ["ski-runs-nordic-ungroomed"]},
        {"axis": "snowmaking", "label": "Beschneit", "style_layer_ids": ["ski-runs-nordic-snowmaking"]},
    ],
    "ski-runs-downhill": [
        {"axis": "grooming-terrain", "label": "Präpariert",
         "style_layer_ids": ["ski-runs-downhill-line"]},
        {"axis": "grooming-terrain", "label": "Waldabfahrt",
         "style_layer_ids": ["ski-runs-downhill-gladed"]},
        {"axis": "grooming-terrain", "label": "Nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-ungroomed"]},
        {"axis": "grooming-terrain", "label": "Waldabfahrt, nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-gladed", "ski-runs-downhill-ungroomed"]},
        {"axis": "snowmaking", "label": "Beschneit",
         "style_layer_ids": ["ski-runs-downhill-snowmaking"]},
    ],
    "ski-lifts": [
        {"axis": "status", "label": "In Betrieb",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"axis": "status", "label": "Sonstiger Status",
         "style_layer_ids": ["ski-lifts-line-other"]},
        # Two Parts bundled under one axis entry per §5.3's "render:
        # Array<Part> can have more than one Part when one filter condition
        # covers several style layers" — not because both are simultaneously
        # visible: -line-private is status==operating, -line-private-other
        # is status!=operating, i.e. they are themselves status-exclusive.
        {"axis": "access", "label": "Privat",
         "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
}


def _build_render(group_layers, group_key, scale_items):
    """
    Build the render:Array<Part> list for one group (GEODATA_PLUGIN_STANDARD.md
    v2.1.0 §5.3): one Part per layer in group_layers, in style order. Layers
    without a mapped kind (determine_part_kind returns None) are skipped, so
    render can be shorter than group_layers.

    A Part whose color is categorized (extract_part_color returns
    "categorized") looks up GROUP_LEGEND_SCALE[group_key]:
      - configured: color becomes {"mode": "scale", "scale_id": ...}; the
        Part's legend items are recorded into scale_items[scale_id] on
        first occurrence. A later Part (in this group or any other) sharing
        the same scale_id with different items logs a warning instead of
        raising (§5.5) — first-seen items win.
      - missing (§5.5 error case — a categorized color with no configured
        scale): log_warn(...), color set to None instead of a scale
        reference. No build abort.
      - configured, but extract_categorized_items can't parse the actual
        color expression into items (extract_part_color's classifier and
        extract_categorized_items's parser can disagree on malformed
        expressions): log_warn(...), color set to None instead of a scale
        reference with null items — never write items: null into
        scale_items/legend_sections (§5.6 requires items to be an array).
        No build abort.

    Args:
        group_layers (list): MapLibre layer objects belonging to one group,
            in style order
        group_key (str): key into GROUP_LEGEND_SCALE
        scale_items (dict): scale_id -> [{"label", "color"}, ...], mutated
            in place; shared across all groups so cross-group scale sharing
            and within-group multi-Part scale sharing use the same
            first-seen/warn-on-drift logic

    Returns:
        list[dict]: Part dicts per §5.3
    """
    parts = []
    for layer in group_layers:
        kind = determine_part_kind(layer)
        if kind is None:
            continue

        color = extract_part_color(layer, kind)
        if color == "categorized":
            scale_id = GROUP_LEGEND_SCALE.get(group_key)
            if scale_id is None:
                log_warn(
                    f"group '{group_key}': layer '{layer.get('id')}' has a categorized "
                    f"color but no GROUP_LEGEND_SCALE entry — color set to null."
                )
                color = None
            else:
                items = extract_categorized_items(layer, kind)
                if items is None:
                    log_warn(
                        f"group '{group_key}': layer '{layer.get('id')}' has a categorized "
                        f"color that could not be parsed into legend items — color set to null."
                    )
                    color = None
                elif scale_id not in scale_items:
                    scale_items[scale_id] = items
                    color = {"mode": "scale", "scale_id": scale_id}
                else:
                    if items != scale_items[scale_id]:
                        log_warn(
                            f"legend_scale_id '{scale_id}': layer '{layer.get('id')}' in group "
                            f"'{group_key}' has legend items differing from the first layer "
                            f"sharing this scale — layer-list.json will use the first layer's items."
                        )
                    color = {"mode": "scale", "scale_id": scale_id}

        parts.append({
            "kind": kind,
            "color": color,
            "stroke_color": extract_part_stroke_color(layer, kind),
            "opacity": extract_part_opacity(layer, kind),
            "width": extract_part_width(layer, kind),
            "dasharray": extract_part_dasharray(layer, kind),
            "radius": extract_part_radius(layer, kind),
            "stroke_width": extract_part_stroke_width(layer, kind),
            "icon": extract_part_icon(layer, kind),
        })

    return parts


def _build_render_and_variants(group_layers, group_key, scale_items):
    """
    Split a group's layers into a shared render list and, for groups
    configured in GROUP_VARIANTS, a list of filter-based variants grouped by
    axis (design docs 2026-08-14 legend-variants, 2026-08-16 axis
    retaxonomy; geodata-plugin-standard#4, part of the standard as of
    v2.1.0).

    Args:
        group_layers (list): MapLibre layer objects belonging to one group,
            in style order
        group_key (str): key into GROUP_VARIANTS
        scale_items (dict): passed through to _build_render unchanged — see
            its docstring; the same dict is used for every _build_render
            call below so cross-group AND cross-variant scale sharing keep
            using the same first-seen/warn-on-drift logic

    Returns:
        tuple[list[dict], list[dict] | None]: (render, variants). variants
            is None when group_key has no GROUP_VARIANTS entry (render is
            then the complete Part list, unchanged from pre-variants
            behavior). Otherwise render holds only the Parts whose style
            layer is not a member of any variant, and each variants[] entry
            is {"axis": str, "label": str, "render": list[dict]}.
    """
    variant_defs = GROUP_VARIANTS.get(group_key)
    if not variant_defs:
        return _build_render(group_layers, group_key, scale_items), None

    variant_member_ids = set()
    for variant_def in variant_defs:
        variant_member_ids.update(variant_def["style_layer_ids"])

    shared_layers = [layer for layer in group_layers if layer.get("id") not in variant_member_ids]
    render = _build_render(shared_layers, group_key, scale_items)

    variants = [
        {
            "axis": variant_def["axis"],
            "label": variant_def["label"],
            "render": _build_render(
                [layer for layer in group_layers if layer.get("id") in variant_def["style_layer_ids"]],
                group_key,
                scale_items,
            ),
        }
        for variant_def in variant_defs
    ]

    return render, variants


def _build_legend_sections(scale_items):
    """
    Turn the scale_id -> items map collected by _build_render into the
    top-level legend_sections list (GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.6).

    Args:
        scale_items (dict): scale_id -> [{"label", "color"}, ...]

    Returns:
        list[dict] | None: [{"id", "label", "items"}, ...] in first-seen
            order, or None if no Part referenced a scale.
    """
    if not scale_items:
        return None

    return [
        {"id": scale_id, "label": LEGEND_SCALE_LABELS[scale_id], "items": items}
        for scale_id, items in scale_items.items()
    ]


def build_layer_list(style_data, style_id, name, pmtiles_path):
    """
    Build the layer-list.json document for one style.

    Args:
        style_data (dict): parsed MapLibre style JSON
        style_id (str): matches the manifest dataset's "id"
        name (str): matches the manifest dataset's "name"
        pmtiles_path (str): path relative to dist/pmtiles/, e.g. "openskimap.pmtiles"

    Returns:
        dict: {"version": "2.1", "styles": [...], "legend_sections": [...] | None}
            per GEODATA_PLUGIN_STANDARD.md v2.1.0 §5. Each group's `variants[]`
            entries carry an `axis` field per the standard's §5.3 model;
            `axis` naming/grouping is a reference-implementation judgment
            call the standard explicitly leaves open. `source_layers`
            (plural) remains a locally-proposed extension, not part of the
            standard.

    Raises:
        KeyError: a style layer's id is not in GROUP_MAP (see module docstring)
    """
    groups_dict = {}
    group_layers = {}

    for layer in style_data.get("layers", []):
        layer_id = layer.get("id")
        source_layer = layer.get("source-layer")
        if not layer_id or not source_layer:
            continue

        if layer_id not in GROUP_MAP:
            raise KeyError(
                f"style layer '{layer_id}' has no entry in GROUP_MAP — "
                "add it so it's included in layer-list.json"
            )
        group_key = GROUP_MAP[layer_id]

        if group_key not in groups_dict:
            groups_dict[group_key] = {
                "source_layer": source_layer,
                "source_layers": [],
                "name": GROUP_NAMES[group_key],
                "template": group_key,
                "original_file": SOURCE_GPKG_REL_PATH,
                "style_layers": [],
            }
            group_layers[group_key] = []

        group = groups_dict[group_key]
        if source_layer not in group["source_layers"]:
            group["source_layers"].append(source_layer)
        group["style_layers"].append(layer_id)
        group_layers[group_key].append(layer)

    scale_items = {}
    for group_key, group in groups_dict.items():
        render, variants = _build_render_and_variants(group_layers[group_key], group_key, scale_items)
        group["render"] = render
        group["variants"] = variants

    legend_sections = _build_legend_sections(scale_items)

    return {
        "version": "2.1",
        "styles": [
            {
                "style_id": style_id,
                "name": name,
                "pmtiles_path": pmtiles_path,
                "groups": list(groups_dict.values()),
            }
        ],
        "legend_sections": legend_sections,
    }


def generate_layer_list(style_path, out_path, style_id, name, pmtiles_path):
    with open(style_path, encoding="utf-8") as f:
        style_data = json.load(f)

    layer_list = build_layer_list(style_data, style_id, name, pmtiles_path)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(layer_list, f, indent=2, ensure_ascii=False)

    return layer_list


if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
    style_path = os.path.join(DIST_DIR, "styles", "openskimap-style.json")
    out_path = os.path.join(DIST_DIR, "layer-list.json")

    manifest_path = os.path.join(DIST_DIR, "manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    dataset = manifest["datasets"][0]

    layer_list = generate_layer_list(
        style_path, out_path, dataset["id"], dataset["name"],
        os.path.basename(dataset["pmtiles_path"]),
    )
    print(f"✅ Generated layer-list.json under: {out_path}")
    print(f"   - {len(layer_list['styles'][0]['groups'])} groups documented")
