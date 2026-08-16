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
from datetime import datetime, timezone

GROUPS = {
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
            yield json.loads(line).get("properties") or {}


def print_report(work_dir):
    for group, cfg in GROUPS.items():
        if not cfg["properties"]:
            continue
        properties_list = []
        found_count = 0
        mtimes = []
        for filename in cfg["files"]:
            path = os.path.join(work_dir, filename)
            if not os.path.exists(path):
                print(f"(skipping {group}: {filename} not found in {work_dir})", file=sys.stderr)
                continue
            found_count += 1
            mtimes.append(os.path.getmtime(path))
            properties_list.extend(read_jsonseq_properties(path))

        total_count = len(cfg["files"])
        suffix = f", INCOMPLETE: {found_count}/{total_count} files found" if found_count < total_count else ""
        print(f"=== {group} ({len(properties_list)} features{suffix}) ===")
        if mtimes:
            oldest = datetime.fromtimestamp(min(mtimes), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            newest = datetime.fromtimestamp(max(mtimes), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if oldest == newest:
                print(f"(source files last modified: {newest})")
            else:
                print(f"(source files last modified: {oldest} to {newest})")
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
