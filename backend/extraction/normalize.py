"""Normalización geométrica (spec §4.5).

Reproyección a CRS métrico, área, bbox y distancias mínimas a OSM. Trabaja en
metros (no grados). Construye accesibilidad + hidrografía del PolygonContext.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
from pyproj import Transformer
from shapely import STRtree, distance as shapely_distance
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

from .config import crs_exchange, crs_metric

# Umbral simple de riesgo hídrico por proximidad a cauce (m).
RIESGO_ALTO_M = 300
RIESGO_MOD_M = 1000


def _clean_str(v) -> str | None:
    """Coerce valores OSM ausentes (NaN de pandas) a None para Pydantic."""
    if v is None:
        return None
    try:
        import math

        if isinstance(v, float) and math.isnan(v):
            return None
    except (TypeError, ValueError):
        pass
    s = str(v).strip()
    return s or None


def _to_metric():
    return Transformer.from_crs(crs_exchange(), crs_metric(), always_xy=True).transform


def polygon_metrics(polygon: dict[str, Any]) -> tuple[list[float], float, Any]:
    """Returns (bbox_4326, area_ha, geom_metric)."""
    geom = shape(polygon)
    minx, miny, maxx, maxy = geom.bounds
    geom_m = shp_transform(_to_metric(), geom)
    area_ha = geom_m.area / 10_000.0
    return [minx, miny, maxx, maxy], round(area_ha, 2), geom_m


def _min_dist(geom_m, gdf_4326: gpd.GeoDataFrame) -> float | None:
    """Distancia mínima (m) del polígono al feature más cercano del gdf."""
    if gdf_4326 is None or len(gdf_4326) == 0:
        return None
    gdf_m = gdf_4326.to_crs(crs_metric())
    geoms = gdf_m.geometry.values
    tree = STRtree(geoms)
    idx = tree.nearest(geom_m)
    return round(float(shapely_distance(geom_m, geoms[idx])), 1)


def build_accesibilidad(geom_m, layers: dict[str, gpd.GeoDataFrame]) -> dict[str, Any]:
    equip = layers.get("equipamiento")
    equipamiento = []
    if equip is not None and len(equip):
        equip_m = equip.to_crs(crs_metric())
        for tipo in equip_m["tipo"].unique():
            sub = equip_m[equip_m["tipo"] == tipo].reset_index(drop=True)
            geoms = sub.geometry.values
            tree = STRtree(geoms)
            i = int(tree.nearest(geom_m))
            equipamiento.append(
                {
                    "tipo": str(tipo),
                    "nombre": _clean_str(sub.iloc[i].get("nombre")),
                    "dist_m": round(float(shapely_distance(geom_m, geoms[i])), 1),
                    "source": "OSM",
                }
            )
    return {
        "dist_huella_urbana_m": _min_dist(geom_m, layers.get("places")),
        "dist_vial_principal_m": _min_dist(geom_m, layers.get("vial")),
        "equipamiento": equipamiento,
    }


def build_hidrografia(geom_m, layers: dict[str, gpd.GeoDataFrame]) -> list[dict[str, Any]]:
    hid = layers.get("hidrografia")
    if hid is None or len(hid) == 0:
        return []
    hid_m = hid.to_crs(crs_metric())
    geoms = hid_m.geometry.values
    tree = STRtree(geoms)
    i = tree.nearest(geom_m)
    row = hid_m.iloc[int(i)] if i < len(hid_m) else None
    return [
        {
            "tipo": _clean_str(row.get("waterway") if row is not None else None) or "cauce",
            "nombre": _clean_str(row.get("name") if row is not None else None),
            "dist_m": round(float(shapely_distance(geom_m, geoms[i])), 1),
            "source": "OSM",
        }
    ]


# Retiro de cauce por defecto (m). No es el valor legal exacto de la ordenanza
# (que varía por cauce); es un buffer documentado para estimar afectación.
RETIRO_CAUCE_M = 100


def build_restricciones(geom_m, layers: dict[str, gpd.GeoDataFrame]) -> list[dict[str, Any]]:
    """Restricciones que afectan el polígono. Hoy: retiro de cauce (buffer OSM).

    geometria_afectada_pct = área(polígono ∩ buffer de cauces) / área(polígono).
    """
    hid = layers.get("hidrografia")
    if hid is None or len(hid) == 0:
        return []
    hid_m = hid.to_crs(crs_metric())
    try:
        buffered = hid_m.geometry.buffer(RETIRO_CAUCE_M).union_all()
    except AttributeError:  # geopandas viejo
        from shapely.ops import unary_union

        buffered = unary_union(list(hid_m.geometry.buffer(RETIRO_CAUCE_M)))
    inter = geom_m.intersection(buffered).area
    pct = round(inter / (geom_m.area or 1.0) * 100, 1)
    if pct <= 0:
        return []
    return [
        {
            "tipo": "retiro_cauce",
            "geometria_afectada_pct": pct,
            "source": f"OSM (buffer {RETIRO_CAUCE_M}m)",
        }
    ]


def riesgo_hidrico(hidrografia: list[dict[str, Any]]) -> str | None:
    if not hidrografia:
        return None
    d = min(
        (h["dist_m"] if h.get("dist_m") is not None else 1e9) for h in hidrografia
    )
    if d <= RIESGO_ALTO_M:
        return "alto"
    if d <= RIESGO_MOD_M:
        return "moderado"
    return "bajo"
