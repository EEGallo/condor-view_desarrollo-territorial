"""Checks físicos: aptitud física (pendiente) + riesgo sísmico (informativo)."""

from __future__ import annotations

from typing import Any, Optional

from ..schema import CheckResult, ProposedLayout
from . import FUENTES

PENDIENTE_MAX_PCT = 15.0


def run(context: dict[str, Any], layout: Optional[ProposedLayout], zona: dict) -> list:
    fisico = context.get("fisico") or {}
    pend = fisico.get("pendiente_media_pct")

    if pend is None:
        apt = CheckResult(
            regla="aptitud_fisica", resultado="no_aplica",
            detalle_tecnico="Pendiente no disponible (sin DEM).",
            datos={}, fuente=FUENTES["aptitud_fisica"],
        )
    elif pend <= PENDIENTE_MAX_PCT:
        apt = CheckResult(
            regla="aptitud_fisica", resultado="cumple",
            detalle_tecnico=f"Pendiente media {pend}% ≤ {PENDIENTE_MAX_PCT}% (apta).",
            datos={"pendiente_media_pct": pend, "umbral": PENDIENTE_MAX_PCT},
            fuente=FUENTES["aptitud_fisica"],
        )
    else:
        apt = CheckResult(
            regla="aptitud_fisica", resultado="observacion",
            detalle_tecnico=f"Pendiente media {pend}% supera {PENDIENTE_MAX_PCT}%: "
            "requiere obras de adecuación.",
            datos={"pendiente_media_pct": pend, "umbral": PENDIENTE_MAX_PCT},
            fuente=FUENTES["aptitud_fisica"],
        )

    # Mendoza = zona de peligrosidad sísmica elevada (informativo, siempre aplica).
    sismico = CheckResult(
        regla="riesgo_sismico", resultado="observacion",
        detalle_tecnico="San Rafael (Mendoza) integra zona de peligrosidad sísmica "
        "elevada: aplica INPRES-CIRSOC 103 al diseño estructural.",
        datos={"zona_sismica": "elevada"}, fuente=FUENTES["riesgo_sismico"],
    )
    return [apt, sismico]
