"""Cliente ArcGIS on-demand: zonificación por polígono (spec §4.1, §4.4).

Envuelve pipeline/lib/arcgis_client + normativa_resolver, consultando por el
polígono dibujado en vez de por bbox del departamento.
"""

from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

from lib import arcgis_client, normativa_resolver

from .config import crs_exchange, crs_metric


def fetch_normativa(polygon: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Devuelve (normativa_dict, warnings) para un polígono GeoJSON.

    normativa_dict ~ {modo, zonas:[...], restricciones:[...]} con cobertura_pct
    por zona. Degrada a {modo:null, zonas:[]} con warning si ArcGIS no está
    configurado/cae.
    """
    warnings: list[str] = []
    coords = polygon.get("coordinates")
    geojson, w = arcgis_client.fetch_zonificacion(polygon_coordinates=coords)
    warnings.extend(w)

    if geojson is None:
        return {"modo": None, "zonas": [], "restricciones": []}, warnings

    sources = arcgis_client.load_sources()
    resolved, rw = normativa_resolver.resolve_features(geojson, sources=sources)
    # No propagar el warning por-parcela de zona en blanco (se resume abajo).
    warnings.extend(w for w in rw if "no está en zonas.yaml" not in w)

    # cobertura_pct = área(zona ∩ polígono) / área(polígono), en CRS métrico.
    to_metric = Transformer.from_crs(
        crs_exchange(), crs_metric(), always_xy=True
    ).transform
    poly_m = shp_transform(to_metric, shape(polygon))
    poly_area = poly_m.area or 1.0

    modo = normativa_resolver.caso(sources)

    # Agregar por categoría: una fila por zona normativa con cobertura sumada,
    # en vez de una fila por parcela (pueden ser miles). Más útil para el panel.
    agg: dict[str, dict[str, Any]] = {}
    for z in resolved:
        cat = (z.get("categoria") or "").strip() or "sin clasificar"
        geom = z.get("geometry")
        cob = 0.0
        if geom is not None:
            try:
                zona_m = shp_transform(to_metric, shape(geom))
                cob = zona_m.intersection(poly_m).area / poly_area * 100
            except Exception:
                cob = 0.0
        if cat not in agg:
            agg[cat] = {k: v for k, v in z.items() if k != "geometry"}
            agg[cat]["categoria"] = cat
            agg[cat]["cobertura_pct"] = 0.0
            agg[cat]["_n"] = 0
        agg[cat]["cobertura_pct"] += cob
        agg[cat]["_n"] += 1

    zonas = []
    for cat, z in sorted(agg.items(), key=lambda kv: -kv[1]["cobertura_pct"]):
        z["cobertura_pct"] = round(z["cobertura_pct"], 1)
        z["n_parcelas"] = z.pop("_n")
        zonas.append(z)

    # Resumen único de parcelas sin categoría (en vez de una por parcela).
    sc = agg.get("sin clasificar")
    if sc:
        warnings.append(
            f"normativa: {sc.get('n_parcelas')} parcelas con 'zona' en blanco "
            "(sin indicadores)"
        )

    return {"modo": modo, "zonas": zonas, "restricciones": []}, warnings
