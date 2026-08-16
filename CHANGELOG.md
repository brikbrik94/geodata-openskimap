# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  `ski-runs-nordic` — löst die seit 2026-08-14 zurückgestellte Lücke (siehe `docs/TODO.md`).
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
