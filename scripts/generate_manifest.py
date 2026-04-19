import os
import json
import sys
from datetime import datetime
import shutil

# Corporate Identity einbinden
sys.path.append(os.path.join(os.path.dirname(__file__), "ci"))
from utils import log_info, log_success, log_warn, log_error

# --- KONFIGURATION ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
PMTILES_DIR = os.path.join(DIST_DIR, "pmtiles")
STYLES_DIR = os.path.join(DIST_DIR, "styles")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")
SPRITES_DIST_DIR = os.path.join(ASSETS_DIR, "sprites", "openskimap")

# Quellen (Migriert auf v1.2 Standard)
WORK_DIR = os.path.join(PROJECT_ROOT, "work")
STYLE_SRC = os.path.join(PROJECT_ROOT, "styles", "openskimap-style.json")
SPRITES_SRC = os.path.join(PROJECT_ROOT, "assets", "sprites", "openskimap")

def format_size(size_bytes):
    if size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def generate_manifest():
    log_info("Generating Manifest according to Plugin-Standard (v1.2)...")
    
    # Verzeichnisse sicherstellen
    for d in [PMTILES_DIR, STYLES_DIR, SPRITES_DIST_DIR]:
        os.makedirs(d, exist_ok=True)

    # 1. PMTiles kopieren
    pmtiles_filename = "openskimap.pmtiles"
    pmtiles_src = os.path.join(WORK_DIR, pmtiles_filename)
    pmtiles_rel_path = f"pmtiles/{pmtiles_filename}"
    
    if os.path.exists(pmtiles_src):
        shutil.copy2(pmtiles_src, os.path.join(PMTILES_DIR, pmtiles_filename))
        size = format_size(os.stat(pmtiles_src).st_size)
        log_success(f"Copied data: {pmtiles_filename} ({size})")
    else:
        log_error(f"Source PMTiles not found in work directory: {pmtiles_src}")
        sys.exit(1)

    # 2. Style kopieren
    style_filename = "openskimap-style.json"
    style_rel_path = f"styles/{style_filename}"
    if os.path.exists(STYLE_SRC):
        shutil.copy2(STYLE_SRC, os.path.join(STYLES_DIR, style_filename))
        log_info(f"Created style: {style_rel_path}")
    else:
        log_warn(f"Source style not found: {STYLE_SRC}")

    # 3. Sprites kopieren
    if os.path.exists(SPRITES_SRC):
        log_info(f"Copying sprites from {SPRITES_SRC}...")
        for item in os.listdir(SPRITES_SRC):
            s = os.path.join(SPRITES_SRC, item)
            d = os.path.join(SPRITES_DIST_DIR, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
        log_success("Sprites copied to dist.")
    else:
        log_warn(f"Sprites source not found: {SPRITES_SRC}")

    # 4. Manifest erstellen
    dataset = {
        "id": "openskimap",
        "type": "overlay",
        "source": "openskimap",
        "sprite_id": "openskimap",
        "name": "OpenSkiMap",
        "style_path": style_rel_path,
        "pmtiles_path": pmtiles_rel_path
    }

    manifest = {
        "version": "1.0",
        "project": "geodata-openskimap",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datasets": [dataset],
        "resources": {
            "sprites": [
                {
                    "id": "openskimap",
                    "path": "assets/sprites/openskimap"
                }
            ],
            "fonts": []
        }
    }

    manifest_file = os.path.join(DIST_DIR, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    log_success(f"Manifest saved to: {manifest_file}")

if __name__ == "__main__":
    generate_manifest()
