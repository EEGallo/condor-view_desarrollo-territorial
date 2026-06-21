"""Ensambla y reproyecta el SceneModel a EPSG:4326 (CAPA 2 §5.6)."""

from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping
from shapely.ops import transform as shp_transform

from ..extraction.config import crs_exchange, crs_metric
from .schema import Masa, Metricas, SceneModel

SIMPLIFY_TOL_M = 0.5


def _to_geo():
    return Transformer.from_crs(crs_metric(), crs_exchange(), always_xy=True).transform


def _fc(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def export(
    *, calles, manzanas, lotes, espacios, masas, metricas, respetadas, warnings,
    sistema: str,
) -> SceneModel:
    to_geo = _to_geo()

    def geo(g):
        return shp_transform(to_geo, g.simplify(SIMPLIFY_TOL_M, preserve_topology=True))

    calles_f = [
        {"type": "Feature", "properties": {"ancho_m": c["ancho_m"], "jerarquia": "local"},
         "geometry": mapping(geo(c["geom"]))}
        for c in calles
    ]
    manzanas_f = [
        {"type": "Feature", "properties": {"manzana_id": f"M{i + 1:02d}"},
         "geometry": mapping(geo(m["geom"]))}
        for i, m in enumerate(manzanas)
    ]
    lotes_f = [
        {"type": "Feature",
         "properties": {"lote_id": l["lote_id"], "sup_m2": l["sup_m2"],
                        "manzana_id": l["manzana_id"],
                        "zona": (l["zona"] or {}).get("categoria")},
         "geometry": mapping(geo(l["geom"]))}
        for l in lotes
    ]
    verdes_f = [
        {"type": "Feature", "properties": {"sup_m2": e["sup_m2"]},
         "geometry": mapping(geo(e["geom"]))}
        for e in espacios
    ]
    masas_m = [
        Masa(
            lote_id=m["lote_id"],
            footprint=mapping(geo(m["footprint"])),
            base_z_m=m["base_z_m"],
            altura_m=m["altura_m"],
            n_pisos=m["n_pisos"],
            uso=m["uso"],
            fos_aplicado=m["fos_aplicado"],
            fot_aplicado=m["fot_aplicado"],
        )
        for m in masas
    ]

    return SceneModel(
        sistema=sistema,
        calles=_fc(calles_f),
        manzanas=_fc(manzanas_f),
        lotes=_fc(lotes_f),
        espacios_verdes=_fc(verdes_f),
        masas=masas_m,
        metricas=Metricas(**metricas),
        restricciones_respetadas=respetadas,
        warnings=warnings,
    )
