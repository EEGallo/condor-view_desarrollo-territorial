#!/usr/bin/env python3
"""
Capa población + servicios → déficit de servicios por zona.

El gap servicios↔población es el indicador de decisión del intendente:
zonas con gente pero lejos de escuelas/salud = prioridad de intervención.

Población por cascada de precisión:
  1. INDEC radios censales 2022  (data/raw/indec_radios.gpkg, si está presente)
  2. OSM places con tag population
  3. Localidades de config.yaml   (fallback)

Servicios desde OSM (osm_educacion.gpkg, osm_salud.gpkg).

Salida: pipeline/data/servicios.parquet
  id, dist_escuela_m, dist_salud_m, poblacion_est, deficit_servicios (0-100)
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from pyproj import Transformer
from shapely import STRtree, distance as shapely_distance
from shapely.geometry import Point

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
RAW = SCRIPT_DIR / "data" / "raw"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
EDU_PATH = RAW / "osm_educacion.gpkg"
SALUD_PATH = RAW / "osm_salud.gpkg"
PLACES_PATH = RAW / "osm_places.gpkg"
INDEC_PATH = RAW / "indec_radios.gpkg"  # opcional (cascada nivel 1)
OUTPUT_PATH = SCRIPT_DIR / "data" / "servicios.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]

# Distancia de referencia para el decaimiento de acceso a servicios.
D0_SERVICIO_M = 5000
# Radio de deduplicación entre fuentes de población (m).
DEDUP_RADIO_M = 3000


def nearest_distances(centroids_arr, features: gpd.GeoDataFrame) -> np.ndarray:
    """Distancia (m) de cada centroide al feature más cercano."""
    if features is None or len(features) == 0:
        return np.full(len(centroids_arr), np.inf)
    tree = STRtree(features.geometry.values)
    idx = tree.nearest(centroids_arr)
    return shapely_distance(centroids_arr, features.geometry.values[idx])


def to_points(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reduce geometrías a puntos (centroides) para distancia y point-in-zone."""
    g = gdf.copy()
    g["geometry"] = g.geometry.centroid
    return g


def build_population_points() -> gpd.GeoDataFrame:
    """Centros de población por cascada de precisión (INDEC → OSM → config)."""
    # --- Cascada nivel 1: INDEC radios censales ---
    if INDEC_PATH.exists():
        print("Población: usando INDEC radios censales (nivel 1)")
        radios = gpd.read_file(INDEC_PATH).to_crs(CRS_WORK)
        pop_col = next(
            (
                c
                for c in ["poblacion", "total_pers", "personas", "pob_tot"]
                if c in radios.columns
            ),
            None,
        )
        if pop_col:
            radios = to_points(radios)
            radios["poblacion"] = pd.to_numeric(
                radios[pop_col], errors="coerce"
            ).fillna(0)
            return radios[["poblacion", "geometry"]]
        print("  ADVERTENCIA: INDEC sin columna de población reconocida")

    points = []

    # --- Cascada nivel 2: OSM places con population ---
    if PLACES_PATH.exists():
        places = gpd.read_file(PLACES_PATH).to_crs(CRS_WORK)
        if "population" in places.columns:
            pop = pd.to_numeric(places["population"], errors="coerce")
            valid = places[pop.notna()].copy()
            valid["poblacion"] = pop[pop.notna()].values
            valid = to_points(valid)
            for _, r in valid.iterrows():
                points.append((r.geometry, float(r["poblacion"])))
            print(f"Población: {len(points)} centros desde OSM places (nivel 2)")

    # --- Cascada nivel 3: config.yaml (relleno de huecos) ---
    to_work = Transformer.from_crs(CRS_OUT, CRS_WORK, always_xy=True)
    añadidos = 0
    for loc in cfg["geografia"]["localidades"]:
        cx, cy = to_work.transform(loc["coords"][0], loc["coords"][1])
        p = Point(cx, cy)
        # Dedup: solo si no hay ya un centro cercano
        if all(p.distance(g) > DEDUP_RADIO_M for g, _ in points):
            points.append((p, float(loc["poblacion"])))
            añadidos += 1
    if añadidos:
        print(f"  + {añadidos} centros de config.yaml (nivel 3, relleno)")

    return gpd.GeoDataFrame(
        {"poblacion": [pop for _, pop in points]},
        geometry=[g for g, _ in points],
        crs=CRS_WORK,
    )


if __name__ == "__main__":
    zonas = gpd.read_file(ZONAS_PATH)
    centroids = zonas.copy()
    centroids.geometry = zonas.centroid
    centroids_arr = centroids.geometry.values

    # --- Distancia a servicios ---
    edu = gpd.read_file(EDU_PATH).to_crs(CRS_WORK) if EDU_PATH.exists() else None
    salud = (
        gpd.read_file(SALUD_PATH).to_crs(CRS_WORK) if SALUD_PATH.exists() else None
    )
    if edu is not None:
        edu = to_points(edu)
    if salud is not None:
        salud = to_points(salud)

    print("Calculando distancia a educación / salud ...")
    dist_escuela = nearest_distances(centroids_arr, edu)
    dist_salud = nearest_distances(centroids_arr, salud)

    # --- Población por zona (point-in-zone) ---
    pop_points = build_population_points()
    print(f"Asignando población a zonas ({len(pop_points)} centros) ...")
    joined = gpd.sjoin(
        pop_points, zonas[["id", "geometry"]], how="left", predicate="within"
    )
    pop_por_zona = (
        joined.dropna(subset=["id"]).groupby("id")["poblacion"].sum()
    )
    zonas = zonas.merge(
        pop_por_zona.rename("poblacion_est"), on="id", how="left"
    )
    zonas["poblacion_est"] = zonas["poblacion_est"].fillna(0).astype(int)

    # --- Déficit de servicios ---
    # Gente lejos de servicios = déficit. Sin gente = sin déficit.
    dist_serv = np.minimum(dist_escuela, dist_salud)
    dist_serv = np.where(np.isfinite(dist_serv), dist_serv, D0_SERVICIO_M * 5)
    falta_acceso = 1 - np.exp(-dist_serv / D0_SERVICIO_M)  # 0=cerca, 1=lejos
    pob = zonas["poblacion_est"].values.astype(float)
    pob_norm = np.log1p(pob) / np.log1p(pob.max()) if pob.max() > 0 else pob * 0
    deficit = (pob_norm * falta_acceso * 100).round().astype(int)

    result = pd.DataFrame(
        {
            "id": zonas["id"].values,
            "dist_escuela_m": np.where(
                np.isfinite(dist_escuela), dist_escuela, -1
            ).astype(int),
            "dist_salud_m": np.where(
                np.isfinite(dist_salud), dist_salud, -1
            ).astype(int),
            "poblacion_est": zonas["poblacion_est"].values,
            "deficit_servicios": deficit,
        }
    )

    pobladas = (result["poblacion_est"] > 0).sum()
    print(f"\nZonas con población: {pobladas} (de {len(result)})")
    print(f"Población total asignada: {result['poblacion_est'].sum():,}")
    print(f"Dist media a escuela: {dist_escuela[np.isfinite(dist_escuela)].mean()/1000:.1f} km")
    print(f"Dist media a salud:   {dist_salud[np.isfinite(dist_salud)].mean()/1000:.1f} km")
    top = result.nlargest(5, "deficit_servicios")[
        ["id", "poblacion_est", "dist_escuela_m", "deficit_servicios"]
    ]
    print("\nTop 5 déficit de servicios:")
    print(top.to_string(index=False))

    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"\nGuardado: {OUTPUT_PATH}")
