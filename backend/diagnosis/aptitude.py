"""Modelo de aptitud multicriterio (CAPA 3 §5) — reusa el del MVP.

indice_aptitud = 100·(0.40·S_norm + 0.30·S_fis + 0.30·S_acc). Eje SEPARADO del
cumplimiento (§1). CÓDIGO PROPIO.
"""

from __future__ import annotations

import math
from typing import Any

from .checks import dominant_zona, usos_list

# uso -> S_norm (mismo mapa que pipeline/lib/normativa_resolver.py)
USO_S_NORM = {
    "residencial_alta": 1.0, "residencial_media": 1.0, "residencial_baja": 0.9,
    "residencial": 1.0, "comercial": 1.0, "mixto": 1.0, "industrial": 0.5,
    "condicionado": 0.5, "agricola": 0.7, "rural": 0.3,
    "reserva_natural": 0.0, "reserva_hidrica": 0.0, "reserva_turistica": 0.0,
}
W_NORM, W_FIS, W_ACC = 0.40, 0.30, 0.30
SLOPE_IDEAL, SLOPE_MAX = 5.0, 25.0
D0_HUELLA, D0_VIAL, D0_AGUA = 8000.0, 5000.0, 6000.0
HIDRICO = {"bajo": 1.0, "moderado": 0.5, "alto": 0.0}


def _s_norm(zona: dict) -> float:
    usos = usos_list(zona)
    return USO_S_NORM.get(usos[0], 0.3) if usos else 0.3


def _s_fis(context: dict) -> float:
    f = context.get("fisico") or {}
    pend = f.get("pendiente_media_pct")
    if pend is None:
        slope = 0.5
    elif pend <= SLOPE_IDEAL:
        slope = 1.0
    elif pend >= SLOPE_MAX:
        slope = 0.0
    else:
        slope = 1 - (pend - SLOPE_IDEAL) / (SLOPE_MAX - SLOPE_IDEAL)
    hidrico = HIDRICO.get(f.get("riesgo_hidrico"), 1.0)
    return max(0.0, slope) * hidrico


def _s_acc(context: dict) -> float:
    a = context.get("accesibilidad") or {}
    dh = a.get("dist_huella_urbana_m")
    dv = a.get("dist_vial_principal_m")
    hid = context.get("hidrografia") or []
    da = min((h.get("dist_m") for h in hid if h.get("dist_m") is not None), default=None)

    def decay(d, d0):
        return math.exp(-d / d0) if d is not None else 0.0

    return 0.45 * decay(dh, D0_HUELLA) + 0.35 * decay(dv, D0_VIAL) + 0.20 * decay(da, D0_AGUA)


def indice_aptitud(context: dict[str, Any]) -> int:
    zona = dominant_zona(context)
    iat = 100 * (W_NORM * _s_norm(zona) + W_FIS * _s_fis(context) + W_ACC * _s_acc(context))
    return int(round(max(0.0, min(100.0, iat))))
