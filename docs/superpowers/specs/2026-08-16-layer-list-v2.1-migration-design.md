# Design: `layer-list.json` v2.1.0-Migration (`stroke_color`/`stroke_width`, `variants[].axis`, Snowmaking-Achsen)

## Problem

`geodata-plugin-standard` wurde von `v2.0.0` auf `v2.1.0` gebumpt (Submodul-Commit
`fa1b44a` → `40a4044`). Der neue Standard formalisiert zwei lokal bereits vorab
implementierte Erweiterungen dieses Repos:

- `stroke_color`/`stroke_width` am `circle`-Part (löst
  [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3),
  siehe `docs/TODO.md`-Eintrag "circle-stroke-color/-width im render-Part-Modell nachziehen")
- `variants: Array<{axis, label, render}>` am Group-Eintrag (löst
  [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4),
  siehe `docs/superpowers/specs/2026-08-14-legend-variants-design.md`)

Die lokale Implementierung (`scripts/layer_metadata_extractor.py`,
`scripts/generate_layer_list.py`) ist gegen keine der beiden Erweiterungen konform:

1. `"version"` ist weiterhin `"2.0"` fest verdrahtet.
2. Es gibt keine `stroke_color`/`stroke_width`-Felder am Part — konsistente Objektform
   (§5.3: "nicht weggelassen") ist verletzt.
3. `GROUP_VARIANTS`-Einträge haben kein `axis`-Feld (Pre-Standard-Provisorium vom
   2026-08-14, bevor der Standard das Feld überhaupt kannte). Zusätzlich ist der
   `ski-lifts`-Zuschnitt (4 flache Kombinations-Zeilen über Status×Zugang) technisch
   unsauber: `ski-lifts-casing` landet in 2 von 4 Varianten, obwohl sein Filter
   (`status == "operating"`) nur die Status-Dimension testet.

## Untersuchung: Paint-Kopplung bei `ski-lifts`

Verifiziert gegen `styles/openskimap-style.json` (nicht nur `filter`, auch `paint`):

| Layer | Filter | Farbe | Breite | Dasharray |
|---|---|---|---|---|
| `-casing` | `status == operating` | fix weiß | 1.8–5.0 | – |
| `-line` | `access != private AND status == operating` | Status-Match-Skala | 0.8–3.0 | – |
| `-line-private` | `access == private AND status == operating` | Status-Match-Skala | 0.8–3.0 | `[1,2]` |
| `-line-other` | `access != private AND status != operating` | Status-Match-Skala | 0.53–1.98 | `[1,3]` |
| `-line-private-other` | `access == private AND status != operating` | Status-Match-Skala | 0.53–1.98 | `[1,3]` |

Erkenntnis: die Zugangs-Dimension (`access`) hat nur bei `status == operating` einen
sichtbaren Effekt (Dasharray `[1,2]`) — bei `status != operating` sind `-line-other` und
`-line-private-other` paint-identisch. Eine vollständig orthogonale 2-Achsen-Zerlegung
(jede Achse unabhängig von der anderen visuell eindeutig) ist damit nicht möglich, ohne
einen der vier realen Style-Layer wegzulassen oder zu duplizieren.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-16)

1. **`stroke_color`/`stroke_width`**: wie im Standard spezifiziert übernehmen — an jedem
   Part, `null` außer bei `kind: "circle"`.
2. **`ski-lifts` wird neu zugeschnitten** (Abkehr vom 4-Kombi-Modell vom 2026-08-14) auf
   zwei Achsen, jeder der 4 realen Style-Layer wird genau einmal verwendet:
   - axis `"status"`: "In Betrieb" → `[ski-lifts-casing, ski-lifts-line]`, "Sonstiger
     Status" → `[ski-lifts-line-other]`
   - axis `"access"` (Single-Value-Achse, siehe Standard-Doku "kein Sonderfall"): "Privat"
     → `[ski-lifts-line-private, ski-lifts-line-private-other]` (beide Statuswerte
     gemeinsam in einem `render`-Array, da paint-technisch nur durch `access`
     unterscheidbar)
   - Ein Konsument, der axis `"status"` UND axis `"access"` gleichzeitig anwendet
     (nicht-exklusiv, siehe Standard §5.3 "keine Exklusivitäts-Semantik"), erhält für
     "privat, in Betrieb" die Vereinigung aus `status:"In Betrieb"` (Casing) und
     `access:"Privat"` (Linie) — deckungsgleich mit der echten Karte.
3. **`ski-runs-downhill` bleibt beim 4-Kombi-Modell**, nur `axis: "grooming-terrain"`
   ergänzt (bewusste Nutzer-Entscheidung: keine zweite Formänderung für `website-v3` in
   kurzer Zeit, siehe Alternativen-Diskussion unten).
4. **`ski-runs-nordic`** bekommt `axis: "grooming"` (unverändert, nur Feld ergänzt).
5. **Snowmaking wird jetzt gelöst**: neue Single-Value-Achse `"snowmaking"` (Label
   "Beschneit") bei `ski-runs-downhill` (`[ski-runs-downhill-snowmaking]`) und
   `ski-runs-nordic` (`[ski-runs-nordic-snowmaking]`). `GROUP_VARIANT_EXCLUDE` wird dadurch
   für beide Einträge leer — Konstante und der Ausschluss-Schritt in
   `_build_render_and_variants` entfallen vollständig (YAGNI, kein totes Feature für einen
   inzwischen leeren Anwendungsfall).
6. **`"version"`** wird `"2.1"`.

### Verworfene Alternative: `ski-runs-downhill` ebenfalls in orthogonale Achsen zerlegen

Geprüft: `-line`/`-gladed`/`-ungroomed` unterscheiden sich nur im `dasharray` (identische
Farbe/Breite), `gladed` und `ungroomed` können in echten Daten gleichzeitig zutreffen —
eine Zerlegung in axis `"terrain"` (`"Waldabfahrt"`, 1 Wert, aus `-gladed`) + axis
`"grooming"` (`"Präpariert"`/`"Nicht präpariert"`, aus `-line`/`-ungroomed`) wäre technisch
sauberer möglich gewesen als bei `ski-lifts` und hätte die vierte Kombi-Zeile
("Waldabfahrt, nicht präpariert") überflüssig gemacht. Nutzer-Entscheidung: nicht jetzt —
`website-v3` hat gerade erst die Kombi-Form vorab getestet, eine zweite Formänderung
innerhalb kurzer Zeit wird vermieden. Bleibt als mögliche zukünftige Iteration, kein
`TODO.md`-Eintrag (keine akute Lücke, nur eine nicht gewählte Verbesserung).

## Neue/geänderte Bausteine

### `scripts/layer_metadata_extractor.py`

- `PART_FIELDS_BY_KIND["circle"]` erhält `"stroke_color": "circle-stroke-color"`,
  `"stroke_width": "circle-stroke-width"`.
- Neue `extract_part_stroke_color(layer, kind)` — identische Struktur zu
  `extract_part_color`, aber über einen neuen `prop = PART_FIELDS_BY_KIND.get(kind,
  {}).get("stroke_color")`-Lookup. Da `stroke_color` (anders als `color`) keine
  `case`-Auflösung braucht (OpenSkiMap nutzt keine `case`-Expression auf
  `circle-stroke-color`), reicht eine einfache Klassifikation (literal → fixed,
  interpolate/match → "categorized"-Marker, sonst `None`) ohne den
  `_resolve_part_color_expression`-Umweg über `case`.
- Neue `extract_part_stroke_width(layer, kind)` — identisch zu `extract_part_width`, über
  `_extract_interpolatable_number` auf `circle-stroke-width`.
- Falls `stroke_color` kategorisierbar ist (aktuell in `styles/openskimap-style.json` nicht
  der Fall, aber die Extraktion muss es korrekt behandeln können): `extract_categorized_items`
  bleibt unverändert nutzbar, da sie bereits kind-parametrisiert ist — sie braucht aber ein
  Pendant, das auf `stroke_color` statt `color` schaut, falls `generate_layer_list.py` das
  benötigt (siehe unten; aktuell hat kein Style-Layer eine kategorisierte `circle-stroke-color`,
  daher genügt eine einfache Extraktion ohne Skalen-Anbindung für `stroke_color` in diesem
  Repo — bei Bedarf später erweiterbar).

### `scripts/generate_layer_list.py`

- `_build_render`: Part-Dict um `"stroke_color": extract_part_stroke_color(layer, kind)` und
  `"stroke_width": extract_part_stroke_width(layer, kind)` erweitern.
- `GROUP_VARIANTS`: jeder Eintrag bekommt `"axis"`. `ski-lifts`-Liste wird komplett ersetzt
  (3 Einträge über 2 Achsen statt 4 Kombi-Zeilen, siehe Entscheidung 2). `ski-runs-downhill`
  und `ski-runs-nordic` behalten ihre `style_layer_ids`, bekommen nur `axis` ergänzt — plus
  je ein neuer `"snowmaking"`-Achsen-Eintrag.
- `GROUP_VARIANT_EXCLUDE`-Konstante und der Ausschluss-Schritt in
  `_build_render_and_variants` (aktuell: `excluded_ids = set(GROUP_VARIANT_EXCLUDE.get(...))`)
  werden entfernt.
- `_build_render_and_variants`: die pro Varianten-Eintrag gebaute Dict-Literal
  (`{"label": ..., "render": ...}`) wird um `"axis": variant_def["axis"]` ergänzt.
- `build_layer_list`: `"version": "2.0"` → `"2.1"`, Docstring-Referenzen auf `v2.0.0` §5.3
  aktualisieren auf `v2.1.0`.

### Tests (`scripts/test_layer_metadata_extractor.py`, `scripts/test_generate_layer_list.py`)

- Neue Tests für `extract_part_stroke_color`/`extract_part_stroke_width`: literal color,
  literal width, fehlende Property → `None`, non-circle kind → `None`.
- `test_generate_layer_list.py`: alle bisherigen Part-Dict-Vergleiche um
  `stroke_color`/`stroke_width` ergänzen (auch dort, wo beide `None` sind — sonst brechen
  bestehende exakte Dict-Vergleiche).
- `version`-Assertion → `"2.1"`.
- `ski-lifts`: bestehende Tests für die 4 Kombi-Varianten ersetzen durch Tests für die 3
  neuen Einträge (2× axis `"status"`, 1× axis `"access"`) inkl. Prüfung, dass
  `ski-lifts-casing` jetzt in genau 1 (nicht mehr 2) Varianten-Eintrag landet.
  `test_ski_lifts_casing_only_in_operating_variants` (siehe Commit `4b2097b`) muss auf die
  neue Struktur angepasst werden — Name/Assertion prüfen, ob "only in operating variants"
  nach der Zerlegung noch die richtige Aussage ist (jetzt: casing nur in axis
  `"status"`-Eintrag "In Betrieb", gar nicht mehr in axis `"access"`).
- Neue Tests: `ski-runs-downhill`/`ski-runs-nordic` haben je einen `"snowmaking"`-Achsen-
  Eintrag mit dem korrekten Style-Layer; `ski-runs-downhill-snowmaking`/
  `ski-runs-nordic-snowmaking` erscheinen weder in `render` noch in einem anderen
  Varianten-Eintrag.
- Regressionstest: Gruppen ohne `GROUP_VARIANTS`-Eintrag unverändert (`variants: None`).
- `legend_sections` unverändert (3 Skalen, keine neue Skala durch diese Migration).

### Dokumentation

- `CHANGELOG.md`: neuer `[Unreleased]`-Journalblock mit Datum+Uhrzeit. Kategorien: Added
  (`stroke_color`/`stroke_width`, `variants[].axis`, `snowmaking`-Achsen), Changed
  (Breaking: `ski-lifts`-Varianten-Form ändert sich erneut, `"version"` → `"2.1"`).
- `docs/TODO.md`: Eintrag "circle-stroke-color/-width im render-Part-Modell nachziehen" und
  Eintrag "snowmaking-Layer haben kein Konzept im render/variants-Schema" nach
  `docs/TODO_ARCHIVE.md` verschieben (erledigt).

## Betroffene Dateien

- `scripts/layer_metadata_extractor.py`
- `scripts/generate_layer_list.py`
- `scripts/test_layer_metadata_extractor.py`
- `scripts/test_generate_layer_list.py`
- `CHANGELOG.md`
- `docs/TODO.md` / `docs/TODO_ARCHIVE.md`

**Nicht betroffen:** `styles/openskimap-style.json`, `scripts/generate_manifest.py`,
`scripts/validate_style.py`, `GROUP_MAP`/`GROUP_LEGEND_SCALE`/`legend_sections`-Mechanik.

## Offen für den Implementierungsplan

- Reihenfolge TDD-gerecht aufbrechen (erst Extractor-Funktionen + Tests, dann
  `generate_layer_list.py`-Integration + Tests, dann Doku).
- Prüfen, ob `test_generate_layer_list.py` Golden-File-Vergleiche nutzt, die komplett
  neu generiert werden müssen, oder ob es reine Struktur-Assertions sind (beeinflusst
  Aufwand der Test-Anpassung).
