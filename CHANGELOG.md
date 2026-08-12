# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
