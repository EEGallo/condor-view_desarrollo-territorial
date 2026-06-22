"""Validador de consistencia narrativa↔checks (CAPA 3 §0, §10) — CÓDIGO PROPIO.

Garantiza que el LLM no se desvió: si una explicación contradice su veredicto,
se reemplaza por el detalle técnico (determinístico) y se emite warning. El
`resultado` en sí nunca lo toca el LLM (lo fija el motor), esto cubre la prosa.
"""

from __future__ import annotations


def _contradice(resultado: str, texto: str | None) -> bool:
    if not texto:
        return False
    t = texto.lower()
    if resultado == "no_cumple":
        # afirma "cumple" sin negarlo
        afirma_cumple = "cumple" in t and not any(
            neg in t for neg in ("no cumple", "no_cumple", "incumple", "no cumpl")
        )
        return afirma_cumple
    return False


def validate(checks: list, estado: str) -> list[str]:
    warnings: list[str] = []
    for c in checks:
        if not c.explicacion:
            c.explicacion = c.detalle_tecnico
        if _contradice(c.resultado, c.explicacion):
            warnings.append(
                f"{c.regla}: la explicación contradecía el veredicto "
                f"'{c.resultado}'; reemplazada por el detalle técnico"
            )
            c.explicacion = c.detalle_tecnico
        if c.resultado not in ("cumple", "no_aplica") and c.fuente is None:
            warnings.append(f"{c.regla}: veredicto sin fuente normativa")
    return warnings
