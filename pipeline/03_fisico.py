#!/usr/bin/env python3
"""
Sub-índice Físico (S_fis) desde DEM real + OSM waterways.

  S_fis = slope_score × hidrico_score × altitude_penalty

- slope_score: derivada del DEM SRTM via zonal stats
- hidrico_score: buffer de ríos OSM + embalses de config
- altitude_penalty: penalización para zonas > 2000m

Salida: pipeline/data/s_fis.parquet
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import yaml
from pyproj import Transformer
from rasterstats import zonal_stats
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
DEM_PATH = SCRIPT_DIR / "data" / "raw" / "dem_san_rafael.tif"
WATERWAYS_PATH = SCRIPT_DIR / "data" / "raw" / "osm_waterways.gpkg"
SLOPE_PATH = SCRIPT_DIR / "data" / "raw" / "slope_san_rafael.tif"
OUTPUT_PATH = SCRIPT_DIR / "data" / "s_fis.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]
SLOPE_IDEAL = cfg["umbrales"]["pendiente"]["ideal_pct"]
SLOPE_MAX = cfg["umbrales"]["pendiente"]["max_pct"]


def build_slope_raster():
    """Calcula raster de pendiente (%) desde DEM. Guarda en SLOPE_PATH."""
    if SLOPE_PATH.exists():
        return
    print("Calculando raster de pendiente ...")
    with rasterio.open(DEM_PATH) as src:
        dem = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            dem[dem == nodata] = np.nan
        res_x = abs(src.transform.a)  # metros por pixel en X
        res_y = abs(src.transform.e)  # metros por pixel en Y

    dz_dy, dz_dx = np.gradient(dem, res_y, res_x)
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_pct = np.tan(slope_rad) * 100
    slope_pct = np.clip(slope_pct, 0, 100)
    slope_pct[np.isnan(slope_pct)] = -9999

    with rasterio.open(DEM_PATH) as src:
        meta = src.meta.copy()
        meta.update(dtype="float32", nodata=-9999.0, count=1)
        with rasterio.open(SLOPE_PATH, "w", **meta) as dst:
            dst.write(slope_pct.astype("float32"), 1)
    print(f"Raster pendiente guardado: {SLOPE_PATH}")


def slope_score(pct: np.ndarray) -> np.ndarray:
    """Decaimiento lineal entre SLOPE_IDEAL y SLOPE_MAX."""
    score = np.ones_like(pct)
    mask_mid = (pct > SLOPE_IDEAL) & (pct <= SLOPE_MAX)
    score[mask_mid] = 1 - (pct[mask_mid] - SLOPE_IDEAL) / (SLOPE_MAX - SLOPE_IDEAL)
    score[pct > SLOPE_MAX] = 0.0
    return np.clip(score, 0, 1)


def build_flood_zones(zonas_crs: str) -> gpd.GeoDataFrame:
    """Construye polígonos de zona inundable desde OSM waterways + embalses."""
    to_work = Transformer.from_crs(CRS_OUT, zonas_crs, always_xy=True)
    flood_geoms = []

    # OSM waterways
    if WATERWAYS_PATH.exists():
        ww = gpd.read_file(WATERWAYS_PATH).to_crs(zonas_crs)
        for _, row in ww.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            waterway_type = row.get("waterway", "stream")
            buf = 3000 if waterway_type == "river" else 1000
            flood_geoms.append(("alto", geom.buffer(buf / 2)))
            flood_geoms.append(("moderado", geom.buffer(buf)))
    else:
        # Fallback: ríos de config.yaml
        print("ADVERTENCIA: osm_waterways.gpkg no encontrado — usando ríos de config")
        for rio_name, rio_cfg in cfg["geografia"]["rios"].items():
            pts = [to_work.transform(p[0], p[1]) for p in rio_cfg["puntos"]]
            line = LineString(pts)
            ancho = rio_cfg["ancho_riesgo_m"]
            flood_geoms.append(("alto", line.buffer(ancho / 2)))
            flood_geoms.append(("moderado", line.buffer(ancho)))

    # Embalses de config
    for embalse in cfg["geografia"]["embalses"]:
        cx, cy = to_work.transform(embalse["coords"][0], embalse["coords"][1])
        pt = Point(cx, cy)
        r = embalse["radio_m"]
        flood_geoms.append(("alto", pt.buffer(r)))
        flood_geoms.append(("moderado", pt.buffer(r * 1.5)))

    rows = [{"nivel": nivel, "geometry": geom} for nivel, geom in flood_geoms]
    return gpd.GeoDataFrame(rows, crs=zonas_crs)


def classify_flood(centroid: object, flood_alto_union, flood_mod_union) -> tuple[str, float]:
    if centroid.within(flood_alto_union):
        return "alto", 0.0
    if centroid.within(flood_mod_union):
        return "moderado", 0.5
    return "bajo", 1.0


if __name__ == "__main__":
    zonas = gpd.read_file(ZONAS_PATH)
    centroids = zonas.centroid

    # --- Elevación y pendiente desde DEM ---
    if DEM_PATH.exists():
        build_slope_raster()
        print("Extrayendo elevación media por zona (zonal stats) ...")
        elev_stats = zonal_stats(
            zonas, str(DEM_PATH), stats=["mean"], nodata=-9999, all_touched=True
        )
        elev_m = np.array([s["mean"] or 0 for s in elev_stats])

        print("Extrayendo pendiente media por zona ...")
        slope_stats = zonal_stats(
            zonas, str(SLOPE_PATH), stats=["mean"], nodata=-9999, all_touched=True
        )
        pendiente_pct = np.array([s["mean"] or 0 for s in slope_stats])
    else:
        print("ADVERTENCIA: DEM no encontrado — usando elevación sintética de config")
        # Fallback sintético basado en longitud (gradiente oeste→este)
        perfiles = cfg["geografia"]["elevacion"]["perfiles"]
        lons_ref = np.array([p["lng"] for p in perfiles])
        alts_ref = np.array([p["alt_m"] for p in perfiles])
        elev_m = np.interp(zonas["lon"].values, lons_ref, alts_ref)
        pendiente_pct = np.clip(
            np.abs(np.gradient(elev_m)) / 2000 * 100, 0.5, 50
        )

    # --- Riesgo hídrico ---
    print("Calculando riesgo hídrico ...")
    flood_zones = build_flood_zones(CRS_WORK)
    flood_alto = flood_zones[flood_zones["nivel"] == "alto"]
    flood_mod = flood_zones[flood_zones["nivel"] == "moderado"]
    flood_alto_union = unary_union(flood_alto.geometry) if len(flood_alto) else None
    flood_mod_union = unary_union(flood_mod.geometry) if len(flood_mod) else None

    riesgo_list = []
    hidrico_score_list = []
    for centroid in centroids:
        if flood_alto_union and centroid.within(flood_alto_union):
            riesgo_list.append("alto")
            hidrico_score_list.append(0.0)
        elif flood_mod_union and centroid.within(flood_mod_union):
            riesgo_list.append("moderado")
            hidrico_score_list.append(0.5)
        else:
            riesgo_list.append("bajo")
            hidrico_score_list.append(1.0)

    # --- S_fis ---
    s_slope = slope_score(pendiente_pct)
    hidrico = np.array(hidrico_score_list)
    altitude_penalty = np.where(elev_m > 2000, 0.5, 1.0)
    s_fis = s_slope * hidrico * altitude_penalty

    result = pd.DataFrame(
        {
            "id": zonas["id"].values,
            "elevacion_m": np.round(elev_m).astype(int),
            "pendiente_pct": np.round(pendiente_pct, 1),
            "riesgo_hidrico": riesgo_list,
            "s_fis": np.round(s_fis, 4),
        }
    )

    print(f"S_fis — media: {s_fis.mean():.3f}, mediana: {np.median(s_fis):.3f}")
    print(f"Riesgo hídrico alto: {sum(r=='alto' for r in riesgo_list)} zonas")

    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH}")
