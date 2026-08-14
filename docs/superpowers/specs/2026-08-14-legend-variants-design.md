# Design: Sich gegenseitig ausschließende Legenden-Varianten (`variants`)

## Problem

Beim Bau des Legenden-Parsers in einem Downstream-Konsumenten (website-v3) hat sich gezeigt,
dass ein naives Rendering von `render[]` für mehrere Gruppen falsche Legenden-Vorschauen
erzeugt: Style-Layer, die sich in Wirklichkeit **gegenseitig ausschließen** (nie gleichzeitig
für dasselbe Feature zutreffen, siehe MapLibre `filter`), werden im aktuellen Schema
gleichrangig in einem einzigen `render`-Array gelistet. Ein Konsument, der `render[]` einfach
der Reihe nach übereinander zeichnet, stapelt sie — bei `ski-runs-nordic` z. B. die durchgezogene
("gespurt") und die strichlierte ("ungespurt") Linie exakt an derselben Stelle, wodurch die
gestrichelte Variante unsichtbar wird bzw. die Legende nicht zwischen beiden Präparierungsstufen
unterscheiden kann. Bei `ski-lifts` betrifft es analog die vier Status/Zugangs-Varianten.

Das `render`/`Part`-Modell (GEODATA_PLUGIN_STANDARD.md v2.0.0 §5.3) bildet nur `paint`/`layout`
ab, nie `filter` — genau das Feld, das in der echten Karte entscheidet, welcher Layer für ein
konkretes Feature überhaupt zutrifft. Das ist eine Lücke im Standard selbst (gleicher
Charakter wie die bereits gemeldete `circle-stroke`-Lücke,
[geodata-plugin-standard#3](https://github.com/brikbrik94/geodata-plugin-standard/issues/3)),
nicht ein Bug in der Extraktion dieses Repos.

## Untersuchung

Alle `filter`-Ausdrücke der drei betroffenen Gruppen wurden gegen
`styles/openskimap-style.json` verifiziert (vollständiger Dump, siehe Session-Log):

### `ski-runs-nordic` — sauber binär

| Style-Layer | Filter | Klassifikation |
|---|---|---|
| `-fill`, `-casing` | `null` | geteilt (jede Variante) |
| `-line` | `grooming NOT IN (backcountry, mogul)` | Variante "Gespurt" |
| `-ungroomed` | `grooming IN (backcountry, mogul)` | Variante "Ungespurt" |
| `-snowmaking` | `snowmaking OR snowfarming` | **ausgeschlossen** (siehe Entscheidung 3) |
| `-labels` | `has(name)` | geteilt (Filter testet nicht die Partitions-Property) |

→ 2 Varianten, keine Überschneidung.

### `ski-runs-downhill` — 4 Varianten, ein Layer kann zu mehreren gehören

| Style-Layer | Filter | Klassifikation |
|---|---|---|
| `-fill`, `-casing` | `null` | geteilt |
| `-line` | `NOT gladed AND grooming NOT IN (backcountry, mogul)` | Variante "Präpariert" |
| `-gladed` | `gladed == true` | Varianten "Waldabfahrt" **und** "Waldabfahrt, nicht präpariert" |
| `-ungroomed` | `grooming IN (backcountry, mogul)` | Varianten "Nicht präpariert" **und** "Waldabfahrt, nicht präpariert" |
| `-snowmaking` | `snowmaking OR snowfarming` | **ausgeschlossen** |
| `-labels` | `has(name)` | geteilt |

`gladed` und `ungroomed` schließen sich in den echten Filtern **nicht** gegenseitig aus (beide
Bedingungen können gleichzeitig zutreffen) — daher landet der `-gladed`-Layer sowohl in der
reinen "Waldabfahrt"-Variante als auch in der Kombi-Variante, analog `-ungroomed`. Nutzer-Entscheidung
2026-08-14: alle 4 real vorkommenden Kombinationen werden als eigene Varianten abgebildet (nicht nur 3).

### `ski-lifts` — 4 Varianten, `casing` ist KEIN reiner Shared-Layer

| Style-Layer | Filter | Klassifikation |
|---|---|---|
| `-casing` | `status == "operating"` | Varianten "In Betrieb" **und** "In Betrieb (privat)" |
| `-line` | `access != private AND status == operating` | Variante "In Betrieb" |
| `-line-other` | `access != private AND status != operating` | Variante "Sonstiger Status" |
| `-line-private` | `access == private AND status == operating` | Variante "In Betrieb (privat)" |
| `-line-private-other` | `access == private AND status != operating` | Variante "Sonstiger Status (privat)" |
| `-labels` | `has(name) OR has(ref)` | geteilt |
| `-icons` | `null` | geteilt |

Wichtiger Fund: `ski-lifts-casing` hat selbst einen Filter (`status == "operating"`) — die
weiße Casing-Linie gilt **nur** für die beiden "In Betrieb"-Varianten, nicht für die beiden
"Sonstiger Status"-Varianten. Vor dieser Untersuchung wurde `casing` fälschlich als
bedingungslos geteilt angenommen (so auch in der aktuellen v2.0-Implementierung, die `filter`
komplett ignoriert). Die Status-**Farbe** (`ski-lift-status-v1`-Skala) bleibt davon unberührt —
sie gruppiert die sechs `status`-Werte anders (hell: operating/proposed/planned/construction,
dunkel: disused/abandoned) als die Varianten-Partition (operating vs. alles andere); beide
Mechanismen sind unabhängig voneinander korrekt.

## Entscheidungen (mit Nutzer abgestimmt, 2026-08-14)

1. **Auflösung server-seitig**: `layer-list.json` liefert fertig gruppierte, unabhängig
   renderbare Varianten statt roher `filter`-Ausdrücke — Downstream-Konsumenten müssen keine
   MapLibre-Filter-Semantik interpretieren.
2. **Alle drei Gruppen** (Loipen, Lifte, Pisten) in einem Zug, nicht nur die zwei akut
   gemeldeten (Loipen, Lifte) — gleicher Mechanismus, eine Iteration.
3. **`snowmaking` wird komplett aus der automatischen Aufteilung herausgenommen** (weder
   geteilt noch eigene Variante) — passt nicht ins Schema "geteilt (immer) vs. Variante (genau
   eine oder mehrere, aber binär bekannt)", da es ein unabhängiger Zusatz-Marker ist, der mit
   jeder Präparierungsstufe gleichzeitig auftreten kann. Separate Behandlung (z. B. ein
   drittes, orthogonales Overlay-Konzept) bewusst zurückgestellt, als `docs/TODO.md`-Eintrag
   festgehalten.
4. **Pisten: 4 Varianten** (nicht 3) — auch die seltene Gladed+Ungroomed-Kombination bekommt
   eine eigene Legenden-Zeile, vollständige Abdeckung aller real vorkommenden Zustände.
5. **Lokale Umsetzung als explizite Config** (`GROUP_VARIANTS`), nicht als generischer
   Filter-Kompatibilitäts-Algorithmus — konsistent mit dem bestehenden Muster
   (`GROUP_MAP`/`GROUP_LEGEND_SCALE` sind ebenfalls von Hand verifizierte, harte Zuordnungen).
   Ein generischer Beweis der gegenseitigen Ausschließlichkeit beliebiger MapLibre-Filter ist im
   Allgemeinen nicht handhabbar; für die drei hier vorkommenden, konkreten Filterformen reicht
   eine von Hand verifizierte Zuordnung.
6. **Varianten-Labels** (deutsch, siehe Untersuchungstabellen oben): "Gespurt"/"Ungespurt";
   "Präpariert"/"Waldabfahrt"/"Nicht präpariert"/"Waldabfahrt, nicht präpariert"; "In
   Betrieb"/"Sonstiger Status"/"In Betrieb (privat)"/"Sonstiger Status (privat)" — "Sonstiger
   Status" in Anlehnung an die bestehende "Sonstige"-Fallback-Konvention dieses Repos.

## Standard-Vorschlag (Issue an `geodata-plugin-standard`)

Analog zu Issue #3: kein bindender Strukturvorschlag, aber eine naheliegende, konsistente
Erweiterung als Diskussionsgrundlage. `Group` (§5.3) bekommt ein neues, optionales Feld:

```
"variants": Array<{ "label": String, "render": Array<Part> }> | null
```

- `render` (bestehend) ändert semantisch zu "Parts, die für **jede** Variante der Gruppe
  gemeinsam gelten" — für Gruppen ohne das Phänomen (die meisten) bleibt `render` einfach die
  vollständige, unveränderte Liste wie bisher, `variants` ist `null`.
- Jeder `variants[]`-Eintrag repräsentiert einen von mehreren **gegenseitig ausschließenden**
  visuellen Zuständen. Ein Konsument rendert `group.render` (geteilt) **plus** genau einen
  `variant.render` gleichzeitig — z. B. eine Legenden-Zeile pro Variante.
- Rein additiv, keine Breaking-Change-Semantik für bestehende Konsumenten/Gruppen ohne
  Varianten → Vorschlag: Minor-Version (z. B. 2.0 → 2.1), keine Major-Version.
- Wie beim `render`-Modell selbst: die Erkennung/Gruppierung der Varianten aus `filter` bleibt
  Sache der Referenz-Implementierung, der Standard schreibt nur die Ausgabeform vor.

## Neue Bausteine (`scripts/generate_layer_list.py`)

```python
# group key -> Liste von {"label": ..., "style_layer_ids": [...]}. Eine Style-Layer-ID kann in
# mehreren Varianten auftauchen (siehe Design-Doc, ski-lifts-casing/-gladed/-ungroomed). Nicht
# gelistete, nicht in GROUP_VARIANT_EXCLUDE stehende Style-Layer-IDs der Gruppe bleiben im
# geteilten render.
GROUP_VARIANTS = {
    "ski-runs-nordic": [
        {"label": "Gespurt", "style_layer_ids": ["ski-runs-nordic-line"]},
        {"label": "Ungespurt", "style_layer_ids": ["ski-runs-nordic-ungroomed"]},
    ],
    "ski-runs-downhill": [
        {"label": "Präpariert", "style_layer_ids": ["ski-runs-downhill-line"]},
        {"label": "Waldabfahrt", "style_layer_ids": ["ski-runs-downhill-gladed"]},
        {"label": "Nicht präpariert", "style_layer_ids": ["ski-runs-downhill-ungroomed"]},
        {"label": "Waldabfahrt, nicht präpariert",
         "style_layer_ids": ["ski-runs-downhill-gladed", "ski-runs-downhill-ungroomed"]},
    ],
    "ski-lifts": [
        {"label": "In Betrieb", "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line"]},
        {"label": "Sonstiger Status", "style_layer_ids": ["ski-lifts-line-other"]},
        {"label": "In Betrieb (privat)",
         "style_layer_ids": ["ski-lifts-casing", "ski-lifts-line-private"]},
        {"label": "Sonstiger Status (privat)", "style_layer_ids": ["ski-lifts-line-private-other"]},
    ],
}

# group key -> Style-Layer-IDs, die aus render UND variants ausgeschlossen werden (siehe
# Entscheidung 3 — unabhängige Zusatz-Marker, noch kein eigenes Konzept dafür).
GROUP_VARIANT_EXCLUDE = {
    "ski-runs-nordic": ["ski-runs-nordic-snowmaking"],
    "ski-runs-downhill": ["ski-runs-downhill-snowmaking"],
}
```

`build_layer_list` (bzw. eine neue `_build_variants(group_layers, group_key)`-Funktion)
verändert die Gruppen-Erzeugung:

1. Für jede Gruppe: Style-Layer-IDs aus `GROUP_VARIANT_EXCLUDE[group_key]` vollständig aus
   `group_layers` herausfiltern, bevor irgendetwas anderes passiert.
2. Für jede in `GROUP_VARIANTS[group_key]` gelistete Variante: `render` per
   `_build_render` aus genau den gelisteten Style-Layer-IDs bauen (gleiche Part-Extraktion wie
   bisher, nur über eine gefilterte Teilliste von `group_layers`).
3. `group["render"]` (geteilt) enthält nur noch die Style-Layer, die in **keiner** Varianten-Liste
   auftauchen (Mengendifferenz `group_layers` minus Vereinigung aller `style_layer_ids` in
   `GROUP_VARIANTS[group_key]`).
4. `group["variants"]` = `null`, wenn `group_key` nicht in `GROUP_VARIANTS` — für alle anderen
   fünf Gruppen (`ski-areas-alpine/-nordic`, `ski-runs-skitour/-other`, `ski-spots`) ändert sich
   nichts.
5. `scale_items`/`legend_sections`-Sammlung (bestehender Mechanismus) läuft unverändert über
   **alle** Parts, egal ob sie in `render` oder in einem `variants[].render` landen — eine
   kategorisierte Farbe in einer Variante referenziert dieselbe zentrale Skala wie bisher.

## Tests

- `_build_variants`/die Gruppen-Aufteilung: pro Gruppe (Loipen/Pisten/Lifte) gegen den echten
  Style verifizieren — Anzahl Varianten, Labels, welche Style-Layer-IDs in welcher Variante
  landen (insbesondere `ski-lifts-casing` in genau 2 von 4, `ski-runs-downhill-gladed`/
  `-ungroomed` je in 2 von 4).
- Regressionstest: `ski-runs-nordic-snowmaking`/`ski-runs-downhill-snowmaking` erscheinen weder
  in `render` noch in irgendeiner Variante.
- Regressionstest: Gruppen ohne `GROUP_VARIANTS`-Eintrag (`ski-areas-alpine`, `ski-spots`, …)
  haben `variants: null`, `render` unverändert wie vor dieser Änderung.
- `legend_sections` unverändert (3 Skalen wie nach der v2.0-Migration) — Varianten ändern nichts
  an der Skalen-Sammlung.

## Betroffene Dateien

- `scripts/generate_layer_list.py` — `GROUP_VARIANTS`/`GROUP_VARIANT_EXCLUDE`-Konstanten, neue
  `_build_variants`, `build_layer_list`-Anpassung.
- `scripts/test_generate_layer_list.py` — neue Tests.
- `CHANGELOG.md` — neuer Eintrag (lokale Erweiterung über den Standard hinaus, bis dieser
  nachzieht — analog zur Dokumentation der `circle-stroke`-Lücke).
- `docs/TODO.md` — Eintrag für die zurückgestellte `snowmaking`-Behandlung.
- Neues GitHub-Issue in `geodata-plugin-standard` (siehe oben), analog Issue #3.

**Nicht betroffen:** `scripts/layer_metadata_extractor.py` (keine neuen Extraktionsfunktionen
nötig — `_build_render` wird lediglich mit gefilterten Teillisten wiederverwendet),
`styles/openskimap-style.json`, `scripts/generate_manifest.py`.

## Versionsfeld

`"version"` in `layer-list.json` bleibt `"2.0"`. `variants` ist eine lokale Erweiterung über
den Standard hinaus (bis dieser das Feld offiziell aufnimmt, siehe Issue), aber rein additiv —
bricht nichts für Konsumenten, die das Feld nicht kennen und ignorieren. Kein Grund für eine
repo-eigene Versionskennzeichnung.
