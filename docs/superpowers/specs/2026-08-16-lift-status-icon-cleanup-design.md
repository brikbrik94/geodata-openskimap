# Design: Lift-Status-Granularität, Icon-Lücken, Legend-Scale-Fix

## Problem

Analog zum Pisten-Restyling wurde die Lift-Legende (`ski-lifts`) gegen die echten,
AT-gefilterten Daten geprüft (`work/ski_lifts.jsonseq`, 2938 Features, nach dem aktuellen
`convert.sh`-Build). Dabei kamen mehrere Diskrepanzen zwischen Style/Legende und der
tatsächlichen Datenlage zutage:

1. **Toter Code in den Match-Expressions:**
   - `status`-Color-Match (`ski-lifts-line`/`-line-other`/`-line-private`/`-line-private-other`,
     4 Vorkommen) hat einen `"planned"`-Zweig. Die echten Daten kennen nur `operating` (2799),
     `disused` (74), `abandoned` (43), `proposed` (18), `construction` (4) — `"planned"` kommt
     nirgends vor.
   - `lift_type`-Icon-Match (`ski-lifts-icons`) hat `t_bar`/`j_bar`-Zweige (Unterstrich). Die
     echten Daten verwenden ausschließlich die Bindestrich-Schreibweise `t-bar` (628)/`j-bar`
     (16) — die Unterstrich-Varianten kommen nie vor.

2. **Icon-Lücke (Unterversorgung, nicht totes Match):** `lift_type` hat 12 reale Werte;
   `mixed_lift` (17 Features, z. B. "Sternstein Express", "Kombibahn Penken") und `railway`
   (2 Features, "Bayerische Zugspitzbahn") fehlen im `icon-image`-Match komplett und fallen auf
   den Default-Zweig `ski-gondola` zurück — für `railway` (Zahnradbahn) fachlich irreführend.

3. **Status-Granularität zu grob:** Die Legende zeigt aktuell nur 2 Stufen ("In Betrieb" /
   "Sonstiger Status"), obwohl "Sonstiger Status" zwei inhaltlich sehr unterschiedliche Zustände
   zusammenwirft: `proposed`+`construction` (22 Features, "existiert noch nicht") vs.
   `disused`+`abandoned` (117 Features, "existiert nicht mehr"). Visuell sind beide identisch
   (gleiche Farbe `hsl(0, 53%, 42%)`, gleicher Dasharray `[1, 3]`).

4. **`ski-lift-status-v1`-Legend-Scale ist strukturell kaputt** (verifiziert gegen
   `dist/layer-list.json`): Jede der drei Legend-Zeilen (`In Betrieb`/`Sonstiger Status`/
   `Privat`) referenziert `{"mode": "scale", "scale_id": "ski-lift-status-v1"}`. Diese eine
   Scale enthält aber **alle 7** Match-Branches unstrukturiert (`Operating`, `Proposed`,
   `Planned`, `Construction`, `Disused`, `Abandoned`, `Sonstige` — unübersetzt, Titel-Case aus
   dem rohen `match`-Key), mit Dubletten (3× `hsl(0, 82%, 42%)`, 3× `hsl(0, 53%, 42%)`). Ein
   Konsument, der die `In Betrieb`-Zeile rendert, bekäme fälschlich auch `Disused`/`Abandoned`
   mit angezeigt. Ursache: `extract_categorized_items` parst die volle `match`-Expression eines
   Layers, unabhängig davon, dass der Layer durch sein `filter` bereits auf einen Status-Teil
   eingeschränkt ist — die Match-Branches jenseits des Filters sind für diesen Layer gar nicht
   erreichbar, verschmutzen aber die extrahierte Scale.

5. **`access`-Kreuzung mit Status:** `private` kombiniert mit einem Nicht-`operating`-Status
   kommt nur 1×  vor (`private`+`disused`); `private`+`proposed`/`construction`/`abandoned`
   kommt nie vor (verifiziert: 2764× `(None, operating)`, 73× `(None, disused)`, 43× `(None,
   abandoned)`, 35× `(private, operating)`, 18× `(None, proposed)`, 4× `(None, construction)`,
   1× `(private, disused)`). Eine 3-stufige Aufsplittung des `access`-Zweigs analog zu Punkt 3
   brächte hier keine Information.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-16)

### Baustein 1 — Toten Code entfernen

`"planned"` raus aus allen 4 `status`-Color-Match-Expressions. `t_bar`/`j_bar` raus aus dem
`lift_type`-Icon-Match. Kein Verhaltensunterschied für echte Daten (beide Zweige waren
unerreichbar), reine Aufräumarbeit — analog zum Entfernen von `expert`/`extreme` beim
Difficulty-Remap.

### Baustein 2 — Status: 3 Stufen statt 2, als Filter statt Match

Ersetzt die bisherige `match`-Expression-basierte Färbung (ein Layer, alle Status-Werte als
Branches, obwohl der Layer durch sein `filter` schon auf einen Teil eingeschränkt ist) durch
eine echte 3-Wege-Aufteilung auf Filter-Ebene — behebt gleichzeitig Baustein 4 (Legend-Scale),
weil jeder Layer danach nur noch einen fixen Wert statt eines Matches führt:

- **In Betrieb** (`status == "operating"`, 2799 Features) — unverändert: Casing (weiß) +
  `hsl(0, 82%, 42%)`, durchgezogen.
- **Geplant / Im Bau** (`status in ["proposed", "construction"]`, 22 Features) — neu:
  `hsl(210, 70%, 45%)` (Blau, signalisiert "noch nicht real, andere Bedeutung als Rot"),
  Dasharray `[4, 2]` (länger gestrichelt, visuell von "Außer Betrieb" unterscheidbar), keine
  Casing.
- **Außer Betrieb** (`status in ["disused", "abandoned"]`, 117 Features) — bestehende Farbe
  `hsl(0, 53%, 42%)`, bestehender Dasharray `[1, 3]`, keine Casing. Visuell identisch zum
  bisherigen "Sonstiger Status", nur ohne die `proposed`/`construction`-Beimischung.

Betroffene Style-Layer: `ski-lifts-line-other` wird zu zwei Layern
(`ski-lifts-line-planned`, `ski-lifts-line-disused`), jeweils mit fixer `line-color` statt
`match`. `ski-lifts-line`/`-casing` (In Betrieb) bleiben strukturell wie sie sind, nur die
`match`-Expression wird durch den Literalwert `hsl(0, 82%, 42%)` ersetzt (Filter grenzt bereits
exklusiv auf `operating` ein).

### Baustein 3 — Privat bleibt unverändert

`ski-lifts-line-private`/`-line-private-other` bleiben bei der bisherigen 2-Wege-Aufteilung
(`operating` vs. `!= operating`), keine 3-Stufen-Aufsplittung. Begründung: nur 1 von 2938
Features fällt in "privat + nicht operating", eine feinere Unterteilung hätte keinen
erkennbaren Nutzen. Deren `match`-Expression wird ebenso durch feste Literalwerte ersetzt
(gleiche Farben wie In-Betrieb/Außer-Betrieb).

### Baustein 4 — `ski-lift-status-v1`-Scale entfernen

Mit Baustein 2/3 hat kein Lift-Layer mehr eine kategorisierte `line-color` — alle sind `fixed`.
`GROUP_LEGEND_SCALE["ski-lifts"]` und `LEGEND_SCALE_LABELS["ski-lift-status-v1"]` werden aus
`scripts/generate_layer_list.py` entfernt; `dist/layer-list.json`s `legend_sections` verliert den
`ski-lift-status-v1`-Eintrag komplett. Die Status-Bedeutung ist weiterhin über die
`variants[].label`-Strings (`In Betrieb`/`Geplant / Im Bau`/`Außer Betrieb`/`Privat`) plus
`color.value` pro Zeile abgedeckt — kein Informationsverlust, nur keine fälschlich geteilte Scale
mehr.

`GROUP_VARIANTS["ski-lifts"]`'s `"status"`-Achse bekommt einen dritten Eintrag
(`Geplant / Im Bau`, referenziert `ski-lifts-line-planned`), der bisherige `"Sonstiger Status"`-
Eintrag wird zu `"Außer Betrieb"` (referenziert `ski-lifts-line-disused` statt
`ski-lifts-line-other`).

### Baustein 5 — `mixed_lift`-Icon: zwei versetzte Symbol-Layer

`mixed_lift` (17 Features) ist in OpenSkiMap ein echtes Hybrid-Konzept (kombinierte
Gondel-/Sesselbahn), kein Datenfehler — es gibt kein singuläres treffendes Icon dafür, und
OpenSkiMap selbst unterscheidet nicht, welcher Streckenabschnitt Gondel- vs. Sesselkabinen
fährt. Statt eines neuen Sprite-Assets: zwei zusätzliche `symbol`-Layer, beide gefiltert auf
`lift_type == "mixed_lift"`, `symbol-placement: "line"` mit derselben `symbol-spacing` wie
`ski-lifts-icons`, aber mit `icon-offset` senkrecht zur Linie versetzt — einer zeigt
`ski-gondola` (z. B. `icon-offset: [0, -8]`), der andere die bestehende Occupancy-basierte
Chairlift-Icon-Auswahl (z. B. `icon-offset: [0, 8]`). Beide nutzen ausschließlich vorhandene
Sprites. `ski-lifts-icons`' bestehendes Match verliert den `mixed_lift`-Zweig (fällt sonst
zusätzlich zum Icon-Paar auf den Default `ski-gondola` zurück) — wird stattdessen exklusiv von
den zwei neuen Layern abgedeckt (`ski-lifts-icons` bekommt einen `lift_type != "mixed_lift"`-
Filter, um Doppel-Icons zu vermeiden).

### Baustein 6 — `railway` zurückgestellt

Nur 2 Features (`Bayerische Zugspitzbahn`, doppelt vorhanden — vermutlich Linie+Kreuzung
desselben Ways oder zwei Segmente). Kein akuter Handlungsbedarf; bekommt vorerst weiterhin
`ski-gondola` als Default-Icon (unverändert). Wird als `docs/ROADMAP.md`-Punkt festgehalten:
eigenes Zahnradbahn-Icon (`railway`) als neues Sprite-Asset, analog zum bereits offenen
Übungswiesen-Sprite-Punkt.

## Out of Scope

- `lift_type`-Icons als eigene Legend-Zeilen (analog Grooming bei Pisten) — laut Nutzer noch
  offen, da erst im `GEODATA_PLUGIN_STANDARD.md` definiert und auf der konsumierenden Website
  getestet werden muss, ob variantenreiche Icon-Legenden praktikabel sind. Kommt als
  `docs/TODO.md`-Punkt, kein Teil dieses Designs.
- Neues Sprite-Icon für `railway` (siehe Baustein 6) — `docs/ROADMAP.md`-Punkt.
- `occupancy`/`capacity`/`duration` — keine Style-/Legend-Relevanz identifiziert, keine
  Aktion nötig.
