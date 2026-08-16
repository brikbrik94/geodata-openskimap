#!/usr/bin/env python3
"""
Builds dist/layer-list.json per docs/superpowers/specs/
2026-08-16-legend-layer-split-design.md (v3.0 — layer-list.json v3.0's
own local extension, ahead of GEODATA_PLUGIN_STANDARD.md formally adopting
it; the standard as of v2.1.0 still describes the pre-split
groups[].render/variants model).

Unlike geodata-overlays (many per-file datasets, each becoming its own
group, always exactly one source-layer per group), geodata-openskimap's
groups can span multiple source-layers: each real-world concept (e.g.
"ski areas, alpine") is stored as separate geometry-pure PMTiles
source-layers (a _point and a _poly layer) so tippecanoe never has to
tile mixed geometry types in one layer — but its style layers (fill,
circle marker, label) still belong together as one togglable unit for
the frontend. Groups are therefore defined explicitly by style-layer id in
GROUP_MAP below, not derived from `source-layer` equality.

`template` and `original_file` have no direct equivalent without a
per-group dataset config or source file: `template` is set to the
group key itself (each of our 12 groups is its own category),
`original_file` points at the shared GeoPackage source. `source_layer`
holds the group's first (file-order) source-layer for spec compliance.
`source_layers` (plural) is a locally-proposed extension, not part of the
standard — it lists every distinct source-layer the group spans, since
collapsing to a single string would lose information for groups split
across point/poly or line/poly PMTiles layers.

`groups[]` (this module's GROUP_MAP/GROUP_NAMES) is now PURE toggle/
rendering metadata — "what can be turned on/off on the map, what style
layers does that control" — and carries no Part-level rendering or legend
information at all. That information lives entirely in the separate
`legend[]` top-level array (LEGEND_HEADINGS below), which is NOT scoped
1:1 to a single group: one legend heading's rows can pull style layers
from several different groups[] entries (e.g. "Pisten" bundles rows from
both the "ski-runs-downhill" AND "ski-runs-skitour" groups, which stay
independently toggleable on the map). This split exists because the old
model (groups[].render/variants, v2.1.0) had no way to express "these
rows from two different toggle-groups belong under one legend heading" —
see the design doc's Problem section for the concrete case that surfaced
this.
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
# missing the frontend's layer-list.json. Purely a toggle-grouping map now (see
# module docstring) — has no bearing on legend content, that's LEGEND_HEADINGS below.
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
    "ski-runs-downhill-labels": "ski-runs-downhill",
    "ski-runs-nordic-fill": "ski-runs-nordic",
    "ski-runs-nordic-casing": "ski-runs-nordic",
    "ski-runs-nordic-line": "ski-runs-nordic",
    "ski-runs-nordic-labels": "ski-runs-nordic",
    "ski-runs-skitour-fill": "ski-runs-skitour",
    "ski-runs-skitour-line": "ski-runs-skitour",
    "ski-runs-skitour-labels": "ski-runs-skitour",
    # Connection ist visuell mit den Pisten verschmolzen (identische
    # Difficulty-Faerbung + weisse Casing) und wandert deshalb in dieselbe
    # Toggle-Gruppe wie Downhill statt eine eigene zu bekommen - vom
    # Nutzer nach visueller Pruefung so bestaetigt (2026-08-16 Follow-up).
    "ski-runs-connection-casing": "ski-runs-downhill",
    "ski-runs-connection-line": "ski-runs-downhill",
    "ski-runs-hike-line": "ski-runs-hike",
    "ski-runs-sled-fill": "ski-runs-sled",
    "ski-runs-sled-line": "ski-runs-sled",
    "ski-runs-snow_park-fill": "ski-runs-snow_park",
    "ski-runs-snow_park-line": "ski-runs-snow_park",
    "ski-runs-playground-fill": "ski-runs-playground",
    "ski-runs-playground-line": "ski-runs-playground",
    "ski-runs-ice_skate-fill": "ski-runs-ice_skate",
    "ski-runs-ice_skate-line": "ski-runs-ice_skate",
    "ski-spots": "ski-spots",
    "ski-lifts-casing": "ski-lifts",
    "ski-lifts-line": "ski-lifts",
    "ski-lifts-line-planned": "ski-lifts",
    "ski-lifts-line-disused": "ski-lifts",
    "ski-lifts-line-private": "ski-lifts",
    "ski-lifts-line-private-other": "ski-lifts",
    "ski-lifts-labels": "ski-lifts",
    "ski-lifts-icons": "ski-lifts",
    "ski-lifts-icons-mixed-gondola": "ski-lifts",
    "ski-lifts-icons-mixed-chair": "ski-lifts",
}

# group key -> German display name shown in downstream toggle UIs. Every key
# in GROUP_MAP's values must appear here (build_layer_list raises KeyError
# via direct dict indexing if one doesn't, same fail-fast convention as
# GROUP_MAP itself).
GROUP_NAMES = {
    "ski-areas-alpine": "Skigebiete (Alpin)",
    "ski-areas-nordic": "Skigebiete (Nordisch)",
    "ski-runs-downhill": "Pisten",
    "ski-runs-nordic": "Loipen",
    "ski-runs-skitour": "Skitouren",
    "ski-runs-hike": "Winterwanderwege",
    "ski-runs-sled": "Rodelbahnen",
    "ski-runs-snow_park": "Snowparks",
    "ski-runs-playground": "Übungswiesen",
    "ski-runs-ice_skate": "Eislaufplätze",
    "ski-spots": "Ski-Spots",
    "ski-lifts": "Lifte",
}

# group key -> shared legend_scale_id. Used only internally by _build_render
# (via _build_legend_row) to resolve a categorized color's scale_id — not
# part of groups[] itself anymore (see module docstring). All three
# run-category groups render categorized colors from the same difficulty
# match expression (verified byte-identical against
# styles/openskimap-style.json — see design doc 2026-08-14), so they share
# one central legend scale. ski-lifts/ski-spots had their own single-use
# scales here too (v2.0/v2.1 migrations), both removed 2026-08-16
# (lift-status-icon-cleanup follow-up): unlike the difficulty scale, each
# had exactly one consumer, so the shared-scale indirection bought nothing
# — see docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md,
# Baustein 4. Both groups' legend rows are fixed-color now (LEGEND_HEADINGS
# below), no categorized color left in either.
GROUP_LEGEND_SCALE = {
    "ski-runs-downhill": "ski-difficulty-v1",
    "ski-runs-nordic": "ski-difficulty-v1",
    "ski-runs-skitour": "ski-difficulty-v1",
}
LEGEND_SCALE_LABELS = {
    "ski-difficulty-v1": "Schwierigkeitsgrade",
}

# heading -> list of {"label": ..., "style_layer_ids": [...], "render": [...]?}
# — the legend[] content (docs/superpowers/specs/
# 2026-08-16-legend-layer-split-design.md, Baustein 3), independent of
# GROUP_MAP/groups[]. A row's Part list is derived from the real style
# layer(s) named in "style_layer_ids" via _build_render UNLESS the row
# already carries an explicit "render" key (a literal list[dict] of Parts)
# — then that literal list is used as-is. The derived path requires every
# id in "style_layer_ids" to belong to the SAME GROUP_MAP group (asserted
# in _build_legend_row) — _build_render needs one group_key for scale
# resolution, so a row spanning layers from different groups (e.g.
# "Freeride" below) must always be hand-authored.
#
# Terminology fix (2026-08-16, superseding the 2026-08-16
# lift-status-icon-cleanup naming): "Skiroute" previously labeled the
# ski-runs-skitour group's main row (uses=skitour, real ski touring, no
# lift) — factually wrong. Corrected: "Skiroute" = a downhill piste in its
# backcountry/ungroomed state (grooming=="backcountry") — still an
# "Abfahrt" via lift-accessible piste infrastructure, just not groomed.
# "Skitour" = the separate uses=skitour category — no lift, ski touring
# proper. Both now sit side by side as distinct rows under the same
# "Pisten" heading, which is what made the previous name collision worth
# fixing (they used to live in separate, disconnected legend blocks where
# the ambiguity was less visible).
#
# "Piste"/"Loipe" renamed to "Präpariert" (shared vocabulary between the
# "Pisten" and "Loipen" headings, user request 2026-08-16); "Piste
# (Backcountry)" renamed to "Skiroute" (see above); "Loipe (Backcountry)"
# renamed to "Unpräpariert". Buckelpiste/Freeride keep their own rows
# rather than collapsing into "Unpräpariert" — decoupling legend rows from
# the old 1:1-Part-per-style-layer model removes the pressure that used to
# make fine-grained rows awkward (each needed its own entry wedged into
# exactly one group). Freeride specifically benefits: downhill and skitour
# used to need two separate "Freeride" rows (one per group, since the old
# variants[] couldn't span groups); now one shared row's style_layer_ids
# lists layers from both, since they render identically (verified:
# hsl(34, 100%, 50%), dasharray [3, 6], byte-identical in
# styles/openskimap-style.json for ski-runs-downhill-line/
# -connection-line/ski-runs-skitour-line).
#
# Since a single style layer's line-dasharray case-expression can't be
# parsed into separate Parts automatically (extract_part_dasharray only
# reads a literal 2-element array — see its docstring), the Pisten/Loipen
# grooming-state rows are hand-authored literals, same as before the
# split. "Skitour" is the one row still derived normally (no hand-authored
# "render") — ski-runs-skitour-line's dasharray is a plain literal (always
# [3, 6], no grooming-based case-expression), so it needs no override.
#
# ski-lifts' status/access rows and ski-spots' spot_type rows are
# unchanged in content from their 2026-08-16 lift-status-icon-cleanup
# shape — only relocated here from the old GROUP_VARIANTS, with the
# "axis" field dropped (superseded by "heading": rows are already
# unambiguously clustered by which LEGEND_HEADINGS list they're in).
LEGEND_HEADINGS = {
    "Pisten": [
        {
            "label": "Präpariert",
            "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
            "render": [{
                "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
                "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
                "radius": None, "stroke_width": None, "icon": None,
            }],
        },
        {
            "label": "Buckelpiste",
            "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
            "render": [{
                "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
                "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [1, 3],
                "radius": None, "stroke_width": None, "icon": None,
            }],
        },
        {
            "label": "Skiroute",
            "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
            "render": [{
                "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
                "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [3, 6],
                "radius": None, "stroke_width": None, "icon": None,
            }],
        },
        {
            "label": "Skitour",
            "style_layer_ids": ["ski-runs-skitour-line"],
        },
        {
            "label": "Freeride",
            "style_layer_ids": [
                "ski-runs-downhill-line", "ski-runs-connection-line", "ski-runs-skitour-line",
            ],
            "render": [{
                "kind": "line", "color": {"mode": "fixed", "value": "hsl(34, 100%, 50%)"},
                "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [3, 6],
                "radius": None, "stroke_width": None, "icon": None,
            }],
        },
    ],
    "Loipen": [
        {
            "label": "Präpariert",
            "style_layer_ids": ["ski-runs-nordic-casing", "ski-runs-nordic-line"],
            "render": [
                {
                    "kind": "outline", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
                    "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
                    "radius": None, "stroke_width": None, "icon": None,
                },
                {
                    "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
                    "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": None,
                    "radius": None, "stroke_width": None, "icon": None,
                },
            ],
        },
        {
            "label": "Unpräpariert",
            "style_layer_ids": ["ski-runs-nordic-casing", "ski-runs-nordic-line"],
            "render": [
                {
                    "kind": "outline", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"},
                    "stroke_color": None, "opacity": 1, "width": 5.0, "dasharray": None,
                    "radius": None, "stroke_width": None, "icon": None,
                },
                {
                    "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"},
                    "stroke_color": None, "opacity": 1, "width": 3.0, "dasharray": [2, 4],
                    "radius": None, "stroke_width": None, "icon": None,
                },
            ],
        },
    ],
    "Lifte": [
        {"label": "In Betrieb", "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"label": "Geplant / Im Bau", "style_layer_ids": ["ski-lifts-line-planned"]},
        {"label": "Außer Betrieb", "style_layer_ids": ["ski-lifts-line-disused"]},
        {"label": "Privat", "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"]},
    ],
    "Ski-Spots": [
        {"label": "Lift Station", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#5a6b8c"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
        {"label": "Halfpipe", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#8e44ad"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
        {"label": "Crossing", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#e67e22"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
        {"label": "Avalanche Transceiver Training", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#c0392b"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
        {"label": "Avalanche Transceiver Checkpoint", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#c0392b"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
        {"label": "Sonstige", "style_layer_ids": ["ski-spots"],
         "render": [{
             "kind": "circle", "color": {"mode": "fixed", "value": "#7f8c8d"},
             "stroke_color": {"mode": "fixed", "value": "#ffffff"}, "opacity": 1,
             "width": None, "dasharray": None, "radius": 4, "stroke_width": 1, "icon": None,
         }]},
    ],
}


def _build_render(group_layers, group_key, scale_items):
    """
    Build a render:Array<Part> list for a set of style layers sharing one
    group_key: one Part per layer in group_layers, in caller-supplied order.
    Layers without a mapped kind (determine_part_kind returns None) are
    skipped, so the result can be shorter than group_layers.

    A Part whose color is categorized (extract_part_color returns
    "categorized") looks up GROUP_LEGEND_SCALE[group_key]:
      - configured: color becomes {"mode": "scale", "scale_id": ...}; the
        Part's legend items are recorded into scale_items[scale_id] on
        first occurrence. A later Part (in this call or any other) sharing
        the same scale_id with different items logs a warning instead of
        raising — first-seen items win.
      - missing (a categorized color with no configured scale): log_warn(...),
        color set to None instead of a scale reference. No build abort.
      - configured, but extract_categorized_items can't parse the actual
        color expression into items (extract_part_color's classifier and
        extract_categorized_items's parser can disagree on malformed
        expressions): log_warn(...), color set to None instead of a scale
        reference with null items — never write items: null into
        scale_items/legend_scales (items must be an array). No build abort.

    Args:
        group_layers (list): MapLibre layer objects, in the order Parts
            should appear
        group_key (str): key into GROUP_LEGEND_SCALE
        scale_items (dict): scale_id -> [{"label", "color"}, ...], mutated
            in place; shared across every _build_render call in one
            build_layer_list run so cross-heading/cross-row scale sharing
            uses the same first-seen/warn-on-drift logic

    Returns:
        list[dict]: Part dicts
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


def _build_legend_row(row_def, layers_by_id, scale_items):
    """
    Build one legend[].rows[] entry: {"label", "render", "style_layer_ids"}.

    Args:
        row_def (dict): one entry from a LEGEND_HEADINGS[heading] list —
            {"label": str, "style_layer_ids": [str, ...], "render": [...]?}
        layers_by_id (dict): style layer id -> MapLibre layer object,
            spanning the WHOLE style (not scoped to one group) since a
            row's style_layer_ids may reference layers from different
            groups
        scale_items (dict): passed through to _build_render unchanged

    Returns:
        dict: {"label": str, "render": list[dict], "style_layer_ids": list[str]}

    Raises:
        AssertionError: row_def has no "render" override and its
            style_layer_ids span more than one GROUP_MAP group — such a row
            must be hand-authored, since _build_render needs exactly one
            group_key for categorized-color/scale resolution.
    """
    if "render" in row_def:
        render = row_def["render"]
    else:
        group_keys = {GROUP_MAP[layer_id] for layer_id in row_def["style_layer_ids"]}
        assert len(group_keys) == 1, (
            f"legend row '{row_def['label']}': style_layer_ids span multiple groups "
            f"({sorted(group_keys)}) but has no hand-authored 'render' — "
            f"_build_render needs exactly one group_key for scale resolution"
        )
        layers = [layers_by_id[layer_id] for layer_id in row_def["style_layer_ids"]]
        render = _build_render(layers, group_keys.pop(), scale_items)

    return {
        "label": row_def["label"],
        "render": render,
        "style_layer_ids": row_def["style_layer_ids"],
    }


def _build_legend(layers_by_id, scale_items):
    """
    Build the top-level legend list (docs/superpowers/specs/
    2026-08-16-legend-layer-split-design.md, Baustein 3):
    [{"heading": str, "rows": [...]}, ...], one entry per LEGEND_HEADINGS key
    in insertion order.

    Args:
        layers_by_id (dict): style layer id -> MapLibre layer object, the
            whole style
        scale_items (dict): passed through to _build_legend_row unchanged

    Returns:
        list[dict] | None: None if LEGEND_HEADINGS is empty (not the case
            in this repo today, but kept for schema genericity — "legend"
            is Array | null per the design doc, same convention as the
            old "variants" field)
    """
    if not LEGEND_HEADINGS:
        return None

    return [
        {
            "heading": heading,
            "rows": [_build_legend_row(row_def, layers_by_id, scale_items) for row_def in row_defs],
        }
        for heading, row_defs in LEGEND_HEADINGS.items()
    ]


def _build_legend_scales(scale_items):
    """
    Turn the scale_id -> items map collected by _build_render (via
    _build_legend_row) into the top-level legend_scales list.

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
        dict: {"version": "3.0", "styles": [...], "legend": [...] | None,
            "legend_scales": [...] | None} per docs/superpowers/specs/
            2026-08-16-legend-layer-split-design.md. `styles[].groups[]`
            carries no `render`/`variants` — pure toggle/rendering
            metadata (`source_layer(s)`, `name`, `template`,
            `original_file`, `style_layers`). All Part-level rendering
            and legend clustering lives in the separate `legend[]` array,
            built from LEGEND_HEADINGS independently of `groups[]`.

    Raises:
        KeyError: a style layer's id is not in GROUP_MAP (see module docstring)
    """
    groups_dict = {}
    layers_by_id = {}

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

        group = groups_dict[group_key]
        if source_layer not in group["source_layers"]:
            group["source_layers"].append(source_layer)
        group["style_layers"].append(layer_id)
        layers_by_id[layer_id] = layer

    scale_items = {}
    legend = _build_legend(layers_by_id, scale_items)
    legend_scales = _build_legend_scales(scale_items)

    return {
        "version": "3.0",
        "styles": [
            {
                "style_id": style_id,
                "name": name,
                "pmtiles_path": pmtiles_path,
                "groups": list(groups_dict.values()),
            }
        ],
        "legend": legend,
        "legend_scales": legend_scales,
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
    print(f"   - {len(layer_list['legend'] or [])} legend headings documented")
