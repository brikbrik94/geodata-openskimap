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

## Versionierung & CHANGELOG.md einführen (oe5ith-coding-rules §4)

`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` §4 verlangt eine zentrale
Versionskonstante als Single Source of Truth sowie ein nach Keep-a-Changelog
strukturiertes `CHANGELOG.md` mit datierten `[Unreleased]`-Journal-Blöcken.
Beides existiert in diesem Repo aktuell nicht.

Bewusst zurückgestellt (Entscheidung 2026-08-11): erst die übrigen offenen
Punkte in dieser Datei abarbeiten (Pisten-Kategorien, Nordic-Einfärbung —
`datetime.utcnow()`, Lift-Status, Sprite-Ausrichtung bereits erledigt,
siehe `docs/TODO_ARCHIVE.md`), danach daraus die erste Version schneiden
(Versionskonstante festlegen, `CHANGELOG.md` mit diesem Stand als erstem
Eintrag anlegen) statt jetzt schon rückwirkend eine Changelog-Historie zu
konstruieren. Reihenfolge: TODO-Punkte zuerst,
Versionierung/Changelog danach.
