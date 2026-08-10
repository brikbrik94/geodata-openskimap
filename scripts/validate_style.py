#!/usr/bin/env python3
"""Validates a MapLibre style against a sprite sheet:
- every layer's source-layer must be one of the known consolidated layers
- every icon-image reference must resolve to a name present in the sprite

Usage: validate_style.py <style.json> <sprite.json>
Exit code 0 if valid, 1 if problems were found, 2 on usage error.
"""
import json
import sys

KNOWN_SOURCE_LAYERS = {
    "ski_areas_alpine",
    "ski_areas_nordic",
    "ski_runs_alpine",
    "ski_runs_nordic",
    "ski_lifts",
    "ski_spots",
}


def collect_icon_names(expr):
    """Collect string literals that occur in icon-name *output* position of a
    MapLibre expression: a plain string, or the outputs/fallback of a
    match/case/coalesce expression. Match *values* and case *conditions* are
    not icon names and are intentionally skipped. Other expression heads
    (get, concat, interpolate, ...) are dynamic and not statically checkable,
    so they contribute no names (under-approximation, never a false positive).
    """
    names = set()
    if isinstance(expr, str):
        names.add(expr)
        return names
    if not isinstance(expr, list) or not expr:
        return names

    op = expr[0]
    if op in ("match", "case"):
        rest = expr[2:] if op == "match" else expr[1:]
        has_fallback = len(rest) % 2 == 1
        fallback = rest[-1] if has_fallback else None
        pairs = rest[:-1] if has_fallback else rest
        for i in range(1, len(pairs), 2):
            names |= collect_icon_names(pairs[i])
        if fallback is not None:
            names |= collect_icon_names(fallback)
    elif op == "coalesce":
        for item in expr[1:]:
            names |= collect_icon_names(item)

    return names


def validate(style_path, sprite_path):
    with open(style_path, encoding="utf-8") as f:
        style = json.load(f)
    with open(sprite_path, encoding="utf-8") as f:
        sprite = json.load(f)

    sprite_names = set(sprite.keys())
    problems = []

    for layer in style.get("layers", []):
        source_layer = layer.get("source-layer")
        if source_layer is not None and source_layer not in KNOWN_SOURCE_LAYERS:
            problems.append(
                f"layer '{layer.get('id')}': unknown source-layer '{source_layer}'"
            )

        icon_image = layer.get("layout", {}).get("icon-image")
        if icon_image is not None:
            for name in collect_icon_names(icon_image):
                if name not in sprite_names:
                    problems.append(
                        f"layer '{layer.get('id')}': icon-image '{name}' not found in sprite"
                    )

    return problems


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <style.json> <sprite.json>", file=sys.stderr)
        sys.exit(2)

    problems = validate(sys.argv[1], sys.argv[2])
    if problems:
        print(f"❌ {len(problems)} problem(s) found:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("✔ Style is valid: all source-layers known, all icon-image references resolve to sprite.")
    sys.exit(0)


if __name__ == "__main__":
    main()
