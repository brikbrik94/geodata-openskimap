# Design: Migration auf `layer-list.json` v2.0 (`render: Array<Part>`-Modell)

## Problem

`geodata-plugin-standard` wurde von v1.1.0 auf v2.0.0 aktualisiert (Submodul-Bump,
2026-08-14, Commit `066fcc7`). §5 des Standards ersetzt das bisherige
Einzel-Property-Paint-Modell (ein "Primär-Layer" pro Gruppe gewinnt per
Typ-Priorität `fill > line > circle > symbol`, plus ein optionaler
Casing/Outline-Layer für `outline_color`/`outline_width`) durch ein generisches
**1:1 Style-Layer→`Part`-Mapping**: jeder MapLibre-Style-Layer einer Gruppe wird
unabhängig zu genau einem `Part` im neuen `render`-Array, ohne Merge und ohne
Prioritäts-Auswahl. `color` wird zum Objekt (`{mode: "fixed", value}` oder
`{mode: "scale", scale_id}`), `legend_scale_id` wird **verpflichtend**, sobald
irgendein `Part` einer Gruppe eine kategorisierte Farbe hat (§5.5). Schema-Version
`"1.1"` → `"2.0"`, Breaking Change (§5.6).

`scripts/layer_metadata_extractor.py` und `scripts/generate_layer_list.py` müssen
laut Portierungshinweis (§5.8) vollständig auf das neue Modell umgestellt werden —
"kein Ergänzung, sondern vollständiger Ersatz" der v1.1-Erweiterung.

## Untersuchung

Alle 33 Style-Layer aus `styles/openskimap-style.json` wurden gegen die neue
Kind-Tabelle (§5.3) durchgespielt (vollständiger Dump aller `paint`/`layout`-Werte,
siehe Session-Log). Wichtigste Erkenntnisse:

1. **Downhill und Nordic sind strukturell asymmetrisch** — naive Annahme "alle vier
   Pisten-Kategorien sehen gleich aus" ist falsch:
   - `ski-runs-downhill-casing`: `line-color` ist ein `case` auf `lit` (Straßenbeleuchtung),
     **nicht** kategorisiert → löst nach der (verallgemeinerten) Case-Regel auf den
     Else-Zweig auf → `{mode: "fixed", value: "hsl(0, 0%, 100%)"}`.
     `ski-runs-downhill-line`/`-gladed`/`-ungroomed`/`-labels`: `case` auf
     `difficulty_convention` → kategorisiert → `{mode: "scale", scale_id:
     "ski-difficulty-v1"}`.
   - `ski-runs-nordic-casing`: **umgekehrt** — hier trägt die Casing-Linie die
     Schwierigkeitsfarbe (`case` auf `difficulty_convention`) → `scale`.
     `ski-runs-nordic-line`/`-ungroomed`: `case` auf `lit` → `fixed`
     `"hsl(0, 0%, 100%)"`. (Dies ist exakt der Fall, den das Standard-Beispiel in
     §5.7 als `ski-runs-nordic`-Referenz zeigt — vermutlich aus genau diesen
     Live-Daten übernommen.)
   - `skitour`/`other` haben keine Casing-Variante, nur `-fill`/`-line`/`-labels`,
     jeweils alle drei kategorisiert (`scale`).
   - Alle kategorisierten Farben innerhalb einer Gruppe sind byte-identisch
     (Python-Vergleich der geparsten Expressions) → ein `legend_scale_id` pro
     Gruppe reicht, keine Part-genaue Skalen-Differenzierung nötig.
2. **Zwei bisher nicht als Skala erfasste kategorisierte Farben** brauchen unter
   v2.0 zwingend eine `legend_scale_id` (v1.1 kannte hier nur gruppen-direkte
   `legend_items` ohne Skalen-Kennung):
   - `ski-lifts-line`/`-line-other`/`-line-private`/`-line-private-other`:
     `match` auf `status` (byte-identisch über alle vier) → neue Skala
     `ski-lift-status-v1` ("Lift-Status").
   - `ski-spots`: `match` auf `spot_type` → neue Skala `ski-spot-type-v1`
     ("Spot-Typ").
   - `ski-lifts-casing` (`"hsl(0, 0%, 100%)"`, literal) und `ski-lifts-labels`
     (`"#2c3e50"`, literal) bleiben `fixed` — anders als bei den Pisten-Gruppen
     ist hier nichts kategorisiert außer den vier Linien-Varianten.
3. **`circle-stroke-color`/`circle-stroke-width`** (`ski-areas-alpine/-nordic-circle`,
   `ski-spots`) haben im `Part`-Modell kein Feld — Standard-seitige Lücke, nicht in
   diesem Repo behebbar. Gemeldet als
   [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3)
   (mit Fallbeispiel aus genau diesen zwei Layern). Datenverlust wird bewusst in
   Kauf genommen, bis der Standard nachzieht.
4. **`ski-lifts-icons`** (`layout.icon-image` ist eine `match`-Expression) bleibt wie
   bisher `icon: null` (nur literale Strings werden extrahiert) — kein Bug, wie
   schon im bestehenden Modul-Docstring dokumentiert.
5. Alle `interpolate`-`line-width`/`circle-radius`-Kurven sind über `["zoom"]`,
   damit greift die bestehende "höchster Zoom-Stop"-Regel unverändert.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-14)

1. **Vollständiger Ersatz**, kein Parallelbetrieb von v1.1 und v2.0 — `dist/` ist
   nicht versioniert, kein Downstream-Konsument innerhalb dieses Repos hängt an
   v1.1. Kein Feature-Flag (`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md`: keine
   Kompat-Shims, wo eine direkte Codeänderung reicht).
2. **`extract_layer_metadata()`** (bereits als toter Code markiert, TODO-Eintrag
   vom 2026-08-14) wird **entfernt statt migriert** — sie verkörpert exakt das
   alte Primär-Layer-Modell, das die Migration ablöst; keine sinnvolle
   Entsprechung im neuen Modell.
3. **Struktur:** eine zentrale `PART_FIELDS_BY_KIND`-Konstante (1:1 Abbild der
   §5.3-Tabelle) plus weiterhin kleine, einzeln testbare Extraktionsfunktionen
   pro Feld (`extract_part_color`, `extract_part_opacity`, `extract_part_width`,
   `extract_part_dasharray`, `extract_part_radius`, `extract_part_icon`), jede
   nimmt `(layer, kind)` — nicht eine einzelne monolithische Funktion.
4. **Case-Auflösung wird verallgemeinert**: die openskimap-Deviation (`case` auf
   `difficulty_convention`, Fallback aufs Else) wandert aus der bisherigen
   `extract_legend_items` in `extract_part_color` selbst und gilt für **jede**
   Farb-Extraktion (nicht nur Legenden-Erkennung). Notwendig, weil unter dem 1:1-
   Modell jeder Part (nicht nur der frühere "Primär-Layer") eine korrekte Farbe
   braucht — sonst würden z. B. `ski-runs-downhill-casing`/`ski-runs-nordic-line`
   fälschlich `color: null` statt der korrekt aufgelösten Fixfarbe bekommen.
5. **Neue Skalen-Namen**: `ski-lift-status-v1` / "Lift-Status" und
   `ski-spot-type-v1` / "Spot-Typ" (siehe Untersuchung Punkt 2).
6. **`circle-stroke`-Lücke**: dokumentieren (Spec + CHANGELOG), nicht versuchen zu
   umgehen (z. B. kein Zweckentfremden eines anderen Feldes) — siehe
   [Issue #3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3).

## Neue/geänderte Bausteine (`scripts/layer_metadata_extractor.py`)

```python
PART_FIELDS_BY_KIND = {
    "fill":    {"color": "fill-color",  "opacity": "fill-opacity"},
    "line":    {"color": "line-color",  "opacity": "line-opacity",
                "width": "line-width",  "dasharray": "line-dasharray"},
    "outline": {"color": "line-color",  "opacity": "line-opacity",
                "width": "line-width",  "dasharray": "line-dasharray"},
    "icon":    {"color": "icon-color",  "opacity": "icon-opacity", "icon": "icon-image"},
    "text":    {"color": "text-color",  "opacity": "text-opacity"},
    "circle":  {"color": "circle-color","opacity": "circle-opacity", "radius": "circle-radius"},
}

def determine_part_kind(layer):
    """type=fill/circle -> gleichnamiger kind. type=line -> "outline" wenn id auf
    -casing/-outline endet, sonst "line". type=symbol -> "icon" wenn
    layout.icon-image gesetzt, sonst "text". Andere/keine -> None (kein Part)."""

def extract_part_color(layer, kind):
    """Literaler String der kind-spezifischen Paint-Property -> {"mode": "fixed",
    "value": ...}. Kategorisierbare Expression (nach Case-Auflösung, siehe
    Entscheidung 4) -> "categorized" (interner Marker, siehe
    generate_layer_list._resolve_scale). Property nicht gesetzt oder andere
    Expression-Form -> None."""

def extract_part_opacity(layer, kind):
    """Wie bisheriges extract_layer_opacity, aber kind-parametrisiert. Default 1."""

def extract_part_width(layer, kind):
    """Wie bisheriges extract_layer_width, kind-parametrisiert (nur line/outline
    haben eine width-Property in PART_FIELDS_BY_KIND, sonst automatisch None)."""

def extract_part_dasharray(layer, kind):
    """Wie bisheriges extract_layer_dasharray, kind-parametrisiert."""

def extract_part_radius(layer, kind):
    """Neu: circle-radius, gleiche Literal/interpolate-Regel wie width (höchster
    Zoom-Stop). Nur kind == "circle" liefert einen Wert."""

def extract_part_icon(layer, kind):
    """Wie bisheriges extract_layer_icon, kind-parametrisiert (nur kind ==
    "icon" liefert einen Wert, literaler String only)."""
```

`_resolve_case_branch`, `_parse_interpolate_expression`, `_parse_match_expression`,
`build_numeric_match_items`, `_build_categorical_match_items` bleiben inhaltlich
unverändert, werden aber jetzt aus `extract_part_color` heraus pro Part statt aus
`extract_legend_items` pro Gruppe aufgerufen. `extract_legend_items` und
`extract_layer_color/opacity/width/dasharray/icon` (alte, `type`-basierte
Signaturen), `extract_outline_metadata` und `extract_layer_metadata` entfallen.

## Änderungen in `scripts/generate_layer_list.py`

- `GROUP_LEGEND_SCALE` erweitert um `"ski-lifts": "ski-lift-status-v1"`,
  `"ski-spots": "ski-spot-type-v1"`; `LEGEND_SCALE_LABELS` entsprechend um
  `"Lift-Status"`/`"Spot-Typ"`.
- Neue Funktion `_build_render(group_layers, group_key)`: baut für jeden Layer der
  Gruppe (in Style-Reihenfolge) einen Part via `determine_part_kind` +
  `extract_part_*`. Liefert `extract_part_color` `"categorized"`:
  `GROUP_LEGEND_SCALE.get(group_key)` nachschlagen →
  - vorhanden: `{"mode": "scale", "scale_id": ...}`, Items (via
    `_parse_interpolate_expression`/`_parse_match_expression`, nach
    Case-Auflösung) zur Sammlung für `legend_sections` geben.
  - fehlt (Spec-5.5-Fehlerfall): `log_warn(...)`, `color: None` am Part, kein
    Abbruch.
  Layer ohne gemappten `kind` (aktuell keiner in diesem Style) werden
  übersprungen — `render` kann dadurch kürzer sein als `style_layers`.
- `_build_legend_sections`: sammelt Items jetzt aus **Parts über alle Gruppen**
  (statt aus einem einzelnen `legend_items`-Feld pro Gruppe). Gleichheitsprüfung
  (`log_warn` bei Abweichung, erstes Vorkommen gewinnt) gilt jetzt sowohl
  gruppenübergreifend (wie bisher: die vier Pisten-Gruppen) als auch **innerhalb**
  einer Gruppe über mehrere Parts hinweg (neu: z. B. die vier
  `ski-lifts-line*`-Varianten).
- `build_layer_list`: `group["render"] = _build_render(...)` statt der bisherigen
  Einzel-Property-Felder (`type`/`color`/`opacity`/`width`/`dasharray`/
  `outline_color`/`outline_width`/`icon`/`legend_items`/`legend_scale_id`
  entfallen alle auf Gruppen-Ebene). `"version": "2.0"` statt `"1.1"`.

## Erwartetes Ergebnis pro Gruppe (Kurzform: `render`-Kinds + color-mode)

| Gruppe | Parts (`kind`: color-mode, Details) |
|---|---|
| Skigebiete (Alpin) | `fill`: fixed `#3085fe`; `circle`: fixed `#3085fe`, radius 6.0¹; `text`: fixed `#3085fe` |
| Skigebiete (Nordisch) | `fill`: fixed `#2ecc71`; `circle`: fixed `#2ecc71`, radius 6.0¹; `text`: fixed `#2ecc71` |
| Pisten (downhill) | `fill`: scale; `outline`(casing): fixed white; `line`: scale, w=3.0; `line`(gladed): scale, w=3.0, dash[0.1,4]; `line`(ungroomed): scale, w=3.0, dash[2,4]; `line`(snowmaking): fixed rgba, w=1.5; `text`: scale |
| Loipen (nordic) | `fill`: scale; `outline`(casing): **scale**²; `line`: fixed white, w=3.0; `line`(ungroomed): fixed white, w=3.0, dash[2,4]; `line`(snowmaking): fixed rgba, w=1.5; `text`: scale |
| Skitouren | `fill`: scale; `line`: scale, w=3.0, dash[3,6]; `text`: scale |
| Sonstige Strecken | `fill`: scale; `line`: scale, w=3.0, dash[3,3]; `text`: scale |
| Ski-Spots | `circle`: scale (`ski-spot-type-v1`), radius 4.0 |
| Lifte | `outline`(casing): fixed white, w=5.0; `line`×4: scale (`ski-lift-status-v1`), opacity 0.8, w=3.0/1.98/3.0/1.98, teils dash; `text`: fixed `#2c3e50`; `icon`: color `null`, icon `null` |

¹ `circle-radius` ist `interpolate` 0→1, 11→6 → höchster Zoom-Stop 6.0.
² Umgekehrt zu Downhill — siehe Untersuchung Punkt 1.

Zwei vollständige Beispiele (nach Migration erwarteter `render`-Array-Ausschnitt):

```json
// Loipen (nordic) — zeigt den asymmetrischen Casing-Fall
{
  "source_layer": "ski_runs_nordic_line",
  "style_layers": ["ski-runs-nordic-casing", "ski-runs-nordic-line", "ski-runs-nordic-ungroomed"],
  "render": [
    { "kind": "outline", "color": { "mode": "scale", "scale_id": "ski-difficulty-v1" },
      "opacity": 1, "width": 5.0, "dasharray": null, "radius": null, "icon": null },
    { "kind": "line", "color": { "mode": "fixed", "value": "hsl(0, 0%, 100%)" },
      "opacity": 1, "width": 3.0, "dasharray": null, "radius": null, "icon": null },
    { "kind": "line", "color": { "mode": "fixed", "value": "hsl(0, 0%, 100%)" },
      "opacity": 1, "width": 3.0, "dasharray": [2, 4], "radius": null, "icon": null }
  ]
}
```

```json
// Lifte — zeigt vier scale-Parts mit derselben scale_id + icon-Part ohne Farbe
{
  "source_layer": "ski_lifts",
  "render": [
    { "kind": "outline", "color": { "mode": "fixed", "value": "hsl(0, 0%, 100%)" },
      "opacity": 1, "width": 5.0, "dasharray": null, "radius": null, "icon": null },
    { "kind": "line", "color": { "mode": "scale", "scale_id": "ski-lift-status-v1" },
      "opacity": 0.8, "width": 3.0, "dasharray": null, "radius": null, "icon": null },
    { "kind": "text", "color": { "mode": "fixed", "value": "#2c3e50" },
      "opacity": 0.9, "width": null, "dasharray": null, "radius": null, "icon": null },
    { "kind": "icon", "color": null,
      "opacity": 1, "width": null, "dasharray": null, "radius": null, "icon": null }
  ]
}
```

`legend_sections` enthält drei Einträge: `ski-difficulty-v1` (8 Items, wie bisher),
`ski-lift-status-v1` (7 Items: Operating…Abandoned + Sonstige),
`ski-spot-type-v1` (6 Items: Lift Station…Avalanche Transceiver Checkpoint +
Sonstige).

## CHANGELOG.md / Versionierung

Neuer `[Unreleased]`-Journal-Block unter `### Changed` (Breaking Change: Schema
2.0), referenziert den Submodul-Bump-Eintrag von 2026-08-14 und ergänzt ihn um die
konkrete Migration; unter `### Known Issues` (oder vergleichbar) ein Hinweis auf
den `circle-stroke`-Datenverlust mit Link auf Issue #3. Kein `VERSION`-Bump in
diesem Schritt (sammelt sich im `[Unreleased]`-Block, Release wird nach Abschluss
separat vorgeschlagen, `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4).

## Tests

`scripts/test_layer_metadata_extractor.py` und `scripts/test_generate_layer_list.py`
werden auf die neuen Funktionssignaturen umgeschrieben (TDD, rot/grün):

- `determine_part_kind`: alle sechs Fälle (fill/circle/line/outline via
  `-casing`/`-outline`-Suffix/icon via `layout.icon-image`/text) + `None` für
  ungemappten Typ.
- `extract_part_color`: fixed (literal), scale (interpolate/match, inkl.
  Case-Auflösung — Regressionsfall `ski-runs-downhill-casing`/
  `ski-runs-nordic-line` müssen jetzt `fixed` statt `null` liefern), `None`
  (andere Expression / Property fehlt).
- `extract_part_opacity`/`_width`/`_dasharray`/`_radius`/`_icon`: je Kind-Fälle
  wie bisher (literal, `interpolate`-Höchststop, `None`-Fälle), neu:
  `extract_part_radius` (circle, literal + interpolate).
- `_build_render`/`_build_legend_sections`: Regressionstests für alle acht
  Gruppen gegen die Tabelle oben (insbesondere den asymmetrischen
  Downhill/Nordic-Casing-Fall), plus die neuen `ski-lift-status-v1`/
  `ski-spot-type-v1`-Skalen und die Fehlerfall-Warnung (Gruppe mit `scale`-Part
  aber ohne `GROUP_LEGEND_SCALE`-Eintrag → `color: None` + `log_warn`, kein
  Abbruch).

## Betroffene Dateien

- `scripts/layer_metadata_extractor.py` — vollständig umgeschrieben (siehe oben).
- `scripts/generate_layer_list.py` — `_group_metadata` entfällt, neue
  `_build_render`, erweiterte `GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS`,
  `_build_legend_sections` angepasst, `"version": "2.0"`.
- `scripts/test_layer_metadata_extractor.py`, `scripts/test_generate_layer_list.py`
  — umgeschrieben.
- `CHANGELOG.md` — neuer `[Unreleased]`-Eintrag.
- `docs/TODO.md` — Eintrag zur v2.0-Migration (vom 2026-08-14) wird nach Abschluss
  ins `TODO_ARCHIVE.md` verschoben (nicht Teil dieser Spec, Teil des
  Implementierungs-Abschlusses).

**Nicht betroffen:** `scripts/convert.sh`, `styles/openskimap-style.json`,
`scripts/generate_manifest.py` (eigenes `manifest.json`-Schema, §4, unberührt),
`scripts/download.sh`.

## Verifikation

- `cd scripts && python3 -m unittest test_layer_metadata_extractor
  test_generate_layer_list test_validate_style -v` — alle grün.
- `python3 scripts/generate_layer_list.py` gegen den echten
  `dist/styles/openskimap-style.json` (nach `run.sh`/`update.sh`) — Ausgabe
  manuell gegen die Tabelle/Beispiele oben prüfen, `"version": "2.0"`, drei
  `legend_sections`-Einträge.
- `python3 -c "import json; json.load(open('dist/layer-list.json'))"` — valides
  JSON.
