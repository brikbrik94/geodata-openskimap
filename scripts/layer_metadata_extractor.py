#!/usr/bin/env python3
"""
Metadata extractor for MapLibre style layers.

Extracts, per style layer, the `Part` fields defined by
GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3 (kind, color, stroke_color, opacity,
width, dasharray, radius, stroke_width, icon) to support automated legend
rendering. One Part
per style layer — no merging, no "primary layer" selection (§5.3: "Kein
Merge mehrerer Style-Layer zu einem Part und keine Prioritäts-Auswahl
eines 'Primär-Layers' mehr").

Ported from geodata-overlays/scripts/layer_metadata_extractor.py per
GEODATA_PLUGIN_STANDARD.md §5.8 ("einfach übernehmen"), with two
deviations required by openskimap's style but absent from the upstream
original (geodata-overlays never uses either of them):

1. extract_part_color/extract_categorized_items resolve a top-level
   `case` expression (openskimap's difficulty/status colors are nested
   case/match expressions, not flat color strings or plain
   interpolate/match) before classifying the paint property — resolution
   always picks the "europe" branch (DACH is this project's target
   audience; see CLAUDE.md), falling back to the case's else-branch if no
   `difficulty_convention == "europe"` condition is present. Without
   this, e.g. `ski-runs-downhill-casing`'s Part.color would be null
   instead of the correctly resolved fixed white, and
   `ski-runs-nordic-casing`'s would be null instead of a
   `{mode: "scale"}` reference.
2. `circle` is a supported `kind` (circle-color/circle-opacity/
   circle-radius) — openskimap uses circle layers for ski_spots and the
   low-zoom ski-area markers. GEODATA_PLUGIN_STANDARD.md's own kind
   table documents this directly as of v2.0.0 (§5.3), unlike v1.1.0
   where it required a local deviation.
"""

DIFFICULTY_CASE_PROPERTY = "difficulty_convention"
DIFFICULTY_CASE_VALUE = "europe"

# kind -> {field name -> MapLibre paint/layout property}, per
# GEODATA_PLUGIN_STANDARD.md v2.1.0 §5.3's kind table. A field absent from a
# kind's sub-dict is always null for that kind's Parts (e.g. "fill" has no
# "width").
PART_FIELDS_BY_KIND = {
    "fill": {"color": "fill-color", "opacity": "fill-opacity"},
    "line": {
        "color": "line-color", "opacity": "line-opacity",
        "width": "line-width", "dasharray": "line-dasharray",
    },
    "outline": {
        "color": "line-color", "opacity": "line-opacity",
        "width": "line-width", "dasharray": "line-dasharray",
    },
    "icon": {"color": "icon-color", "opacity": "icon-opacity", "icon": "icon-image"},
    "text": {"color": "text-color", "opacity": "text-opacity"},
    "circle": {
        "color": "circle-color", "opacity": "circle-opacity", "radius": "circle-radius",
        "stroke_color": "circle-stroke-color", "stroke_width": "circle-stroke-width",
    },
}


def determine_part_kind(layer):
    """
    Determine a style layer's Part `kind` per GEODATA_PLUGIN_STANDARD.md
    v2.1.0 §5.3.

    Args:
        layer (dict): A MapLibre style layer object

    Returns:
        str | None: one of PART_FIELDS_BY_KIND's keys, or None if the
            layer's `type` has no kind mapping (e.g. fill-extrusion,
            heatmap, raster) — such a layer produces no Part.
    """
    layer_type = layer.get("type")

    if layer_type == "fill":
        return "fill"
    if layer_type == "circle":
        return "circle"
    if layer_type == "line":
        layer_id = layer.get("id", "")
        return "outline" if layer_id.endswith(("-casing", "-outline")) else "line"
    if layer_type == "symbol":
        return "icon" if "icon-image" in layer.get("layout", {}) else "text"

    return None


def _resolve_part_color_expression(layer, kind):
    """
    Look up the kind-specific color paint property (PART_FIELDS_BY_KIND) and
    resolve it one step: a top-level "case" expression is resolved via
    _resolve_case_branch (openskimap deviation, see module docstring).

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        str | list | None: a literal color string, a resolved
            interpolate/match expression (list), or None (kind has no color
            field, property unset, non-list/non-string value, or an
            unsupported expression form after case-resolution).
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("color")
    if prop is None:
        return None

    value = layer.get("paint", {}).get(prop)

    if isinstance(value, str):
        return value

    if not isinstance(value, list) or not value:
        return None

    if value[0] == "case":
        value = _resolve_case_branch(value, DIFFICULTY_CASE_PROPERTY, DIFFICULTY_CASE_VALUE)
        if isinstance(value, str):
            return value
        if not isinstance(value, list):
            return None

    if value[0] in ("interpolate", "match"):
        return value

    return None


def extract_part_color(layer, kind):
    """
    Extract a Part's `color` field per GEODATA_PLUGIN_STANDARD.md v2.0.0
    §5.3/§5.4.

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        dict | str | None: {"mode": "fixed", "value": str} for a literal
            color; the string "categorized" (internal marker — the actual
            {"mode": "scale", "scale_id": ...} is assembled one level up in
            generate_layer_list.py, which owns the group->scale_id config,
            see extract_categorized_items for the item list) for an
            interpolate/match expression; None otherwise.
    """
    resolved = _resolve_part_color_expression(layer, kind)

    if isinstance(resolved, str):
        return {"mode": "fixed", "value": resolved}
    if isinstance(resolved, list):
        return "categorized"
    return None


def extract_part_stroke_color(layer, kind):
    """
    Extract a Part's `stroke_color` field per GEODATA_PLUGIN_STANDARD.md
    v2.1.0 §5.3: only kind:"circle" has a stroke_color field (from
    circle-stroke-color); every other kind gets None.

    Unlike extract_part_color, this does not classify interpolate/match
    expressions as "categorized" — no style layer in this repo has a
    categorized circle-stroke-color, and generate_layer_list.py's scale
    resolution (GROUP_LEGEND_SCALE) only wires up `color`, not
    `stroke_color`. A non-literal expression is treated like any other
    unsupported form and returns None (same as extract_part_dasharray's
    contract), not like extract_part_color's "categorized" marker.

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        dict | None: {"mode": "fixed", "value": str} for a literal color;
            None if the kind has no stroke_color field, the property is
            unset, or its value isn't a literal string.
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("stroke_color")
    if prop is None:
        return None

    value = layer.get("paint", {}).get(prop)
    return {"mode": "fixed", "value": value} if isinstance(value, str) else None


def extract_categorized_items(layer, kind):
    """
    Extract legend items ({label, color} per category) for a Part whose
    color is categorized (see extract_part_color).

    Args:
        layer (dict): A MapLibre style layer object
        kind (str): One of PART_FIELDS_BY_KIND's keys

    Returns:
        list[dict] | None: [{"label": ..., "color": ...}, ...], or None if
            the layer's color is not categorized.
    """
    resolved = _resolve_part_color_expression(layer, kind)

    if not isinstance(resolved, list):
        return None
    if resolved[0] == "interpolate":
        return _parse_interpolate_expression(resolved)
    if resolved[0] == "match":
        return _parse_match_expression(resolved)
    return None


def _extract_interpolatable_number(value):
    """
    Shared rule for width/dasharray-adjacent numeric fields (width, radius,
    opacity): a literal number is returned directly; an `interpolate`
    expression over `["zoom"]` returns its highest-zoom stop value (the last
    value in the stop list); any other form (missing, data-driven, etc.)
    returns None.
    """
    if isinstance(value, (int, float)):
        return value

    if isinstance(value, list) and value and value[0] == "interpolate":
        stops_and_values = value[3:]
        if stops_and_values and len(stops_and_values) % 2 == 0:
            last_value = stops_and_values[-1]
            if isinstance(last_value, (int, float)):
                return last_value

    return None


def extract_part_opacity(layer, kind):
    """Kind-specific opacity (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. Defaults to 1 if unset/unresolvable or
    if `kind` has no opacity field."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("opacity")
    if prop is None:
        return 1

    result = _extract_interpolatable_number(layer.get("paint", {}).get(prop))
    return result if result is not None else 1


def extract_part_width(layer, kind):
    """Kind-specific line-width (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no width field."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("width")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))


def extract_part_stroke_width(layer, kind):
    """Kind-specific circle-stroke-width (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no stroke_width field
    (only "circle" does)."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("stroke_width")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))


def extract_part_radius(layer, kind):
    """Kind-specific circle-radius (PART_FIELDS_BY_KIND), see
    _extract_interpolatable_number. None if `kind` has no radius field
    (only "circle" does)."""
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("radius")
    if prop is None:
        return None
    return _extract_interpolatable_number(layer.get("paint", {}).get(prop))


def extract_part_dasharray(layer, kind):
    """
    Kind-specific line-dasharray (PART_FIELDS_BY_KIND). Only a literal
    2-element numeric array counts, whether written as a raw array
    (`[1, 3]`) or wrapped in a MapLibre "literal" expression
    (`["literal", [1, 3]]` — the form openskimap's style actually uses).
    None if `kind` has no dasharray field, the field is missing, or the
    value doesn't match either form.
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("dasharray")
    if prop is None:
        return None

    dasharray = layer.get("paint", {}).get(prop)
    if not isinstance(dasharray, list):
        return None

    if len(dasharray) == 2 and dasharray[0] == "literal" and isinstance(dasharray[1], list):
        candidate = dasharray[1]
    else:
        candidate = dasharray

    if len(candidate) == 2 and all(isinstance(v, (int, float)) for v in candidate):
        return candidate

    return None


def extract_part_icon(layer, kind):
    """
    Kind-specific icon-image (PART_FIELDS_BY_KIND). Only returns a value
    when `kind` has an icon field (only "icon" does) and the layout
    property is a literal string (openskimap's lift-icon layer uses a
    `match` expression there, so this returns None for it — correct per
    spec, not a bug).
    """
    prop = PART_FIELDS_BY_KIND.get(kind, {}).get("icon")
    if prop is None:
        return None

    icon = layer.get("layout", {}).get(prop)
    return icon if isinstance(icon, str) else None







def _resolve_case_branch(expr, property_name, target_value):
    """
    Resolve a MapLibre "case" expression to the output of the branch whose
    condition is ["==", ["get", property_name], target_value], falling back
    to the case's else-branch (its final element) if no branch matches.

    Expected format:
    ["case", cond1, output1, cond2, output2, ..., else_output]

    Args:
        expr (list): Case expression array
        property_name (str): property name to match in an ["==", ["get", ...], value] condition
        target_value: value the condition must compare against

    Returns:
        The matching (or else-branch) output, or None if the expression is malformed
    """
    branches = expr[1:]
    if len(branches) % 2 == 0:
        return None

    for i in range(0, len(branches) - 1, 2):
        condition = branches[i]
        output = branches[i + 1]
        if (
            isinstance(condition, list)
            and len(condition) == 3
            and condition[0] == "=="
            and condition[1] == ["get", property_name]
            and condition[2] == target_value
        ):
            return output

    return branches[-1]


def _parse_interpolate_expression(expr):
    """
    Parse MapLibre interpolate expression and extract legend items.

    Expected format:
    ["interpolate", ["linear"], ["get", "property"], stop1, color1, stop2, color2, ...]

    Args:
        expr (list): Interpolate expression array

    Returns:
        list: List of {label, color} dicts representing ranges
    """
    if len(expr) < 5:
        return None

    # Extract stops and colors: [stop1, color1, stop2, color2, ...]
    stops_and_colors = expr[3:]

    if len(stops_and_colors) % 2 != 0:
        return None

    # Parse stops and colors
    stops = []
    colors = []
    for i in range(0, len(stops_and_colors), 2):
        stop = stops_and_colors[i]
        color = stops_and_colors[i + 1]
        if isinstance(stop, (int, float)) and isinstance(color, str):
            stops.append(stop)
            colors.append(color)

    if not stops:
        return None

    # Create legend items from ranges
    legend_items = []
    for i, stop in enumerate(stops):
        color = colors[i]
        if i < len(stops) - 1:
            next_stop = stops[i + 1]
            label = f"{int(stop)}-{int(next_stop)} min"
        else:
            label = f"{int(stop)}+ min"
        legend_items.append({
            "label": label,
            "color": color
        })

    return legend_items


def _parse_match_expression(expr):
    """
    Parse a MapLibre match expression and extract legend items.

    Expected format:
    ["match", ["get", "property"], value1, color1, value2, color2, ..., fallback_color]

    Numeric values (e.g. time-stage thresholds) produce range labels
    ("X-Y min", sorted ascending, no fallback item). String values (e.g.
    categorical types) produce one item per value plus a "Sonstige" item
    for the fallback color, if present.

    Args:
        expr (list): Match expression array

    Returns:
        list: List of {label, color} dicts, or None if unparseable
    """
    if len(expr) < 4:
        return None

    values_colors_and_fallback = expr[2:]

    if len(values_colors_and_fallback) < 2:
        return None

    # Last element might be fallback if we have odd number of elements
    fallback_color = None
    if len(values_colors_and_fallback) % 2 != 0:
        fallback_color = values_colors_and_fallback[-1]
        values_colors_and_fallback = values_colors_and_fallback[:-1]

    values = []
    colors = []
    for i in range(0, len(values_colors_and_fallback), 2):
        value = values_colors_and_fallback[i]
        color = values_colors_and_fallback[i + 1]
        if isinstance(color, str):
            values.append(value)
            colors.append(color)

    if not values:
        return None

    if all(isinstance(v, (int, float)) for v in values):
        return build_numeric_match_items(values, colors)

    return _build_categorical_match_items(values, colors, fallback_color)


def build_numeric_match_items(values, colors):
    """Build "X-Y min"-style range legend items from sorted numeric match values."""
    stop_color_pairs = sorted(zip(values, colors), key=lambda pair: pair[0])
    sorted_values = [pair[0] for pair in stop_color_pairs]
    sorted_colors = [pair[1] for pair in stop_color_pairs]

    legend_items = []
    for i, value in enumerate(sorted_values):
        color = sorted_colors[i]
        if i == 0:
            label = f"0-{int(value)} min"
        else:
            prev_value = sorted_values[i - 1]
            label = f"{int(prev_value)}-{int(value)} min"
        legend_items.append({"label": label, "color": color})
    return legend_items


def _build_categorical_match_items(values, colors, fallback_color):
    """Build one legend item per string match value, plus a "Sonstige" item for the fallback color."""
    legend_items = [
        {"label": str(value).replace("_", " ").title(), "color": color}
        for value, color in zip(values, colors)
    ]
    if fallback_color is not None:
        legend_items.append({"label": "Sonstige", "color": fallback_color})
    return legend_items


