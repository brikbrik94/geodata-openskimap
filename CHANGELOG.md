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
  *(Korrigiert durch den folgenden Eintrag: die Farbe stand am falschen
  Layer — siehe unten.)*

## [Unreleased] - 2026-08-11 19:45

### Fixed
- Schwierigkeitsfarbe bei Loipen stand am falschen Layer: `ski-runs-nordic-casing`
  (Außenrand) und `ski-runs-nordic-line`/`-ungroomed` (Mittellinie) getauscht.
  Root Cause per systematic-debugging nach Live-Test von Commit `ae5dadf`:
  Auf OpenSkiMap ist die visuelle Konvention bei Loipen umgekehrt zu Pisten
  — der **äußere Rand** trägt die Schwierigkeitsfarbe, die **innere Linie**
  bleibt `lit`-basiert weiß/gelb (nicht umgekehrt wie bei Pisten). Das ist
  die bewusste optische Unterscheidung Loipe vs. Piste, selbst bei gleicher
  Schwierigkeits-Farbpalette. `ski-runs-nordic-casing` bekommt jetzt die
  Schwierigkeits-Match-Expression, `ski-runs-nordic-line`/`-ungroomed` die
  `lit`-Case-Expression zurück. Breiten/Dasharrays/Filter unverändert.

## [1.0.0] - 2026-08-11

### Added
- Initiale versionierte Veröffentlichung.
