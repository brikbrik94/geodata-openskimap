# Abhängigkeiten und Verwendete Programme

Dieses Dokument listet die Programme und Bibliotheken auf, die für die Ausführung der OpenSkiMap-Datenverarbeitung erforderlich sind.

## System-Anforderungen

Das Projekt ist für den Einsatz auf **Linux-Systemen** (vorzugsweise Debian-basiert) konzipiert. Die Ausführung erfolgt über Bash-Skripte.

## Erforderliche Programme

### 1. Bash (v4.0+)
Die zentrale Orchestrierung erfolgt über Bash-Skripte.
- **Zweck:** Ausführung von `update.sh`, `download.sh` und `convert.sh`.
- **Installation (Debian/Ubuntu):** Standardmäßig installiert.

### 2. aria2c
Ein leichtgewichtiger Multi-Protokoll-Download-Client.
- **Zweck:** Effizientes Herunterladen des GeoPackage mit Unterstützung für `--conditional-get` (lädt die Datei nur herunter, wenn sie sich seit dem letzten Mal geändert hat).
- **Installation (Debian/Ubuntu):** `sudo apt-get install aria2`

### 3. GDAL (ogr2ogr)
Die Geospatial Data Abstraction Library.
- **Zweck:** Extraktion der verschiedenen Layer aus dem heruntergeladenen `openskidata.gpkg` in das `GeoJSONSeq`-Format.
- **Installation (Debian/Ubuntu):** `sudo apt-get install gdal-bin`

### 4. Tippecanoe
Ein Tool zum Erstellen von Vector-Tiles aus großen Mengen von GeoJSON-Daten.
- **Zweck:** Konvertierung der extrahierten Layer in das `.pmtiles`-Format für das Web-Deployment.
- **Installation:** Muss meist aus den Quellen gebaut werden oder über `felt/tippecanoe` bezogen werden.
- **Projekt:** [https://github.com/felt/tippecanoe](https://github.com/felt/tippecanoe)

## Optionale Abhängigkeiten

### Python 3
Wird aktuell für die Hilfsfunktionen in `scripts/ci/utils.py` bereitgehalten, aber im Haupt-Workflow noch nicht aktiv genutzt.

## Prüfung der Abhängigkeiten

Die Abhängigkeiten können automatisch geprüft werden:
```bash
bash scripts/ci/check_dependencies.sh
```
Diese Prüfung wird auch automatisch beim Start von `update.sh` ausgeführt.
