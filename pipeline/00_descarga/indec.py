#!/usr/bin/env python3
"""
INDEC Censo 2022 — radios censales con población para San Rafael.

Fuente: CONICET RI handle 11336/284095 (radios 2022 con población REDATAM).
  https://ri.conicet.gov.ar/handle/11336/284095

Descarga el GPKG nacional (si falta), filtra el departamento San Rafael
(Mendoza) y normaliza la columna de población (CA3 → poblacion).

Salida: pipeline/data/raw/indec_radios.gpkg  (lo consume 07_servicios.py, nivel 1)
"""

import unicodedata
from pathlib import Path

import geopandas as gpd
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
RAW = SCRIPT_DIR / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
NACIONAL_PATH = RAW / "indec_nacional.gpkg"
OUTPUT_PATH = RAW / "indec_radios.gpkg"

NACIONAL_URL = (
    "https://ri.conicet.gov.ar/bitstream/handle/11336/284095/"
    "radios_2022_conDatos_1habHa.gpkg?sequence=2&isAllowed=y"
)

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
CRS_WORK = cfg["piloto"]["crs_trabajo"]


def norm(s: str) -> str:
    """Minúsculas sin acentos para comparar nombres."""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def download_nacional():
    if NACIONAL_PATH.exists():
        print(f"GPKG nacional ya existe: {NACIONAL_PATH}")
        return
    import urllib.request
    import ssl

    print("Descargando GPKG nacional de radios 2022 (CONICET, ~42MB) ...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # cert chain de CONICET incompleto
    with urllib.request.urlopen(NACIONAL_URL, context=ctx) as r:
        NACIONAL_PATH.write_bytes(r.read())
    print(f"Guardado: {NACIONAL_PATH}")


if __name__ == "__main__":
    download_nacional()

    print("Cargando radios nacionales ...")
    gdf = gpd.read_file(NACIONAL_PATH)
    print(f"  {len(gdf)} radios, cols clave: NOMPROV/NOMDEPTO/CA3 presentes:",
          all(c in gdf.columns for c in ["NOMPROV", "NOMDEPTO", "CA3"]))

    mask = gdf["NOMDEPTO"].map(norm).eq(norm("San Rafael")) & gdf[
        "NOMPROV"
    ].map(norm).str.contains(norm("Mendoza"))
    sr = gdf[mask].copy()
    print(f"Radios en San Rafael, Mendoza: {len(sr)}")

    if len(sr) == 0:
        print("ADVERTENCIA: 0 radios. Valores NOMDEPTO de Mendoza:")
        mza = gdf[gdf["NOMPROV"].map(norm).str.contains("mendoza")]
        print(sorted(mza["NOMDEPTO"].unique())[:40])
        raise SystemExit(1)

    sr = sr.rename(columns={"CA3": "poblacion"})
    sr["poblacion"] = sr["poblacion"].fillna(0).astype(int)
    sr = sr[["poblacion", "NOMDEPTO", "geometry"]].to_crs(CRS_WORK)

    print(f"Población total (censo 2022, radios SR): {sr['poblacion'].sum():,}")
    sr.to_file(OUTPUT_PATH, driver="GPKG")
    print(f"Guardado: {OUTPUT_PATH}")
