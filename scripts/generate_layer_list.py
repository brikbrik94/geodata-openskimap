#!/usr/bin/env python3
"""
Builds dist/layer-list.json per GEODATA_PLUGIN_STANDARD.md §5.

Unlike geodata-overlays (many per-file datasets, each becoming its own
group), geodata-openskimap has a single hand-crafted style sourced from one
shared GeoPackage. Groups here are simply "all style layers that reference
the same source-layer" (e.g. ski_runs_alpine's casing/line/gladed/
ungroomed/fill/snowmaking/labels layers become one group) — exactly the
"labels + polygons + lines that logically belong together" grouping the
spec's legend/toggle automation is for.

`template` and `original_file` have no direct equivalent without a
per-group dataset config or source file: `template` is set to the
source-layer name itself (each of our 6 groups is its own category),
`original_file` points at the shared GeoPackage source.
"""
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
from layer_metadata_extractor import extract_layer_metadata

SOURCE_GPKG_REL_PATH = "data/src/openskidata.gpkg"


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
    """
    groups_dict = {}

    for layer in style_data.get("layers", []):
        source_layer = layer.get("source-layer")
        layer_id = layer.get("id")

        if not source_layer or not layer_id:
            continue

        if source_layer not in groups_dict:
            layer_metadata = extract_layer_metadata(style_data, source_layer)

            group = {
                "source_layer": source_layer,
                "name": source_layer.replace("_", " ").title(),
                "template": source_layer,
                "original_file": SOURCE_GPKG_REL_PATH,
                "style_layers": [],
            }
            if layer_metadata:
                group["type"] = layer_metadata.get("type")
                group["color"] = layer_metadata.get("color")
                group["opacity"] = layer_metadata.get("opacity")
                group["legend_items"] = layer_metadata.get("legend_items")

            groups_dict[source_layer] = group

        groups_dict[source_layer]["style_layers"].append(layer_id)

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
