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
