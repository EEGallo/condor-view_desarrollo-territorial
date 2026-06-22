"""Orquestador CAPA 3: diagnose(context, layout) -> DiagnosticReport (§3)."""

from __future__ import annotations

from typing import Any, Optional

from . import aptitude, norm_retriever, report_composer, rules_engine, validator
from .schema import DiagnosticReport, ProposedLayout, Riesgo


def diagnose(
    context: dict[str, Any], layout: Optional[ProposedLayout]
) -> DiagnosticReport:
    # 1) Motor de reglas (decide) — determinístico.
    checks, estado, warnings = rules_engine.evaluate(context, layout)

    # 2) Aptitud (eje separado del cumplimiento).
    aptitud = aptitude.indice_aptitud(context)

    # 3) Retrieval normativo por check.
    retrieved = {
        c.regla: norm_retriever.retrieve(
            c.regla, c.fuente.norma if c.fuente else None
        )
        for c in checks
    }

    # 4) Redacción (LLM solo redacta; degrada a determinístico).
    explicaciones, resumen, comp_warnings = report_composer.compose(
        checks, retrieved, estado, aptitud
    )
    for c in checks:
        c.explicacion = explicaciones.get(c.regla) or c.detalle_tecnico

    # 5) Validación de consistencia (puede reemplazar explicaciones desviadas).
    val_warnings = validator.validate(checks, estado)

    riesgos = [
        Riesgo(tipo="sismico", nivel="alto", nota="Aplica INPRES-CIRSOC 103.")
    ]
    fuentes = sorted({c.fuente.norma for c in checks if c.fuente})

    return DiagnosticReport(
        estado_global=estado,
        indice_aptitud=aptitud,
        evaluo_trazado=layout is not None,
        checks=checks,
        riesgos=riesgos,
        resumen_ejecutivo=resumen,
        fuentes_citadas=fuentes,
        warnings=warnings + comp_warnings + val_warnings,
    )
