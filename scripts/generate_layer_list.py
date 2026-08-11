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
group key itself (each of our 6 groups is its own category),
`original_file` points at the shared GeoPackage source. `source_layer`
holds the group's first (file-order) source-layer for spec compliance;
`source_layers` (plural, not in the spec) additionally lists every
distinct source-layer the group actually spans, since collapsing that
to a single string would lose information for groups split across
point/poly or line/poly PMTiles layers.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
from layer_metadata_extractor import (
    extract_layer_color,
    extract_layer_opacity,
    extract_legend_items,
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


def _group_metadata(group_layers):
    """Same fill > line > circle > symbol primary-layer selection as
    layer_metadata_extractor.extract_layer_metadata, but over an already
    collected list of layers instead of filtering style_data by a single
    source-layer name (a group here can span several)."""
    layer_type_priority = {"fill": 4, "line": 3, "circle": 2, "symbol": 1}

    primary_layer = None
    for layer in group_layers:
        layer_type = layer.get("type")
        if layer_type not in layer_type_priority:
            continue
        if primary_layer is None or layer_type_priority[layer_type] > layer_type_priority[primary_layer.get("type")]:
            primary_layer = layer

    if primary_layer is None:
        return None

    return {
        "type": primary_layer.get("type"),
        "color": extract_layer_color(primary_layer),
        "opacity": extract_layer_opacity(primary_layer),
        "legend_items": extract_legend_items(group_layers),
    }


def build_layer_list(style_data, style_id, name, pmtiles_path):
    """
    Build the layer-list.json document for one style.

    Args:
        style_data (dict): parsed MapLibre style JSON
        style_id (str): matches the manifest dataset's "id"
        name (str): matches the manifest dataset's "name"
        pmtiles_path (str): path relative to dist/pmtiles/, e.g. "openskimap.pmtiles"

    Returns:
        dict: {"version": "1.0", "styles": [...]} per the plugin standard schema

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
                "name": group_key.replace("-", " ").title(),
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

    for group_key, group in groups_dict.items():
        metadata = _group_metadata(group_layers[group_key])
        if metadata:
            group["type"] = metadata.get("type")
            group["color"] = metadata.get("color")
            group["opacity"] = metadata.get("opacity")
            group["legend_items"] = metadata.get("legend_items")

    return {
        "version": "1.0",
        "styles": [
            {
                "style_id": style_id,
                "name": name,
                "pmtiles_path": pmtiles_path,
                "groups": list(groups_dict.values()),
            }
        ],
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
