"""Cliente terreno on-demand (spec §4.3).

Deriva pendiente media/máx del DEM (pipeline/data/raw/dem_san_rafael.tif,
EPSG:5343) recortado al polígono. Mismo cálculo de gradiente que 03_fisico.py.
Si el DEM no está disponible -> campos null + warning.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

from .config import DEM_PATH, crs_exchange, crs_metric


def fetch_terrain(polygon: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Returns (fisico_dict, warnings). fisico_dict ~ {pendiente_media_pct,
    pendiente_max_pct, dem_source}. riesgo_hidrico lo fija normalize/extract.
    """
    warnings: list[str] = []
    if not DEM_PATH.exists():
        warnings.append("terrain: DEM no disponible, pendiente=null")
        return {
            "pendiente_media_pct": None,
            "pendiente_max_pct": None,
            "dem_source": None,
        }, warnings

    import rasterio
    from rasterio.mask import mask as rio_mask

    # Reproyectar polígono 4326 -> CRS del DEM (métrico).
    to_metric = Transformer.from_crs(
        crs_exchange(), crs_metric(), always_xy=True
    ).transform
    geom_metric = shp_transform(to_metric, shape(polygon))

    try:
        with rasterio.open(DEM_PATH) as src:
            dem, transform = rio_mask(src, [geom_metric.__geo_interface__], crop=True)
            nodata = src.nodata
            res_x = abs(src.transform.a)
            res_y = abs(src.transform.e)
    except Exception as exc:
        warnings.append(f"terrain: recorte DEM falló ({exc}), pendiente=null")
        return {
            "pendiente_media_pct": None,
            "pendiente_max_pct": None,
            "dem_source": None,
        }, warnings

    band = dem[0].astype(float)
    if nodata is not None:
        band[band == nodata] = np.nan
    if band.size < 4 or np.all(np.isnan(band)):
        warnings.append("terrain: polígono sin cobertura DEM, pendiente=null")
        return {
            "pendiente_media_pct": None,
            "pendiente_max_pct": None,
            "dem_source": None,
        }, warnings

    dz_dy, dz_dx = np.gradient(band, res_y, res_x)
    slope_pct = np.tan(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))) * 100
    slope_pct = np.clip(slope_pct, 0, 100)
    valid = slope_pct[~np.isnan(slope_pct)]

    return {
        "pendiente_media_pct": round(float(np.mean(valid)), 1),
        "pendiente_max_pct": round(float(np.max(valid)), 1),
        "dem_source": "SRTM3 (pipeline)",
    }, warnings
