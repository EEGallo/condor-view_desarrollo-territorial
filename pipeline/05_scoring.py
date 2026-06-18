#!/usr/bin/env python3
"""
Calcula IAT final combinando S_norm + S_fis + S_acc.


  IAT = 100 × (w_norm·S_norm + w_fis·S_fis + w_acc·S_acc)

Aplica reglas duras (override IAT=0) y genera los 13 flags.
Salida: pipeline/data/zonas_scored.gpkg
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ZONAS_PATH = SCRIPT_DIR / "data" / "zonas_grid.gpkg"
S_NORM_PATH = SCRIPT_DIR / "data" / "s_norm.parquet"
S_FIS_PATH = SCRIPT_DIR / "data" / "s_fis.parquet"
S_ACC_PATH = SCRIPT_DIR / "data" / "s_acc.parquet"
SERVICIOS_PATH = SCRIPT_DIR / "data" / "servicios.parquet"
ISOCRONAS_PATH = SCRIPT_DIR / "data" / "isocronas.parquet"
OUTPUT_PATH = SCRIPT_DIR / "data" / "zonas_scored.gpkg"

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

W_NORM = cfg["pesos"]["w_norm"]
W_FIS = cfg["pesos"]["w_fis"]
W_ACC = cfg["pesos"]["w_acc"]
CAT_ALTA = cfg["categorias"]["alta"]
CAT_MEDIA = cfg["categorias"]["media"]

USOS_OVERRIDE = {"reserva_natural", "reserva_hidrica", "reserva_turistica"}


def categorize(iat: np.ndarray) -> list[str]:
    cats = []
    for v in iat:
        if v == 0:
            cats.append("no_apto")
        elif v >= CAT_ALTA:
            cats.append("alta")
        elif v >= CAT_MEDIA:
            cats.append("media")
        else:
            cats.append("baja")
    return cats


def compute_flags(row: pd.Series) -> list[str]:
    flags = []
    p = row["pendiente_pct"]
    e = row["elevacion_m"]
    rh = row["riesgo_hidrico"]
    uso = row["uso_permitido"]
    dh = row["dist_huella_m"]
    dv = row["dist_vial_m"]

    if p > 20:
        flags.append("pendiente_critica")
    elif p > 15:
        flags.append("pendiente_elevada")

    if rh == "alto":
        flags.append("riesgo_hidrico_alto")
    elif rh == "moderado":
        flags.append("riesgo_hidrico_moderado")

    if dh > 15000:
        flags.append("lejos_de_huella")
    if dv > 10000:
        flags.append("sin_acceso_vial")

    if uso in USOS_OVERRIDE:
        flags.append("uso_no_permitido")
    if uso == "reserva_natural":
        flags.append("reserva_natural")
    if uso == "reserva_hidrica":
        flags.append("reserva_hidrica")

    if e > 2500:
        flags.append("altitud_extrema")
    elif e > 1500:
        flags.append("zona_montanosa")

    # zona_desertica: fuera del oasis, baja altitud, uso rural
    oasis = cfg["geografia"]["oasis"]
    in_oasis = (
        oasis["west"] <= row["lon"] <= oasis["east"]
        and oasis["south"] <= row["lat"] <= oasis["north"]
    )
    if not in_oasis and e < 1500 and uso in {"rural", "condicionado"}:
        flags.append("zona_desertica")

    return flags


if __name__ == "__main__":
    print("Cargando datos ...")
    zonas = gpd.read_file(ZONAS_PATH)
    s_norm_df = pd.read_parquet(S_NORM_PATH)
    s_fis_df = pd.read_parquet(S_FIS_PATH)
    s_acc_df = pd.read_parquet(S_ACC_PATH)

    # Join por id
    df = zonas.merge(s_norm_df, on="id")
    df = df.merge(s_fis_df, on="id")
    df = df.merge(s_acc_df, on="id")

    # Capa población + servicios (opcional — fallback si 07 no corrió)
    if SERVICIOS_PATH.exists():
        df = df.merge(pd.read_parquet(SERVICIOS_PATH), on="id", how="left")
    else:
        print("ADVERTENCIA: servicios.parquet no encontrado — campos en 0")
        for c in ["dist_escuela_m", "dist_salud_m"]:
            df[c] = -1
        df["poblacion_est"] = 0
        df["deficit_servicios"] = 0

    # Isócronas reales (opcional — fallback si 08 no corrió)
    if ISOCRONAS_PATH.exists():
        df = df.merge(pd.read_parquet(ISOCRONAS_PATH), on="id", how="left")
    else:
        print("ADVERTENCIA: isocronas.parquet no encontrado — tiempos en cap")
        df["tiempo_huella_min"] = 180
        df["tiempo_servicio_min"] = 180
    df["tiempo_huella_min"] = df["tiempo_huella_min"].fillna(180)
    df["tiempo_servicio_min"] = df["tiempo_servicio_min"].fillna(180)

    # --- IAT ---
    iat_raw = 100.0 * (W_NORM * df["s_norm"] + W_FIS * df["s_fis"] + W_ACC * df["s_acc"])

    # Reglas duras
    override_mask = df["uso_permitido"].isin(USOS_OVERRIDE) | (df["elevacion_m"] > 3000)
    iat_raw[override_mask] = 0.0

    df["iat"] = np.round(iat_raw).astype(int)
    df["categoria"] = categorize(df["iat"].values)

    # en_oasis
    oasis = cfg["geografia"]["oasis"]
    df["en_oasis"] = (
        (df["lon"] >= oasis["west"])
        & (df["lon"] <= oasis["east"])
        & (df["lat"] >= oasis["south"])
        & (df["lat"] <= oasis["north"])
    )

    # Flags
    print("Calculando flags ...")
    df["flags"] = df.apply(compute_flags, axis=1)

    # Seleccionar columnas de salida
    cols = [
        "id", "iat", "categoria",
        "s_norm", "s_fis", "s_acc",
        "uso_permitido", "pendiente_pct", "riesgo_hidrico",
        "elevacion_m", "dist_huella_m", "dist_vial_m", "dist_agua_m",
        "poblacion_est", "dist_escuela_m", "dist_salud_m", "deficit_servicios",
        "tiempo_huella_min", "tiempo_servicio_min",
        "en_oasis", "distrito", "flags",
        "lon", "lat", "geometry",
    ]
    result = gpd.GeoDataFrame(df[cols], crs=zonas.crs)

    # Stats
    cat_dist = result["categoria"].value_counts()
    print("\nDistribución de categorías:")
    for cat, count in cat_dist.items():
        print(f"  {cat}: {count} ({count/len(result)*100:.1f}%)")
    print(f"IAT medio: {result['iat'].mean():.1f}")

    # GPKG no soporta columnas lista — serializar flags como JSON string
    result["flags"] = result["flags"].apply(json.dumps)

    result.to_file(OUTPUT_PATH, driver="GPKG")
    print(f"\nGuardado: {OUTPUT_PATH} ({len(result)} zonas)")
