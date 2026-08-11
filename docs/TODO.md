# TODO

Offene Punkte für kommende Iterationen des Styles/der Konvertierung. Nicht
umgesetzt, nur dokumentiert.

## Referenz: echtes OpenSkiMap-Stylesheet

Alle Punkte unten sind gegen das tatsächliche, produktive Stylesheet von
openskimap.org verifiziert (nicht geraten):

- Homepage lädt `https://openskimap.org/assets/index-*.js`, darin referenziert:
  `https://tiles.openskimap.org/styles/terrain_v2.json` und `.../satellite_v2.json`.
- Lokal gesichert unter `/tmp/openskimap_terrain_style.json` (Session-Snapshot,
  nicht Teil des Repos — bei Bedarf per curl neu laden, URL s.o.).
- `line-color: ["get", "color"]` bei den meisten Lauf-/Lift-Layern bedeutet:
  OpenSkiMap berechnet die Farbe serverseitig (in ihrer `openskidata`-Pipeline)
  und liefert sie als fertiges Feature-Property aus — nicht per Client-seitiger
  match/case-Expression wie bei uns. Die eigentlichen Farbwerte pro
  Schwierigkeit/Status dürften trotzdem mit unserer Task-5-Tabelle
  übereinstimmen (dort ebenfalls aus `openskidata-format` übernommen); die
  Lücken unten sind strukturell (welche Layer/Kategorien es gibt), nicht bei
  den Farbwerten selbst.

## Lift-Status visuell unterscheiden (operating vs. alles andere)

Echtes Stylesheet, zwei Layer statt unserer einen:

- `operating-lift`: Filter `status == operating AND access != private`.
  Durchgezogen, `line-opacity: 0.8`.
- `other-lift`: Filter `status != operating` (deckt proposed/planned/
  construction/disused/abandoned in einem Rutsch ab). **Gestrichelt
  `line-dasharray: [1, 3]`**, dünner (`line-width` Faktor ~0.66 von operating).

Bei uns (`styles/openskimap-style.json`, `ski-lifts-line`) rendern
`operating`/`proposed`/`planned`/`construction` alle identisch, durchgezogen.

Beispiel: `feature_id=84b8d675587243994b24ee9b7e0aa4629a6e54f6`
("Steyrsbergerreithbahn", `status=proposed`, `lift_type=gondola`).

Betrifft `ski-lifts-line`/`ski-lifts-line-private`/`ski-lifts-casing`.

## Pisten-Kategorien: downhill / nordic / skitour / other statt nur alpine/nordic

Echtes Stylesheet nutzt **vier** Kategorien pro Lauf-Feature (nicht zwei wie
unser Alpine/Nordic-Split), jede mit eigenem Layer + Dash-Pattern, per
`["has", "<kategorie>"]`-Flag (serverseitig vorberechnet, vermutlich
Mehrfachzuordnung möglich):

- `downhill-runs`: `has downhill`, durchgezogen, schwierigkeitsgefärbt.
- `nordic-runs`: `has nordic` — **keine Schwierigkeitsfarbe**, nur
  casing-artiges Weiß/Gelb(falls `lit`). Loipen haben im Datensatz meist gar
  keine `difficulty` (Beispiel unten: `difficulty=null`).
- `skitour-runs`: `has skitour`, gestrichelt `[3, 6]`.
- `other-runs`: `has other` — Sammeltopf für alles, was in keine der drei
  obigen Kategorien fällt (Rodelbahnen, Winterwanderwege, vermutlich auch
  `fatbike`/`ice_skate`/`playground`/`sleigh`/`snow_park`). Gestrichelt `[3, 3]`.

Bei Mehrfachnutzung (z.B. `uses=downhill,skitour`) zeichnet OpenSkiMap **mehrere
parallel versetzte Linien** (`line-offset`, eine pro zutreffender Kategorie),
statt wie bei uns eine Linie mit einer einzigen gewählten Farbe/Filterpriorität.

Zwei Lücken bei uns dadurch bestätigt:

1. **Rodelbahn nicht gestrichelt.** `feature_id=3d4a993682eda4d6b4b318d83fc3178819d74d0e`
   ("Gaisberg", `uses=sled`, sonst nichts) — bei uns aktuell im
   Alpine-Katalog (`uses NOT LIKE '%nordic%'`-Catchall), durchgezogen,
   Schwierigkeitsfarbe (meist grauer Fallback, da `difficulty` oft leer).
   Auf OpenSkiMap: `other`-Kategorie, gestrichelt `[3,3]`.
2. **Winterwanderweg nicht erkennbar.** `feature_id=62ad174f8ac9d72c286582fd5d680ba007ea795f`
   ("Hannenkamm", `uses=hike`) — landet bei uns ebenfalls unmarkiert im
   Alpine-Katalog statt in `other`.

`uses` ist ein Mehrfachwert-Feld, volle Taxonomie im aktuellen Datensatz:
`downhill`, `nordic`, `skitour`, `hike`, `sled`, `connection`, `fatbike`,
`ice_skate`, `playground`, `sleigh`, `snow_park`. Bei Umsetzung klären, welche
davon OpenSkiMaps `other`-Bucket zugeordnet werden (vermutlich alle außer
downhill/nordic/skitour/connection).

Betrifft `scripts/convert.sh` (WHERE-Klauseln/Source-Layer neu denken — evtl.
weg vom reinen Alpine/Nordic-Split hin zu den vier echten Kategorien),
`styles/openskimap-style.json` (neue Layer-Gruppe(n)), `scripts/generate_layer_list.py`
(`GROUP_MAP` erweitern).

## Loipen (nordic) nicht nach Schwierigkeit einfärben

Siehe oben — OpenSkiMap färbt `nordic-runs` nicht nach Schwierigkeit
(nur casing-artiges Weiß/gelb bei `lit`). Wir haben in Task 6 die komplette
Alpine-Schwierigkeitsfarblogik 1:1 auf Nordic gespiegelt (`ski-runs-nordic-*`
in `styles/openskimap-style.json`) — das war laut echtem Stylesheet so nicht
vorgesehen. Beispiel: `feature_id=6a6a6f940d135a95cf034a6e7ca99563a5364bd0`
(`uses=nordic`, `difficulty=null`).

Hängt mit dem Punkt oben zusammen — beim Überarbeiten der Pisten-Kategorien
gleich mitentscheiden, ob/wie stark `ski-runs-nordic-line` etc. vereinfacht
werden.

## Ausrichtung der Sprites prüfen

Sprite-Ausrichtung (Icons) aktuell nicht korrekt — genauer eingrenzen,
welche Icons/Layer betroffen sind und was konkret falsch ausgerichtet ist.
