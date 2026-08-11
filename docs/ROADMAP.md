# ROADMAP

Neue Features/Funktionen, die es im Code noch nicht gibt (keine Erweiterung
von etwas Bestehendem) — siehe `oe5ith-coding-rules/AGENT_INSTRUCTIONS.md`
§3 zur Abgrenzung gegenüber `docs/TODO.md`. Erledigte Punkte wandern nach
`docs/ROADMAP_ARCHIVE.md` (nicht löschen — Historie bleibt erhalten).

## Parallel versetzte Linien bei Pisten-Mehrfachnutzung (`line-offset`)

Das echte OpenSkiMap-Stylesheet zeichnet bei Mehrfachnutzung einer Piste
(z. B. `uses=downhill,skitour`) **mehrere parallel versetzte Linien** —
eine pro zutreffender Kategorie —, über ein serverseitig vorberechnetes
numerisches Feld pro Kategorie (`downhill`/`nordic`/`skitour`/`other`),
das zusätzlich als `line-offset`-Multiplikator dient (siehe
`downhill-runs-casing` im Session-Snapshot `/tmp/openskimap_terrain_style.json`:
`"line-offset": ["interpolate", ..., ["*", 0.5, ["get", "downhill"]], ...]`).

Wir haben stattdessen (Entscheidung in
`docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`) ein
einfacheres Modell: jedes Feature bekommt genau eine Kategorie nach fester
Priorität (`downhill > nordic > skitour > other`), keine parallelen
Linien. Grund: unser GeoPackage hat kein vorberechnetes Offset-Index-Feld,
das selbst zu berechnen wäre deutlich komplexer als die aktuelle
Prioritäts-Zuordnung (u. a. müsste für jede Kombination aus mehreren
zutreffenden Kategorien ein stabiler Index ermittelt werden, der bei
paralleler Nutzung mehrerer benachbarter Pisten nicht überlappt).

Für eine spätere Umsetzung: `scripts/convert.sh` müsste die Feature-Zahl
pro Kategorie in ein eigenes numerisches Property schreiben (z. B. per
SQL-`CASE`/Fensterfunktion oder einem nachgelagerten Python-Skript vor der
`ogr2ogr`-Extraktion), `styles/openskimap-style.json`s Run-Line-Layer
bräuchten dann `line-offset`-Expressions analog zum echten Stylesheet.
