# OpenSkiMap Plugin - Projekt-Kontext

Dieses Dokument dient als Orientierungshilfe für Gemini CLI. Anweisungen hier haben Vorrang vor Standard-Workflows.

Bevor du nach den hier ergänzten, repo-spezifischen Angaben handelst: lies zuerst
`oe5ith-coding-rules/AGENT_INSTRUCTIONS.md` (Submodul) vollständig — die dortigen
Mandate sind verbindlich und werden hier nicht wiederholt.

## Projektziel
Transformation von OpenSkiMap GeoPackage-Daten in optimierte PMTiles und Bereitstellung eines MapLibre-kompatiblen Stylesheets inklusive Sprites.

## Kern-Workflow
Drei Einstiegspunkte nach `geodata-plugin-standard` (Submodul, §1 "Dreifaltigkeit"):
- **`setup.sh`:** Initialisierung & Abhängigkeitsprüfung (einmalig/bei Bedarf).
- **`run.sh`:** Kompletter Build-Durchlauf, erzwingt Update. Phasen:
  1. `check_dependencies.sh`: Prüfung der System-Tools.
  2. `download.sh`: Download via `aria2c` (conditional get, Quelle: `sources/openskimap.env`).
  3. `convert.sh`: Layer-Extraktion via `ogr2ogr` und Tile-Generierung via `tippecanoe`.
  4. **Deployment:** Finalisierung der Daten im `dist/`-Ordner (`generate_manifest.py`).
- **`update.sh`:** Intelligenter Orchestrator — prüft per Download-Check, ob sich die
  Upstream-Daten seit dem letzten erfolgreichen Build geändert haben, und ruft `run.sh`
  nur dann auf. Beide Skripte schreiben zusätzlich JSONL-Run-Logs (`scripts/ci/run_logger.sh`,
  siehe `geodata-plugin-standard/GEODATA_PLUGIN_STANDARD.md` §7).

## Wichtige Abhängigkeiten
- **aria2c:** Download-Client.
- **GDAL/ogr2ogr:** Vektordaten-Verarbeitung.
- **Tippecanoe:** Erstellung von Vector Tiles (Zoom 0-14).

## Speicherung von Erinnerungen (Memory)
Ich nutze das `save_memory`-Tool, um projektspezifische oder globale Fakten dauerhaft zu speichern. Diese werden **nicht** im Repository committet:

1.  **Project Scope (`project`):** 
    - Speichert lokale Pfade, spezifische Entwicklungs-Workflows oder projektspezifische Präferenzen.
    - Speicherort: Privat im Workspace des Nutzers (meist unter `.gemini/project.json` im Home- oder Projektverzeichnis, vom System verwaltet).
2.  **Global Scope (`global`):** 
    - Speichert allgemeine Vorlieben (z. B. Sprachpräferenzen, bevorzugte Code-Styles).
    - Speicherort: Globales Konfigurationsverzeichnis von Gemini CLI auf diesem System.

## Konventionen
- **Bash:** Alle Skripte nutzen `set -e` (oder `set -euo pipefail`) und laden die `scripts/ci/utils.sh` für ein konsistentes Logging.
- **Doku:** Neue Abhängigkeiten oder Programmänderungen müssen in `DEPENDENCIES.md` nachgepflegt werden.
