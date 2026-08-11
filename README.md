# Roadmap: Migration OpenSkiMap zu Plugin-Struktur

Dieses Dokument dient als interaktive Roadmap für den Umbau der OpenSkiMap-Verarbeitung in ein eigenständiges Plugin-Repository.

## 0. Voraussetzungen & Abhängigkeiten

Das Projekt benötigt folgende Programme:
*   `aria2c`
*   `ogr2ogr` (GDAL)
*   `tippecanoe`

Eine detaillierte Liste mit Installationshinweisen findest du in [DEPENDENCIES.md](DEPENDENCIES.md).

Die Abhängigkeiten werden beim Start von `setup.sh`, `run.sh` und `update.sh` automatisch geprüft. Alternativ kann die Prüfung manuell aufgerufen werden:
```bash
bash scripts/check_dependencies.sh
```

## 1. Zukünftiger Standard (Ziel)
Ein spezialisiertes Plugin, das GeoPackages verarbeitet, Layer mit Tippecanoe präzise benennt und eigene Ski-Symbole (Sprites) mitliefert.

### Erwartete Verzeichnisstruktur im Zielzustand:
```text
geodata-openskimap/
├── setup.sh                  # Initialisierung & Abhängigkeitsprüfung
├── run.sh                    # Kompletter Build-Durchlauf (erzwingt Update)
├── update.sh                 # Intelligenter Orchestrator (prüft auf Änderungen vor run.sh)
├── DEPENDENCIES.md
├── sources/                  # Definition der Datenquellen
│   └── openskimap.env
├── scripts/                  # Übernommene Skripte
│   ├── check_dependencies.sh
│   ├── download.sh           # GPKG Download (aria2c --conditional-get)
│   ├── convert.sh            # OGR2OGR & Tippecanoe Logik
│   ├── generate_manifest.py
│   └── ci/                   # Standard CI-Utilities
│       ├── utils.sh          # Bash-Hilfsfunktionen (CI)
│       ├── utils.py          # Python-Hilfsfunktionen (CI)
│       └── run_logger.sh     # JSONL Run-Logging
├── assets/
│   └── sprites/
│       └── openskimap/       # Die Ski-spezifischen Symbole
├── styles/                   # Das MapLibre Stylesheet (openskimap-style.json)
└── dist/                     # Das fertige Ausgabeverzeichnis
    ├── manifest.json         # Deployment-Steuerung
    ├── layer-list.json       # Layer-Metadaten für Legenden-Rendering
    ├── pmtiles/              # Die fertige openskimap.pmtiles
    ├── styles/               # Das finale Stylesheet
    └── assets/
        └── sprites/          # Das openskimap Sprite-Set
```

## 2. Aktueller Status (Vorhandener Code)
Folgende Dateien wurden aus dem alten System in den Ordner `code/` kopiert:
*   `download_openskimap.sh`
*   `convert_openskimap_pmtiles.sh`
*   `ci/utils.sh` (CI Standard)
*   `styles/openskimap-style.json`
*   `assets/sprites/` (noch leer)

## 3. Interaktiver Fahrplan (Schritt für Schritt)

### Schritt 1: Struktur-Vorbereitung
*   [x] Ordner `code/` in `scripts/` umbenennen.
*   [x] Basis-Verzeichnisse (`dist/`, `dist/pmtiles/`, `dist/styles/`, `dist/assets/sprites/`) erstellen.
*   [x] Eine `update.sh` als zentrales Orchestrierungs-Skript anlegen.

### Schritt 2: Download & Asset-Sicherung
*   [x] `download.sh` (ehemals `download_openskimap.sh`) anpassen (Verwendung von `aria2c`).
*   [x] Sicherstellen, dass die Sprites im Repo (`assets/sprites/openskimap/`) abgelegt sind.

### Schritt 3: Tippecanoe-Layer-Mapping (Präzision)
*   [x] `convert.sh` (ehemals `convert_openskimap_pmtiles.sh`) optimieren:
    *   [x] Einsatz von `-L` in Tippecanoe für exakte Layer-Namen.
    *   [x] Entscheidung über minimale Zoom-Level (Bleibt bei 0-14, wie bestätigt).

### Schritt 4: Manifest & Deployment
*   [x] Erstellen der `manifest.json`.
*   [x] Validierung des Stylesheets (Platzhalter für URLs eingefügt).

---
*Status: Alle Schritte der Roadmap abgeschlossen. Das Plugin ist bereit für den Einsatz.*
