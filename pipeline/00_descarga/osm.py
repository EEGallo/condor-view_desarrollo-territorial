#!/usr/bin/env python3
"""
Descarga features OSM para San Rafael via osmnx (Overpass API).

Salidas en pipeline/data/raw/:
  osm_roads.gpkg       — rutas primarias/secundarias/terciarias
  osm_waterways.gpkg   — ríos y arroyos
  osm_landuse.gpkg     — polígonos de uso del suelo
  osm_places.gpkg      — localidades (city/town/village/hamlet)
"""

from pathlib import Path

import time

import geopandas as gpd
import osmnx as ox
import yaml

ox.settings.overpass_rate_limit = False

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
RAW_DIR = SCRIPT_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

bbox = cfg["piloto"]["bbox"]
CRS = cfg["piloto"]["crs_trabajo"]

# osmnx bbox convention: (north, south, east, west)
N, S, E, W = bbox["north"], bbox["south"], bbox["east"], bbox["west"]

LAYERS = {
    "osm_roads.gpkg": {
        "tags": {"highway": ["motorway", "trunk", "primary", "secondary", "tertiary"]},
        "desc": "rutas",
    },
    "osm_waterways.gpkg": {
        "tags": {"waterway": ["river", "stream", "canal"]},
        "desc": "ríos y cursos de agua",
    },
    "osm_landuse.gpkg": {
        "tags": {"landuse": True},
        "desc": "uso del suelo",
    },
    "osm_places.gpkg": {
        "tags": {"place": ["city", "town", "village", "hamlet", "suburb"]},
        "desc": "localidades",
    },
}


def download_layer(filename: str, tags: dict, desc: str):
    out_path = RAW_DIR / filename
    if out_path.exists():
        existing = gpd.read_file(out_path)
        print(f"{filename} ya existe ({len(existing)} features)")
        return
    print(f"Descargando {desc} ...")
    try:
        gdf = ox.features_from_bbox(bbox=(W, S, E, N), tags=tags)
        gdf = gdf.to_crs(CRS)
        # Mantener solo geometrías útiles y columnas clave
        cols = ["geometry"] + [c for c in gdf.columns if c not in ["geometry", "nodes", "ways"]]
        gdf = gdf[cols].reset_index(drop=True)
        gdf.to_file(out_path, driver="GPKG")
        print(f"  → {len(gdf)} features guardadas en {out_path}")
    except Exception as exc:
        print(f"  ERROR descargando {desc}: {exc}")
        raise


if __name__ == "__main__":
    for i, (fname, params) in enumerate(LAYERS.items()):
        download_layer(fname, params["tags"], params["desc"])
        if i < len(LAYERS) - 1:
            print("  Pausa 15s entre layers (rate limit) ...")
            time.sleep(15)
    print("Descarga OSM completa.")
