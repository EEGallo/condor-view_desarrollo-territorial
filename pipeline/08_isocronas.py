#!/usr/bin/env python3
"""
Isócronas reales: tiempo de viaje sobre la red vial (osmnx + networkx).

Precompute offline — sin servicio de ruteo en runtime. Foco en el oasis
(90% población + servicios + rutas); periferia remota → fallback por cap.

  tiempo_huella_min   = tiempo de viaje al centro urbano más cercano
  tiempo_servicio_min = tiempo de viaje a escuela/salud más cercana

Salida: pipeline/data/isocronas.parquet  (id, tiempo_huella_min, tiempo_servicio_min)
"""

from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
RAW = SCRIPT_DIR / "data" / "raw"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
OUTPUT_PATH = SCRIPT_DIR / "data" / "isocronas.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_OUT = cfg["piloto"]["crs_salida"]
oasis = cfg["geografia"]["oasis"]

# Cap de tiempo (min) para zonas sin acceso o fuera del alcance del grafo.
TIEMPO_CAP_MIN = 180
# Distancia máx (m) zona→nodo de grafo para considerar accesible por red.
SNAP_MAX_M = 4000


def add_travel_times(G):
    """Agrega velocidades y tiempos de viaje (osmnx 1.x y 2.x)."""
    try:
        G = ox.routing.add_edge_speeds(G)
        G = ox.routing.add_edge_travel_times(G)
    except AttributeError:
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)
    return G


def nearest_nodes_for(G, gdf_points: gpd.GeoDataFrame):
    """Nodos de grafo más cercanos a un set de puntos (lon/lat WGS84)."""
    pts = gdf_points.to_crs(CRS_OUT)
    xs = pts.geometry.x.values
    ys = pts.geometry.y.values
    nodes = ox.distance.nearest_nodes(G, xs, ys)
    return list(set(np.atleast_1d(nodes).tolist()))


def load_points(path: Path) -> gpd.GeoDataFrame | None:
    if not path.exists():
        return None
    g = gpd.read_file(path)
    g["geometry"] = g.geometry.centroid
    return g


if __name__ == "__main__":
    print("Construyendo grafo vial del oasis ...")
    G = ox.graph_from_bbox(
        bbox=(oasis["west"], oasis["south"], oasis["east"], oasis["north"]),
        network_type="drive",
    )
    G = add_travel_times(G)
    print(f"  grafo: {len(G.nodes)} nodos, {len(G.edges)} edges")

    # --- Fuentes: centros urbanos y servicios ---
    places = load_points(RAW / "osm_places.gpkg")
    edu = load_points(RAW / "osm_educacion.gpkg")
    salud = load_points(RAW / "osm_salud.gpkg")

    urban_sources = nearest_nodes_for(G, places) if places is not None else []
    serv_pts = [g for g in [edu, salud] if g is not None]
    serv_gdf = (
        gpd.GeoDataFrame(pd.concat(serv_pts, ignore_index=True))
        if serv_pts
        else None
    )
    serv_sources = (
        nearest_nodes_for(G, serv_gdf) if serv_gdf is not None else []
    )
    print(f"  fuentes urbanas: {len(urban_sources)}, servicios: {len(serv_sources)}")

    # --- Multi-source Dijkstra (segundos) ---
    print("Calculando tiempos de viaje (Dijkstra multi-fuente) ...")
    t_urban = nx.multi_source_dijkstra_path_length(
        G, urban_sources, weight="travel_time"
    )
    t_serv = nx.multi_source_dijkstra_path_length(
        G, serv_sources, weight="travel_time"
    )

    # --- Asignar a zonas ---
    zonas = gpd.read_file(ZONAS_PATH)
    lon = zonas["lon"].values
    lat = zonas["lat"].values
    in_oasis = (
        (lon >= oasis["west"])
        & (lon <= oasis["east"])
        & (lat >= oasis["south"])
        & (lat <= oasis["north"])
    )

    nodes, dists = ox.distance.nearest_nodes(G, lon, lat, return_dist=True)
    nodes = np.atleast_1d(nodes)
    dists = np.atleast_1d(dists)

    def time_to(node, snap_d, table):
        if snap_d > SNAP_MAX_M:
            return TIEMPO_CAP_MIN
        secs = table.get(node)
        if secs is None:
            return TIEMPO_CAP_MIN
        return min(round(secs / 60, 1), TIEMPO_CAP_MIN)

    tiempo_huella = np.full(len(zonas), float(TIEMPO_CAP_MIN))
    tiempo_serv = np.full(len(zonas), float(TIEMPO_CAP_MIN))
    for i in range(len(zonas)):
        if not in_oasis[i]:
            continue  # periferia → cap (sin red relevante)
        tiempo_huella[i] = time_to(nodes[i], dists[i], t_urban)
        tiempo_serv[i] = time_to(nodes[i], dists[i], t_serv)

    result = pd.DataFrame(
        {
            "id": zonas["id"].values,
            "tiempo_huella_min": np.round(tiempo_huella, 1),
            "tiempo_servicio_min": np.round(tiempo_serv, 1),
        }
    )

    en_red = (result["tiempo_servicio_min"] < TIEMPO_CAP_MIN).sum()
    print(f"\nZonas con acceso por red: {en_red} (de {len(result)})")
    print(
        f"Tiempo medio a servicios (en red): "
        f"{result.loc[result['tiempo_servicio_min'] < TIEMPO_CAP_MIN, 'tiempo_servicio_min'].mean():.1f} min"
    )
    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH}")
