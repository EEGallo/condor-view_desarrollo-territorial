"""Orquestador de /api/extract (spec §5).

Corre arcgis ∥ overpass ∥ terrain con degradación elegante (equivalente a
Promise.allSettled), fusiona y valida contra PolygonContext (Pydantic).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from . import arcgis, normalize, overpass, terrain
from .config import crs_metric
from .schema import PolygonContext


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def extract(polygon: dict[str, Any]) -> PolygonContext:
    bbox, area_ha, geom_m = normalize.polygon_metrics(polygon)
    bbox_t = (bbox[0], bbox[1], bbox[2], bbox[3])
    warnings: list[str] = []

    # Fuentes en paralelo; cada una degrada sin romper.
    norm_res, osm_res, terr_res = await asyncio.gather(
        asyncio.to_thread(arcgis.fetch_normativa, polygon),
        asyncio.to_thread(overpass.fetch_osm, bbox_t),
        asyncio.to_thread(terrain.fetch_terrain, polygon),
        return_exceptions=True,
    )

    # Normativa
    if isinstance(norm_res, Exception):
        warnings.append(f"normativa: error ({norm_res})")
        normativa = {"modo": None, "zonas": [], "restricciones": []}
    else:
        normativa, w = norm_res
        warnings.extend(w)

    # OSM (overpass)
    if isinstance(osm_res, Exception):
        warnings.append(f"overpass: error ({osm_res})")
        layers = {}
    else:
        layers, w = osm_res
        warnings.extend(w)

    # Terreno
    if isinstance(terr_res, Exception):
        warnings.append(f"terrain: error ({terr_res})")
        fisico = {"pendiente_media_pct": None, "pendiente_max_pct": None, "dem_source": None}
    else:
        fisico, w = terr_res
        warnings.extend(w)

    # Distancias / hidrografía / accesibilidad
    hidrografia = normalize.build_hidrografia(geom_m, layers)
    accesibilidad = normalize.build_accesibilidad(geom_m, layers)
    fisico["riesgo_hidrico"] = normalize.riesgo_hidrico(hidrografia)
    fisico["fetch_date"] = _now()

    fetched = _now()
    for z in normativa["zonas"]:
        z.setdefault("fetch_date", fetched)
    for h in hidrografia:
        h.setdefault("source", "OSM")

    # Colapsar warnings idénticos en uno con contador (evita ruido repetido).
    counts: dict[str, int] = {}
    order: list[str] = []
    for w in warnings:
        if w not in counts:
            order.append(w)
        counts[w] = counts.get(w, 0) + 1
    warnings = [f"{w} (x{counts[w]})" if counts[w] > 1 else w for w in order]

    return PolygonContext(
        polygon=polygon,
        bbox=bbox,
        area_ha=area_ha,
        crs_metric=crs_metric(),
        normativa=normativa,
        fisico=fisico,
        hidrografia=hidrografia,
        accesibilidad=accesibilidad,
        parcelas=[],
        warnings=warnings,
    )
