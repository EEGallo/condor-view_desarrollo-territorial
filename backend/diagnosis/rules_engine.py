"""Motor de reglas determinístico (CAPA 3 §4) — decide estado_global.

CÓDIGO PROPIO. El LLM nunca toca esto.
"""

from __future__ import annotations

from typing import Any, Optional

from .checks import run_checks
from .schema import EstadoGlobal, ProposedLayout


def estado_global(checks: list) -> EstadoGlobal:
    if any(c.es_regla_dura and c.resultado == "no_cumple" for c in checks):
        return "no_apto"
    if any(c.resultado == "no_cumple" for c in checks):
        return "no_cumple"
    if any(c.resultado == "observacion" for c in checks):
        return "cumple_con_observaciones"
    return "cumple"


def evaluate(
    context: dict[str, Any], layout: Optional[ProposedLayout]
) -> tuple[list, EstadoGlobal, list[str]]:
    checks = run_checks(context, layout)
    warnings = [
        f"{c.regla}: dato faltante, check no_aplica"
        for c in checks
        if c.resultado == "no_aplica"
    ]
    return checks, estado_global(checks), warnings
