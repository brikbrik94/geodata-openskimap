# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-08-16 21:05

### Fixed
- `assets/sprites/openskimap/sprite@2x.json`: alle 13 Icon-Einträge hatten dieselben `x`/`y`/
  `width`/`height`-Werte wie `sprite.json` (48×48-Raster) übernommen, obwohl `sprite@2x.png`
  bereits korrekt doppelt so groß ist (384×384, Icons darin real 96×96) und `pixelRatio: 2`
  richtig deklariert war — nur die Koordinaten selbst waren nie verdoppelt worden. Auf jedem
  Bildschirm mit `devicePixelRatio > 1` (praktisch jeder aktuelle Laptop/Monitor) lud MapLibre
  entsprechend `sprite@2x.png`, schnitt aber mit den unskalierten 48×48-Boxen nur das linke obere
  Viertel jedes echten 96×96-Icons aus — sichtbar als abgeschnittene und dazu meist auf ein
  benachbartes Gitterfeld verrutschte Icons (deshalb der Eindruck "überall Sessellifte": mehrere
  falsch zugeordnete Viertel-Crops landeten zufällig auf benachbarten Sessellift-Rasterfeldern).
  Nicht durch Cache verursacht (reproduziert auch mit Hard-Refresh/privatem Fenster) und nicht
  durch heutige Style-/Legend-Änderungen — Sprite-Dateien waren seit April unangetastet, der
  Fehler bestand schon vorher, ist aber erst jetzt aufgefallen. Fix: alle `x`/`y`/`width`/`height`
  in `sprite@2x.json` verdoppelt (Werte 1:1 aus `sprite.json` × 2 abgeleitet, `pixelRatio`
  unverändert). `sprite@2x.png` selbst war bereits korrekt, keine Änderung nötig.

## [Unreleased] - 2026-08-16 19:44

### Changed
- `scripts/generate_layer_list.py`: `ski-spot-type-v1`-Legend-Scale entfernt (`GROUP_LEGEND_SCALE`/
  `LEGEND_SCALE_LABELS`) — wie zuvor bei `ski-lift-status-v1` hatte diese Scale exakt einen
  Konsumenten (den einzigen `circle`-Part von `ski-spots`), der Umweg über eine geteilte Scale
  brachte also keinen Vorteil (im Gegensatz zu `ski-difficulty-v1`, das echt von drei Gruppen
  geteilt wird). `GROUP_VARIANTS["ski-spots"]` bekommt stattdessen 6 hand-authored Zeilen (Achse
  `spot_type`: Lift Station, Halfpipe, Crossing, Avalanche Transceiver Training, Avalanche
  Transceiver Checkpoint, Sonstige) mit fixer Farbe statt Scale-Referenz, direkt aus dem echten
  `circle-color`-Match in `styles/openskimap-style.json` übernommen — ein neuer Regressionstest
  liest diese Werte zur Laufzeit aus dem Style, damit sie nicht unbemerkt auseinanderlaufen. Keine
  Style-Änderung nötig, `ski-spots` bleibt ein einziger physischer Circle-Layer.

## [Unreleased] - 2026-08-16 18:45

### Changed
- `scripts/generate_layer_list.py`: `GROUP_VARIANTS["ski-lifts"]`s neue `"lift_type"`-Achse
  (`Kombibahn (Gondel + Sessellift)`, eingeführt im vorigen Journal-Block) wieder entfernt —
  Nutzer-Feedback: eine eigene Legend-Zeile nur für `mixed_lift` wäre inkonsistent, da die
  anderen 11 `lift_type`-Werte ebenfalls keine eigene Zeile bekommen (generischer, ungelabelter
  Icon-Part in `render`). Die beiden Style-Layer (`ski-lifts-icons-mixed-gondola`/`-mixed-chair`)
  bleiben unverändert bestehen (Icon-Paar rendert weiterhin korrekt auf der Karte) und landen
  jetzt stattdessen in der flachen `render`-Liste der Gruppe statt in einem Variant — weiterhin
  §5.3-konform (jeder Style-Layer landet in `render` oder genau einem `variants[]`-Eintrag),
  nur eben nicht mehr als eigene Legend-Zeile sichtbar.

## [Unreleased] - 2026-08-16 18:39

### Removed
- `styles/openskimap-style.json`: toten `difficulty == "freeride"`-Sonderfall aus
  `ski-runs-nordic-fill`s und `ski-runs-skitour-fill`s `fill-color`-Expression entfernt.
  Verifiziert gegen `work/`: `ski_runs_nordic_poly.jsonseq` hat 2 Features, `ski_runs_skitour_poly.jsonseq`
  1 Feature (ggü. 2.767 bei `ski_runs_downhill_poly.jsonseq`, wo der Zweig bleibt) — Polygon-Fläche
  ist bei Loipen/Skitouren praktisch nie vorhanden. Bei Loipen kommt Freeride laut den echten Daten
  zusätzlich nie vor (bereits verifiziert, siehe `ski-difficulty-v1`-Scale-Historie), der Zweig war
  dort ohnehin unerreichbar. Bei Skitouren bleibt Freeride weiterhin über die eigene
  Linien-Legendenzeile (`GROUP_VARIANTS["ski-runs-skitour"]`, Achse `difficulty`, Label `Freeride`)
  sinnvoll dargestellt — das ist jetzt die einzige Freeride-Darstellung für Skitouren, statt einer
  zusätzlichen, für die kaum vorhandene Polygon-Fläche irrelevanten Sonderfarbe. Keine Änderungen an
  `scripts/generate_layer_list.py` oder Tests nötig: die extrahierte `ski-difficulty-v1`-Skala hängt
  nur an der dahinterliegenden `difficulty_convention`-Match-Verschachtelung, die unverändert bleibt.

## [Unreleased] - 2026-08-16 17:18

### Changed
- `styles/openskimap-style.json`: Lift-`status`-Färbung von einer gemeinsamen `match`-Expression
  auf feste Filter-Layer umgestellt. Neu 3 Stufen statt 2: **In Betrieb** (`operating`,
  unverändert `hsl(0, 82%, 42%)`), **Geplant / Im Bau** (`proposed`+`construction`, neue Farbe
  `hsl(210, 70%, 45%)`, Dasharray `[4, 2]`), **Außer Betrieb** (`disused`+`abandoned`,
  unverändert `hsl(0, 53%, 42%)`, Dasharray `[1, 3]`) — vorher in "Sonstiger Status"
  zusammengeworfen. `ski-lifts-line-other` ersetzt durch `ski-lifts-line-planned`/
  `ski-lifts-line-disused`. `ski-lifts-line-private`/`-line-private-other` bleiben bei der
  bisherigen 2-Wege-Aufteilung (nur 1 von 2938 Lift-Features ist `private`+nicht-`operating`),
  Farben aber ebenfalls fest statt Match. Toten `"planned"`-Match-Zweig (kommt nie in den Daten
  vor) und `t_bar`/`j_bar`-Icon-Zweige (Daten verwenden ausschließlich `t-bar`/`j-bar`) entfernt.
  Siehe `docs/superpowers/specs/2026-08-16-lift-status-icon-cleanup-design.md`.
- `scripts/generate_layer_list.py`: `ski-lift-status-v1`-Legend-Scale komplett entfernt
  (`GROUP_LEGEND_SCALE`/`LEGEND_SCALE_LABELS`) — sie hatte strukturell alle 7 Status-Match-
  Branches ungefiltert in eine Scale gepackt, sodass z. B. die "In Betrieb"-Legend-Zeile
  fälschlich auch auf "Disused"/"Abandoned"-Farben verwies. Jeder Lift-Layer hat jetzt eine feste
  Farbe statt eines Matches, daher keine kategorisierte Farbe mehr in der Gruppe.
  `GROUP_VARIANTS["ski-lifts"]`s `"status"`-Achse hat jetzt 3 statt 2 Einträge
  (`In Betrieb`/`Geplant / Im Bau`/`Außer Betrieb`).

### Added
- `styles/openskimap-style.json`: `mixed_lift` (17 Features, z. B. "Sternstein Express") bekommt
  ein Icon-Paar statt des irreführenden Default-Fallbacks `ski-gondola` — zwei neue Symbol-Layer
  (`ski-lifts-icons-mixed-gondola`/`-mixed-chair`), per `icon-offset` vertikal (im Bildschirmraum,
  da `icon-rotation-alignment` weiterhin `viewport` bleibt) versetzt,
  nutzen ausschließlich bestehende Sprites (Gondel-Icon + die bestehende Occupancy-basierte
  Sessellift-Icon-Auswahl). `ski-lifts-icons` bekommt einen `lift_type != "mixed_lift"`-Filter,
  um Doppel-Icons zu vermeiden. `scripts/generate_layer_list.py`s `GROUP_VARIANTS["ski-lifts"]`
  bekommt eine neue `"lift_type"`-Achse mit einer Zeile (`Kombibahn (Gondel + Sessellift)`) für
  dieses Icon-Paar — kein Vorgriff auf Lift-Typ-Icons als Legend-Zeilen generell (siehe
  `docs/TODO.md`).
- `docs/ROADMAP.md`: Eintrag für ein eigenes `railway`-Sprite-Icon (2 Features, aktuell
  `ski-gondola`-Fallback) — zurückgestellt.
- `docs/TODO.md`: Eintrag für Lift-Typ-Icons als eigene Legend-Zeilen (analog Grooming bei
  Pisten) — zurückgestellt, siehe Design-Dokument "Out of Scope".

## [Unreleased] - 2026-08-16 16:01

### Changed
- `styles/openskimap-style.json`: die `difficulty`-`color`-Match-Expressions (10 Vorkommen über
  `ski-runs-downhill-fill/-line/-labels`, `ski-runs-nordic-fill/-casing/-labels`,
  `ski-runs-skitour-fill/-line/-labels`, `ski-runs-connection-line`) verlieren die toten
  `expert`/`extreme`-Zweige (identisch zu `advanced`/`freeride`, seit dem Difficulty-Remap nie
  mehr in den Daten) und den `freeride`-Zweig — Freeride wird jetzt über einen vorgezogenen
  `["==", ["get","difficulty"], "freeride"]`-Case-Zweig mit fixer Farbe behandelt (identisch zu
  vorher, `hsl(34, 100%, 50%)`, über alle Convention-Zweige hinweg verifiziert konsistent), statt
  als Teil der verschachtelten `difficulty_convention`-Match-Expressions. Rendering-Verhalten
  unverändert (Freeride-Pisten bleiben orange, unabhängig von `difficulty_convention`) —
  `layer_metadata_extractor.py`s `_resolve_case_branch` überspringt den neuen Zweig automatisch
  (Property-Mismatch), sodass die extrahierte `ski-difficulty-v1`-Skala jetzt nur noch 4 echte
  Stufen (Novice/Easy/Intermediate/Advanced) + `Sonstige` zeigt, ohne Änderungen am Extractor.
- `ski-runs-downhill-line`/`ski-runs-connection-line`s `line-dasharray` bekommt einen dritten
  `difficulty == "freeride"`-Zweig (gestrichelt `[3, 6]`, nach den grooming-Zweigen — Buckelpiste/
  Backcountry haben weiterhin Vorrang vor Freeride, falls eine Piste beides ist).

### Added
- `scripts/generate_layer_list.py`: `GROUP_VARIANTS["ski-runs-downhill"]` bekommt eine vierte,
  eigene `"difficulty"`-Achsen-Zeile `"Freeride"` (fixe orange Farbe statt Skalen-Referenz,
  gestrichelt) neben den drei `"grooming"`-Zeilen. `GROUP_VARIANTS["ski-runs-skitour"]` ist neu
  (vorher `variants: null`): zwei `"difficulty"`-Zeilen `"Skiroute"` (weiterhin
  skalen-referenziert, ganz normal aus dem Style abgeleitet — Skitour-`line-dasharray` war nie
  eine `case`-Expression) und `"Freeride"` (wie bei Downhill). `ski-runs-nordic` bekommt keine
  Freeride-Zeile — verifiziert gegen die echten AT-gefilterten Daten: `freeride`/`extreme` kommen
  bei Loipen (`uses LIKE '%nordic%'`) in keinem einzigen Feature vor. Zwei neue Regressionstests
  lesen die echten `case`-Expression-Werte (Dasharray UND Farbe) aus dem Style, damit die
  hand-authored Freeride-Werte nicht unbemerkt auseinanderlaufen. 120/120 Tests grün.

### Removed
- `ski-runs-downhill-snowmaking`/`ski-runs-nordic-snowmaking` komplett aus
  `styles/openskimap-style.json` entfernt (`GROUP_MAP`-Einträge in
  `scripts/generate_layer_list.py` entsprechend entfernt). Wie zuvor bei
  `ski-runs-downhill-gladed` (Waldabfahrten) gilt: das `snowmaking`-Feld im
  GeoPackage-Export ist immer `false` (Upstream-Bug bei OpenSkiMap, siehe
  `docs/TODO.md`), diese Layer haben also nie echte Daten gematcht und nie
  etwas gerendert. Statt sie als permanent leere Layer im Style zu behalten,
  komplett entfernt. `scripts/test_generate_layer_list.py` entsprechend
  angepasst (118/118 Tests grün).

### Added
- `scripts/generate_layer_list.py`: `ski-runs-downhill`/`ski-runs-nordic` get a `"grooming"`
  `variants[]` axis back — 3 Zeilen für Downhill (`Piste`/`Piste (Backcountry)`/`Buckelpiste`,
  deckt auch `ski-runs-connection-line` mit ab, da es visuell identisch rendert) und 2 Zeilen
  für Nordic (`Loipe`/`Loipe (Backcountry)`). Anders als bei `ski-lifts` sind diese Varianten
  NICHT aus dem Style abgeleitet, sondern hand-authored literale `Part`-Objekte
  (`_build_render_and_variants` unterstützt jetzt einen optionalen `"render"`-Schlüssel im
  Variant-Def, der die sonst übliche Style-Layer-Extraktion überspringt) — der Grund:
  `extract_part_dasharray` kann `line-dasharray`-`case`-Expressions grundsätzlich nicht
  parsen (nur ein literales 2-Element-Array), und drei Legenden-Zeilen aus demselben
  Style-Layer über Feld-Overrides abzuleiten hätte unübersichtliche Abhängigkeiten zwischen
  den Varianten-Einträgen erzeugt — auf Nutzerwunsch stattdessen bewusst einfach und
  in sich geschlossen gehalten. Ein neuer Regressionstest
  (`test_downhill_and_nordic_variant_dasharray_matches_style_case_expression`) liest die
  echten `case`-Expression-Werte aus `styles/openskimap-style.json` und vergleicht sie gegen
  die hand-authored Werte, damit beide nicht unbemerkt auseinanderlaufen.
  `scripts/test_generate_layer_list.py` entsprechend angepasst (118/118 Tests grün).

### Fixed
- `ski-runs-downhill`/`ski-runs-nordic` in `scripts/generate_layer_list.py`: `GROUP_VARIANTS`-
  Einträge (grooming-terrain/grooming + snowmaking-Achsen) komplett entfernt. Sie waren um
  dedizierte gefilterte Style-Layer (`-downhill-gladed`, `-downhill-ungroomed`,
  `-nordic-ungroomed`) herumgebaut, die das Pisten-Restyling vom selben Tag bereits ersatzlos
  gestrichen hatte (Grooming läuft seitdem über eine `line-dasharray`-`case`-Expression auf
  einem einzigen `-line`-Layer statt über separate gefilterte Layer) — die `variants[]`-
  Einträge referenzierten dadurch nicht mehr existierende Style-Layer-IDs und produzierten
  leere `render[]`-Listen (4 fehlschlagende Tests). Beide Gruppen fallen jetzt auf flaches
  `render[]` zurück wie jede Gruppe ohne `GROUP_VARIANTS`-Eintrag — das behebt nebenbei auch
  `ski-runs-downhill`'s bisherige bekannte, dokumentierte Abweichung von
  `GEODATA_PLUGIN_STANDARD.md` §5.3 (Part-Duplikation über zwei `variants[]`-Einträge hinweg),
  da es jetzt keine `variants[]` mehr gibt, in die dupliziert werden könnte. Die entsprechende
  TODO.md-Notiz ist damit hinfällig und wurde entfernt. `scripts/test_generate_layer_list.py`
  entsprechend angepasst (117/117 Tests grün). Breaking Change für `website-v3`: beide Gruppen
  liefern jetzt `variants: null` statt Achsen-Varianten — vom Nutzer nach Rückfrage (Optionen
  "variants entfernen" vs. "nur snowmaking behalten") explizit so entschieden.

### Removed
- `ski-runs-other`-Gruppe komplett aus Style, Layer-Liste und Validierung entfernt: sie hatte
  0 Features (die "Other"-Kategorie wurde am selben Tag bereits vollständig in sechs eigene
  Kategorien aufgeteilt, siehe Eintrag `2026-08-16 06:27`ff. — ein leerer Layer wäre für
  Konsumenten sichtbar, aber sinnlos gewesen). Entfernt: `ski-runs-other-fill/-line/-labels`
  aus `styles/openskimap-style.json`, die zugehörigen `-L`-Einträge aus dem
  `tippecanoe`-Aufruf in `scripts/convert.sh`, sowie die `GROUP_MAP`/`GROUP_NAMES`/
  `GROUP_LEGEND_SCALE`-Einträge und `KNOWN_SOURCE_LAYERS`-Einträge in
  `scripts/generate_layer_list.py`/`scripts/validate_style.py`.
- Die `ogr2ogr`-Extraktion von `ski_runs_other_line/_poly.jsonseq` (`OTHER_RUN_WHERE`, echtes
  Rest-Auffangbecken für unbekannte `uses`-Werte) bleibt bewusst bestehen — nur nicht mehr im
  `tippecanoe`-Build. Neu: `scripts/convert.sh` prüft nach der Extraktion die Zeilenzahl beider
  Dateien und gibt bei > 0 Features eine `log_warn` aus, damit ein künftiger/unbekannter
  `uses`-Wert nicht stillschweigend im PMTiles-Output fehlt.



### Added
- `scripts/normalize_run_tags.py`: neue, kategorie-unabhängige `difficulty`-Remappierung
  (`DIFFICULTY_REMAP`, `normalize_difficulty()`) — `expert` → `advanced`, `extreme` → `freeride`,
  angewandt auf **alle vier** Pisten-Kategorien (auch `other`, das dafür jetzt ebenfalls durch
  `normalize_run_tags.py` läuft, `grooming` bleibt dort aber weiterhin unverändert). Grund: die
  Style-Match-Expression für `difficulty` färbt `advanced`/`expert` bereits identisch (Schwarz)
  und `freeride`/`extreme` bereits identisch (Orange) — der 7-stufige Rohwert rendert schon heute
  nur als 5 Farben, die Legende hinkt dem nur hinterher. Verifiziert gegen die echten Daten:
  `ski_runs_downhill`'s `difficulty`-Verteilung hat jetzt `advanced: 1281` (= vorher 1211+70) und
  `freeride: 334` (= vorher 327+7), kein `expert`/`extreme` mehr.
- **Bewusst zurückgestellt (nächster Schritt):** Style (`styles/openskimap-style.json`, tote
  `expert`/`extreme`-Zweige in vier Match-Expressions) und Legende (`ski-difficulty-v1` zeigt
  noch 8 statt 5 Einträge) sind noch nicht angepasst — folgt als separater Schritt.



### Added
- `scripts/normalize_run_tags.py`: `GROOMING_ALLOWLIST` um `"skitour": {"backcountry"}` erweitert.
  Anders als bei Downhill/Nordic sind die betroffenen Werte (`classic`/`classic+skating`/
  `skating`/`scooter`/`mogul`, 18 von 1.673 Skitour-Features) überwiegend **keine**
  OpenSkiMap-Merge-Artefakte, sondern sitzen auf reinen Skitour-Ways — nach manueller Prüfung
  aller 18 betroffenen OSM-Ways/-Relationen gegen die Live-Daten bestätigt: unzureichend
  gepflegte OSM-Tags ohne Skitour-Relevanz (Skitouren sind qua Definition ungroomed). Verworfen.
- `scripts/convert.sh`: `normalize_run_tags.py`-Aufruf für `ski_runs_skitour_line/_poly.jsonseq`
  ergänzt (analog zu Downhill/Nordic).

## [Unreleased] - 2026-08-16 09:59

### Added
- `scripts/normalize_run_tags.py`: normalisiert `grooming`-Werte pro Pisten-/Loipen-Kategorie
  (Downhill: nur `mogul`/`backcountry` bleiben erhalten; Nordic: `classic`/`classic+skating`/
  `skating`/`scooter`/`backcountry`) — behebt sowohl OpenSkiMap-Merge-Artefakte (Loipe+Piste zu
  einem Feature fusioniert) als auch die semantisch redundante `classic`-Markierung auf reinen
  Downhill-Pisten. Siehe
  `docs/superpowers/specs/2026-08-16-run-duplication-tag-normalization-legend-extractor-design.md`.
- `scripts/analyze_legend_categories.py`: manuelles Analyse-Tool (kein Pipeline-Schritt), das aus
  den `.jsonseq`-Zwischendateien in `work/` Häufigkeitstabellen pro Gruppe/Property erzeugt.

### Changed
- **Breaking:** `scripts/convert.sh` dupliziert Pisten/Loipen mit Mehrfachnutzung jetzt in jede
  zutreffende Kategorie (analog zu Ski-Gebieten) statt fester Priorität
  `downhill > nordic > skitour > other` — ein Feature mit `uses="nordic,downhill"` erscheint jetzt
  in beiden Layern. Betrifft `ski_runs_nordic_*`/`ski_runs_skitour_*`. Löst das Problem, dass eine
  "nur Loipen"-Ansicht Mischnutzungs-Segmente sonst komplett verliert.
- `scripts/convert.sh` löscht die `.jsonseq`-Zwischendateien am Ende nicht mehr (`work/` ist
  bereits vollständig gitignored) — Voraussetzung für `analyze_legend_categories.py`.

### Fixed
- **Korrektur (finales Branch-Review, 2026-08-16):** die im Design-Dokument als generelle
  "~0,1 %"-Überlappung angegebene Zahl galt nur für Downhill∩Nordic (17 Features). Gegen die
  echten `work/*.jsonseq`-Ausgaben gemessen: Downhill∩Skitour teilen sich tatsächlich 180
  Features (~10,8 % von Skitours ~1.673 Features, **nicht** selten), Nordic∩Skitour 29 Features,
  Paare mit "other" 0. Betrifft nur die Dokumentation/Zahlen (Design-Spec, Baustein 1) — der
  akzeptierte Duplizierungs-Ansatz und der Code bleiben unverändert.

## [Unreleased] - 2026-08-16 08:21

### Changed
- **Breaking (Datenumfang):** `scripts/convert.sh` beschneidet den weltweiten OpenSkiMap-Datensatz
  jetzt auf Skigebiete/Pisten/Lifte/Spots mit Österreich-Bezug (`country_codes LIKE '%AT%'`,
  neue Variable `COUNTRY_WHERE`, kombiniert per `AND` in alle bestehenden `-where`-Klauseln sowie
  neu bei den bisher ungefilterten `ski_lifts`/`ski_spots`-Extraktionen). Grund: die belieferte
  Deployment-Umgebung nutzt eine Basiskarte, die nur Österreich + Nachbarländer abdeckt: der
  globale Datensatz war unnötig groß und die Legende zeigte international übliche, in Österreich
  aber kaum relevante Kategorien. `LIKE '%AT%'` erfasst reine AT-Gebiete **und**
  grenzüberschreitende (z. B. Ischgl/Samnaun, `AT;CH`) — kein Bounding-Box-Clip, sondern ein
  Attribut-Filter auf dem semikolon-getrennten ISO-Alpha-2-Feld. Verifiziert: 29.725 Features
  gesamt nach Filter (vorher u. a. 214.912 `runs_linestring`, 33.119 `lifts_linestring` weltweit).
  Konsumenten, die auf globale Abdeckung angewiesen waren, bekommen jetzt nur noch AT+Grenzgebiete.

### Known Issues
- Die Legende (Schwierigkeitsstufen, Waldabfahrt-Variante, Lift-Status, Spot-Typ) ist weiterhin
  fest in `styles/openskimap-style.json` als `match`/`case`-Expression hinterlegt und wird **nicht**
  automatisch durch diesen Datenfilter verkleinert — z. B. bleibt die Waldabfahrt-Variante und die
  7-teilige Schwierigkeitsskala im Style bestehen, auch wenn sie in den jetzt AT-beschnittenen
  Daten kaum/nicht vorkommen. Eine datengetriebene Legenden-Generierung ist als separates Vorhaben
  in Planung (Brainstorming lief in dieser Session).

## [Unreleased] - 2026-08-16 06:27

### Added
- `dist/layer-list.json`: jeder `Part` trägt jetzt `stroke_color`/`stroke_width`
  (`scripts/layer_metadata_extractor.py`, `scripts/generate_layer_list.py`) — `null` außer bei
  `kind: "circle"`, dort aus `circle-stroke-color`/`circle-stroke-width` (betrifft
  `ski-areas-alpine/-nordic-circle`, `ski-spots`). Schließt die in
  [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3)
  gemeldete Lücke, jetzt offiziell Teil des Standards (v2.1.0 §5.3).
- `variants[]`-Einträge tragen jetzt ein `axis`-Feld (String) — jetzt offiziell Teil des
  Standards (v2.1.0 §5.3, löst
  [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4)).
- Neue Single-Value-Achse `"snowmaking"` (Label "Beschneit") bei `ski-runs-downhill` und
  `ski-runs-nordic` — löst die seit 2026-08-14 zurückgestellte Lücke (siehe
  `docs/TODO_ARCHIVE.md`).
- `"version"` in `dist/layer-list.json` auf `"2.1"` angehoben.

### Changed
- **Breaking:** `ski-lifts`' `variants[]` von 4 flachen Status×Zugang-Kombinations-Einträgen
  auf 3 Einträge über 2 Achsen umgestellt — axis `"status"` ("In Betrieb"/"Sonstiger Status")
  und axis `"access"` (Single-Value "Privat", deckt beide Statuswerte gemeinsam ab). Grund:
  `ski-lifts-casing` (Filter testet nur `status`) landete im alten Modell fälschlich in 2 von 4
  Einträgen; die neue Achsen-Struktur verwendet jeden der 4 realen Style-Layer genau einmal.
  Konsumenten, die die alte 4-Kombi-Form positionell parsen (z. B. `website-v3`), müssen
  angepasst werden.
- `GROUP_VARIANT_EXCLUDE` (und der zugehörige Ausschluss-Schritt in
  `_build_render_and_variants`) entfernt — beide bisherigen Einträge (Nordic-/Downhill-
  Snowmaking) sind jetzt reguläre `"snowmaking"`-Achsen-Einträge statt eines Ausschlusses.
- `ski-runs-downhill`/`ski-runs-nordic` behalten ihre bisherige Varianten-Form (4 bzw. 2
  Einträge) unverändert, zusätzlich zum `axis`-Feld und dem neuen Snowmaking-Eintrag —
  bewusste Entscheidung, keine zweite Formänderung für `website-v3` in kurzer Zeit
  (Alternative einer vollen Orthogonal-Zerlegung geprüft und verworfen, siehe
  `docs/superpowers/specs/2026-08-16-layer-list-v2.1-migration-design.md`).
- **Bekannte Abweichung:** `ski-runs-downhill`'s `variants[]` erreicht dadurch keine volle
  §5.3-Konformität (`-gladed`/`-ungroomed` landen je in 2 statt genau 1 `variants[]`-Eintrag) —
  siehe neuen `docs/TODO.md`-Eintrag "`ski-runs-downhill`'s `variants[]` ist nicht
  §5.3-konform".
- Submodul `geodata-plugin-standard` von v2.0.0 auf v2.1.0 gebumpt.

## [Unreleased] - 2026-08-14 15:26

### Added
- `dist/layer-list.json`: neues, lokal vorgeschlagenes Feld `variants` auf Gruppen-Ebene
  (`scripts/generate_layer_list.py`, Design-Dokument
  `docs/superpowers/specs/2026-08-14-legend-variants-design.md`) für Style-Layer, die sich
  laut ihrem MapLibre `filter` gegenseitig ausschließen (z. B. Loipen "gespurt"/"ungespurt",
  Lifte Status×Zugang) — verhindert, dass ein naiver Legenden-Renderer sie deckungsgleich
  übereinander zeichnet. Betrifft `ski-runs-nordic` (2 Varianten), `ski-runs-downhill`
  (4 Varianten), `ski-lifts` (4 Varianten). Vorgeschlagen
  als [geodata-plugin-standard#4](https://github.com/brikbrik94/geodata-plugin-standard/issues/4)
  (noch nicht Teil des Standards).

### Changed
- **Konsumen-Inkompatibilität**: das `render`-Array für `ski-runs-nordic`, `ski-runs-downhill`
  und `ski-lifts` ist geschrumpft, weil Style-Layer, die sich gegenseitig ausschließen,
  jetzt aus `render` in `variants[].render` migriert sind: Legenden-Renderer, die das neue
  `variants`-Feld ignorieren, zeigen für diese drei Gruppen eine unvollständige Legende
  (ohne Loipen-/Pisten-/Lift-Status-Layer). Auch: das Feld `style_layers` listete schon
  vorher `snowmaking`-Layer auf, obwohl kein Part dafür in `render`/`variants` existiert,
  was Konsumenten, die `style_layers` positionell mit `render` korrelieren, verwirrt.

### Known Issues
- `snowmaking`-Layer (`ski-runs-downhill-snowmaking`, `ski-runs-nordic-snowmaking`) sind aus
  `render`/`variants` komplett entfernt — passen als unabhängiger, mit jeder
  Präparierungsstufe gleichzeitig auftretender Zusatz-Marker nicht ins
  geteilt/Variante-Schema. Datenverlust bewusst in Kauf genommen, bis das Standard-Schema
  für solche orthogonalen Marker wächst (siehe `docs/TODO.md`).

## [Unreleased] - 2026-08-14 08:36

### Changed
- Submodul `geodata-plugin-standard` von v1.1.0 auf v2.0.0 gebumpt. **Breaking
  Change im Standard**: §5-Layer-Listen-Spezifikation von Einzel-Property-Paint
  (`color`/`width`/`dasharray`/`outline_*`) auf ein generisches
  `render: Array<Part>`-Modell umgestellt, Schema-Version "2.0".
- `dist/layer-list.json` auf das neue Schema migriert (`scripts/layer_metadata_extractor.py`,
  `scripts/generate_layer_list.py`, Design-Dokument
  `docs/superpowers/specs/2026-08-14-render-parts-v2.0-migration-design.md`):
  jeder Style-Layer einer Gruppe wird jetzt unabhängig zu einem `Part` im
  `render`-Array (kein Primär-Layer-Merge mehr), `color` wird zum
  `{mode, value|scale_id}`-Objekt. Zwei neue zentrale Farbskalen
  `ski-lift-status-v1` ("Lift-Status") und `ski-spot-type-v1` ("Spot-Typ"),
  die in v1.1 nur als ungruppierte `legend_items` ohne Skalen-Kennung
  vorlagen. `"version": "1.1"` → `"2.0"`.

### Known Issues
- `circle-stroke-color`/`circle-stroke-width` (auf `ski-areas-*-circle` und
  `ski-spots`) haben im neuen `Part`-Modell kein Feld — Standard-seitige
  Lücke, gemeldet als
  [geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3).
  Datenverlust bewusst in Kauf genommen, bis der Standard nachzieht.

## [2.0.0] - 2026-08-12

### Changed
- `layer-list.json`-Schema auf v1.1 (`geodata-plugin-standard` v1.1.0,
  §5) angehoben: neue Felder `width`, `dasharray`, `outline_color`,
  `outline_width`, `icon`, `legend_scale_id` je Gruppe, neuer
  Top-Level-Block `legend_sections`. **Breaking Change**: Gruppen mit
  gesetzter `legend_scale_id` haben jetzt `legend_items: null` — die
  Werte liegen zentral in `legend_sections`.
- Die vier Pisten-Gruppen (`ski-runs-downhill/-nordic/-skitour/-other`)
  teilen sich jetzt eine zentrale Schwierigkeits-Legende
  (`legend_scale_id: "ski-difficulty-v1"`) statt sie viermal identisch
  zu duplizieren.
- Gruppen-Anzeigenamen auf Deutsch umgestellt (Pisten, Loipen,
  Skitouren, Sonstige Strecken, Skigebiete (Alpin/Nordisch),
  Ski-Spots, Lifte) statt automatisch generierter
  Titel-Case-Platzhalter.

### Fixed
- `layer-list.json`: `legend_items` für die schwierigkeitsbasierten Pisten-Fill-Layer
  (`ski-runs-{downhill,nordic,skitour,other}-fill`) war immer `null`, weil deren
  `fill-color` ein `case` (Umschaltung nach `difficulty_convention`: europe/japan/
  default) ist, das jeweils ein `match` auf `difficulty` verschachtelt —
  `extract_legend_items()` in `scripts/layer_metadata_extractor.py` erkannte bisher
  nur `interpolate`/`match` auf oberster Ebene, nicht `case`. Legende wird jetzt aus
  der `europe`-Convention aufgelöst (Zielgruppe DACH), mit Fallback auf den
  `case`-Else-Zweig, falls kein `europe`-Branch vorhanden ist.
- `ski-lifts`-Gruppe zeigte `color: "hsl(0, 0%, 100%)"` (weiß, von der
  Casing-Linie `ski-lifts-casing`), obwohl die eigentliche
  Status-Farbe (rot/…) in `ski-lifts-line` liegt und `legend_items`
  bereits korrekt die Status-Farben zeigte. Casing-/Outline-Layer
  (`id` endet auf `-casing`/`-outline`) werden jetzt nie mehr als
  Primär-Layer gewählt.

## [1.0.1] - 2026-08-11

### Fixed
- `ski-runs-skitour-{fill,line,labels}` und `ski-runs-other-{fill,line,labels}`
  färben jetzt nach Schwierigkeit ein (dieselbe Match-Expression wie
  `ski-runs-downhill-*`) statt einer erfundenen Volltonfarbe pro Kategorie
  — `openskidata-format`s Farblogik ist grundsätzlich schwierigkeitsbasiert,
  unabhängig von der Nutzungskategorie.
- Loipen-Einfärbung: der Außenrand (`ski-runs-nordic-casing`) trägt jetzt
  die Schwierigkeitsfarbe, die innere Linie (`ski-runs-nordic-line`/
  `-ungroomed`) bleibt `lit`-basiert weiß/gelb — bei OpenSkiMap ist das
  gegenüber Pisten (Farbe innen, `lit`-Rand außen) bewusst umgekehrt, um
  Loipe und Piste auch bei gleicher Schwierigkeits-Farbpalette optisch
  unterscheidbar zu halten.

Alle drei Punkte wurden beim Live-Test des `v1.0.0`-Release gefunden
(Winterwanderwege grau statt grün, Loipen ohne farbigen Rand bzw. Farbe am
falschen Layer) und gegen die echte openskimap.org-Site verifiziert
(u. a. `openskidata-format`-Quellcode, Live-Screenshot-Vergleich
`feature_id=7edf1c552ccd0cd4362e099e4b5adcaf068ad594` "Loipe Aschau").

## [1.0.0] - 2026-08-11

### Added
- Initiale versionierte Veröffentlichung.
