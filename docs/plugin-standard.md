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
│   │   └── run_logger.sh # JSONL Run-Logging (siehe §5)
│   ├── init.sh           # Initialisierung der Ordnerstruktur
│   └── check_dependencies.sh # Automatisierte Prüfung der Tools
├── sources/              # Definition der Datenquellen
└── dist/                 # Das fertige Ausgabeverzeichnis (Deployment-Quelle)
    ├── manifest.json     # Metadaten für das Deployment
    └── layer-list.json   # Layer-Gruppierung für Frontend-Legenden/Toggles (siehe §4.5; nur Overlay-Plugins)
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

### 4.5 Layer-Listen-Standard (layer-list.json)

Nur für **Overlay-Plugins** relevant (Repos, deren `dist/pmtiles/` als Overlay über eine Basemap gelegt wird — z.B. dieses Repo, `geodata-overlays`; Basemap-Repos wie `geodata-basemap-at` brauchen es nicht). `deploy_external.py` kopiert es beim Deployment nach `/srv/info/staging/layers/<repo-name>.json`, von wo `run_inventory.py` es zur zentralen `/srv/info/layers_info.json` aggregiert — **das Frontend (map.oe5ith.at) liest ausschließlich diese aggregierte Datei**, nicht `manifest.json`/`style.json` direkt. Fehlt `dist/layer-list.json`, taucht das Plugin für das Frontend faktisch nicht auf, selbst wenn `dist/pmtiles/`+`dist/styles/` korrekt deployed sind.

`dist/layer-list.json` gruppiert alle Style-Layer nach `source-layer` (ein Eintrag pro Gruppe fasst z.B. Casing+Line+Labels derselben logischen Ebene zusammen, damit das Frontend sie gemeinsam togglen kann), angereichert mit `type`/`color`/`opacity`/`legend_items` pro Gruppe für automatisiertes Legenden-Rendering. Volles Schema, Beispiele und Referenz-Implementierung: `GEODATA_PLUGIN_STANDARD.md` §5 (im `geodata-updater`-Repo-Root, nicht hier lokal dupliziert). Referenz-Extractor `scripts/layer_metadata_extractor.py` (aus `geodata-overlays` übernommen, um `circle`-Layer-Unterstützung erweitert — die Referenz kennt nur `fill`/`line`/`symbol`) + `scripts/generate_layer_list.py` (hier eigenständig, da dieses Repo — anders als `geodata-overlays` — einen einzigen handgeschriebenen Style statt vieler Datei-pro-Gruppe-Datasets hat: `template`/`original_file` sind entsprechend auf `source_layer`-Name bzw. die gemeinsame GeoPackage-Quelle abgebildet statt auf ein Dataset-Config-System).

## 5. Run-Logging & Monitoring (JSONL)
Jeder Lauf hinterlässt zusätzlich zur Konsolenausgabe einen maschinenlesbaren Status unter `/var/log`, den die zentrale `log-api` einsammelt — so ist Erfolg/Fehler eines Laufs auf einen Blick sichtbar.

**Zwei Quellen pro Plugin** (`<slug>` = Repo-Name, `-`→`_`, z.B. `geodata-overlays` → `geodata_overlays`):

| Quelle | Geschrieben von | Status | Dateien | log-api `interval` |
|---|---|---|---|---|
| Update-Check | `update.sh` | `up_to_date` \| `build_triggered` \| `error` | `/var/log/<slug>_update_history.jsonl` (+ `_status.json`) | `1d` |
| Build | Build-Orchestrator | `ok` \| `error` | `/var/log/<slug>_build_history.jsonl` (+ `_status.json`) | — |

`update.sh` schreibt bei **jedem** Lauf (Heartbeat); schlägt ein getriggerter Build fehl, meldet die Update-Zeile `error`. Die Build-Quelle schreibt nur bei tatsächlichem Build.

**Schema** (fixe Reihenfolge, Extras dazwischen): `timestamp` (UTC, `…Z`), `status`, `duration_seconds`, `<extras>`, `message`, `error` (`null` bei Erfolg). Empfohlene Build-Extras: `source`, `datasets`, `stages`, `clean`.
```json
{"timestamp":"2026-06-30T06:35:12Z","status":"ok","duration_seconds":418,"source":"external","stages":["pmtiles","styles"],"datasets":14,"message":"Build erfolgreich.","error":null}
```

**Helper** `scripts/ci/run_logger.sh` (pure-bash, Referenz-Implementierung im Repo `geodata-overlays` — einfach übernehmen): `run_log_init <history> <status>` registriert einen `trap … EXIT` (Default-Status `error`); `run_log_str/num/raw` für Extras; vor regulärem Ende `RUN_LOG_STATUS`/`RUN_LOG_MESSAGE`/`RUN_LOG_ERROR` setzen. **Best-effort:** Schreibfehler → nur `log_warn`, nie Abbruch, ursprünglicher Exit-Code bleibt; `GEODATA_LOG_DIR` überschreibt das Log-Verzeichnis (für Tests ohne Root).

**log-api:** zwei Sources je Plugin in `/opt/log-api/config.yaml` (`format: jsonl`, `ts_field: timestamp`, `level_field: status`, `message_field: message`; Update-Quelle `interval: 1d`, Build-Quelle ohne `interval`), danach `systemctl restart log-api.service`.

**Cron:** `update.sh` täglich planen (auf den `1d`-Heartbeat ausgelegt), z.B. `30 2 * * * /pfad/zum/plugin/update.sh`.

---
*Dieser Standard stellt sicher, dass neue Datenquellen ohne manuelle Konfiguration des Deployment-Systems hinzugefügt werden können.*
