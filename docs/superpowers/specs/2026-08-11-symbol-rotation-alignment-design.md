# Design: Icon- und Label-Ausrichtung bei linienplatzierten Symbolen

## Problem

`docs/TODO.md` → "Ausrichtung der Sprites prüfen": ursprünglich vage
("Sprite-Ausrichtung (Icons) aktuell nicht korrekt — genauer eingrenzen,
welche Icons/Layer betroffen sind und was konkret falsch ausgerichtet
ist.").

## Untersuchung

Nur ein Layer in `styles/openskimap-style.json` verwendet `icon-image`:
`ski-lifts-icons` (`symbol-placement: "line"`, `symbol-spacing: 150`,
Icons aus `assets/sprites/openskimap/` — `ski-chairlift-*`, `ski-gondola`,
`ski-cable-car`, `ski-drag-lift-*`, `ski-funicular`, `ski-magic-carpet`,
`ski-rope-tow`).

Das Sprite-Sheet selbst ist unauffällig: alle 13 Icons 48×48px quadratisch
(`assets/sprites/openskimap/sprite.json`), visuell geprüft (vergrößerte
Ansicht) — statische Frontalansichten (Mast senkrecht, Sitze/Kabine
darunter/-neben hängend), keine Richtungspfeile oder asymmetrischen
Artefakte im Sheet selbst.

`ski-lifts-icons` setzt kein `icon-rotation-alignment`. MapLibre/Mapbox
Style-Spec-Default dafür ist `"auto"`, was bei `symbol-placement: "line"`
zu `"map"` aufgelöst wird — die Icons rotieren also automatisch mit der
Bearing der Linie an ihrer jeweiligen Platzierungsposition. Da die Sprites
statische, nicht-richtungsbezogene Frontalansichten sind, führt das dazu,
dass Icons auf nicht Nord-Süd verlaufenden Lift-Segmenten gekippt/rotiert
erscheinen — das ist die konkrete Ursache hinter der vagen TODO-Notiz.

Abgleich mit dem echten OpenSkiMap-Stylesheet (`/tmp/openskimap_terrain_style.json`,
Session-Snapshot) nicht direkt möglich: OpenSkiMap zeigt Lift-Typ-Icons gar
nicht wiederholt entlang der Linie, nur ein generisches `lift-station`-Icon
an Stationen (eigener Punkt-Layer, `source-layer: "spots"`). Das
wiederholte Icon-entlang-der-Linie-Konzept ist unser eigenes, kein
Standard-Vorbild vorhanden.

**Nebenfund** (beim Untersuchen von Rotations-/Ausrichtungs-Properties im
Style entdeckt, nicht Teil der ursprünglichen TODO-Notiz, aber vom Nutzer
für dieselbe Iteration freigegeben): `ski-runs-alpine-labels`,
`ski-runs-nordic-labels`, `ski-lifts-labels` setzen
`text-rotation-alignment: "map"` (Labels folgen der Linienkontur, so
gewollt) **und** `text-keep-upright: false`. Kein Beleg in der Git-Historie
(`git log -S "text-keep-upright"`) für eine bewusste Design-Entscheidung —
alle vier Treffer sind reine Feature-Commits ohne erklärende Message.
`false` weicht vom MapLibre-Standardverhalten (`true`) ab und kann dazu
führen, dass Text auf bestimmten Linienabschnitten kopfüber gerendert wird.
Das echte OpenSkiMap-Stylesheet überschreibt dieses Feld für seinen
analogen linienplatzierten Text-Layer (`lift-names`) gar nicht — bleibt
also beim Default `true`.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-11)

1. **`ski-lifts-icons`**: `icon-rotation-alignment: "viewport"` ergänzen.
   Icons bleiben dadurch immer aufrecht, unabhängig von der
   Linienrichtung. `symbol-placement: "line"` und `symbol-spacing: 150`
   bleiben unverändert — Icons weiterhin wiederholt entlang der
   Lift-Linie platziert, nur die Rotation wird entkoppelt.
2. **Nebenfund wird in derselben Iteration mitgefixt** (nicht separat
   zurückgestellt): `text-keep-upright` bei `ski-runs-alpine-labels`,
   `ski-runs-nordic-labels`, `ski-lifts-labels` von `false` auf `true`.
   `text-rotation-alignment: "map"` bleibt unverändert — Labels sollen
   weiterhin der Linie folgen, nur nicht mehr potenziell kopfüber
   gerendert werden.

**Nicht betroffen:** `assets/sprites/openskimap/*` (Sprite-Sheet selbst
unauffällig), `scripts/convert.sh`, `scripts/generate_layer_list.py`
(keine neuen/umbenannten Layer-IDs, reine Property-Änderungen an
bestehenden Layern).

## Betroffene Dateien

- `styles/openskimap-style.json` — 4 Layer, 2 Arten von Änderungen:
  - `ski-lifts-icons`: eine neue Property (`icon-rotation-alignment: "viewport"`).
  - `ski-runs-alpine-labels`, `ski-runs-nordic-labels`, `ski-lifts-labels`:
    je ein Wertwechsel (`text-keep-upright`: `false` → `true`).

## Verifikation

Reine Property-Wertänderungen an bestehenden, bereits validen Layern —
kein neuer Layer, keine neue `source-layer`-Referenz, kein neues Icon.
Daher:

- `python3 -c "import json; json.load(open('styles/openskimap-style.json'))"`
  — JSON weiterhin valide.
- `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
  bleibt grün (prüft `source-layer`/Icon-Referenzen, nicht Rotations-Properties
  — bestätigt nur, dass nichts kaputt gegangen ist, nicht dass die Rotation
  jetzt korrekt aussieht).
- `python3 scripts/test_validate_style.py` bleibt grün.
- Gezielte Property-Prüfung nach der Änderung: `ski-lifts-icons.layout["icon-rotation-alignment"] == "viewport"`,
  alle drei Label-Layer `layout["text-keep-upright"] == True` — per Skript
  gegen den geschriebenen Style geprüft (keine visuelle Rendering-Prüfung
  möglich, dieses Repo hat kein MapLibre-Rendering-Tooling; die Korrektheit
  der Property-Werte selbst ist durch die MapLibre-Style-Spec-Semantik
  begründet, siehe Untersuchungs-Abschnitt oben).
- Kompletter `run.sh`-Build gegen die echten Daten (etablierter
  End-to-End-Testpfad aus den vorherigen Sub-Projekten).
