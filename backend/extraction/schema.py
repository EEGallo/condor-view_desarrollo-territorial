"""Schema Pydantic de PolygonContext (CAPA 1, spec §3, schema_version 1.1).

Equivalente Python del Zod de la spec. Toda capa lleva source + fetch_date.
Fuente caída -> campos null + warning; nunca rompe la respuesta.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

GeoJSONPolygon = dict  # {"type": "Polygon", "coordinates": [...]}


class ExtractRequest(BaseModel):
    polygon: GeoJSONPolygon


class Zona(BaseModel):
    categoria: Optional[str] = None
    uso_permitido: Optional[list[str] | str] = None
    fos: Optional[float] = None
    fot: Optional[float] = None
    altura_max_m: Optional[float] = None
    densidad: Optional[str] = None
    sup_min_lote_m2: Optional[float] = None
    cobertura_pct: Optional[float] = None
    n_parcelas: Optional[int] = None
    source: Optional[str] = None
    fetch_date: Optional[str] = None
    # Crudos + flags de variantes (trazabilidad / citación legal, Capa 3).
    normativa_raw: Optional[dict] = None


class Restriccion(BaseModel):
    tipo: str
    geometria_afectada_pct: Optional[float] = None
    source: Optional[str] = None


class Normativa(BaseModel):
    modo: Optional[Literal["atributos", "tabla"]] = None
    zonas: list[Zona] = Field(default_factory=list)
    restricciones: list[Restriccion] = Field(default_factory=list)


class Fisico(BaseModel):
    pendiente_media_pct: Optional[float] = None
    pendiente_max_pct: Optional[float] = None
    riesgo_hidrico: Optional[Literal["bajo", "moderado", "alto"]] = None
    dem_source: Optional[str] = None
    fetch_date: Optional[str] = None


class Hidrografia(BaseModel):
    tipo: str
    nombre: Optional[str] = None
    dist_m: Optional[float] = None
    source: Optional[str] = None


class Equipamiento(BaseModel):
    tipo: str
    nombre: Optional[str] = None
    dist_m: Optional[float] = None
    source: Optional[str] = None


class Accesibilidad(BaseModel):
    dist_huella_urbana_m: Optional[float] = None
    dist_vial_principal_m: Optional[float] = None
    equipamiento: list[Equipamiento] = Field(default_factory=list)


class Parcela(BaseModel):
    id: Optional[str] = None
    sup_m2: Optional[float] = None
    source: Optional[str] = None


class PolygonContext(BaseModel):
    schema_version: str = "1.1"
    polygon: GeoJSONPolygon
    bbox: list[float]
    area_ha: float
    crs_metric: str

    normativa: Normativa = Field(default_factory=Normativa)
    fisico: Fisico = Field(default_factory=Fisico)
    hidrografia: list[Hidrografia] = Field(default_factory=list)
    accesibilidad: Accesibilidad = Field(default_factory=Accesibilidad)
    parcelas: list[Parcela] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
