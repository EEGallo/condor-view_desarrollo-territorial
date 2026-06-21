"""Cliente OSM on-demand (spec §4.2).

Lee los gpkg que el pipeline YA descargó (pipeline/data/raw/osm_*.gpkg) y los
recorta al bbox del polígono. Fuente local = confiable y offline; evita el
endpoint público de Overpass (flaky / rate-limited). Si falta un gpkg, cae a
Overpass en vivo vía osmnx.

Devuelve GeoDataFrames en EPSG:4326; normalize.py reproyecta y calcula
distancias.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd

from .config import RAW_DIR

# Roads que cuentan como "vial principal".
VIAL_PRINCIPAL = {"motorway", "trunk", "primary", "secondary"}

# Tags OSM para fallback en vivo (si falta el gpkg local).
EQUIPAMIENTO_TAGS: dict[str, dict[str, Any]] = {
    "escuela": {"amenity": ["school", "kindergarten", "college", "university"]},
    "hospital": {"amenity": ["hospital", "clinic", "doctors"]},
    "salud": {"amenity": ["pharmacy"]},
}


def _clip(gpkg: str, bbox: tuple[float, float, float, float]) -> "gpd.GeoDataFrame | None":
    """Lee un gpkg local, reproyecta a 4326 y recorta al bbox. None si no existe."""
    path = RAW_DIR / gpkg
    if not path.exists():
        return None
    gdf = gpd.read_file(path).to_crs("EPSG:4326")
    minx, miny, maxx, maxy = bbox
    sub = gdf.cx[minx:maxx, miny:maxy]
    sub = sub[sub.geometry.notna() & ~sub.geometry.is_empty]
    return sub if len(sub) else gdf.iloc[0:0]  # gdf vacío conserva columnas


def _equip_tipo(amenity: Any) -> str:
    a = str(amenity or "").lower()
    if a in ("hospital", "clinic", "doctors"):
        return "hospital"
    if a == "pharmacy":
        return "salud"
    return "escuela"


def _from_local(
    bbox: tuple[float, float, float, float],
) -> "tuple[dict[str, gpd.GeoDataFrame], list[str]] | None":
    """Arma las capas desde gpkg locales. None si no hay ninguno (sin pipeline)."""
    roads = _clip("osm_roads.gpkg", bbox)
    edu = _clip("osm_educacion.gpkg", bbox)
    salud = _clip("osm_salud.gpkg", bbox)
    water = _clip("osm_waterways.gpkg", bbox)
    places = _clip("osm_places.gpkg", bbox)

    if all(x is None for x in (roads, edu, salud, water, places)):
        return None

    warnings: list[str] = []
    layers: dict[str, gpd.GeoDataFrame] = {}

    # Equipamiento (educación + salud) con tipo + nombre.
    equip_rows = []
    if edu is not None:
        for _, r in edu.iterrows():
            equip_rows.append({"tipo": "escuela", "nombre": r.get("name"), "geometry": r.geometry})
    if salud is not None:
        for _, r in salud.iterrows():
            equip_rows.append(
                {"tipo": _equip_tipo(r.get("amenity")), "nombre": r.get("name"), "geometry": r.geometry}
            )
    if equip_rows:
        layers["equipamiento"] = gpd.GeoDataFrame(equip_rows, crs="EPSG:4326")
    else:
        warnings.append("osm-local: sin equipamiento en el área")

    # Hidrografía.
    if water is not None and len(water):
        layers["hidrografia"] = water
    else:
        warnings.append("osm-local: sin hidrografía en el área")

    # Vial principal.
    if roads is not None and "highway" in roads.columns:
        vial = roads[roads["highway"].isin(VIAL_PRINCIPAL)]
        if len(vial):
            layers["vial"] = vial
        else:
            warnings.append("osm-local: sin vial principal en el área")
    else:
        warnings.append("osm-local: sin red vial en el área")

    # Huella urbana (localidades).
    if places is not None and len(places):
        layers["places"] = places
    else:
        warnings.append("osm-local: sin localidades en el área")

    return layers, warnings


# --- Fallback Overpass en vivo (solo si no hay gpkg locales) ---

def _safe_features(bbox: tuple[float, float, float, float], tags: dict):
    import osmnx as ox

    ox.settings.overpass_rate_limit = False
    w, s, e, n = bbox
    try:
        gdf = ox.features_from_bbox(bbox=(w, s, e, n), tags=tags)
        return gdf if len(gdf) else None
    except Exception:
        return None


def _from_overpass(
    bbox: tuple[float, float, float, float],
) -> tuple[dict[str, gpd.GeoDataFrame], list[str]]:
    warnings = ["osm: usando Overpass en vivo (sin gpkg locales del pipeline)"]
    layers: dict[str, gpd.GeoDataFrame] = {}
    w, s, e, n = bbox

    equip_rows = []
    for tipo, tags in EQUIPAMIENTO_TAGS.items():
        gdf = _safe_features((w, s, e, n), tags)
        if gdf is None:
            continue
        for _, row in gdf.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                continue
            equip_rows.append({"tipo": tipo, "nombre": row.get("name"), "geometry": row.geometry})
    if equip_rows:
        layers["equipamiento"] = gpd.GeoDataFrame(equip_rows, crs="EPSG:4326")
    else:
        warnings.append("overpass: sin equipamiento (API caída o sin datos)")

    hid = _safe_features((w, s, e, n), {"waterway": ["river", "stream", "canal"]})
    if hid is not None:
        layers["hidrografia"] = hid[hid.geometry.notna()].to_crs("EPSG:4326")
    else:
        warnings.append("overpass: sin hidrografía (API caída o sin datos)")

    vial = _safe_features((w, s, e, n), {"highway": list(VIAL_PRINCIPAL)})
    if vial is not None:
        layers["vial"] = vial[vial.geometry.notna()].to_crs("EPSG:4326")
    else:
        warnings.append("overpass: sin vial (API caída o sin datos)")

    return layers, warnings


def fetch_osm(
    bbox: tuple[float, float, float, float],
) -> tuple[dict[str, gpd.GeoDataFrame], list[str]]:
    """bbox = (minLon, minLat, maxLon, maxLat).

    Prioriza gpkg locales del pipeline; si no hay ninguno, cae a Overpass.
    """
    local = _from_local(bbox)
    if local is not None:
        return local
    return _from_overpass(bbox)
