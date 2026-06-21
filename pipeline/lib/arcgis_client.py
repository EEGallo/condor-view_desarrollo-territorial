"""Cliente ArcGIS FeatureServer (CAPA 1, spec §4.1).

Consulta features de zonificación/restricciones/catastro de la UGDT que
intersecan un polígono o bbox. Degradación elegante: si el FeatureServer no
está configurado (base_url = <TODO> / vacío), retorna None y un warning — el
llamador cae al proxy OSM landuse, sin romper.

Sin dependencias externas: usa urllib (stdlib).
"""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SOURCES_PATH = CONFIG_DIR / "sources.yaml"

DEFAULT_TIMEOUT = 25


def load_sources(path: Path | None = None) -> dict[str, Any]:
    with open(path or SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _is_todo(value: Any) -> bool:
    """True si el valor está sin completar (None, vacío o placeholder <TODO>)."""
    if value is None:
        return True
    if isinstance(value, str):
        v = value.strip()
        return v == "" or v.startswith("<TODO")
    return False


def is_configured(sources: dict[str, Any]) -> bool:
    """¿El FeatureServer ArcGIS está listo para consultarse?"""
    arc = sources.get("arcgis") or {}
    if _is_todo(arc.get("base_url")):
        return False
    zon = arc.get("zonificacion") or {}
    if _is_todo(zon.get("layer_id")):
        return False
    field_map = zon.get("field_map") or {}
    if _is_todo(field_map.get("categoria")):
        return False
    return True


def _bbox_envelope(bbox: tuple[float, float, float, float]) -> str:
    """bbox (minLon, minLat, maxLon, maxLat) -> Esri envelope JSON."""
    min_lon, min_lat, max_lon, max_lat = bbox
    env = {
        "xmin": min_lon,
        "ymin": min_lat,
        "xmax": max_lon,
        "ymax": max_lat,
        "spatialReference": {"wkid": 4326},
    }
    return json.dumps(env)


def _esri_polygon(coordinates: list) -> str:
    """Anillos GeoJSON (lon/lat) -> Esri polygon JSON."""
    poly = {"rings": coordinates, "spatialReference": {"wkid": 4326}}
    return json.dumps(poly)


def _query_url(base_url: str, layer_id: str | int) -> str:
    return f"{base_url.rstrip('/')}/{layer_id}/query"


def _esri_to_geojson(esri: dict[str, Any]) -> dict[str, Any]:
    """Convierte respuesta ArcGIS f=json a GeoJSON FeatureCollection.

    Soporta polígonos (rings), puntos y polilíneas. Fallback usado solo si el
    server no soporta f=geojson (ArcGIS viejo).
    """
    features = []
    for feat in esri.get("features", []):
        attrs = feat.get("attributes", {})
        geom = feat.get("geometry")
        gj_geom = None
        if geom:
            if "rings" in geom:
                gj_geom = {"type": "Polygon", "coordinates": geom["rings"]}
            elif "paths" in geom:
                gj_geom = {"type": "MultiLineString", "coordinates": geom["paths"]}
            elif "x" in geom and "y" in geom:
                gj_geom = {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
        features.append({"type": "Feature", "properties": attrs, "geometry": gj_geom})
    return {"type": "FeatureCollection", "features": features}


def query_layer(
    layer_id: str | int,
    *,
    sources: dict[str, Any],
    polygon_coordinates: list | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Consulta una capa del FeatureServer. Devuelve GeoJSON FeatureCollection.

    Pasar polygon_coordinates (anillos GeoJSON) o bbox. Lanza si la red falla;
    el llamador decide la degradación.
    """
    arc = sources["arcgis"]
    base_url = arc["base_url"]
    auth = (arc.get("zonificacion") or {}).get("auth", "none")
    token = (arc.get("zonificacion") or {}).get("token")

    params: dict[str, str] = {
        "geometryType": "esriGeometryPolygon"
        if polygon_coordinates is not None
        else "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": "4326",
        "outSR": "4326",
        "outFields": "*",
        "where": "1=1",
        "f": "geojson",
    }
    if polygon_coordinates is not None:
        params["geometry"] = _esri_polygon(polygon_coordinates)
    elif bbox is not None:
        params["geometry"] = _bbox_envelope(bbox)
    else:
        raise ValueError("query_layer requiere polygon_coordinates o bbox")

    if auth == "token" and token:
        params["token"] = token

    url = _query_url(base_url, layer_id) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "condor-view/1.0"})

    # Algunos servidores gov (p.ej. mendoza.gov.ar) tienen cadena de cert
    # incompleta. verify_ssl: false usa contexto sin verificación.
    ctx = None
    if arc.get("verify_ssl") is False:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    # Si el server no soportó f=geojson y devolvió esri json, convertir.
    if "features" in raw and raw.get("type") != "FeatureCollection":
        return _esri_to_geojson(raw)
    return raw


def fetch_zonificacion(
    *,
    polygon_coordinates: list | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    sources: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Trae la capa de zonificación. Degradación elegante.

    Returns (geojson | None, warnings). geojson None si no está configurado
    o si la consulta falla.
    """
    warnings: list[str] = []
    src = sources or load_sources()

    if not is_configured(src):
        warnings.append(
            "arcgis: FeatureServer no configurado (sources.yaml con <TODO>); "
            "usando fallback OSM landuse"
        )
        return None, warnings

    layer_id = src["arcgis"]["zonificacion"]["layer_id"]
    try:
        gj = query_layer(
            layer_id,
            sources=src,
            polygon_coordinates=polygon_coordinates,
            bbox=bbox,
        )
        # No silenciar truncamiento: ArcGIS limita por maxRecordCount.
        if gj.get("exceededTransferLimit") or gj.get("properties", {}).get(
            "exceededTransferLimit"
        ):
            warnings.append(
                f"arcgis: respuesta truncada por maxRecordCount "
                f"({len(gj.get('features', []))} features); falta paginar "
                "(resultOffset) para cubrir todo el bbox"
            )
        return gj, warnings
    except Exception as exc:  # red caída, timeout, etc.
        warnings.append(f"arcgis: consulta falló ({exc}); usando fallback OSM landuse")
        return None, warnings
