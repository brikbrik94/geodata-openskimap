# Design: `layer-list.json` v1.1-Felder + zentrale Schwierigkeits-Legende

## Problem

`geodata-plugin-standard` wurde von v1.0.0 auf v1.1.0 aktualisiert (Submodul-Bump,
2026-08-12). §5 des Standards erweitert das `layer-list.json`-Schema um
Legend-Rendering-Felder (`width`, `dasharray`, `outline_color`, `outline_width`,
`icon`, `legend_scale_id`) sowie einen neuen Top-Level-Block `legend_sections` für
**geteilte** Farbskalen (Schema-Version `"1.0"` → `"1.1"`, Breaking Change laut §5.6).
Das Standard-Beispiel in §5.7 verwendet explizit openskimap-Daten (Ski-Lifte, Pisten,
`ski-difficulty-v1`) als Referenz.

`scripts/layer_metadata_extractor.py` und `scripts/generate_layer_list.py` in diesem
Repo müssen laut Portierungshinweis (§5.8) um diese Felder erweitert werden.

Zusätzliche Anforderung des Nutzers: die vier Pisten-Kategorien
(`ski-runs-downhill`, `-nordic`, `-skitour`, `-other`) verwenden im Style
byte-identische Schwierigkeitsgrad-Farben (verifiziert, siehe Untersuchung) — die
Schwierigkeits-Legende soll deshalb über `legend_scale_id`/`legend_sections` **einmal
zentral** definiert werden statt viermal dupliziert, und die Gruppen bekommen
sprechende deutsche Anzeigenamen statt der bisherigen automatisch generierten
Titel-Case-Strings.

## Untersuchung

- `fill-color` von `ski-runs-{downhill,nordic,skitour,other}-fill` ist Byte-für-Byte
  identisch (Python-Vergleich der geparsten Expressions, siehe Session-Log) — ein
  `case`-Umschalter nach `difficulty_convention` (europe/japan/default), jeweils ein
  `match` auf `difficulty` mit denselben sieben Kategorien + Fallback.
- Bestehender, bereits unstaged vorliegender Fix (`case`-Resolution in
  `extract_legend_items`, siehe `git diff scripts/layer_metadata_extractor.py`) ist
  Voraussetzung dafür, dass diese Legende überhaupt extrahiert wird — wird vor
  diesem Feature als eigener Commit abgeschlossen (siehe Betroffene Dateien).
- **Bug in der aktuellen Primär-Layer-Auswahl** (`_group_metadata` in
  `generate_layer_list.py`): bei der Gruppe `ski-lifts` liegt der Casing-Layer
  (`ski-lifts-casing`, weiße Linie) vor dem eigentlichen Status-Layer
  (`ski-lifts-line`, rot nach `status`) in der Style-Layer-Reihenfolge. Die
  Prioritäts-Logik (`fill > line > circle > symbol`, bei Gleichstand gewinnt der
  zuerst gesehene) wählt daher aktuell die weiße Casing-Linie als Primär-Layer:
  `color: "hsl(0, 0%, 100%)"` (weiß), obwohl `legend_items` korrekt die
  Status-Farben (rot/…) zeigt — inkonsistent. Reproduziert via
  `build_layer_list()` gegen den echten Style (siehe Session-Log).
- `ski-lifts-casing` hat `line-color: "hsl(0, 0%, 100%)"` als **literalen String**
  (keine Expression) → eignet sich direkt als `outline_color`.
- Layer-Übersicht aller acht Gruppen (Primär-Typ, Casing-Layer, Icon-Layer) wurde
  vollständig gegen `styles/openskimap-style.json` verifiziert (siehe Session-Log).

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-12)

1. **Alle vier Pisten-Gruppen teilen sich `legend_scale_id: "ski-difficulty-v1"`**
   (nicht nur downhill/nordic) — Style-Farben sind für alle vier identisch, daher
   kein Informationsverlust, maximale Deduplizierung.
2. **Gruppennamen** (`name`-Feld, ersetzt `group_key.replace("-", " ").title()`):

   | `group_key` | `name` (neu) |
   |---|---|
   | `ski-areas-alpine` | `Skigebiete (Alpin)` |
   | `ski-areas-nordic` | `Skigebiete (Nordisch)` |
   | `ski-runs-downhill` | `Pisten` |
   | `ski-runs-nordic` | `Loipen` |
   | `ski-runs-skitour` | `Skitouren` |
   | `ski-runs-other` | `Sonstige Strecken` |
   | `ski-spots` | `Ski-Spots` |
   | `ski-lifts` | `Lifte` |

3. **Primär-Layer-Auswahl-Fix wird mitgemacht**: Casing/Outline-Layer (`id` endet
   auf `-casing`/`-outline`) werden von der Kandidatenliste für den Primär-Layer
   (bestimmt `type`/`color`/`opacity`/`width`/`dasharray`) ausgeschlossen — sie
   liefern stattdessen ausschließlich `outline_color`/`outline_width`. Behebt den
   oben beschriebenen Bug als Nebeneffekt der ohnehin nötigen Outline-Erkennung.
4. **`extract_layer_metadata()` in `layer_metadata_extractor.py` bleibt unangetastet**
   (unbenutzter Code — `generate_layer_list.py` reimplementiert die Gruppen-Logik
   lokal, weil openskimap-Gruppen mehrere `source-layer`s umspannen können, siehe
   Moduldocstring von `generate_layer_list.py`). Wird als `docs/TODO.md`-Eintrag
   dokumentiert (Erweiterung oder Entfernung als spätere, separate Entscheidung),
   nicht in diesem Zug mitgezogen — kein Scope dieser Aufgabe.

## Neue Extraktions-Helper (`scripts/layer_metadata_extractor.py`)

```python
def extract_layer_width(layer):
    """line-width des Layers: literale Zahl direkt, interpolate → höchster
    Zoom-Stop-Wert (letzter Stop), sonst None. None für Nicht-line-Layer."""

def extract_layer_dasharray(layer):
    """line-dasharray: entpackt sowohl ["literal", [a, b]] (so im Style
    tatsächlich verwendet, z.B. ski-lifts-line-other/-private) als auch ein
    rohes 2-Element-Array. Sonst None."""

def extract_outline_metadata(group_layers):
    """Erster Layer der Gruppe mit id.endswith(('-casing', '-outline')) und
    type == 'line': liefert {"outline_color": ..., "outline_width": ...}
    (extract_layer_color/extract_layer_width auf diesem Layer). Kein
    Treffer → beide None."""

def extract_layer_icon(layer):
    """layout.icon-image nur wenn literaler String, sonst None
    (openskimaps icon-image ist durchgehend eine match-Expression, bleibt
    also None — Verhalten korrekt gemäß Spec, nicht toter Code)."""
```

`_resolve_case_branch` (bereits vorhanden, unstaged) bleibt unverändert.

## Änderungen in `scripts/generate_layer_list.py`

- `_group_metadata`: Primär-Layer-Kandidaten filtern (Casing/Outline raus, siehe
  Entscheidung 3), dann wie bisher nach `fill > line > circle > symbol`
  priorisieren. `type` wird `"icon"` statt `"symbol"`, wenn der gewählte
  Primär-Layer selbst `layout.icon-image` gesetzt hat (unabhängig vom
  `extract_layer_icon`-Rückgabewert — ein reiner Text-Layer ohne `icon-image`
  bleibt `"symbol"`). Zusätzlich `width`, `dasharray`,
  `outline_color`/`outline_width` (via `extract_outline_metadata` über die
  *ungefilterte* Layer-Liste der Gruppe), `icon` ins Ergebnis-Dict aufnehmen.
- Neue Modul-Konstanten `GROUP_NAMES`, `GROUP_LEGEND_SCALE`,
  `LEGEND_SCALE_LABELS` (siehe Entscheidung 1/2).
- `build_layer_list`:
  - `group["name"] = GROUP_NAMES[group_key]` statt `.title()`-Fallback.
  - Nach dem Befüllen aller Gruppen: für jede Gruppe mit
    `GROUP_LEGEND_SCALE.get(group_key)` gesetzt → `group["legend_scale_id"] =
    <id>`, `group["legend_items"] = None` (§5.6-Regel).
  - `legend_sections` einmal pro distinkter `legend_scale_id` aufbauen: `id`,
    `label` (aus `LEGEND_SCALE_LABELS`), `items` (aus der *ersten* Gruppe mit
    dieser Scale, vor dem Nullen extrahiert). Wenn eine spätere Gruppe mit
    derselben Scale abweichende `legend_items` liefert: `log_warn(...)`
    (§5.5-Empfehlung, kein Abbruch) — Import von `scripts/ci/utils.py`.
  - `"version": "1.1"` statt `"1.0"`.
  - Rückgabe-Dict bekommt `"legend_sections": [...]` oder `None`, falls keine
    Gruppe eine Scale referenziert (§5.1: "`null`/fehlend, wenn keine Gruppe
    eine `legend_scale_id` gesetzt hat").

## Erwartetes Ergebnis pro Gruppe (Kurzform)

| Gruppe | type | color | width | outline_color | outline_width | legend_scale_id | legend_items |
|---|---|---|---|---|---|---|---|
| Skigebiete (Alpin) | fill | `#3085fe` | – | – | – | – | – |
| Skigebiete (Nordisch) | fill | `#2ecc71` | – | – | – | – | – |
| Pisten | fill | `null` (Expression) | – | `null`¹ | `5.0`² | `ski-difficulty-v1` | `null` |
| Loipen | fill | `null` | – | `null`¹ | `5.0`² | `ski-difficulty-v1` | `null` |
| Skitouren | fill | `null` | – | – | – | `ski-difficulty-v1` | `null` |
| Sonstige Strecken | fill | `null` | – | – | – | `ski-difficulty-v1` | `null` |
| Ski-Spots | circle | `null` (Expression) | – | – | – | – | `[Lift Station, Halfpipe, …]` |
| Lifte | line | `null` (Status-Expression) | `3.0` | `"hsl(0, 0%, 100%)"` | `5.0` | – | `[Operating, Proposed, …]` |

¹ `ski-runs-{downhill,nordic}-casing` existieren (im Gegensatz zu skitour/other,
die keinen Casing-Layer haben), aber ihre `line-color` ist selbst eine Expression
(`lit`- bzw. seit dem Nordic-Casing/Line-Swap difficulty-basiert) → kein literaler
String → `outline_color: null` trotz vorhandenem Casing-Layer.
² `line-width` der beiden Casing-Layer ist eine `interpolate`-Expression mit
identischer Zoom-Kurve (6→1.8, 9→2.8, 12→4.0, 14→5.0) → höchster Stop `5.0`.

`legend_sections` (einziger Eintrag): `{"id": "ski-difficulty-v1", "label":
"Schwierigkeitsgrade", "items": [Novice…Extreme, Sonstige]}`.

## CHANGELOG.md / Versionierung

Neuer `[Unreleased]`-Journal-Block (zusätzlich zum bereits unstaged vorhandenen
`case`-Resolution-Fix-Eintrag, der zuerst als eigener Commit abgeschlossen wird):
Feature-Eintrag unter `### Changed` (Breaking Change: Schema-Version 1.0 → 1.1)
für die neuen Felder + zentrale Schwierigkeits-Legende + deutsche Gruppennamen.
Kein Versions-Bump von `VERSION` in diesem Schritt (sammelt sich im
`[Unreleased]`-Block, Release wird nach Abschluss separat vorgeschlagen, siehe
`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4).

## Tests

Neu: `scripts/test_layer_metadata_extractor.py` (pytest, analog
`scripts/test_validate_style.py`), TDD (rot/grün):

- `extract_layer_width`: literale Zahl, `interpolate`-Höchststop, Nicht-line-Layer
  → `None`.
- `extract_layer_dasharray`: `["literal", [1, 3]]`-Form (wie im echten Style),
  rohes 2-Element-Array, fehlendes Feld → `None`.
- `extract_outline_metadata`: Treffer über `-casing`, kein Treffer → beide `None`.
- `extract_layer_icon`: literaler String vs. Expression.
- Regressionstest für den Primär-Layer-Fix: `ski-lifts`-Gruppe liefert `color:
  null`, `outline_color: "hsl(0, 0%, 100%)"`, **nicht** mehr `color: "hsl(0, 0%,
  100%)"`.
- `legend_sections`-Aufbau: alle vier Pisten-Gruppen referenzieren dieselbe
  Scale, `legend_items` je `null`, ein `legend_sections`-Eintrag mit den
  erwarteten acht Items.

## Betroffene Dateien

- `scripts/layer_metadata_extractor.py` — vier neue Helper-Funktionen.
- `scripts/generate_layer_list.py` — `_group_metadata`-Fix, neue Konstanten,
  `legend_sections`-Aufbau, Version-Bump.
- `scripts/test_layer_metadata_extractor.py` — neu.
- `CHANGELOG.md` — neuer `[Unreleased]`-Eintrag.
- `docs/TODO.md` — neuer Eintrag für toten Code (`extract_layer_metadata`).

**Nicht betroffen:** `scripts/convert.sh`, `styles/openskimap-style.json`,
`scripts/generate_manifest.py` (dessen eigenes `manifest.json`-`"version": "1.0"`
ist ein anderes Schema, §4, unberührt), `scripts/download.sh`.

## Verifikation

- `python3 -m pytest scripts/test_layer_metadata_extractor.py -v` — neue Tests grün.
- `python3 -m pytest scripts/test_validate_style.py -v` — weiterhin grün
  (unverändertes Verhalten für Style-Validierung).
- `python3 scripts/generate_layer_list.py` gegen den echten
  `dist/styles/openskimap-style.json` (nach `run.sh`/`update.sh`) — Ausgabe
  manuell gegen die Tabelle oben prüfen, `legend_sections` vorhanden,
  `version: "1.1"`.
- `python3 -c "import json; json.load(open('dist/layer-list.json'))"` — valides JSON.
