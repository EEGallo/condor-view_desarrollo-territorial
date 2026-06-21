"""Cóndor View — Backend de extracción (CAPA 1, spec §1).

FastAPI. Endpoint principal POST /api/extract; sub-recursos GET reutilizables.

Run:  uvicorn backend.main:app --reload   (desde la raíz del repo)
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.extraction import arcgis, overpass, terrain
from backend.extraction.extract import extract
from backend.extraction.schema import ExtractRequest, PolygonContext
from backend.procedural.generate import generate as generate_scene
from backend.procedural.schema import GenerateRequest, SceneModel

app = FastAPI(title="Cóndor View — Extracción", version="1.1")

# El frontend Next.js (localhost:3000) consume estos endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
        return parts[0], parts[1], parts[2], parts[3]
    except ValueError:
        raise HTTPException(400, "bbox debe ser 'minLon,minLat,maxLon,maxLat'")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/extract", response_model=PolygonContext)
async def post_extract(req: ExtractRequest) -> PolygonContext:
    if req.polygon.get("type") != "Polygon":
        raise HTTPException(400, "polygon debe ser un GeoJSON Polygon")
    return await extract(req.polygon)


@app.post("/api/generate", response_model=SceneModel)
def post_generate(req: GenerateRequest) -> SceneModel:
    """CAPA 2: PolygonContext -> escenario 3D procedural (SceneModel)."""
    if not req.context.get("polygon"):
        raise HTTPException(400, "context.polygon requerido")
    return generate_scene(req.context, req.params)


@app.get("/api/zonas")
def get_zonas(bbox: str) -> dict:
    """Zonificación normalizada (proxy ArcGIS) por bbox. Cacheable."""
    minx, miny, maxx, maxy = _parse_bbox(bbox)
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny],
        ]],
    }
    normativa, parcelas, warnings = arcgis.fetch_normativa(polygon)
    return {"normativa": normativa, "parcelas": parcelas, "warnings": warnings}


@app.get("/api/equipamiento")
def get_equipamiento(bbox: str, tipos: str | None = None) -> dict:
    """Equipamiento (PDI) vía Overpass por bbox."""
    bb = _parse_bbox(bbox)
    layers, warnings = overpass.fetch_osm(bb)
    equip = layers.get("equipamiento")
    out = []
    if equip is not None:
        wanted = set(tipos.split(",")) if tipos else None
        from .extraction.normalize import _clean_str

        for _, row in equip.iterrows():
            if wanted and row["tipo"] not in wanted:
                continue
            out.append({"tipo": str(row["tipo"]), "nombre": _clean_str(row.get("nombre"))})
    return {"equipamiento": out, "warnings": warnings}


@app.get("/api/terrain")
def get_terrain(bbox: str) -> dict:
    """Pendiente/riesgo del DEM para el bbox (como polígono rectangular)."""
    minx, miny, maxx, maxy = _parse_bbox(bbox)
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny],
        ]],
    }
    fisico, warnings = terrain.fetch_terrain(polygon)
    return {"fisico": fisico, "warnings": warnings}
