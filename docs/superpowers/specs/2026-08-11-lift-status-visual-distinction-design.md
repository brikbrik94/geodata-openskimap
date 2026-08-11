# Design: Lift-Status visuell unterscheiden (operating vs. other)

## Problem

`docs/TODO.md` → "Lift-Status visuell unterscheiden (operating vs. alles
andere)": Das echte, produktive OpenSkiMap-Stylesheet (tiles.openskimap.org)
rendert Lifte über zwei Layer, abhängig vom `status`-Feld:

- `operating-lift`: Filter `status == operating AND access != private`.
  Durchgezogen, `line-opacity: 0.8`.
- `other-lift`: Filter `status != operating` (deckt proposed/planned/
  construction/disused/abandoned in einem Rutsch ab). Gestrichelt
  (`line-dasharray: [1, 3]`), dünner (`line-width`-Faktor ~0.66 von
  operating).

Bei uns (`styles/openskimap-style.json`) rendern `ski-lifts-line` und
`ski-lifts-line-private` alle Status-Werte identisch, durchgezogen, ohne
Breiten-/Opacity-Unterschied. Betrifft laut TODO `ski-lifts-line`,
`ski-lifts-line-private`, `ski-lifts-casing`.

Beispiel-Feature: `feature_id=84b8d675587243994b24ee9b7e0aa4629a6e54f6`
("Steyrsbergerreithbahn", `status=proposed`, `lift_type=gondola`).

## Ausgangslage: bestehender private/public-Split

Anders als das echte Stylesheet kennen wir bereits eine zweite Dimension,
die dort nicht existiert: `ski-lifts-line` (public, `access != private`,
durchgezogen) vs. `ski-lifts-line-private` (private, `access == private`,
bereits gestrichelt `[1,2]`). Diese Dimension bleibt erhalten (siehe
Entscheidung unten) — der neue Status-Split kommt on top.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-11)

1. **Private-Split bleibt bestehen und wird mit dem Status-Split kombiniert**
   → 4 Line-Layer statt 2 (public×{operating,other} × private×{operating,other}).
2. **Casing (`ski-lifts-casing`) nur für `status == operating`** — für
   `other`-Lifte (dünn, gestrichelt) keine weiße Outline; passt optisch besser
   zu einer feinen gestrichelten Linie.
3. **Breitenfaktor 0.66 auf die bestehende Zoom-Interpolationskurve
   angewendet** (jeder Stop × 0.66), nicht eine neue, unabhängige Kurve.
4. **`line-opacity: 0.8` gilt für beide Status-Varianten** (operating und
   other) — die einzige im echten Stylesheet spezifizierte Zahl, konsistent
   auf beide angewendet statt eine neue für `other` zu erfinden.
5. **Dash-Konflikt bei "other + private"**: Status-Dash `[1,3]` gewinnt
   gegenüber dem bestehenden Private-Dash `[1,2]` — Betriebsstatus ist die
   dominantere visuelle Aussage; der access-Unterschied bleibt über die
   Layer-Trennung (eigener Filter) weiterhin bestehen, nur nicht mehr über
   ein eigenes Dash-Pattern sichtbar.

**Nicht betroffen:** Die Farbgebung (`match` auf `status` in `line-color`)
bleibt in allen Line-Layern unverändert — nicht Teil der TODO-Beanstandung.
`ski-lifts-labels`/`ski-lifts-icons` bleiben unverändert (TODO nennt sie
nicht).

## Neue Layer-Struktur

Ersetzt `ski-lifts-casing`, `ski-lifts-line`, `ski-lifts-line-private` durch:

| Layer-ID | Filter | Dash | Breiten-Faktor | Opacity |
|---|---|---|---|---|
| `ski-lifts-casing` | `status == operating` | — | unverändert | — |
| `ski-lifts-line` | `access != private AND status == operating` | durchgezogen | 1× | 0.8 |
| `ski-lifts-line-other` | `access != private AND status != operating` | `[1,3]` | 0.66× | 0.8 |
| `ski-lifts-line-private` | `access == private AND status == operating` | `[1,2]` (unverändert) | 1× | 0.8 |
| `ski-lifts-line-private-other` | `access == private AND status != operating` | `[1,3]` | 0.66× | 0.8 |

`line-width`-Stops für die `-other`-Varianten (bestehende Kurve × 0.66,
gerundet auf 2 Nachkommastellen): Zoom 6→0.53, 9→0.92, 12→1.45, 14→1.98
(Basis: 6→0.8, 9→1.4, 12→2.2, 14→3.0).

`line-color` (`match` auf `status`) und `line-cap`/`line-join` bleiben in
allen vier Line-Layern identisch zur bisherigen `ski-lifts-line`-Definition.

Filter-Kombination: `["all", ["==/!=", access-check], ["==/!=", status-check]]`
je Layer, analog zum bestehenden Muster in anderen Layern des Styles.

## Betroffene Dateien

- `styles/openskimap-style.json` — 3 Layer werden zu 5 (siehe Tabelle oben).
- `scripts/generate_layer_list.py` — `GROUP_MAP` bekommt die zwei neuen
  Layer-IDs (`ski-lifts-line-other`, `ski-lifts-line-private-other`)
  ergänzt (beide → Gruppe `ski-lifts`), sonst wirft der Build laut
  bestehendem Fail-Fast-Mechanismus einen `KeyError`.
- `scripts/convert.sh` — keine Änderung nötig (Lift-Daten liegen bereits als
  ein Source-Layer `ski_lifts` vor, `status`/`access` sind Properties
  darin, keine neue Geometrie-Extraktion nötig).

## Verifikation

- `python3 scripts/validate_style.py styles/openskimap-style.json assets/sprites/openskimap/sprite.json`
  bleibt grün (alle `source-layer`-Referenzen bekannt, keine kaputten
  Icon-Referenzen).
- `python3 scripts/test_validate_style.py` bleibt grün.
- Kompletter `run.sh`-Build gegen die echten Daten (bereits als
  End-to-End-Testpfad aus der vorherigen Restrukturierung etabliert).
- Stichprobe am Beispiel-Feature `feature_id=84b8d675587243994b24ee9b7e0aa4629a6e54f6`
  (`status=proposed`) im generierten PMTiles/Style: landet im
  `ski-lifts-line-other`-Layer (oder `-private-other`, falls `access=private`),
  keine Casing-Linie darunter.
