# Design: Pisten-Duplizierung, Tag-Normalisierung, Legenden-Kategorien-Extractor

## Problem

Nach der Umstellung auf AT+Grenzgebiete (`d557680`) wurde die Legende gegen die echten,
beschnittenen Daten geprüft (Session-Exploration, `data/src/openskidata.gpkg` per `sqlite3`
direkt abgefragt sowie einzelne OSM-Ways live gegen `api.openstreetmap.org` verifiziert). Dabei
kamen mehrere reale Dateneigenschaften zutage, die die ursprüngliche Idee "Legende/Style aus den
vorkommenden Werten generieren" komplizieren:

1. **`convert.sh` weist Pisten/Loipen nach fester Priorität genau einer Kategorie zu**
   (`downhill > nordic > skitour > other`, siehe
   `docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`) — anders als bei
   Ski-Gebieten, die bei Mehrfachnutzung dupliziert werden. Ein Feature mit
   `uses="nordic,downhill"` landet komplett im Downhill-Layer; bei einer reinen
   "nur Loipen"-Ansicht fehlt es dort komplett.
2. **OpenSkiMap fusioniert beim Aufbau von `openskidata.gpkg` geometrisch benachbarte Ways
   unterschiedlichen Typs zu einem Feature** (verifiziert am Beispiel "Rundloipe Steyersberger
   Schwaig", Feature `3965815c...`: `way/251612265` ist auf OSM sauber `piste:type=downhill`,
   `way/1479515882` sauber `piste:type=nordic, piste:grooming=classic+skating` — OpenSkiMap
   verschmilzt beide zu einer `LINESTRING` mit `uses="nordic,downhill"` und vererbt den
   Loipen-Grooming-Wert auf das kombinierte Feature). Betrifft nur ~13 von 10.890 AT-Downhill-
   Features (~0,1 %) für `grooming ∈ {classic+skating, skating, scooter}` bei Downhill.
3. **`grooming=classic` ist bei Downhill KEIN Merge-Artefakt, sondern verbreitete, echte
   OSM-Tagging-Praxis** (verifiziert an `way/30066149` "Silleralmabfahrt":
   `piste:type=downhill, piste:grooming=classic` direkt auf demselben Way) — betrifft 3.995 von
   10.890 Features (~37 %). Semantisch ist das aber redundant: eine Downhill-Piste ist per
   Annahme präpariert, sofern nicht anders vermerkt (`mogul`/`backcountry`).
4. **Alle `BOOLEAN`-Spalten in der gesamten GeoPackage sind tabellenübergreifend immer `0`**
   (`gladed`, `snowmaking`, `snowfarming`, `patrolled`, `lit`, `oneway`, `detachable`, `bubble`,
   `heating`, `entry`, `exit` — geprüft über `runs_linestring`, `runs_multipolygon`,
   `lifts_linestring`, `spots_point`, sowie gegen einen älteren lokalen Snapshot
   `openskidata.1.gpkg`). Unabhängig bestätigt: `way/30066149` hat auf OSM `oneway=yes`, unser
   Export zeigt `0`. Das ist ein Export-/Konvertierungsfehler bei OpenSkiMap selbst (nicht durch
   den AT-Filter verursacht) — **out of scope für dieses Design**, siehe `docs/TODO.md`-Eintrag
   (neu, siehe unten).

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-16)

### Baustein 1 — Pisten/Loipen wie Ski-Gebiete duplizieren

`convert.sh`s `NORDIC_RUN_WHERE`/`SKITOUR_RUN_WHERE` verlieren ihre `uses NOT LIKE
'%downhill%'`/`NOT LIKE '%nordic%'`-Ausschlüsse — jede Kategorie wird wie bei
`ALPINE_AREA_WHERE`/`NORDIC_AREA_WHERE` unabhängig/inklusiv gefiltert. `OTHER_RUN_WHERE` bleibt
unverändert exklusiv (repräsentiert weiterhin "keine der drei spezifischen `uses` trifft zu" —
kein Kandidat für Duplizierung, da es per Definition der Rest ist).

**Konsequenz:** ein Feature mit `uses="nordic,downhill"` erscheint identisch (gleiche Geometrie)
sowohl im Downhill- als auch im Nordic-Layer. Das supersedet die "genau eine Kategorie pro
Feature"-Entscheidung aus `docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md`
für Pisten/Loipen — jene Spec bleibt als Historie bestehen, wird aber durch dieses Dokument
inhaltlich abgelöst.

**Rendering-Konsequenz (akzeptiert):** an den ~0,1 % Überlappungsstellen zeigt eine gleichzeitig
sichtbare Downhill+Nordic-Ansicht nur die obere Linie (kein `line-offset`, beide Layer
`opacity: 1`). Bei isolierter Ansicht einer Kategorie (z. B. "nur Loipen") ist das Feature dort
korrekt vorhanden. Trade-off bewusst akzeptiert angesichts der Seltenheit echter Überlappung.

### Baustein 2 — Tag-Normalisierung pro Kategorie

Neues Python-Skript `scripts/normalize_run_tags.py`, das nach der `ogr2ogr`-Extraktion
(Baustein 1) und vor dem `tippecanoe`-Build läuft und jede `ski_runs_<kategorie>_line.jsonseq`/
`_poly.jsonseq`-Datei zeilenweise verarbeitet: das `grooming`-Property wird auf `null` gesetzt,
wenn sein Wert für die jeweilige Kategorie nicht in der zugehörigen Allowlist steht.

```python
GROOMING_ALLOWLIST = {
    "downhill": {"mogul", "backcountry"},
    "nordic": {"classic", "classic+skating", "skating", "scooter", "backcountry"},
    # skitour/other: diese Session hat deren grooming-Verteilung nicht untersucht -
    # keine Allowlist, Werte bleiben unverändert (kein Normalisierungs-Scope hier).
}
```

Begründung pro Kategorie (siehe Investigations-Funde oben):
- **downhill**: `classic`/`skating`/`classic+skating`/`scooter` sind Loipen-Vokabular (entweder
  echte Merge-Artefakte wie bei "Rundloipe Steyersberger Schwaig", oder — bei reinem `classic`
  — semantisch redundant, da "präpariert" der Downhill-Standardfall ist). Nur `mogul`
  (Buckelpiste) und `backcountry` (nicht präpariert) sind für Downhill echte Zusatzinformation.
- **nordic**: `mogul` ist Downhill-spezifisch (Buckelpiste ergibt bei einer Loipe keinen Sinn),
  alle anderen Werte sind reguläres Loipen-Vokabular.

Warum ein Python-Post-Processing-Schritt statt SQL `CASE` direkt in `ogr2ogr -sql`: `ogr2ogr
-sql` bräuchte eine vollständige Spaltenliste der Quelltabelle (kein `SELECT * REPLACE(...)` in
der SQLite-Dialect-Kompatibilität von GDAL) — fragil gegenüber Schema-Änderungen bei
OpenSkiMap. Ein Python-Schritt auf den bereits extrahierten `.jsonseq`-Zeilen ist robuster und
folgt dem bestehenden Muster (`generate_layer_list.py` verarbeitet ebenfalls Property-JSON in
Python, stdlib-only).

### Baustein 3 — Legenden-Kategorien-Extractor

Neues Skript `scripts/analyze_legend_categories.py` — **kein** Pipeline-Schritt (nicht in
`run.sh`/`update.sh` eingebunden), manuell aufgerufenes Analyse-Tool. Liest dieselben
`.jsonseq`-Dateien wie Baustein 2 (nach Duplizierung + Normalisierung, vor dem
`tippecanoe`-Build), garantiert dadurch Konsistenz mit dem tatsächlichen Karteninhalt ohne
zweite Filterlogik.

Voraussetzung: `convert.sh`s abschließendes `rm -f *.jsonseq` darf die Dateien nicht mehr
kommentarlos löschen, bevor der Extractor (falls gewünscht) laufen konnte — `work/` ist bereits
vollständig gitignored (siehe `CLAUDE.md`), zusätzlicher Speicherplatz für die
Zwischendateien ist unkritisch. Einfachste Lösung: `rm -f *.jsonseq` entfällt ersatzlos: die
Dateien bleiben nach jedem Build in `work/` liegen (wie `work/openskimap.pmtiles` auch), werden
beim nächsten `convert.sh`-Lauf ohnehin überschrieben.

**Output:** pro Gruppe (`ski_runs_downhill`, `_nordic`, `_skitour`, `_other`, `ski_lifts`,
`ski_spots`) und pro legenden-relevanter Property (`difficulty`, `grooming`, `status`,
`spot_type`) eine nach Häufigkeit sortierte Tabelle (Wert → Anzahl) auf stdout — dasselbe Format
wie die Kreuztabellen/Häufigkeitslisten, die in dieser Session händisch per `sqlite3` erzeugt
wurden.

**Nicht Teil dieses Bausteins:** die Entscheidung, ob die Ergebnisse automatisch in
`legend_sections`/`GROUP_LEGEND_SCALE` (nur Legende) oder zusätzlich ins Stylesheet
(`styles/openskimap-style.json`) einfließen, bleibt bewusst offen — das Extractor-Ergebnis
soll genau diese Entscheidung informieren, nicht vorwegnehmen (Nutzer-Vorgabe von
Gesprächsbeginn dieses Items).

## Explizit zurückgestellt / außerhalb dieses Designs

- **Boolean-Export-Bug** (`gladed`/`snowmaking`/`snowfarming`/`patrolled`/`lit`/`oneway`/...
  immer `0`): eigener `docs/TODO.md`-Eintrag, kein Teil dieses Designs — betrifft die
  `snowmaking`-Achse und die `-gladed`-Variante aus der v2.1.0-Migration (`e5f227f`), die mit
  den aktuellen Daten nie matchen können.
- **Echtes Geometrie-Splitting per Live-OSM-Abfragen oder Umstieg auf rohe OSM/Overpass-Daten**:
  geprüft und verworfen — die gemergte Feature-Geometrie ist bereits eine einzelne
  `LINESTRING` ohne erkennbare Teilgrenze; ein echter Split bräuchte pro betroffenem Feature
  einen Live-OSM-Lookup (Netzwerk-Abhängigkeit im bisher offline-reproduzierbaren Build) oder
  einen kompletten Umstieg auf einen rohen OSM-Datensatz (Wegfall der OpenSkiMap-Vorarbeit:
  Ski-Gebiets-Zuordnung, Routen-Merging, Difficulty-Auflösung). Baustein 1 (Duplizierung der
  gesamten Geometrie statt Teilung) ist der pragmatische Ersatz dafür.
- **`skitour`/`other`-Kategorien' `grooming`-Normalisierung**: nicht untersucht diese Session,
  daher keine Allowlist in Baustein 2 — Werte bleiben dort unverändert.
- **Stylesheet-Generierung selbst** (nicht nur Legende): bleibt offene Entscheidung nach
  Baustein 3's Ergebnissen.

## Betroffene Dateien

- `scripts/convert.sh` — `NORDIC_RUN_WHERE`/`SKITOUR_RUN_WHERE` (Baustein 1), Aufruf von
  `normalize_run_tags.py` nach der `ogr2ogr`-Extraktion (Baustein 2), `rm -f *.jsonseq` entfällt
  (Baustein 3, Voraussetzung).
- `scripts/normalize_run_tags.py` — neu (Baustein 2).
- `scripts/analyze_legend_categories.py` — neu (Baustein 3).
- `docs/TODO.md` — neuer Eintrag zum Boolean-Export-Bug.
- `docs/superpowers/specs/2026-08-11-run-category-taxonomy-design.md` — bleibt als Historie
  bestehen, wird durch dieses Dokument inhaltlich abgelöst (Hinweis-Kommentar dort ergänzen).

**Nicht betroffen:** `styles/openskimap-style.json`, `scripts/generate_layer_list.py`,
`scripts/layer_metadata_extractor.py` (diese Session ändert nur die Datenextraktion/-analyse,
nicht die Style-/Legenden-**Generierung** selbst — das ist die noch offene Anschluss-
Entscheidung).
