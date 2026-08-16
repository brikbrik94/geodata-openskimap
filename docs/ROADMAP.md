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

Ursprünglich (Entscheidung in
`docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`) galt
stattdessen ein einfacheres Modell: jedes Feature bekam genau eine
Kategorie nach fester Priorität (`downhill > nordic > skitour > other`),
keine parallelen Linien. Unter diesem Modell konnte ein Feature nie
gleichzeitig in zwei Kategorie-Layern auftauchen — `line-offset` wäre also
nur ein hypothetisches Nice-to-have für einen Fall gewesen, der so gar
nicht vorkommen konnte.

Seit `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`
(Baustein 1) gilt das nicht mehr: Pisten/Loipen mit mehreren zutreffenden
`uses`-Werten werden jetzt (analog zu Ski-Gebieten) in **jede** zutreffende
Kategorie dupliziert (identische Geometrie), statt einer festen Priorität
zu folgen. Damit entstehen an echten Mehrfachnutzungs-Stellen (z. B.
`uses="downhill,skitour"`) tatsächlich zwei sich deckende Linien in
unterschiedlichen Kategorie-Layern, von denen aktuell nur die obenliegende
sichtbar ist. `line-offset` ist damit kein hypothetisches Feature mehr,
sondern der naheliegende nächste Schritt, um diese echten Duplikate sauber
parallel versetzt statt deckungsgleich übereinander darzustellen.

Für eine spätere Umsetzung: `scripts/convert.sh` müsste die Feature-Zahl
pro Kategorie in ein eigenes numerisches Property schreiben (z. B. per
SQL-`CASE`/Fensterfunktion oder einem nachgelagerten Python-Skript vor der
`ogr2ogr`-Extraktion), `styles/openskimap-style.json`s Run-Line-Layer
bräuchten dann `line-offset`-Expressions analog zum echten Stylesheet.

## Pisten/Lifte erst ab höherer Zoomstufe einblenden (analog echtes OpenSkiMap)

Aktuell haben nur Labels/Icons (`minzoom: 10`/`13`) und die beiden
Snowmaking-Layer (`minzoom: 11`) ein `minzoom` in
`styles/openskimap-style.json` — die eigentliche Pisten-/Lift-Geometrie
(`ski-runs-*-fill/-casing/-line/-gladed/-ungroomed`, `ski-lifts-*`) rendert
bei jeder Zoomstufe 0–14 (verifiziert per Skript-Dump aller `minzoom`-Werte,
2026-08-16). Die echte openskimap.org blendet Pisten/Lifte bei niedrigem
Zoom vermutlich ebenfalls erst später ein — Ziel: weniger visuelles
Rauschen und geringere Tile-Last bei niedrigen Zoomstufen.

Zwei unabhängige Hebel, vermutlich in dieser Reihenfolge sinnvoll:

1. **Style-seitig (günstig, zuerst):** `minzoom` auf den Geometrie-Layern in
   `styles/openskimap-style.json` setzen (z. B. Pisten/Lifte erst ab
   Zoomstufe X). Reiner Style-Edit, kein Pipeline-Rebuild nötig, aber
   reduziert nur die Darstellung — nicht die tatsächliche `.pmtiles`-Größe.
2. **Tiling-seitig (aufwändiger, falls Tile-Gewicht selbst das Problem
   ist):** Features erst ab einer Zoomstufe überhaupt in die `.pmtiles`
   aufnehmen. Die aktuelle einfache `-L name:file`-Syntax in
   `scripts/convert.sh`s tippecanoe-Aufruf unterstützt kein Per-Layer-
   `minzoom` — dafür bräuchte es die JSON-`-L`-Form
   (`-L'{"file":"...", "layer":"...", "minzoom":N}'`) oder mehrere
   getrennte tippecanoe-Läufe plus `tile-join`. Größerer Umbau von
   `convert.sh`, Auswirkung auf Tile-Größe müsste gemessen werden.

Vorgeschlagener erster Schritt: Punkt 1 (Style-seitig) umsetzen und dabei
zunächst am realen openskimap.org-Verhalten orientieren (welche Zoomstufe
dort tatsächlich verwendet wird — Live-Vergleich nötig, siehe Methode in
`docs/TODO_ARCHIVE.md`s Korrektur-Einträgen zu ähnlichen Recherchen).
Punkt 2 nur angehen, falls Tile-Größe/Bandbreite sich als tatsächlicher
Engpass herausstellt.
