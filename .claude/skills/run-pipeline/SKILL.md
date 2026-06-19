---
name: run-pipeline
description: Ejecuta el pipeline geoespacial de Cóndor View (San Rafael) en orden, sintético o con datos reales, y valida la salida zonas.geojson. Úsala cuando el usuario pida "correr el pipeline", "regenerar zonas", "generar el geojson" o cambie config.yaml / un script de etapa.
---

# Ejecutar el pipeline de Cóndor View

El pipeline vive en `pipeline/` y produce `frontend/public/data/zonas.geojson`,
que el frontend Next.js consume. Gestión de entorno con **uv** (`uv.lock` presente).

## Dos modos

### A. Atajo sintético (rápido, sin descargas)
Un solo script genera datos realistas simulados y escribe el geojson final:

```bash
cd pipeline
uv run python generate_zones.py
```

Usar para iterar UI/estética sin red. Produce ~25.000–30.000 zonas.

### B. Pipeline real (datos descargados, DAG por etapas)
Correr en orden estricto — cada etapa lee artefactos de la anterior:

```bash
cd pipeline
uv run python 00_descarga/dem.py        # → data/raw/dem_san_rafael.tif (+ slope)
uv run python 00_descarga/osm.py        # → data/raw/osm_{roads,places,landuse,waterways}.gpkg
uv run python 01_zonas.py               # → data/zonas_grid.gpkg
uv run python 02_normativa.py           # → data/s_norm.parquet
uv run python 03_fisico.py              # → data/s_fis.parquet
uv run python 04_accesibilidad.py       # → data/s_acc.parquet
uv run python 05_scoring.py             # → data/zonas_scored.gpkg
uv run python 06_export.py              # → ../frontend/public/data/zonas.geojson
```

## Contrato de artefactos (no saltar etapas)

| Etapa | Lee | Escribe |
|-------|-----|---------|
| `00 dem` | config.yaml | `data/raw/dem_san_rafael.tif`, `slope_san_rafael.tif` |
| `00 osm` | config.yaml | `data/raw/osm_{roads,places,landuse,waterways}.gpkg` |
| `01 zonas` | config.yaml | `data/zonas_grid.gpkg` |
| `02 normativa` | zonas_grid, osm_landuse | `data/s_norm.parquet` |
| `03 fisico` | zonas_grid, dem, slope, osm_waterways | `data/s_fis.parquet` |
| `04 accesibilidad` | zonas_grid, osm_roads, osm_places | `data/s_acc.parquet` |
| `05 scoring` | zonas_grid, s_norm, s_fis, s_acc | `data/zonas_scored.gpkg` |
| `06 export` | zonas_scored | `frontend/public/data/zonas.geojson` |

`01_zonas.py` y `00 dem` cachean: si el artefacto existe, no recalculan.
Para forzar: borrar el `.gpkg`/`.tif` correspondiente en `data/`.

## Reglas

- Si el usuario cambia **pesos/umbrales** en `config.yaml`, basta re-correr
  `05_scoring.py` + `06_export.py` (no hace falta re-descargar ni re-grillar).
- Si cambia **bbox o grilla.tamano_m**, borrar `data/zonas_grid.gpkg` y correr
  el DAG completo desde `01`.
- Tras cualquier corrida, validar la salida (ver skill `geo-validate`) antes de
  dar por terminado.
- `pesos.w_norm + w_fis + w_acc` deben sumar 1.0 — avisar si no.

## Verificación rápida tras correr

```bash
cd pipeline
uv run python -c "import json; d=json.load(open('../frontend/public/data/zonas.geojson')); print(len(d['features']), 'features')"
```
Esperar varios miles de features y campos `iat`, `categoria`, `s_norm`, `s_fis`,
`s_acc` por feature.
