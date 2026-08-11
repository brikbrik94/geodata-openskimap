# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
