"""Orquestador CAPA 2: generate(context, params) -> SceneModel.

Cómputo en EPSG:5343; el exporter reproyecta a 4326.
"""

from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

from ..extraction.config import crs_exchange, crs_metric
from . import (
    block_subdivider,
    green_allocator,
    mass_generator,
    metrics,
    restrictions,
    scene_exporter,
    street_generator,
)
from .schema import SceneModel, TrazadoParams

DEFAULT_ZONA = {
    "categoria": None, "uso_permitido": "rural",
    "sup_min_lote_m2": None, "fos": None, "fot": None, "altura_max_m": None,
}


def _dominant_zona(context: dict[str, Any]) -> dict[str, Any]:
    zonas = ((context.get("normativa") or {}).get("zonas")) or []
    for z in zonas:  # ya vienen ordenadas por cobertura desc
        cat = (z.get("categoria") or "").strip()
        if cat and cat != "sin clasificar":
            return z
    return zonas[0] if zonas else DEFAULT_ZONA


def generate(context: dict[str, Any], params: TrazadoParams) -> SceneModel:
    warnings: list[str] = []

    polygon_gj = context.get("polygon")
    if not polygon_gj:
        raise ValueError("context.polygon ausente")
    to_metric = Transformer.from_crs(
        crs_exchange(), crs_metric(), always_xy=True
    ).transform
    poly_m = shp_transform(to_metric, shape(polygon_gj))

    zona = _dominant_zona(context)

    urb, respetadas, w = restrictions.urbanizable(poly_m, context)
    warnings.extend(w)
    if urb.is_empty or urb.area <= 0:
        warnings.append("generate: área urbanizable vacía")

    manzanas, calles, w = street_generator.generate(urb, params, context)
    warnings.extend(w)

    espacios, manzanas_edif, sup_verde = green_allocator.allocate(
        manzanas, params, urb.area
    )

    lotes = block_subdivider.subdivide(manzanas_edif, params, zona)

    masas, w = mass_generator.generate(lotes)
    warnings.extend(w)

    met = metrics.compute(urb.area, lotes, espacios, masas)

    return scene_exporter.export(
        calles=calles,
        manzanas=manzanas_edif,
        lotes=lotes,
        espacios=espacios,
        masas=masas,
        metricas=met,
        respetadas=respetadas,
        warnings=warnings,
        sistema=params.sistema,
    )
