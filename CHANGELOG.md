# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-08-11 14:07

### Fixed
- `ski-runs-nordic-fill`, `ski-runs-skitour-{fill,line,labels}` und
  `ski-runs-other-{fill,line,labels}` färben jetzt wie im echten
  OpenSkiMap-Stylesheet nach Schwierigkeit ein (dieselbe Match-Expression
  wie `ski-runs-downhill-*`) statt einer erfundenen Volltonfarbe pro
  Kategorie. Ursache: `openskidata-format`s Farblogik ist rein
  schwierigkeitsbasiert, unabhängig von der Nutzungskategorie — nur
  `nordic`s *Linie* (nicht Fläche) ist mit einer fixen `lit`-basierten
  Weiß/Gelb-Farbe speziell behandelt. Gefunden beim Live-Test des
  `v1.0.0`-Release (Winterwanderwege grau statt grün, Loipen ohne
  farbigen Flächenrand).

## [1.0.0] - 2026-08-11

### Added
- Initiale versionierte Veröffentlichung.
