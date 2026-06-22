"""Schema Pydantic de CAPA 3 — DiagnosticReport, CheckResult, Fuente."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Resultado = Literal["cumple", "observacion", "no_cumple", "no_aplica"]
EstadoGlobal = Literal[
    "cumple", "cumple_con_observaciones", "no_cumple", "no_apto"
]

DISCLAIMER = (
    "Diagnóstico orientativo. No reemplaza estudios profesionales ni la "
    "aprobación municipal."
)


class Fuente(BaseModel):
    norma: str
    articulo: str = "<TODO>"


class CheckResult(BaseModel):
    regla: str
    resultado: Resultado
    es_regla_dura: bool = False
    detalle_tecnico: str = ""
    datos: dict[str, Any] = Field(default_factory=dict)
    fuente: Optional[Fuente] = None
    explicacion: Optional[str] = None  # la rellena el LLM (o fallback)


class Riesgo(BaseModel):
    tipo: str
    nivel: str
    nota: str


class ProposedLayout(BaseModel):
    """== SceneModel.metricas de Capa 2."""
    n_lotes: Optional[int] = None
    sup_total_m2: Optional[float] = None
    sup_calles_m2: Optional[float] = None
    sup_lotes_m2: Optional[float] = None
    sup_verde_m2: Optional[float] = None
    sup_verde_pct: Optional[float] = None
    ocupacion_propuesta: Optional[float] = None
    fot_propuesto: Optional[float] = None
    densidad_lotes_ha: Optional[float] = None
    # campo extra opcional (altura máxima del escenario, si se expone)
    altura_max_propuesta_m: Optional[float] = None


class DiagnoseRequest(BaseModel):
    context: dict
    proposed_layout: Optional[ProposedLayout] = None


class DiagnosticReport(BaseModel):
    schema_version: str = "1.0"
    estado_global: EstadoGlobal
    indice_aptitud: int
    evaluo_trazado: bool
    checks: list[CheckResult] = Field(default_factory=list)
    riesgos: list[Riesgo] = Field(default_factory=list)
    resumen_ejecutivo: str = ""
    fuentes_citadas: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
