# Design: Split `layer-list.json` into Layer-Info and Legend-Info (v3.0)

## Problem

`GEODATA_PLUGIN_STANDARD.md` v2.1.0 §5.3 ties legend metadata 1:1 to the map's toggle
structure: every `Part` (in `groups[].render` or `groups[].variants[]`) belongs to exactly one
`groups[]` entry, and a `groups[]` entry is exactly one map-toggle unit (one `source_layer`/
`template`). Two unrelated concerns are conflated in one array:

1. **Layer-Info**: which style layers belong together as one toggleable map unit.
2. **Legend-Info**: which visually distinguishable states exist and how to label/cluster them
   for a human-readable legend.

This conflation surfaced concretely while trying to answer a simple question against this
repo's real data (`styles/openskimap-style.json`, `dist/layer-list.json`): "Pisten" and
"Skitouren" are two separate `groups[]` entries (different `source_layer`s:
`ski_runs_downhill_line`/`_poly` vs. `ski_runs_skitour_line`/`_poly`, correctly — a user wants to
toggle them independently on the map). But for a **legend**, both are "downhill-direction"
disciplines that share the same `ski-difficulty-v1` color scale, and a reader benefits from
seeing them clustered under one "Pisten" heading rather than as two disconnected legend blocks.
The current schema has no way to express "these rows from two different toggle-groups belong
under one legend heading" — `axis` (v2.1.0's `variants[]` grouping key) is scoped to a single
`groups[]` entry, not across entries.

A second, independent finding surfaced during the same investigation: this repo's own naming had
a real ambiguity. The `ski-runs-skitour` group's main row was labeled "Skiroute" (German for "ski
route"), but the data it represents (`uses LIKE '%skitour%'`) is real ski touring — no lift, hike
up on skins, ski down. Meanwhile `ski-runs-downhill`'s `grooming == "backcountry"` state (a
still-lift-accessible, ungroomed piste — a descent, "Abfahrt") had no dedicated clear label at
all (bundled as "Piste (Backcountry)"). Corrected terminology (user decision, 2026-08-16):
- **"Skiroute"** = a downhill piste in its backcountry/ungroomed state — still an "Abfahrt" via
  lift-accessible piste infrastructure, just not groomed.
- **"Skitour"** = the separate `uses=skitour` category — no lift, ski touring proper.

## Decisions (aligned with user, 2026-08-16)

### Baustein 1 — `groups[]` stays, loses `render`/`variants`

No rename (the key is established in the standard, §5.2). Content shrinks to pure toggle/
rendering metadata: `source_layer`, `source_layers`, `name`, `template`, `original_file`,
`style_layers`. `render`/`variants` (and the `axis` concept) are removed entirely from this
array — a frontend that only needs "what can I toggle, what style layers does that turn on/off"
reads `groups[]` alone, unconcerned with legend presentation.

### Baustein 2 — `legend_sections[]` renamed to `legend_scales[]`

Same shape, unchanged content (`{id, label, items: [{label, color}]}`) — still exactly the
`ski-difficulty-v1`-style color palettes. Renamed because `legend_sections` is easily confused
with the new `legend[]` array (Baustein 3) — "Scale" is precise and already the internal
vocabulary (`GROUP_LEGEND_SCALE`, `scale_id`), "Section" was vague.

### Baustein 3 — new `legend[]` array

```text
legend: Array<{
  heading: String,
  rows: Array<{
    label: String,
    render: Array<Part>,          // same Part shape as today (kind/color/opacity/width/
                                   // dasharray/radius/stroke_width/icon) - reused as-is
    style_layer_ids: Array<String> // traceability: which real style layer(s) this row
                                   // was derived from/hand-authored against; may span
                                   // MULTIPLE groups[] entries (the whole point)
  }>
}> | null
```

Deliberately mirrors the existing `variants[]` shape (`{label, render: Array<Part>}`) rather than
inventing new vocabulary — the only structural changes are: `axis` is dropped (no longer needed;
rows are already explicitly labeled and clustered by `heading` instead), and a `legend[]` entry is
no longer scoped to one `groups[]` entry — `style_layer_ids` on a row may reference style layers
from **any** `groups[]` entry.

A renderer's contract (as stated by the user): `legend[].heading` renders as a left-aligned title
above a block of rows; `legend[].rows[].label` renders to the right of each row's rendered
preview (drawn from `rows[].render`).

Groups with no meaningful visually-distinguishable states (e.g. `ski-areas-alpine`,
`ski-areas-nordic`, `ski-runs-hike`, `ski-runs-sled`, `ski-runs-snow_park`, `ski-runs-playground`,
`ski-runs-ice_skate` — all single fixed-color renders today, verified against
`styles/openskimap-style.json`: none of these groups has a `GROUP_VARIANTS`/categorized-color
entry) get no `legend[]` heading at all — `legend: null` is valid, same convention as today's
`variants: null`.

### Baustein 4 — Terminology fix: Skiroute vs. Skitour

- `ski-runs-downhill`'s `grooming == "backcountry"` row: relabeled **"Skiroute"** (was "Piste
  (Backcountry)").
- `ski-runs-skitour`'s main (non-freeride) row: relabeled **"Skitour"** (was "Skiroute").
- Both live as separate rows under the shared **"Pisten"** heading (Baustein 3) — the renaming
  removes the previous name collision now that they sit side by side in one legend block.

### Baustein 5 — Row granularity kept, not collapsed

Buckelpiste (mogul) and Freeride remain their own rows, not folded into a generic "Unpräpariert"
— decoupling `legend[]` from the 1:1 Part-per-style-layer model removes the pressure that
previously made fine-grained rows awkward (each used to need its own hand-authored `variants[]`
entry wedged into exactly one `groups[]` entry with matching `axis`). Freeride specifically
benefits: downhill and skitour previously needed two separate "Freeride" rows (one per group,
since a `variants[]` entry couldn't span groups); now one shared "Freeride" row's
`style_layer_ids` can list both `ski-runs-downhill-line`/`ski-runs-connection-line` and
`ski-runs-skitour-line`, since they render identically (verified: `hsl(34, 100%, 50%)`, dasharray
`[3, 6]`, byte-identical in `styles/openskimap-style.json`).

`grooming`/`difficulty` naming for the two states shared between Pisten and Loipen (matching the
user's simplification): **"Präpariert"** (was "Piste" for downhill, "Loipe" for nordic) /
**"Unpräpariert"** — used as the row label for the plain groomed/ungroomed distinction, with
Buckelpiste/Skiroute/Skitour/Freeride as additional, more specific rows alongside them under the
"Pisten" heading. Nordic only has two real states worth naming (Präpariert/Unpräpariert;
Buckelpiste/Skiroute/Skitour/Freeride are downhill/skitour-only concepts, verified: nordic's
`GROOMING_ALLOWLIST` only ever nulls or passes through `classic`/`classic+skating`/`skating`/
`scooter`/`backcountry` — no mogul-equivalent, no freeride at all in nordic data).

### Baustein 6 — Nordic's asymmetric color placement stays in the style, resolved in the row

`ski-runs-nordic-casing` (not `-line`) carries the `ski-difficulty-v1` scale color; `-line` is
fixed white with the grooming-state dasharray. This asymmetry (documented back in the
2026-08-14 design work) doesn't change in the style — but a `legend[]` row can now cleanly
represent the **combined** visual (`render: [outline_part, line_part]`, both sourced from their
respective real layers) under one label, exactly like today's flat `render[]` already does for a
whole group — just now scoped to a single named row instead of the group's unconditional default.

### Baustein 7 — Version bump

`groups[].render`/`variants` removal is breaking. `layer-list.json`'s `version` field goes
`"2.1"` → `"3.0"` per SemVer (breaking change to a published schema = major).

## Illustrative example (this repo's real data, abbreviated)

```json
{
  "version": "3.0",
  "styles": [{ "style_id": "openskimap", "name": "OpenSkiMap", "pmtiles_path": "openskimap.pmtiles",
    "groups": [
      { "source_layer": "ski_runs_downhill_poly", "source_layers": ["ski_runs_downhill_poly", "ski_runs_downhill_line", "ski_runs_connection_line"],
        "name": "Pisten", "template": "ski-runs-downhill", "original_file": "data/src/openskidata.gpkg",
        "style_layers": ["ski-runs-downhill-fill", "ski-runs-downhill-casing", "ski-runs-downhill-line", "ski-runs-downhill-labels", "ski-runs-connection-casing", "ski-runs-connection-line"] },
      { "source_layer": "ski_runs_skitour_line", "source_layers": ["ski_runs_skitour_line", "ski_runs_skitour_poly"],
        "name": "Skitouren", "template": "ski-runs-skitour", "original_file": "data/src/openskidata.gpkg",
        "style_layers": ["ski-runs-skitour-fill", "ski-runs-skitour-line", "ski-runs-skitour-labels"] }
    ]}
  ],
  "legend": [
    { "heading": "Pisten", "rows": [
      { "label": "Präpariert", "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
        "render": [{ "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 3.0, "dasharray": null, "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }] },
      { "label": "Buckelpiste", "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
        "render": [{ "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 3.0, "dasharray": [1, 3], "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }] },
      { "label": "Skiroute", "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line"],
        "render": [{ "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 3.0, "dasharray": [3, 6], "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }] },
      { "label": "Skitour", "style_layer_ids": ["ski-runs-skitour-line"],
        "render": [{ "kind": "line", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 3.0, "dasharray": [3, 6], "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }] },
      { "label": "Freeride", "style_layer_ids": ["ski-runs-downhill-line", "ski-runs-connection-line", "ski-runs-skitour-line"],
        "render": [{ "kind": "line", "color": {"mode": "fixed", "value": "hsl(34, 100%, 50%)"}, "opacity": 1, "width": 3.0, "dasharray": [3, 6], "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }] }
    ]},
    { "heading": "Loipen", "rows": [
      { "label": "Präpariert", "style_layer_ids": ["ski-runs-nordic-casing", "ski-runs-nordic-line"],
        "render": [
          { "kind": "outline", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 5.0, "dasharray": null, "radius": null, "stroke_color": null, "stroke_width": null, "icon": null },
          { "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"}, "opacity": 1, "width": 3.0, "dasharray": null, "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }
        ]},
      { "label": "Unpräpariert", "style_layer_ids": ["ski-runs-nordic-casing", "ski-runs-nordic-line"],
        "render": [
          { "kind": "outline", "color": {"mode": "scale", "scale_id": "ski-difficulty-v1"}, "opacity": 1, "width": 5.0, "dasharray": null, "radius": null, "stroke_color": null, "stroke_width": null, "icon": null },
          { "kind": "line", "color": {"mode": "fixed", "value": "hsl(0, 0%, 100%)"}, "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": null, "stroke_color": null, "stroke_width": null, "icon": null }
        ]}
    ]},
    { "heading": "Lifte", "rows": [
      { "label": "In Betrieb", "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"], "render": [ /* outline + line, unchanged from today's variant */ ] },
      { "label": "Geplant / Im Bau", "style_layer_ids": ["ski-lifts-line-planned"], "render": [ /* unchanged */ ] },
      { "label": "Außer Betrieb", "style_layer_ids": ["ski-lifts-line-disused"], "render": [ /* unchanged */ ] },
      { "label": "Privat", "style_layer_ids": ["ski-lifts-line-private", "ski-lifts-line-private-other"], "render": [ /* unchanged */ ] }
    ]},
    { "heading": "Ski-Spots", "rows": [
      { "label": "Lift Station", "style_layer_ids": ["ski-spots"], "render": [ /* unchanged from today's variant */ ] }
      /* ... 5 more spot_type rows, unchanged content ... */
    ]}
  ],
  "legend_scales": [
    { "id": "ski-difficulty-v1", "label": "Schwierigkeitsgrade", "items": [
      {"label": "Novice", "color": "hsl(125, 100%, 33%)"}, {"label": "Easy", "color": "hsl(208, 100%, 33%)"},
      {"label": "Intermediate", "color": "hsl(359, 94%, 53%)"}, {"label": "Advanced", "color": "hsl(0, 0%, 0%)"},
      {"label": "Sonstige", "color": "hsl(0, 0%, 35%)"}
    ]}
  ]
}
```

## Out of Scope

- Lift-type icons as `legend[]` rows (gondola/chairlift/t-bar/…) — still deferred per
  `docs/TODO.md`, needs website-v3 testing first regardless of this split.
- `groups[]` entries with no visual state distinctions (ski-areas-*, ski-runs-hike/-sled/
  -snow_park/-playground/-ice_skate) get no `legend[]` heading — not addressed further here,
  `legend: null`/absent is sufficient.
- Whether `website-v3` actually renders `legend[]` this way — out of this repo's control; per
  user (2026-08-16), the live frontend doesn't consume any legend metadata yet, so this is safe
  to redesign without a live break.
