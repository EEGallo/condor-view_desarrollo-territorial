"""Reserva de espacios verdes (CAPA 2 §5.3).

Manzanas no_edificable (pendiente/restricción) -> verde. Si no alcanzan el
reserva_verde_pct del área urbanizable, convierte manzanas adicionales hasta
llegar. CRS métrico.
"""

from __future__ import annotations


def allocate(
    manzanas: list[dict], params, urbanizable_area: float
) -> tuple[list[dict], list[dict], float]:
    """Returns (espacios_verdes, manzanas_edificables, sup_verde_m2)."""
    verdes = [m for m in manzanas if not m.get("edificable", True)]
    edificables = [m for m in manzanas if m.get("edificable", True)]

    sup_verde = sum(m["geom"].area for m in verdes)
    target = params.reserva_verde_pct * urbanizable_area

    # Convertir manzanas adicionales (peor aptitud ~ las más chicas primero).
    edificables.sort(key=lambda m: m["geom"].area)
    i = 0
    while sup_verde < target and i < len(edificables):
        m = edificables[i]
        verdes.append(m)
        sup_verde += m["geom"].area
        i += 1
    edificables = edificables[i:]

    espacios = [{"geom": m["geom"], "sup_m2": round(m["geom"].area, 1)} for m in verdes]
    return espacios, edificables, round(sup_verde, 1)
