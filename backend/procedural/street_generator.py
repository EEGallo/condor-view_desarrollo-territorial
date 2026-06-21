"""Trazado damero: calles + manzanas (CAPA 2 §5.1).

Trabaja en un marco rotado (calles eje-alineadas) y rota de vuelta. CRS métrico.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from shapely.affinity import rotate
from shapely.geometry import LineString, box


def _orientation_deg(polygon_m) -> float:
    """Ángulo (deg) del borde más largo del minimum rotated rectangle."""
    mrr = polygon_m.minimum_rotated_rectangle
    pts = list(mrr.exterior.coords)[:5]
    best_len, best_ang = 0.0, 0.0
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        d = math.hypot(dx, dy)
        if d > best_len:
            best_len = d
            best_ang = math.degrees(math.atan2(dy, dx))
    return best_ang


def _largest(geom):
    if geom.is_empty:
        return geom
    if geom.geom_type == "MultiPolygon":
        return max(geom.geoms, key=lambda g: g.area)
    return geom


def generate(
    urbanizable_m, params, context: dict[str, Any]
) -> tuple[list[dict], list[dict], list[str]]:
    """Returns (manzanas, calles, warnings).

    manzanas: [{geom, edificable: bool}]; calles: [{geom: LineString, ancho_m}].
    """
    warnings: list[str] = []
    lado = params.lado_manzana_m
    calle = params.ancho_calle_m
    pitch = lado + calle

    theta = (
        params.orientacion_deg
        if params.orientacion_deg is not None
        else _orientation_deg(urbanizable_m)
    )
    origin = urbanizable_m.centroid
    rot = rotate(urbanizable_m, -theta, origin=origin)

    minx, miny, maxx, maxy = rot.bounds
    xs = np.arange(minx, maxx, pitch)
    ys = np.arange(miny, maxy, pitch)

    # Gate de pendiente a nivel polígono (MVP): si la zona es muy empinada,
    # todas las manzanas quedan no_edificable -> candidatas a verde.
    pend = (context.get("fisico") or {}).get("pendiente_media_pct")
    edificable_default = not (pend is not None and pend > params.slope_max_buildable_pct)
    if not edificable_default:
        warnings.append(
            f"pendiente media {pend}% > {params.slope_max_buildable_pct}% "
            "-> manzanas no edificables (verde)"
        )

    min_area = 0.25 * lado * lado
    manzanas: list[dict] = []
    for x in xs:
        for y in ys:
            inter = _largest(box(x, y, x + lado, y + lado).intersection(rot))
            if not inter.is_empty and inter.area >= min_area:
                manzanas.append(
                    {"geom": rotate(inter, theta, origin=origin),
                     "edificable": edificable_default}
                )

    calles: list[dict] = []
    for x in xs:
        cx = x + lado + calle / 2.0
        seg = LineString([(cx, miny), (cx, maxy)]).intersection(rot)
        if not seg.is_empty:
            calles.append({"geom": rotate(seg, theta, origin=origin), "ancho_m": calle})
    for y in ys:
        cy = y + lado + calle / 2.0
        seg = LineString([(minx, cy), (maxx, cy)]).intersection(rot)
        if not seg.is_empty:
            calles.append({"geom": rotate(seg, theta, origin=origin), "ancho_m": calle})

    if not manzanas:
        warnings.append("street_generator: no se generaron manzanas (polígono chico?)")
    return manzanas, calles, warnings
