"""Schema Pydantic de CAPA 2 — TrazadoParams, SceneModel, ProposedLayout."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

GeoJSON = dict


class TrazadoParams(BaseModel):
    sistema: str = "damero"          # MVP: solo damero
    orientacion_deg: Optional[float] = None  # null => borde más largo
    ancho_calle_m: float = 15
    ancho_avenida_m: float = 25
    lado_manzana_m: float = 100
    frente_lote_m: float = 12
    fondo_lote_min_m: float = 25
    reserva_verde_pct: float = 0.10
    slope_max_buildable_pct: float = 15


class GenerateRequest(BaseModel):
    context: dict                     # PolygonContext (de /api/extract)
    params: TrazadoParams = Field(default_factory=TrazadoParams)


class Masa(BaseModel):
    lote_id: str
    footprint: GeoJSON
    base_z_m: float
    altura_m: float
    n_pisos: int
    uso: Optional[str] = None
    fos_aplicado: Optional[float] = None
    fot_aplicado: Optional[float] = None


class Metricas(BaseModel):
    """== ProposedLayout para la futura Capa 3."""
    n_lotes: int
    sup_total_m2: float
    sup_calles_m2: float
    sup_lotes_m2: float
    sup_verde_m2: float
    sup_verde_pct: float
    ocupacion_propuesta: float
    fot_propuesto: float
    densidad_lotes_ha: float


class SceneModel(BaseModel):
    schema_version: str = "1.0"
    crs: str = "EPSG:4326"
    sistema: str = "damero"
    calles: GeoJSON
    manzanas: GeoJSON
    lotes: GeoJSON
    espacios_verdes: GeoJSON
    masas: list[Masa] = Field(default_factory=list)
    metricas: Metricas
    restricciones_respetadas: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
