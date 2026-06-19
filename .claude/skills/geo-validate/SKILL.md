---
name: geo-validate
description: Valida la salida geoespacial del pipeline (zonas.geojson y artefactos intermedios) — CRS, geometrías válidas, cobertura del bbox de San Rafael, esquema de campos y rangos del scoring. Úsala antes de dar por buena una corrida del pipeline o al diagnosticar mapas vacíos/desplazados en el frontend.
---

# Validar salida geoespacial

Errores geoespaciales comunes en este proyecto: CRS mal asignado (mapa
desplazado/vacío), geometrías inválidas tras simplificar, IAT fuera de rango,
o cobertura que no cae sobre San Rafael.

CRS del proyecto (`config.yaml`):
- Trabajo (métrico): `EPSG:5343` (POSGAR 2007 faja 3)
- Salida (web): `EPSG:4326`
- Bbox: W −70.17 / S −36.00 / E −66.92 / N −34.25

## Validar el GeoJSON final

```bash
cd pipeline
uv run python - <<'PY'
import json
from pathlib import Path
p = Path("../frontend/public/data/zonas.geojson")
d = json.load(open(p))
feats = d["features"]
print("features:", len(feats))

# CRS debe ser geográfico (lat/lng), sin bloque crs o EPSG:4326
print("crs:", d.get("crs", "implícito 4326 (ok)"))

# Esquema y rangos
reqd = {"id","iat","categoria","s_norm","s_fis","s_acc","uso_permitido",
        "pendiente_pct","riesgo_hidrico","dist_huella_m","dist_vial_m","flags"}
p0 = feats[0]["properties"]
missing = reqd - set(p0)
print("campos faltantes:", missing or "ninguno")

iats = [f["properties"]["iat"] for f in feats]
print("iat min/max:", min(iats), max(iats), "(esperado 0..100)")
cats = set(f["properties"]["categoria"] for f in feats)
print("categorias:", cats, "(esperado subset de alta/media/baja/no_apto)")

# Cobertura: las coords deben caer dentro del bbox
xs, ys = [], []
for f in feats[:2000]:
    g = f["geometry"]["coordinates"][0]
    for x,y in g:
        xs.append(x); ys.append(y)
print("lng range:", min(xs), max(xs), "(bbox -70.17..-66.92)")
print("lat range:", min(ys), max(ys), "(bbox -36.00..-34.25)")
PY
```

## Validar artefactos intermedios (.gpkg / .parquet)

```bash
cd pipeline
uv run python - <<'PY'
import geopandas as gpd
g = gpd.read_file("data/zonas_grid.gpkg")
print("zonas_grid CRS:", g.crs, "(esperado EPSG:5343)")
print("inválidas:", (~g.geometry.is_valid).sum())
print("vacías:", g.geometry.is_empty.sum())
print("bounds:", g.total_bounds)
PY
```

## Checklist de aprobación

- [ ] CRS salida geográfico (4326); intermedios en 5343.
- [ ] 0 geometrías inválidas/vacías.
- [ ] `iat` ∈ [0,100]; sub-índices `s_*` ∈ [0,1].
- [ ] `categoria` solo en {alta, media, baja, no_apto}.
- [ ] Todos los campos del esquema presentes (ver tabla en `pipeline/README.md`).
- [ ] Coordenadas dentro del bbox de San Rafael.

Si algo falla, no relanzar a ciegas: identificar la etapa del DAG dueña del
campo/artefacto roto (ver skill `run-pipeline`) y corregir ahí.
