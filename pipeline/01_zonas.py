#!/usr/bin/env python3
"""
Construye la grilla de análisis 2km × 2km sobre San Rafael.

Lee config.yaml (bbox + CRS), genera celdas en EPSG:5343, exporta geometrías limpias.
Salida: pipeline/data/zonas_grid.gpkg
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml
from pyproj import Transformer
from shapely.geometry import box

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
OUTPUT_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

bbox = cfg["piloto"]["bbox"]
CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]
CELL_SIZE = cfg["grilla"]["tamano_m"]


def build_grid() -> gpd.GeoDataFrame:
    to_work = Transformer.from_crs(CRS_OUT, CRS_WORK, always_xy=True)

    x_min, y_min = to_work.transform(bbox["west"], bbox["south"])
    x_max, y_max = to_work.transform(bbox["east"], bbox["north"])

    xs = np.arange(x_min, x_max, CELL_SIZE)
    ys = np.arange(y_min, y_max, CELL_SIZE)

    n_cols = len(xs)
    n_rows = len(ys)
    total = n_cols * n_rows
    print(f"Grilla: {n_cols} cols × {n_rows} filas = {total} zonas")

    ox_arr = np.repeat(xs, n_rows)
    oy_arr = np.tile(ys, n_cols)

    ids = [f"Z-{i:05d}" for i in range(total)]
    geometries = [
        box(ox_arr[i], oy_arr[i], ox_arr[i] + CELL_SIZE, oy_arr[i] + CELL_SIZE)
        for i in range(total)
    ]

    gdf = gpd.GeoDataFrame({"id": ids, "geometry": geometries}, crs=CRS_WORK)

    # Centroids en coordenadas geográficas para referencia
    to_out = Transformer.from_crs(CRS_WORK, CRS_OUT, always_xy=True)
    cx = ox_arr + CELL_SIZE / 2
    cy = oy_arr + CELL_SIZE / 2
    lon, lat = to_out.transform(cx, cy)
    gdf["lon"] = np.round(lon, 6)
    gdf["lat"] = np.round(lat, 6)

    return gdf


if __name__ == "__main__":
    if OUTPUT_PATH.exists():
        print(f"Grid ya existe: {OUTPUT_PATH}")
    else:
        gdf = build_grid()
        gdf.to_file(OUTPUT_PATH, driver="GPKG")
        print(f"Guardado: {OUTPUT_PATH} ({len(gdf)} zonas)")
