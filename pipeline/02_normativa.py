#!/usr/bin/env python3
"""
Sub-índice Normativo (S_norm) desde OSM landuse.

Spatial join entre la grilla y los polígonos de uso del suelo de OSM.
Mapeo OSM landuse tag → uso_permitido → s_norm.

Nota: proxy de la ordenanza municipal real hasta que se digitalice.
Salida: pipeline/data/s_norm.parquet
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
LANDUSE_PATH = SCRIPT_DIR / "data" / "raw" / "osm_landuse.gpkg"
OUTPUT_PATH = SCRIPT_DIR / "data" / "s_norm.parquet"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

CRS_WORK = cfg["piloto"]["crs_trabajo"]

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


if __name__ == "__main__":
    print("Cargando grilla y landuse OSM ...")
    zonas = gpd.read_file(ZONAS_PATH)

    if not LANDUSE_PATH.exists():
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
