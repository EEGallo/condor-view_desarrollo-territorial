#!/usr/bin/env python3
"""
Descarga DEM SRTM3 (90m) para el departamento de San Rafael y lo reproyecta a EPSG:5343.

Requiere: gdal-bin en el sistema (`sudo apt-get install gdal-bin`)
Salida: pipeline/data/raw/dem_san_rafael.tif (EPSG:5343, float32)
"""

import shutil
from pathlib import Path

import rasterio
import yaml
from rasterio.warp import Resampling, calculate_default_transform, reproject

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
RAW_DIR = SCRIPT_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

WGS84_PATH = RAW_DIR / "dem_san_rafael_wgs84.tif"
OUTPUT_PATH = RAW_DIR / "dem_san_rafael.tif"

# elevation package no escapa espacios en paths — usar /tmp como intermedio
TMP_WGS84 = Path("/tmp/dem_san_rafael_wgs84.tif")

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

bbox = cfg["piloto"]["bbox"]
DST_CRS = cfg["piloto"]["crs_trabajo"]

BOUNDS = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])


def download_srtm():
    if WGS84_PATH.exists():
        print(f"DEM WGS84 ya existe: {WGS84_PATH}")
        return
    import elevation
    print(f"Descargando SRTM3 (90m) para bbox {BOUNDS} ...")
    # elevation.clip usa Makefile que no escapa espacios — output a /tmp primero
    elevation.clip(bounds=BOUNDS, output=str(TMP_WGS84), product="SRTM3")
    elevation.clean()
    shutil.move(str(TMP_WGS84), str(WGS84_PATH))
    print(f"Guardado: {WGS84_PATH}")


def reproject_to_metric():
    if OUTPUT_PATH.exists():
        print(f"DEM reproyectado ya existe: {OUTPUT_PATH}")
        return
    print(f"Reproyectando a {DST_CRS} ...")
    with rasterio.open(WGS84_PATH) as src:
        transform, width, height = calculate_default_transform(
            src.crs, DST_CRS, src.width, src.height, *src.bounds
        )
        meta = src.meta.copy()
        meta.update(
            crs=DST_CRS,
            transform=transform,
            width=width,
            height=height,
            dtype="float32",
            nodata=-9999.0,
        )
        with rasterio.open(OUTPUT_PATH, "w", **meta) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=DST_CRS,
                resampling=Resampling.bilinear,
            )
    print(f"Guardado: {OUTPUT_PATH}")


def verify():
    with rasterio.open(OUTPUT_PATH) as src:
        print(f"CRS: {src.crs}")
        print(f"Resolución: {src.res[0]:.1f}m × {src.res[1]:.1f}m")
        print(f"Dimensiones: {src.width} × {src.height} px")
        print(f"Bounds: {src.bounds}")


if __name__ == "__main__":
    download_srtm()
    reproject_to_metric()
    verify()
