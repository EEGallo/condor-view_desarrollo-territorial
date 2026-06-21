"""Cliente Overpass on-demand (spec §4.2).

Consulta equipamiento, hidrografía y vial por bbox vía osmnx (mismo motor que
pipeline/00_descarga/osm.py). Devuelve GeoDataFrames en EPSG:4326; normalize.py
reproyecta y calcula distancias.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import osmnx as ox

ox.settings.overpass_rate_limit = False

# tipo canónico -> tags OSM
EQUIPAMIENTO_TAGS: dict[str, dict[str, Any]] = {
    "escuela": {"amenity": ["school", "kindergarten", "college", "university"]},
    "hospital": {"amenity": ["hospital", "clinic", "doctors"]},
    "salud": {"amenity": ["pharmacy"]},
    "banco": {"amenity": ["bank", "atm"]},
    "policia": {"amenity": ["police"]},
    "municipal": {"office": ["government"]},
    "plaza": {"leisure": ["park", "playground"]},
}


def _safe_features(bbox_wsen: tuple[float, float, float, float], tags: dict):
    """ox.features_from_bbox tolerante: GeoDataFrame vacío si falla/sin datos."""
    w, s, e, n = bbox_wsen
    try:
        gdf = ox.features_from_bbox(bbox=(w, s, e, n), tags=tags)
        return gdf if len(gdf) else None
    except Exception:
        return None


def fetch_osm(
    bbox: tuple[float, float, float, float],
) -> tuple[dict[str, gpd.GeoDataFrame], list[str]]:
    """bbox = (minLon, minLat, maxLon, maxLat).

    Returns (layers, warnings). layers: {equipamiento, hidrografia, vial}
    GeoDataFrames (EPSG:4326). Capa caída -> ausente + warning.
    """
    warnings: list[str] = []
    layers: dict[str, gpd.GeoDataFrame] = {}
    w, s, e, n = bbox

    # Equipamiento (todos los tipos en una pasada por tag).
    equip_rows = []
    for tipo, tags in EQUIPAMIENTO_TAGS.items():
        gdf = _safe_features((w, s, e, n), tags)
        if gdf is None:
            continue
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            equip_rows.append(
                {"tipo": tipo, "nombre": row.get("name"), "geometry": geom}
            )
    if equip_rows:
        layers["equipamiento"] = gpd.GeoDataFrame(equip_rows, crs="EPSG:4326")
    else:
        warnings.append("overpass: sin equipamiento OSM en el bbox")

    # Hidrografía.
    hid = _safe_features((w, s, e, n), {"waterway": ["river", "stream", "canal"]})
    if hid is not None:
        hid = hid[hid.geometry.notna()].copy()
        layers["hidrografia"] = hid.to_crs("EPSG:4326")
    else:
        warnings.append("overpass: sin hidrografía OSM en el bbox")

    # Vial principal.
    vial = _safe_features(
        (w, s, e, n),
        {"highway": ["motorway", "trunk", "primary", "secondary"]},
    )
    if vial is not None:
        vial = vial[vial.geometry.notna()].copy()
        layers["vial"] = vial.to_crs("EPSG:4326")
    else:
        warnings.append("overpass: sin vial OSM en el bbox")

    return layers, warnings
