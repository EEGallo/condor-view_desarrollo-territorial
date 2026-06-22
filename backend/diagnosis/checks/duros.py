"""Checks de regla dura (pueden forzar no_apto): uso, área protegida, hídrico."""

from __future__ import annotations

from typing import Any, Optional

from ..schema import CheckResult, ProposedLayout
from . import FUENTES, USOS_RESERVA, usos_list


def _uso_permitido(context, layout, zona) -> CheckResult:
    usos = usos_list(zona)
    es_reserva = any(u in USOS_RESERVA for u in usos)
    if not usos:
        return CheckResult(
            regla="uso_permitido", resultado="no_aplica", es_regla_dura=True,
            detalle_tecnico="Zona sin uso permitido informado.",
            datos={"uso_permitido": usos}, fuente=FUENTES["uso_permitido"],
        )
    if es_reserva:
        return CheckResult(
            regla="uso_permitido", resultado="no_cumple", es_regla_dura=True,
            detalle_tecnico=f"El uso de la zona ({', '.join(usos)}) corresponde a "
            "reserva: no admite urbanización.",
            datos={"uso_permitido": usos}, fuente=FUENTES["uso_permitido"],
        )
    return CheckResult(
        regla="uso_permitido", resultado="cumple", es_regla_dura=True,
        detalle_tecnico=f"La zona admite usos urbanizables ({', '.join(usos)}).",
        datos={"uso_permitido": usos}, fuente=FUENTES["uso_permitido"],
    )


def _area_protegida(context, layout, zona) -> CheckResult:
    usos = usos_list(zona)
    cat = (zona.get("categoria") or "")
    protegida = any(u in USOS_RESERVA for u in usos) or "reserva" in cat.lower()
    if protegida:
        return CheckResult(
            regla="area_protegida", resultado="no_cumple", es_regla_dura=True,
            detalle_tecnico="El polígono cae en área protegida / reserva.",
            datos={"categoria": cat, "uso_permitido": usos},
            fuente=FUENTES["area_protegida"],
        )
    return CheckResult(
        regla="area_protegida", resultado="cumple", es_regla_dura=True,
        detalle_tecnico="El polígono no intersecta áreas protegidas conocidas.",
        datos={"categoria": cat}, fuente=FUENTES["area_protegida"],
    )


def _restriccion_hidrica(context, layout, zona) -> CheckResult:
    restr = (context.get("normativa") or {}).get("restricciones") or []
    cauce = next((r for r in restr if r.get("tipo") == "retiro_cauce"), None)
    pct = cauce.get("geometria_afectada_pct") if cauce else None
    riesgo = (context.get("fisico") or {}).get("riesgo_hidrico")
    if pct and pct > 0:
        return CheckResult(
            regla="restriccion_hidrica", resultado="no_cumple", es_regla_dura=True,
            detalle_tecnico=f"El {pct}% del polígono cae en retiro de cauce / zona "
            "inundable.",
            datos={"geometria_afectada_pct": pct, "riesgo_hidrico": riesgo},
            fuente=FUENTES["restriccion_hidrica"],
        )
    if riesgo == "alto":
        return CheckResult(
            regla="restriccion_hidrica", resultado="observacion", es_regla_dura=True,
            detalle_tecnico="Riesgo hídrico alto en proximidad, sin intersección "
            "directa de retiro.",
            datos={"riesgo_hidrico": riesgo}, fuente=FUENTES["restriccion_hidrica"],
        )
    return CheckResult(
        regla="restriccion_hidrica", resultado="cumple", es_regla_dura=True,
        detalle_tecnico="Sin intersección con retiros de cauce ni zonas inundables.",
        datos={"riesgo_hidrico": riesgo}, fuente=FUENTES["restriccion_hidrica"],
    )


def run(context: dict[str, Any], layout: Optional[ProposedLayout], zona: dict) -> list:
    return [
        _uso_permitido(context, layout, zona),
        _area_protegida(context, layout, zona),
        _restriccion_hidrica(context, layout, zona),
    ]
