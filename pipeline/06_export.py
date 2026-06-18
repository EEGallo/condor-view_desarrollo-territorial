#!/usr/bin/env python3
"""
Exporta zonas_scored.gpkg → frontend/public/data/zonas.geojson

- Reproyecta EPSG:5343 → EPSG:4326
- Simplifica geometría (tolerancia 20m en métrico, antes de reproyectar)
- Redondea iat a int, coords a 6 decimales
- Serializa flags como JSON array
- Imprime estadísticas de verificación
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
INPUT_PATH = SCRIPT_DIR / "data" / "zonas_scored.gpkg"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

OUTPUT_PATH = (SCRIPT_DIR / cfg["rutas"]["salida_geojson"]).resolve()
CRS_OUT = cfg["piloto"]["crs_salida"]

SIMPLIFY_TOLERANCE_M = 20  # metros, antes de reproyectar
COORD_DECIMALS = 6


def export():
    print(f"Cargando {INPUT_PATH} ...")
    gdf = gpd.read_file(INPUT_PATH)
    print(f"  {len(gdf)} zonas, CRS: {gdf.crs}")

    # Simplificar en CRS métrico
    gdf.geometry = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)

    # Reproyectar a WGS84
    gdf = gdf.to_crs(CRS_OUT)

    # Eliminar columnas internas no necesarias en el frontend
    drop_cols = [c for c in ["lon", "lat"] if c in gdf.columns]
    gdf = gdf.drop(columns=drop_cols)

    # Asegurar tipos correctos
    gdf["iat"] = gdf["iat"].astype(int)
    gdf["s_norm"] = gdf["s_norm"].round(4)
    gdf["s_fis"] = gdf["s_fis"].round(4)
    gdf["s_acc"] = gdf["s_acc"].round(4)
    gdf["pendiente_pct"] = gdf["pendiente_pct"].round(1)
    gdf["elevacion_m"] = gdf["elevacion_m"].astype(int)
    gdf["dist_huella_m"] = gdf["dist_huella_m"].astype(int)
    gdf["dist_vial_m"] = gdf["dist_vial_m"].astype(int)
    gdf["en_oasis"] = gdf["en_oasis"].astype(bool)

    # flags: asegurar que sea lista (puede venir como string de geopackage)
    def normalize_flags(v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return []

    gdf["flags"] = gdf["flags"].apply(normalize_flags)

    # Exportar como GeoJSON con precisión controlada
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUTPUT_PATH, driver="GeoJSON")

    # Redondear coordenadas en el archivo resultante
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        data = json.load(f)

    def round_coords(coords):
        if isinstance(coords[0], list):
            return [round_coords(c) for c in coords]
        return [round(v, COORD_DECIMALS) for v in coords]

    for feat in data["features"]:
        feat["geometry"]["coordinates"] = round_coords(
            feat["geometry"]["coordinates"]
        )

    # Fuente de verdad de umbrales de categoría: config.yaml.
    # El frontend los lee de aquí para reclasificar al ajustar pesos.
    data["metadata"] = {
        "umbrales": {
            "alta": cfg["categorias"]["alta"],
            "media": cfg["categorias"]["media"],
        }
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = OUTPUT_PATH.stat().st_size / 1_000_000
    print(f"\nExportado: {OUTPUT_PATH}")
    print(f"  Tamaño: {size_mb:.1f} MB")
    print(f"  Zonas: {len(gdf)}")

    cat_dist = gdf["categoria"].value_counts()
    print("\nDistribución final:")
    for cat, count in cat_dist.items():
        print(f"  {cat}: {count} ({count/len(gdf)*100:.1f}%)")


if __name__ == "__main__":
    export()
