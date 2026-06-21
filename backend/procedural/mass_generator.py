"""Lotes -> masas 3D LOD1 (CAPA 2 §5.4).

Cada masa es el SOBRE NORMATIVO del lote: footprint cubre FOS, pisos alcanzan
FOT acotado por altura_max. base_z desde el DEM. CRS métrico.
"""

from __future__ import annotations

import math
from typing import Any

from shapely.affinity import scale

from ..extraction.config import DEM_PATH

ALTURA_PISO = 3.0
DEFAULT_FOS = 0.40
DEFAULT_FOT = 0.60
DEFAULT_ALTURA = 9.0


def _first_uso(z: dict[str, Any]) -> str:
    u = z.get("uso_permitido")
    if isinstance(u, list) and u:
        return str(u[0])
    if isinstance(u, str) and u:
        return u
    return "residencial"


def _open_dem():
    if not DEM_PATH.exists():
        return None
    import rasterio

    return rasterio.open(DEM_PATH)


def generate(lotes: list[dict]) -> tuple[list[dict], list[str]]:
    """Returns (masas, warnings). footprint en CRS métrico (5343)."""
    warnings: list[str] = []
    if not lotes:
        return [], warnings

    src = _open_dem()
    if src is None:
        warnings.append("mass: DEM no disponible, base_z_m=0")
    nodata = src.nodata if src is not None else None

    used_defaults = False
    masas: list[dict] = []
    for lot in lotes:
        z = lot["zona"]
        fos = z.get("fos")
        fot = z.get("fot")
        alt_max = z.get("altura_max_m")
        if fos is None or fot is None or alt_max is None:
            used_defaults = True
            fos = fos if fos is not None else DEFAULT_FOS
            fot = fot if fot is not None else DEFAULT_FOT
            alt_max = alt_max if alt_max is not None else DEFAULT_ALTURA

        geom = lot["geom"]
        sup = geom.area
        s = math.sqrt(max(0.0, min(1.0, fos)))
        footprint = scale(geom, s, s, origin="centroid")

        n_pisos = max(1, min(int(fot / fos) if fos > 0 else 1,
                             int(alt_max / ALTURA_PISO)))
        altura = min(n_pisos * ALTURA_PISO, alt_max)
        fot_aplicado = round(footprint.area * n_pisos / sup, 3) if sup else 0.0

        base_z = 0.0
        if src is not None:
            cx, cy = footprint.centroid.x, footprint.centroid.y
            try:
                v = next(src.sample([(cx, cy)]))[0]
                if nodata is None or v != nodata:
                    base_z = round(float(v), 1)
            except Exception:
                pass

        masas.append(
            {
                "lote_id": lot["lote_id"],
                "footprint": footprint,
                "base_z_m": base_z,
                "altura_m": round(altura, 1),
                "n_pisos": n_pisos,
                "uso": _first_uso(z),
                "fos_aplicado": round(footprint.area / sup, 3) if sup else 0.0,
                "fot_aplicado": fot_aplicado,
            }
        )

    if src is not None:
        src.close()
    if used_defaults:
        warnings.append(
            "mass: zona sin FOS/FOT/altura -> defaults "
            f"(fos {DEFAULT_FOS}, fot {DEFAULT_FOT}, altura {DEFAULT_ALTURA}m)"
        )
    return masas, warnings
