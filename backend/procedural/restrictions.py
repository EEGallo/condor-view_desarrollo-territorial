"""Área urbanizable = polígono − buffers de restricción (CAPA 2 §5.1).

La Capa 1 expone restricciones solo como % (sin geometría); acá se reconstruye
el buffer de cauce desde el gpkg local de waterways (igual fuente que
backend/extraction/overpass.py), buffer RETIRO_CAUCE_M.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
from shapely.geometry import shape

from ..extraction.config import RAW_DIR, crs_metric

RETIRO_CAUCE_M = 100  # coincide con extraction.normalize.RETIRO_CAUCE_M


def urbanizable(polygon_m, context: dict[str, Any]) -> tuple[Any, list[str], list[str]]:
    """polygon_m: shapely Polygon en CRS métrico (5343).

    Returns (urbanizable_geom, restricciones_respetadas, warnings).
    """
    warnings: list[str] = []
    respetadas: list[str] = []
    geom = polygon_m

    water_path = RAW_DIR / "osm_waterways.gpkg"
    if water_path.exists():
        ww = gpd.read_file(water_path).to_crs(crs_metric())
        ww = ww[ww.geometry.notna() & ~ww.geometry.is_empty]
        # Recortar al entorno del polígono antes de buffear (perf).
        minx, miny, maxx, maxy = geom.bounds
        pad = RETIRO_CAUCE_M * 2
        ww = ww.cx[minx - pad:maxx + pad, miny - pad:maxy + pad]
        if len(ww):
            buf = ww.geometry.buffer(RETIRO_CAUCE_M).union_all()
            if buf.intersects(geom):
                geom = geom.difference(buf)
                respetadas.append("retiro_cauce")
    else:
        warnings.append("urbanizable: sin osm_waterways.gpkg, no se resta cauce")

    if geom.is_empty or geom.area <= 0:
        warnings.append("urbanizable: vacío tras restar restricciones")
    return geom, respetadas, warnings
