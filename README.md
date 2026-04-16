# Roadmap: Migration OpenSkiMap zu Plugin-Struktur

Dieses Dokument dient als interaktive Roadmap für den Umbau der OpenSkiMap-Verarbeitung in ein eigenständiges Plugin-Repository.

## 1. Zukünftiger Standard (Ziel)
Ein spezialisiertes Plugin, das GeoPackages verarbeitet, Layer mit Tippecanoe präzise benennt und eigene Ski-Symbole (Sprites) mitliefert.

### Erwartete Verzeichnisstruktur im Zielzustand:
```text
geodata-openskimap/
├── update.sh                 # Zentraler Einstiegspunkt
├── scripts/                  # Übernommene Skripte
│   ├── download.sh           # GPKG Download (aria2c --conditional-get)
│   ├── convert.sh            # OGR2OGR & Tippecanoe Logik
│   └── utils.sh              # Hilfsfunktionen
├── assets/
│   └── sprites/
│       └── openskimap/       # Die Ski-spezifischen Symbole
├── styles/                   # Das MapLibre Stylesheet (openskimap-style.json)
└── dist/                     # Das fertige Ausgabeverzeichnis
    ├── manifest.json         # Deployment-Steuerung
    ├── pmtiles/              # Die fertige openskimap.pmtiles
    ├── styles/               # Das finale Stylesheet
    └── assets/
        └── sprites/          # Das openskimap Sprite-Set
```

## 2. Aktueller Status (Vorhandener Code)
Folgende Dateien wurden aus dem alten System in den Ordner `code/` kopiert:
*   `download_openskimap.sh`
*   `convert_openskimap_pmtiles.sh`
*   `utils.sh`
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
