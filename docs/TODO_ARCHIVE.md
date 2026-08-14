# TODO Archive

Erledigte Punkte aus `docs/TODO.md` (Historie, kein Nachschlagewerk für die
laufende Aufgabe — siehe `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §3).

## `datetime.utcnow()` DeprecationWarning in generate_manifest.py

*Erledigt: 2026-08-11 (Commit `fix(manifest): replace deprecated
datetime.utcnow() with timezone-aware call`)*

`scripts/generate_manifest.py:90` nutzte `datetime.utcnow()` für `generated_at`
im Manifest — unter aktuellem Python 3 (3.13, siehe `.venv`) als deprecated
markiert, geplante Entfernung in künftiger Version:

```
scripts/generate_manifest.py:90: DeprecationWarning: datetime.datetime.utcnow() is deprecated
and scheduled for removal in a future version. Use timezone-aware objects to represent
datetimes in UTC: datetime.datetime.now(datetime.UTC).
```

Fix: `timezone.utc` (Python 3.2+, kompatibler als `datetime.UTC` ab 3.11)
statt `datetime.utcnow()`. Beim Restrukturierungs-Build (2026-08-11,
`update.sh`/`run.sh`-Einführung) entdeckt, außerhalb des dortigen Scopes,
daher zunächst nur dokumentiert statt mitgefixt — dann als eigener
Mini-Zyklus (D) im Zuge der TODO-Abarbeitung umgesetzt.

## Lift-Status visuell unterscheiden (operating vs. alles andere)

*Erledigt: 2026-08-11 (Sub-Projekt A, Spec
`docs/superpowers/specs/2026-08-11-lift-status-visual-distinction-design.md`,
Plan `docs/superpowers/plans/2026-08-11-lift-status-visual-distinction-plan.md`,
Commit `feat(style): distinguish lift status (operating vs. other) visually`)*

Echtes Stylesheet, zwei Layer statt unserer einen:

- `operating-lift`: Filter `status == operating AND access != private`.
  Durchgezogen, `line-opacity: 0.8`.
- `other-lift`: Filter `status != operating` (deckt proposed/planned/
  construction/disused/abandoned in einem Rutsch ab). **Gestrichelt
  `line-dasharray: [1, 3]`**, dünner (`line-width` Faktor ~0.66 von operating).

Bei uns (`styles/openskimap-style.json`, `ski-lifts-line`) renderten
`operating`/`proposed`/`planned`/`construction` alle identisch, durchgezogen.

Beispiel: `feature_id=84b8d675587243994b24ee9b7e0aa4629a6e54f6`
("Steyrsbergerreithbahn", `status=proposed`, `lift_type=gondola`).

Betraf `ski-lifts-line`/`ski-lifts-line-private`/`ski-lifts-casing`. Gelöst
durch fünf Layer statt drei (Kreuzung `{public,private} × {operating,other}`
plus operating-only Casing) — Details siehe Spec/Plan oben.

## Ausrichtung der Sprites prüfen

*Erledigt: 2026-08-11 (Sub-Projekt C, Spec
`docs/superpowers/specs/2026-08-11-symbol-rotation-alignment-design.md`,
Plan `docs/superpowers/plans/2026-08-11-symbol-rotation-alignment-plan.md`,
Commit `fix(style): keep lift icons upright and run/lift labels right-side-up`)*

Sprite-Ausrichtung (Icons) war nicht korrekt. Ursache gefunden:
`ski-lifts-icons` (einziger Layer mit `icon-image`) hatte kein
`icon-rotation-alignment` gesetzt — MapLibre-Default `"auto"` löst bei
`symbol-placement: "line"` zu `"map"` auf, Icons rotierten also mit der
Linienrichtung, obwohl die Sprites statische Frontalansichten ohne
Richtungsbedeutung sind. Fix: `icon-rotation-alignment: "viewport"`.

Nebenfund im selben Zyklus mitgefixt: `ski-runs-alpine-labels`,
`ski-runs-nordic-labels`, `ski-lifts-labels` hatten `text-keep-upright: false`
ohne dokumentierte Begründung — konnte zu kopfüber gerenderten Labels
führen. Fix: auf `true` (MapLibre-Default, entspricht auch dem echten
OpenSkiMap-Stylesheet, das dieses Feld für seinen analogen Layer nicht
überschreibt).

## Pisten-Kategorien: downhill / nordic / skitour / other statt nur alpine/nordic

*Erledigt: 2026-08-11 (Sub-Projekt B, Spec
`docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`,
Plan `docs/superpowers/plans/2026-08-11-run-category-taxonomy-plan.md`,
Commit `feat(style): replace alpine/nordic run split with downhill/nordic/skitour/other`)*

Echtes Stylesheet nutzte vier Kategorien pro Lauf-Feature (nicht zwei wie
unser bisheriger Alpine/Nordic-Split). Beide dokumentierten Lücken behoben:
Rodelbahn (`feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`, `uses=sled`)
und Winterwanderweg (`feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`,
`uses=hike`) landen jetzt beide sichtbar gestrichelt in der neuen
`other`-Kategorie statt unmarkiert im alten Alpine-Katalog. Mehrfachnutzung
mit parallel versetzten Linien (`line-offset`) bewusst nicht nachgebaut —
siehe `docs/ROADMAP.md`.

## Loipen (nordic) nicht nach Schwierigkeit einfärben

*Erledigt: 2026-08-11 (Sub-Projekt B, selber Commit wie oben)*

**Korrektur 2026-08-11, 16:20 Uhr: diese Prämisse war falsch.** Live-Vergleich
mit openskimap.org (`feature_id=7edf1c552ccd0cd4362e099e4b5adcaf068ad594`
"Loipe Aschau", `difficulty=easy`) zeigt: die echte Seite färbt Loipen sehr
wohl nach Schwierigkeit (blau für "easy"), im Widerspruch zur statischen
`terrain_v2.json`-Style-Datei. `ski-runs-nordic-line`/`-ungroomed` wurden
daraufhin wieder auf Schwierigkeitsfarbe umgestellt (Commit
`fix(style): restore difficulty-based coloring for nordic line/ungroomed`).
Nur `ski-runs-nordic-casing` blieb `lit`-basiert (wie `ski-runs-downhill-casing`
auch).

**Korrektur 2026-08-11, 19:45 Uhr: auch das war noch falsch — Farbe stand am
falschen Layer.** Live-Test von Commit `ae5dadf` zeigte eine durchgängig
einfarbige Linie ohne Rand-Kontrast. Root Cause (systematic-debugging): bei
Loipen ist die visuelle Konvention gegenüber Pisten **umgekehrt** — der
äußere Rand (`ski-runs-nordic-casing`) trägt die Schwierigkeitsfarbe, die
innere Linie (`ski-runs-nordic-line`/`-ungroomed`) bleibt `lit`-basiert
weiß/gelb. Farben entsprechend getauscht (Commit `fix(style): swap nordic
casing/line colors — difficulty on casing, not line`). Ursprünglicher
(überholter) Text unten, nicht mehr aktuell:

OpenSkiMap färbt `nordic-runs` nicht nach Schwierigkeit (nur casing-artiges
Weiß/gelb bei `lit`). Die 1:1 von Alpine gespiegelte Schwierigkeitsfarblogik
auf `ski-runs-nordic-*` wurde durch die `case lit`-Expression vom echten
Stylesheet ersetzt (Fill/Line/Ungroomed). Beispiel:
`feature_id=6a6a6f940d135a95cf034a6e7ca99563a5364bd0` (`uses=nordic`,
`difficulty=null`).

## `layer-list.json` auf `geodata-plugin-standard` v2.0.0 (render-Parts-Modell) migrieren

Erledigt am 2026-08-14: `scripts/layer_metadata_extractor.py` und
`scripts/generate_layer_list.py` vollständig auf das
`render: Array<Part>`-Modell umgestellt (Design:
`docs/superpowers/specs/2026-08-14-render-parts-v2.0-migration-design.md`).
