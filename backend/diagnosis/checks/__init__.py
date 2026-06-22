"""Catálogo de checks determinísticos (CAPA 3 §4).

Cada check es una función pura (context, layout, zona) -> CheckResult.
El motor (rules_engine) los corre y deriva estado_global.
"""

from __future__ import annotations

from typing import Any, Optional

from ..schema import Fuente, ProposedLayout

# Fuente normativa por regla (artículo <TODO> hasta confirmar con Ema).
FUENTES: dict[str, Fuente] = {
    "uso_permitido": Fuente(norma="Ordenanza 15214"),
    "area_protegida": Fuente(norma="Ley 8051 / PMOT"),
    "restriccion_hidrica": Fuente(norma="Ley 8051 / DGI"),
    "fos": Fuente(norma="Ordenanza 12998"),
    "fot": Fuente(norma="Ordenanza 12998"),
    "altura": Fuente(norma="Ordenanza 12998"),
    "sup_min_lote": Fuente(norma="Ordenanza 12998"),
    "densidad": Fuente(norma="Ordenanza 12998"),
    "reserva_verde": Fuente(norma="Ordenanza 12998 / Ley 8051"),
    "aptitud_fisica": Fuente(norma="Criterio técnico"),
    "riesgo_sismico": Fuente(norma="INPRES-CIRSOC 103"),
}

USOS_RESERVA = {"reserva_natural", "reserva_hidrica", "reserva_turistica"}


def dominant_zona(context: dict[str, Any]) -> dict[str, Any]:
    zonas = ((context.get("normativa") or {}).get("zonas")) or []
    for z in zonas:
        cat = (z.get("categoria") or "").strip()
        if cat and cat != "sin clasificar":
            return z
    return zonas[0] if zonas else {}


def usos_list(zona: dict[str, Any]) -> list[str]:
    u = zona.get("uso_permitido")
    if isinstance(u, list):
        return [str(x) for x in u]
    if isinstance(u, str) and u:
        return [u]
    return []


def run_checks(
    context: dict[str, Any], layout: Optional[ProposedLayout]
) -> list:
    from . import duros, fisicos, indicadores

    zona = dominant_zona(context)
    checks = []
    checks += duros.run(context, layout, zona)
    checks += indicadores.run(context, layout, zona)
    checks += fisicos.run(context, layout, zona)
    return checks
