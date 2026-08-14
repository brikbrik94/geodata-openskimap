#!/usr/bin/env python3
"""
Metadata extractor for MapLibre style layers.

Extracts type, color, opacity, width, dasharray, outline color/width,
icon, and legend items from style JSON layers to support automated
legend rendering.

Ported from geodata-overlays/scripts/layer_metadata_extractor.py per
GEODATA_PLUGIN_STANDARD.md §5.6 ("einfach übernehmen"), with three
deviations required by openskimap's style but absent from the upstream
original (geodata-overlays never uses any of them):

1. extract_layer_color only returns a value when it is actually a string
   (hex/rgba/hsl) — the spec documents `color` as `String | null`, but
   openskimap's difficulty/status colors are nested case/match
   expressions, not flat color strings.
2. `circle` is supported alongside fill/line/symbol (circle-color/
   circle-opacity, priority between line and symbol) — openskimap uses
   circle layers for ski_spots and the low-zoom ski-area markers, which
   the upstream priority map silently drops (source-layer ends up with no
   type/color/opacity/legend_items at all when circle is its only layer
   type, e.g. ski_spots).
3. `extract_legend_items` resolves a top-level `case` expression before
   looking for `interpolate`/`match` — openskimap's piste-difficulty fill
   colors (`ski-runs-*-fill`) switch on `difficulty_convention`
   (europe/japan/default) via `case`, each branch a `match` on
   `difficulty`. Without this, these layers — the legend a ski map
   actually needs — silently got `legend_items: null`. Resolution always
   picks the "europe" branch (DACH is this project's target audience;
   see CLAUDE.md), falling back to the `case`'s else-branch if no
   `difficulty_convention == "europe"` condition is present.
"""

DIFFICULTY_CASE_PROPERTY = "difficulty_convention"
DIFFICULTY_CASE_VALUE = "europe"

# kind -> {field name -> MapLibre paint/layout property}, per
# GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.3's kind table. A field absent from a
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
    "circle": {"color": "circle-color", "opacity": "circle-opacity", "radius": "circle-radius"},
}


def determine_part_kind(layer):
    """
    Determine a style layer's Part `kind` per GEODATA_PLUGIN_STANDARD.md
    v2.0.0 §5.3.

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


def extract_layer_color(layer):
    """
    Extract color from a MapLibre style layer.

    For fill layers, looks for 'fill-color' in paint properties.
    For line layers, looks for 'line-color' in paint properties.
    For symbol layers, tries 'text-color' or 'icon-color'.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        str: Hex color string (e.g., "#3b82f6") or None if not found or
             not a plain string (e.g. a case/match/interpolate expression)
    """
    if "paint" not in layer:
        return None

    paint = layer.get("paint", {})
    layer_type = layer.get("type")

    # Try type-specific color properties
    if layer_type == "fill":
        color = paint.get("fill-color")
    elif layer_type == "line":
        color = paint.get("line-color")
    elif layer_type == "circle":
        color = paint.get("circle-color")
    elif layer_type == "symbol":
        color = paint.get("text-color") or paint.get("icon-color")
    elif layer_type == "background":
        color = paint.get("background-color")
    else:
        color = None

    return color if isinstance(color, str) else None


def extract_layer_opacity(layer):
    """
    Extract opacity from a MapLibre style layer.

    For fill layers, looks for 'fill-opacity' in paint properties.
    For line layers, looks for 'line-opacity' in paint properties.
    For symbol layers, tries 'text-opacity' or 'icon-opacity'.
    Defaults to 1 if not specified.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        float: Opacity value (0-1), defaults to 1
    """
    paint = layer.get("paint", {})
    layer_type = layer.get("type")

    # Try type-specific opacity properties
    if layer_type == "fill":
        opacity = paint.get("fill-opacity")
        if opacity is not None:
            return opacity
    elif layer_type == "line":
        opacity = paint.get("line-opacity")
        if opacity is not None:
            return opacity
    elif layer_type == "circle":
        opacity = paint.get("circle-opacity")
        if opacity is not None:
            return opacity
    elif layer_type == "symbol":
        opacity = paint.get("text-opacity") or paint.get("icon-opacity")
        if opacity is not None:
            return opacity

    # Default to 1 if not specified
    return 1


def extract_layer_width(layer):
    """
    Extract line-width from a MapLibre line layer.

    Literal numbers are returned directly. An `interpolate` expression over
    zoom returns its highest-zoom stop value (the last value in the stop
    list) — the width the layer renders at when fully zoomed in. Any other
    expression form (e.g. data-driven) returns None, as does any non-line
    layer.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        float | int | None
    """
    if layer.get("type") != "line":
        return None

    width = layer.get("paint", {}).get("line-width")

    if isinstance(width, (int, float)):
        return width

    if isinstance(width, list) and width and width[0] == "interpolate":
        stops_and_values = width[3:]
        if stops_and_values and len(stops_and_values) % 2 == 0:
            last_value = stops_and_values[-1]
            if isinstance(last_value, (int, float)):
                return last_value

    return None


def extract_layer_dasharray(layer):
    """
    Extract line-dasharray from a MapLibre line layer.

    Only a literal 2-element numeric array counts, whether written as a raw
    array (`[1, 3]`) or wrapped in a MapLibre "literal" expression
    (`["literal", [1, 3]]` — the form openskimap's style actually uses for
    the private/other lift-line variants). Anything else (missing field,
    wrong length, non-numeric values) returns None.

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        list[float | int] | None
    """
    dasharray = layer.get("paint", {}).get("line-dasharray")

    if not isinstance(dasharray, list):
        return None

    if len(dasharray) == 2 and dasharray[0] == "literal" and isinstance(dasharray[1], list):
        candidate = dasharray[1]
    else:
        candidate = dasharray

    if len(candidate) == 2 and all(isinstance(v, (int, float)) for v in candidate):
        return candidate

    return None


def extract_outline_metadata(group_layers):
    """
    Find a group's casing/outline layer and extract its color/width.

    Scans group_layers for the first `type: "line"` layer whose `id` ends in
    "-casing" or "-outline" (GEODATA_PLUGIN_STANDARD.md v1.1 §5.3 extraction
    rule — id-suffix only, no z-order or other fallback). Its `line-color`
    (via extract_layer_color — None if it's an expression, not a literal
    string) and `line-width` (via extract_layer_width) become
    outline_color/outline_width. No matching layer -> both None.

    Args:
        group_layers (list): List of MapLibre layer objects in one group

    Returns:
        dict: {"outline_color": str | None, "outline_width": float | int | None}
    """
    for layer in group_layers:
        layer_id = layer.get("id", "")
        if layer.get("type") == "line" and (
            layer_id.endswith("-casing") or layer_id.endswith("-outline")
        ):
            return {
                "outline_color": extract_layer_color(layer),
                "outline_width": extract_layer_width(layer),
            }

    return {"outline_color": None, "outline_width": None}


def extract_layer_icon(layer):
    """
    Extract icon-image from a MapLibre symbol layer.

    Only returns a value for `type: "symbol"` layers, and only when
    `layout.icon-image` is a literal string (openskimap's lift-icon layer
    uses a `match` expression there, so this returns None for it — correct
    per spec, not a bug).

    Args:
        layer (dict): A MapLibre layer object

    Returns:
        str | None
    """
    if layer.get("type") != "symbol":
        return None

    icon = layer.get("layout", {}).get("icon-image")
    return icon if isinstance(icon, str) else None


# NOTE: unlike generate_layer_list.py's _group_metadata, which excludes
# -casing/-outline-suffixed layers from primary-layer selection (so a casing
# layer never determines a group's color/type), extract_legend_items below
# is deliberately NOT given that same filtered list — it scans ALL of a
# group's layers (including casing/outline ones) for a categorized color
# expression. Today this is harmless (no casing layer's color expression
# currently wins the scan ahead of the "real" one), but it's a latent
# inconsistency risk: if a future style change moves a group's only
# categorized color expression onto a casing-only layer while a non-casing
# layer has a different/no color, legend_items and the primary color/type
# could show inconsistent information. Watch for this if style layer order
# changes.
def extract_legend_items(style_layers):
    """
    Extract legend items from style layers.

    Scans fill-color (fill layers) and line-color (line layers) for
    interpolate/match expressions, resolving a top-level "case" first (see
    module docstring, deviation 3) if present. Numeric match/interpolate
    values produce time-range-style labels ("X-Y min"); string match values
    produce one item per matched value plus a trailing "Sonstige" item for
    the fallback color, if any.

    Args:
        style_layers (list): List of MapLibre layer objects

    Returns:
        list: List of {label, color} dicts for categorized layers, or None for simple layers
    """
    if not style_layers:
        return None

    color_prop_by_type = {"fill": "fill-color", "line": "line-color", "circle": "circle-color"}

    for layer in style_layers:
        layer_type = layer.get("type")
        color_prop = color_prop_by_type.get(layer_type)
        if color_prop is None:
            continue

        paint = layer.get("paint", {})
        color_expr = paint.get(color_prop)

        if not isinstance(color_expr, list):
            continue

        if color_expr[0] == "case":
            color_expr = _resolve_case_branch(
                color_expr, DIFFICULTY_CASE_PROPERTY, DIFFICULTY_CASE_VALUE
            )
            if not isinstance(color_expr, list):
                continue

        if color_expr[0] == "interpolate":
            return _parse_interpolate_expression(color_expr)
        elif color_expr[0] == "match":
            return _parse_match_expression(color_expr)

    return None


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


def extract_layer_metadata(style_data, source_layer):
    """
    Extract comprehensive metadata for a source layer from a style.

    Determines the primary layer type based on priority: fill > line > symbol.
    Extracts color and opacity from the primary layer.

    Args:
        style_data (dict): A MapLibre style JSON object
        source_layer (str): The source-layer name to extract metadata for

    Returns:
        dict: Metadata object with keys:
            - type: "fill" | "line" | "symbol" (from primary layer)
            - color: hex string or None
            - opacity: number (0-1)
            - legend_items: list or None
        Returns None if no matching layers found for source_layer
    """
    layers = style_data.get("layers", [])

    # Filter layers by source-layer
    matching_layers = [
        layer for layer in layers
        if layer.get("source-layer") == source_layer
    ]

    if not matching_layers:
        return None

    # Determine primary layer type by priority: fill > line > symbol
    primary_layer = None
    layer_type_priority = {"fill": 4, "line": 3, "circle": 2, "symbol": 1}

    for layer in matching_layers:
        layer_type = layer.get("type")
        if layer_type in layer_type_priority:
            if primary_layer is None:
                primary_layer = layer
            else:
                current_priority = layer_type_priority.get(layer_type, 0)
                existing_priority = layer_type_priority.get(primary_layer.get("type"), 0)
                if current_priority > existing_priority:
                    primary_layer = layer

    if primary_layer is None:
        return None

    # Extract metadata from primary layer
    return {
        "type": primary_layer.get("type"),
        "color": extract_layer_color(primary_layer),
        "opacity": extract_layer_opacity(primary_layer),
        "legend_items": extract_legend_items(matching_layers),
    }
