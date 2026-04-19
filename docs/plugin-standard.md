# Standard: Automatisierte Geodata-Plugins

Dieser Standard definiert, wie neue Repositories (Plugins) aufgebaut sein müssen, um nahtlos in das automatisierte Deployment-System integriert werden zu können.

## 1. Kern-Prinzipien
1. **Einheitliche Struktur:** Jedes Plugin muss dieselben Grundverzeichnisse nutzen.
2. **Standardisierte Ausgabe:** Das Ergebnis muss immer im Ordner `dist/` liegen und eine `manifest.json` enthalten.
3. **Zentraler Einstieg:** Jedes Plugin muss eine `update.sh` im Hauptverzeichnis besitzen, die den Build steuert.
4. **Corporate Identity (CI):** Alle CLI-Ausgaben müssen den einheitlichen Logging-Standard aus `scripts/ci/` nutzen.

## 2. Verzeichnisstruktur (Pflicht)
```text
plugin-repo/
├── update.sh             # Zentraler Einstiegspunkt (koordininiert den Build)
├── DEPENDENCIES.md       # Liste aller benötigten Tools
├── docs/                 # Zentrale Dokumentation (Usage, CI, etc.)
├── scripts/              # Alle Build-Skripte
│   ├── ci/               # Standardisierte CI Utilities (Bash/Python)
│   ├── init.sh           # Initialisierung der Ordnerstruktur
│   └── check_dependencies.sh # Automatisierte Prüfung der Tools
├── sources/              # Definition der Datenquellen
└── dist/                 # Das fertige Ausgabeverzeichnis (Deployment-Quelle)
    └── manifest.json     # Metadaten für das Deployment
```

## 3. Automatisierungs-Logik
Jedes Plugin sollte folgende Phasen abbilden:
1. **Pre-Flight:** Prüfung von Abhängigkeiten und Ordnerstruktur.
2. **Ingest:** Download oder Generierung der Rohdaten (Quellen-Tracking!).
3. **Processing:** Transformation der Daten (z.B. nach PMTiles, GeoJSON, MBTiles).
4. **Finalize:** Generierung des Manifests und Bereitstellung der Styles.

## 4. Manifest-Standard (manifest.json)
Das Manifest steuert das Deployment auf den Zielservern:
- `id`: Eindeutiger Bezeichner des Datensatzes.
- `type`: Art des Datensatzes (z.B. `basemap`, `overlay`, `poi`).
- `source`: Herkunft der Daten (z.B. `osm`, `basemap.at`).
- `pmtiles_path`: Relativer Pfad zur Datendatei innerhalb von `dist/`.
- `style_path`: Relativer Pfad zur MapLibre-Style-Datei innerhalb von `dist/`.

---
*Dieser Standard stellt sicher, dass neue Datenquellen ohne manuelle Konfiguration des Deployment-Systems hinzugefügt werden können.*
