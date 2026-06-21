#!/usr/bin/env python3
"""
Sub-índice Normativo (S_norm) desde OSM landuse.

Spatial join entre la grilla y los polígonos de uso del suelo de OSM.
Mapeo OSM landuse tag → uso_permitido → s_norm.

Nota: proxy de la ordenanza municipal real hasta que se digitalice.
Salida: pipeline/data/s_norm.parquet
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely.geometry import shape

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib import arcgis_client, normativa_resolver  # noqa: E402

CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
LANDUSE_PATH = SCRIPT_DIR / "data" / "raw" / "osm_landuse.gpkg"
OUTPUT_PATH = SCRIPT_DIR / "data" / "s_norm.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_WORK = cfg["piloto"]["crs_trabajo"]
CRS_OUT = cfg["piloto"]["crs_salida"]

# OSM landuse → (uso_permitido, s_norm)
# Proxy hasta tener la ordenanza de San Rafael digitalizada.
LANDUSE_MAP: dict[str, tuple[str, float]] = {
    "residential": ("residencial", 1.0),
    "commercial": ("mixto", 1.0),
    "retail": ("mixto", 1.0),
    "mixed_use": ("mixto", 1.0),
    "farmland": ("agricola", 0.7),
    "vineyard": ("agricola", 0.7),
    "orchard": ("agricola", 0.7),
    "meadow": ("agricola", 0.5),
    "industrial": ("condicionado", 0.5),
    "military": ("condicionado", 0.3),
    "forest": ("reserva_natural", 0.0),
    "nature_reserve": ("reserva_natural", 0.0),
    "conservation": ("reserva_natural", 0.0),
    "scrub": ("rural", 0.2),
    "grass": ("rural", 0.3),
    "reservoir": ("reserva_hidrica", 0.0),
    "basin": ("reserva_hidrica", 0.0),
    "wetland": ("reserva_hidrica", 0.0),
}

DEFAULT_USO = "rural"
DEFAULT_S_NORM = 0.3


def classify_zone(landuse_tag: str | None) -> tuple[str, float]:
    if landuse_tag and landuse_tag in LANDUSE_MAP:
        return LANDUSE_MAP[landuse_tag]
    return DEFAULT_USO, DEFAULT_S_NORM


def compute_s_norm(zonas: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame) -> pd.DataFrame:
    # Largest overlap: spatial join on centroids to avoid multi-matches
    zonas_centroid = zonas[["id", "geometry"]].copy()
    zonas_centroid.geometry = zonas.centroid

    joined = gpd.sjoin(
        zonas_centroid,
        landuse[["geometry", "landuse"]].dropna(subset=["landuse"]),
        how="left",
        predicate="within",
    )

    # If multiple matches, keep first (largest polygon wins via index sort)
    joined = joined[~joined.index.duplicated(keep="first")]

    uso_list = []
    s_norm_list = []
    for idx, row in zonas.iterrows():
        tag = joined.loc[idx, "landuse"] if idx in joined.index else None
        if isinstance(tag, pd.Series):
            tag = tag.iloc[0]
        uso, s = classify_zone(tag)
        uso_list.append(uso)
        s_norm_list.append(s)

    return pd.DataFrame(
        {"id": zonas["id"].values, "uso_permitido": uso_list, "s_norm": s_norm_list}
    )


def compute_s_norm_arcgis(
    zonas: gpd.GeoDataFrame, geojson: dict,
    osm_fallback: pd.DataFrame | None = None,
) -> pd.DataFrame | None:
    """S_norm desde zonificación real (UGDT/ArcGIS), híbrido con OSM.

    Asigna a cada celda el uso DOMINANTE de las parcelas que la intersecan.
    Las parcelas solo cubren el oasis -> las celdas sin parcela usan el
    fallback OSM landuse (osm_fallback, mapeado por id) si está disponible, o
    rural por defecto. Devuelve None si no hay geometrías ArcGIS usables.
    """
    sources = arcgis_client.load_sources()
    resolved, warns = normativa_resolver.resolve_features(geojson, sources=sources)
    for w in warns:
        print(f"  WARN {w}")

    # La grilla/geojson esperan uso_permitido como STRING (Caso B puede traer
    # lista desde zonas.yaml -> tomar el uso primario, igual que s_norm).
    def _uso_str(u):
        if isinstance(u, list):
            return u[0] if u else None
        return u

    rows = [
        {"uso_permitido": _uso_str(z["uso_permitido"]), "s_norm": z["s_norm"],
         "geometry": shape(z["geometry"])}
        for z in resolved
        if z.get("geometry") is not None
    ]
    if not rows:
        return None

    zonif = gpd.GeoDataFrame(rows, crs=CRS_OUT).to_crs(CRS_WORK)

    # Grilla 2km vs parcelas chicas: el centroide casi nunca cae en una parcela.
    # Usamos el uso DOMINANTE (más frecuente) entre las parcelas que intersecan
    # cada celda. Celdas sin parcela (fuera del oasis) -> rural default.
    cells = zonas[["id", "geometry"]].copy()
    joined = gpd.sjoin(
        cells, zonif[["geometry", "uso_permitido"]],
        how="left", predicate="intersects",
    )

    def _dominante(s: pd.Series) -> "str | None":
        s = s.dropna()
        m = s.mode()
        return m.iloc[0] if not m.empty else None

    dom = joined.groupby("id")["uso_permitido"].apply(_dominante).to_dict()

    # Fallback OSM landuse por id (para celdas sin parcela, fuera del oasis).
    osm_uso = (
        dict(zip(osm_fallback["id"], osm_fallback["uso_permitido"]))
        if osm_fallback is not None else {}
    )

    def _uso(i):
        u = dom.get(i)
        if u is not None and not (isinstance(u, float) and pd.isna(u)):
            return u                      # parcela ArcGIS (oasis)
        return osm_uso.get(i) or normativa_resolver.DEFAULT_USO  # fallback OSM

    uso_list = [_uso(i) for i in zonas["id"].values]
    s_list = [
        normativa_resolver.USO_S_NORM.get(u, normativa_resolver.DEFAULT_S_NORM)
        for u in uso_list
    ]
    n_arcgis = sum(
        1 for i in zonas["id"].values
        if dom.get(i) is not None and not (isinstance(dom.get(i), float) and pd.isna(dom.get(i)))
    )
    print(f"  {n_arcgis} celdas con zonificación ArcGIS, resto fallback OSM/rural")
    return pd.DataFrame(
        {"id": zonas["id"].values, "uso_permitido": uso_list, "s_norm": s_list}
    )


if __name__ == "__main__":
    print("Cargando grilla ...")
    zonas = gpd.read_file(ZONAS_PATH)

    # 1) Intentar zonificación real (UGDT/ArcGIS) si está configurada.
    bbox = cfg["piloto"]["bbox"]
    geojson, arc_warns = arcgis_client.fetch_zonificacion(
        bbox=(bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    )
    for w in arc_warns:
        print(f"  WARN {w}")

    result = None
    if geojson is not None:
        print(f"Zonificación ArcGIS: {len(geojson.get('features', []))} features "
              f"(Caso {normativa_resolver.caso(arcgis_client.load_sources()).upper()})")
        # Fallback OSM landuse para celdas fuera del oasis (sin parcela).
        osm_fb = None
        if LANDUSE_PATH.exists():
            osm_fb = compute_s_norm(
                zonas, gpd.read_file(LANDUSE_PATH).to_crs(CRS_WORK)
            )
        result = compute_s_norm_arcgis(zonas, geojson, osm_fallback=osm_fb)

    # 2) Fallback: proxy OSM landuse (comportamiento histórico).
    if result is not None:
        pass
    elif not LANDUSE_PATH.exists():
        print("ADVERTENCIA: osm_landuse.gpkg no encontrado — asignando defaults")
        result = pd.DataFrame(
            {
                "id": zonas["id"],
                "uso_permitido": DEFAULT_USO,
                "s_norm": DEFAULT_S_NORM,
            }
        )
    else:
        landuse = gpd.read_file(LANDUSE_PATH).to_crs(CRS_WORK)
        print(f"  {len(zonas)} zonas, {len(landuse)} polígonos landuse")
        result = compute_s_norm(zonas, landuse)

    dist = result["uso_permitido"].value_counts()
    print("Distribución de usos:")
    for uso, count in dist.items():
        print(f"  {uso}: {count} zonas ({count/len(result)*100:.1f}%)")

    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH}")
