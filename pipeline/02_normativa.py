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
    zonas: gpd.GeoDataFrame, geojson: dict
) -> pd.DataFrame | None:
    """S_norm desde zonificación real (UGDT/ArcGIS).

    Resuelve Caso A/B por feature, reproyecta a CRS_WORK y asigna a cada celda
    por centroide-dentro-de-zona. Devuelve None si no hay geometrías usables.
    """
    sources = arcgis_client.load_sources()
    resolved, warns = normativa_resolver.resolve_features(geojson, sources=sources)
    for w in warns:
        print(f"  WARN {w}")

    rows = [
        {"uso_permitido": z["uso_permitido"], "s_norm": z["s_norm"], "geometry": shape(z["geometry"])}
        for z in resolved
        if z.get("geometry") is not None
    ]
    if not rows:
        return None

    zonif = gpd.GeoDataFrame(rows, crs=CRS_OUT).to_crs(CRS_WORK)

    zonas_centroid = zonas[["id", "geometry"]].copy()
    zonas_centroid.geometry = zonas.centroid
    joined = gpd.sjoin(
        zonas_centroid, zonif[["geometry", "uso_permitido", "s_norm"]],
        how="left", predicate="within",
    )
    joined = joined[~joined.index.duplicated(keep="first")]

    uso = joined["uso_permitido"].where(joined["uso_permitido"].notna(),
                                        normativa_resolver.DEFAULT_USO)
    s = joined["s_norm"].where(joined["s_norm"].notna(),
                               normativa_resolver.DEFAULT_S_NORM)
    return pd.DataFrame(
        {"id": zonas["id"].values, "uso_permitido": uso.values, "s_norm": s.values}
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
        result = compute_s_norm_arcgis(zonas, geojson)

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
