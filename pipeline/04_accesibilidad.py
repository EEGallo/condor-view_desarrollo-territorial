#!/usr/bin/env python3
"""
Sub-índice de Accesibilidad (S_acc) desde OSM roads y places.

  score_i = exp(-dist_i / d0_i)
  S_acc = 0.45 * score_huella + 0.35 * score_vial + 0.20 * score_agua

Distancias calculadas desde el centroide de cada zona al feature OSM más cercano.
Salida: pipeline/data/s_acc.parquet
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from pyproj import Transformer
from shapely import STRtree, distance as shapely_distance
from shapely.geometry import LineString, Point

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
ROADS_PATH = SCRIPT_DIR / "data" / "raw" / "osm_roads.gpkg"
PLACES_PATH = SCRIPT_DIR / "data" / "raw" / "osm_places.gpkg"
OUTPUT_PATH = SCRIPT_DIR / "data" / "s_acc.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]
D0_HUELLA = cfg["umbrales"]["accesibilidad"]["d0_huella_m"]
D0_VIAL = cfg["umbrales"]["accesibilidad"]["d0_vial_m"]
D0_AGUA = cfg["umbrales"]["accesibilidad"]["d0_agua_m"]


def nearest_distances(centroids_array: np.ndarray, features: gpd.GeoDataFrame) -> np.ndarray:
    """Distancia (metros) de cada centroide al feature más cercano."""
    tree = STRtree(features.geometry.values)
    nearest_idx = tree.nearest(centroids_array)
    nearest_geoms = features.geometry.values[nearest_idx]
    return shapely_distance(centroids_array, nearest_geoms)


def fallback_localidades(crs: str) -> gpd.GeoDataFrame:
    """Localidades de config.yaml como fallback si no hay OSM places."""
    to_work = Transformer.from_crs(CRS_OUT, crs, always_xy=True)
    rows = []
    for loc in cfg["geografia"]["localidades"]:
        cx, cy = to_work.transform(loc["coords"][0], loc["coords"][1])
        r = loc.get("radio_urbano_m", 1000)
        rows.append({"nombre": loc["nombre"], "geometry": Point(cx, cy).buffer(r)})
    return gpd.GeoDataFrame(rows, crs=crs)


def fallback_roads(crs: str) -> gpd.GeoDataFrame:
    """Rutas de config.yaml como fallback si no hay OSM roads."""
    to_work = Transformer.from_crs(CRS_OUT, crs, always_xy=True)
    rows = []
    for ruta, puntos in cfg["geografia"]["rutas_viales"].items():
        pts = [to_work.transform(p[0], p[1]) for p in puntos]
        rows.append({"nombre": ruta, "geometry": LineString(pts)})
    return gpd.GeoDataFrame(rows, crs=crs)


if __name__ == "__main__":
    zonas = gpd.read_file(ZONAS_PATH)
    centroids_gdf = zonas.copy()
    centroids_gdf.geometry = zonas.centroid
    centroids_arr = centroids_gdf.geometry.values

    # --- Distancia a huella urbana ---
    if PLACES_PATH.exists():
        places = gpd.read_file(PLACES_PATH).to_crs(CRS_WORK)
        print(f"OSM places: {len(places)} features")
    else:
        print("ADVERTENCIA: osm_places.gpkg no encontrado — usando config.yaml localidades")
        places = fallback_localidades(CRS_WORK)

    print("Calculando distancia a huella urbana ...")
    dist_huella = nearest_distances(centroids_arr, places)

    # --- Distancia a red vial ---
    if ROADS_PATH.exists():
        roads = gpd.read_file(ROADS_PATH).to_crs(CRS_WORK)
        print(f"OSM roads: {len(roads)} features")
    else:
        print("ADVERTENCIA: osm_roads.gpkg no encontrado — usando config.yaml rutas")
        roads = fallback_roads(CRS_WORK)

    print("Calculando distancia a red vial ...")
    dist_vial = nearest_distances(centroids_arr, roads)

    # --- Distancia a agua (ríos de config como proxy) ---
    to_work = Transformer.from_crs(CRS_OUT, CRS_WORK, always_xy=True)
    rio_geoms = []
    for rio_cfg in cfg["geografia"]["rios"].values():
        pts = [to_work.transform(p[0], p[1]) for p in rio_cfg["puntos"]]
        rio_geoms.append(LineString(pts))
    rios_gdf = gpd.GeoDataFrame({"geometry": rio_geoms}, crs=CRS_WORK)
    print("Calculando distancia a agua ...")
    dist_agua = nearest_distances(centroids_arr, rios_gdf)

    # --- S_acc ---
    score_huella = np.exp(-dist_huella / D0_HUELLA)
    score_vial = np.exp(-dist_vial / D0_VIAL)
    score_agua = np.exp(-dist_agua / D0_AGUA)
    s_acc = 0.45 * score_huella + 0.35 * score_vial + 0.20 * score_agua

    # Nombre del distrito más cercano
    tree = STRtree(places.geometry.values)
    nearest_idx = tree.nearest(centroids_arr)
    nombre_col = "name" if "name" in places.columns else "nombre"
    if nombre_col in places.columns:
        distrito = places[nombre_col].values[nearest_idx]
    else:
        distrito = [None] * len(zonas)

    result = pd.DataFrame(
        {
            "id": zonas["id"].values,
            "dist_huella_m": dist_huella.astype(int),
            "dist_vial_m": dist_vial.astype(int),
            "dist_agua_m": dist_agua.astype(int),
            "distrito": distrito,
            "s_acc": np.round(s_acc, 4),
        }
    )

    print(f"S_acc — media: {s_acc.mean():.3f}, mediana: {np.median(s_acc):.3f}")
    print(f"Dist media a huella: {dist_huella.mean()/1000:.1f}km")
    print(f"Dist media a vial:   {dist_vial.mean()/1000:.1f}km")

    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH}")
