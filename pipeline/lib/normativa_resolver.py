"""Resolver normativo Caso A / Caso B (CAPA 1, spec §4.4).

Toma las features de zonificación del FeatureServer (GeoJSON) y las normaliza a
zonas canónicas con fos/fot/altura/densidad/uso.

  Caso A (modo="atributos"): field_map trae fos/fot/altura -> leer del feature.
  Caso B (modo="tabla"):      field_map nulos -> resolver categoría vs zonas.yaml.
                              categoría faltante -> warning + campos null.

Sin dependencias geométricas en el núcleo. cobertura_pct la calcula el llamador
(normalize.py / 02_normativa.py) con shapely.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .normativa_parser import parse_indicador, resolver_indicador

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
ZONAS_TABLE_PATH = CONFIG_DIR / "zonas.yaml"

# uso canónico -> s_norm (compatibilidad con el motor de scoring del pipeline).
# Cubre tanto los usos de la Ordenanza (residencial_*) como los del proxy OSM.
USO_S_NORM: dict[str, float] = {
    "residencial_alta": 1.0,
    "residencial_media": 1.0,
    "residencial_baja": 0.9,
    "residencial": 1.0,
    "comercial": 1.0,
    "mixto": 1.0,
    "industrial": 0.5,
    "condicionado": 0.5,
    "agricola": 0.7,
    "rural": 0.3,
    "reserva_natural": 0.0,
    "reserva_hidrica": 0.0,
    "reserva_turistica": 0.0,
}
DEFAULT_USO = "rural"
DEFAULT_S_NORM = 0.3


def load_zonas_table(path: Path | None = None) -> dict[str, Any]:
    p = path or ZONAS_TABLE_PATH
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("zonas", {})


def _field_map(sources: dict[str, Any]) -> dict[str, Any]:
    return ((sources.get("arcgis") or {}).get("zonificacion") or {}).get(
        "field_map", {}
    )


def caso(sources: dict[str, Any]) -> str:
    """Determina Caso A (atributos) o B (tabla) según field_map.

    Caso A si hay mapeo de FOS/FOT/altura, sea como campo único (fos) o como
    variantes (fos_1/fos_2/fos_3) del esquema UGDT.
    """
    fm = _field_map(sources)
    keys = ("fos", "fot", "altura_max", "fos_1", "fot_1")
    has_attrs = any(fm.get(k) for k in keys)
    return "atributos" if has_attrs else "tabla"


def _variant_fields(fm: dict[str, Any], base: str) -> list[str]:
    """Nombres de campo para un indicador: variantes base_1/2/3 o campo único."""
    variants = [fm.get(f"{base}_{i}") for i in (1, 2, 3)]
    variants = [v for v in variants if v]
    if variants:
        return variants
    single = fm.get(base)
    return [single] if single else []


def _first_uso(uso_value: Any) -> str:
    """Normaliza uso (lista o string) a un uso primario para s_norm."""
    if isinstance(uso_value, list) and uso_value:
        return str(uso_value[0])
    if isinstance(uso_value, str) and uso_value:
        return uso_value
    return DEFAULT_USO


def s_norm_for(uso_value: Any) -> float:
    return USO_S_NORM.get(_first_uso(uso_value), DEFAULT_S_NORM)


def resolve_feature(
    props: dict[str, Any],
    *,
    sources: dict[str, Any],
    zonas_table: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Normaliza una feature de zonificación a zona canónica."""
    warnings: list[str] = []
    fm = _field_map(sources)
    categoria = props.get(fm.get("categoria")) if fm.get("categoria") else None
    modo = caso(sources)

    zona: dict[str, Any] = {
        "categoria": categoria,
        "uso_permitido": None,
        "fos": None,
        "fot": None,
        "altura_max_m": None,
        "densidad": None,
        "sup_min_lote_m2": None,
        "modo": modo,
        "source": "UGDT/ArcGIS",
    }

    if modo == "atributos":  # Caso A — atributos STRING parseados/normalizados
        fos_raw = [props.get(f) for f in _variant_fields(fm, "fos")]
        fot_raw = [props.get(f) for f in _variant_fields(fm, "fot")]
        fos_res = resolver_indicador(fos_raw, "fos")
        fot_res = resolver_indicador(fot_raw, "fot")

        alt_field = fm.get("altura_max")
        alt_raw = props.get(alt_field) if alt_field else None
        alt_warn: list[str] = []
        alt_val = parse_indicador(alt_raw, "altura", alt_warn)

        zona["fos"] = fos_res["valor"]
        zona["fot"] = fot_res["valor"]
        zona["altura_max_m"] = alt_val
        zona["densidad"] = props.get(fm["densidad"]) if fm.get("densidad") else None
        zona["uso_permitido"] = props.get(fm["uso"]) if fm.get("uso") else categoria

        # Crudos + flags para citación legal (Capa 3 / XAI).
        zona["normativa_raw"] = {
            "fos": fos_res["raw"],
            "fos_variantes_difieren": fos_res["variantes_difieren"],
            "fot": fot_res["raw"],
            "fot_variantes_difieren": fot_res["variantes_difieren"],
            "altura_max": alt_raw,
        }
        warnings.extend(fos_res["warnings"])
        warnings.extend(fot_res["warnings"])
        warnings.extend(alt_warn)
    else:  # Caso B — resolver contra zonas.yaml
        entry = zonas_table.get(str(categoria)) if categoria is not None else None
        if entry is None:
            warnings.append(
                f"normativa: categoría '{categoria}' no está en zonas.yaml "
                "-> campos null"
            )
        else:
            zona["uso_permitido"] = entry.get("uso_permitido")
            zona["fos"] = entry.get("fos")
            zona["fot"] = entry.get("fot")
            zona["altura_max_m"] = entry.get("altura_max_m")
            zona["densidad"] = entry.get("densidad")
            zona["sup_min_lote_m2"] = entry.get("sup_min_lote_m2")
            zona["source"] = entry.get("fuente", "Ordenanza 15214")

    zona["s_norm"] = s_norm_for(zona["uso_permitido"])
    return zona, warnings


def resolve_features(
    geojson: dict[str, Any],
    *,
    sources: dict[str, Any],
    zonas_table: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Normaliza todas las features de una FeatureCollection de zonificación."""
    table = zonas_table if zonas_table is not None else load_zonas_table()
    zonas: list[dict[str, Any]] = []
    all_warnings: list[str] = []
    for feat in geojson.get("features", []):
        zona, w = resolve_feature(
            feat.get("properties", {}), sources=sources, zonas_table=table
        )
        zona["geometry"] = feat.get("geometry")
        zonas.append(zona)
        all_warnings.extend(w)
    return zonas, all_warnings
