"""Checks de indicadores (blandos): FOS, FOT, altura, sup_min, densidad, verde.

Requieren ProposedLayout. Sin trazado o sin dato de zona -> no_aplica + warning.
"""

from __future__ import annotations

from typing import Any, Optional

from ..schema import CheckResult, ProposedLayout
from . import FUENTES

TOL = 0.02            # tolerancia 2%
MIN_VERDE_PCT = 0.10  # Ord. 12998 Anexo II: 7-10% equipamiento/verde
DENS_MAX = {"baja": 15.0, "media": 40.0, "alta": 1e9}


def _na(regla: str, motivo: str) -> CheckResult:
    return CheckResult(
        regla=regla, resultado="no_aplica", detalle_tecnico=motivo,
        datos={}, fuente=FUENTES[regla],
    )


def _limite(regla, valor, limite, label) -> CheckResult:
    """Patrón ≤ límite con tolerancia; excede leve -> observación, fuerte -> no_cumple."""
    if valor <= limite * (1 + TOL):
        res, det = "cumple", f"{label} propuesto {valor} ≤ {limite} de zona."
    elif valor <= limite * 1.2:
        res, det = "observacion", f"{label} propuesto {valor} supera levemente {limite} de zona."
    else:
        res, det = "no_cumple", f"{label} propuesto {valor} supera {limite} de zona."
    return CheckResult(
        regla=regla, resultado=res,
        detalle_tecnico=det,
        datos={f"{regla}_propuesto": valor, f"{regla}_zona": limite},
        fuente=FUENTES[regla],
    )


def run(context: dict[str, Any], layout: Optional[ProposedLayout], zona: dict) -> list:
    out = []
    if layout is None:
        # Sin trazado: indicadores no evaluables.
        for r in ("fos", "fot", "altura", "sup_min_lote", "densidad", "reserva_verde"):
            out.append(_na(r, "No se evaluó trazado (proposed_layout ausente)."))
        return out

    # FOS
    if zona.get("fos") is None:
        out.append(_na("fos", "FOS de zona no publicado (dato faltante)."))
    elif layout.ocupacion_propuesta is None:
        out.append(_na("fos", "Ocupación propuesta ausente."))
    else:
        out.append(_limite("fos", layout.ocupacion_propuesta, zona["fos"], "Ocupación (FOS)"))

    # FOT
    if zona.get("fot") is None:
        out.append(_na("fot", "FOT de zona no publicado (dato faltante)."))
    elif layout.fot_propuesto is None:
        out.append(_na("fot", "FOT propuesto ausente."))
    else:
        out.append(_limite("fot", layout.fot_propuesto, zona["fot"], "FOT"))

    # Altura
    if zona.get("altura_max_m") is None:
        out.append(_na("altura", "Altura máxima de zona no publicada (dato faltante)."))
    elif layout.altura_max_propuesta_m is None:
        out.append(_na("altura", "Altura propuesta no informada por el trazado."))
    else:
        out.append(_limite("altura", layout.altura_max_propuesta_m, zona["altura_max_m"], "Altura"))

    # Sup mínima de lote (promedio)
    sup_min = zona.get("sup_min_lote_m2")
    if sup_min is None:
        out.append(_na("sup_min_lote", "Superficie mínima de lote no definida."))
    elif not layout.n_lotes or not layout.sup_lotes_m2:
        out.append(_na("sup_min_lote", "Trazado sin lotes."))
    else:
        avg = layout.sup_lotes_m2 / layout.n_lotes
        if avg >= sup_min * (1 - TOL):
            res, det = "cumple", f"Lote promedio {avg:.0f} m² ≥ mínimo {sup_min} m²."
        else:
            res, det = "no_cumple", f"Lote promedio {avg:.0f} m² < mínimo {sup_min} m²."
        out.append(CheckResult(
            regla="sup_min_lote", resultado=res, detalle_tecnico=det,
            datos={"lote_promedio_m2": round(avg, 1), "sup_min_lote_m2": sup_min},
            fuente=FUENTES["sup_min_lote"],
        ))

    # Densidad
    dens_z = (zona.get("densidad") or "").lower()
    if dens_z not in DENS_MAX or layout.densidad_lotes_ha is None:
        out.append(_na("densidad", "Densidad de zona o propuesta no disponible."))
    else:
        maxd = DENS_MAX[dens_z]
        if layout.densidad_lotes_ha <= maxd:
            res, det = "cumple", f"Densidad propuesta {layout.densidad_lotes_ha} lotes/ha coherente con '{dens_z}'."
        else:
            res, det = "observacion", f"Densidad propuesta {layout.densidad_lotes_ha} lotes/ha alta para zona '{dens_z}'."
        out.append(CheckResult(
            regla="densidad", resultado=res, detalle_tecnico=det,
            datos={"densidad_lotes_ha": layout.densidad_lotes_ha, "densidad_zona": dens_z},
            fuente=FUENTES["densidad"],
        ))

    # Reserva verde
    if layout.sup_verde_pct is None:
        out.append(_na("reserva_verde", "Reserva verde propuesta ausente."))
    else:
        v = layout.sup_verde_pct
        if v >= MIN_VERDE_PCT * (1 - TOL):
            res, det = "cumple", f"Reserva verde {v*100:.1f}% ≥ mínimo {MIN_VERDE_PCT*100:.0f}%."
        else:
            res, det = "no_cumple", f"Reserva verde {v*100:.1f}% < mínimo {MIN_VERDE_PCT*100:.0f}%."
        out.append(CheckResult(
            regla="reserva_verde", resultado=res, detalle_tecnico=det,
            datos={"sup_verde_pct": v, "min_verde_pct": MIN_VERDE_PCT},
            fuente=FUENTES["reserva_verde"],
        ))
    return out
