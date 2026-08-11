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
  Kategorie. Ursache: `openskidata-format`s Farblogik ist grundsätzlich
  schwierigkeitsbasiert. Gefunden beim Live-Test des `v1.0.0`-Release
  (Winterwanderwege grau statt grün, Loipen ohne farbigen Flächenrand).
  *(Korrigiert durch den folgenden Eintrag: dass nur nordics Linie
  lit-basiert speziell behandelt sei, war eine falsche Annahme an dieser
  Stelle — siehe unten.)*

## [Unreleased] - 2026-08-11 16:20

### Fixed
- `ski-runs-nordic-line`/`-ungroomed` färben wieder nach Schwierigkeit
  statt der `lit`-basierten Weiß/Gelb-Logik. Per Live-Vergleich mit
  openskimap.org (Screenshots, `feature_id=7edf1c552ccd0cd4362e099e4b5adcaf068ad594`
  "Loipe Aschau", `difficulty=easy`) bestätigt: die echte Seite färbt
  Loipen nach Schwierigkeit (blau für "easy"), nicht `lit`-basiert weiß —
  im Widerspruch zur statischen `terrain_v2.json`-Style-Datei (die nur
  `lit`-basierte Weiß/Gelb-Werte für `nordic-runs`/`-ungroomed` zeigt) und
  zur ursprünglichen, vor dieser Session dokumentierten TODO-Prämisse
  ("Loipen nicht nach Schwierigkeit einfärben"). `ski-runs-nordic-casing`
  bleibt bewusst `lit`-basiert — `ski-runs-downhill-casing` (das Vorbild)
  ist ebenfalls `lit`-basiert, nicht schwierigkeitsgefärbt.

## [1.0.0] - 2026-08-11

### Added
- Initiale versionierte Veröffentlichung.
