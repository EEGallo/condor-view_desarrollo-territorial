"""Subdivisión de manzanas en lotes (CAPA 2 §5.2).

Por manzana: OBB -> tiras de frente_lote, dos hileras frente-a-frente (fondo
hasta el eje medio). Descarta lotes < sup_min de la zona. CRS métrico.
"""

from __future__ import annotations

from typing import Any

from shapely.affinity import rotate
from shapely.geometry import box

from .street_generator import _largest, _orientation_deg


def subdivide(
    manzanas: list[dict], params, zona: dict[str, Any]
) -> list[dict]:
    """Returns lotes: [{geom, lote_id, manzana_id, sup_m2, zona}]."""
    frente = params.frente_lote_m
    fondo_min = params.fondo_lote_min_m
    sup_min = zona.get("sup_min_lote_m2") or (frente * fondo_min)

    lotes: list[dict] = []
    for mi, m in enumerate(manzanas):
        if not m.get("edificable", True):
            continue
        manzana = m["geom"]
        manzana_id = f"M{mi + 1:02d}"
        ang = _orientation_deg(manzana)
        c = manzana.centroid
        rot = rotate(manzana, -ang, origin=c)
        minx, miny, maxx, maxy = rot.bounds
        w = maxx - minx
        d = maxy - miny
        if w <= 0 or d <= 0:
            continue

        n_cols = max(1, int(w // frente))
        col_w = w / n_cols
        two_rows = d >= 2 * fondo_min
        depth = d / 2.0 if two_rows else d

        li = 0
        for col in range(n_cols):
            x0 = minx + col * col_w
            rects = []
            if two_rows:
                rects.append(box(x0, miny, x0 + col_w, miny + depth))
                rects.append(box(x0, maxy - depth, x0 + col_w, maxy))
            else:
                rects.append(box(x0, miny, x0 + col_w, maxy))
            for r in rects:
                lot = _largest(r.intersection(rot))
                if lot.is_empty or lot.area < sup_min:
                    continue
                li += 1
                lotes.append(
                    {
                        "geom": rotate(lot, ang, origin=c),
                        "lote_id": f"{manzana_id}-L{li:02d}",
                        "manzana_id": manzana_id,
                        "sup_m2": round(lot.area, 1),
                        "zona": zona,
                    }
                )
    return lotes
