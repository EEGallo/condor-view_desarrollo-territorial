# Pipeline de Datos

## Stack

- **Python 3.11+**
- `geopandas`, `shapely`, `numpy`, `pyproj`, `pyyaml`
- QGIS para digitalización manual y QA visual (datos reales)

---

## Estado actual: pipeline sintético

Un único script genera el GeoJSON completo desde `config.yaml`:

```
pipeline/
├── generate_zones.py   # Script sintético — lee config.yaml, exporta zonas.geojson
├── config.yaml         # Todos los parámetros geográficos y de scoring
└── requirements.txt
```

### Flujo de `generate_zones.py`

1. Carga `config.yaml` (bbox, pesos, umbrales, geografía)
2. Genera grilla 2km en EPSG:5343 sobre el bounding box
3. Para cada celda calcula:
   - Elevación por interpolación lineal lon→altitud
   - Pendiente derivada de elevación
   - Distancia a ríos (buffer → riesgo hídrico)
   - Distancia a huella urbana (radios por localidad)
   - Distancia a rutas (polilíneas RN40/143/144/146)
   - `uso_permitido` por ubicación (oasis/montaña/embalse/etc.)
4. Aplica fórmula IAT, reglas duras, genera flags
5. Reproyecta a EPSG:4326, simplifica geometría, exporta GeoJSON

**Salida:** `frontend/public/data/zonas.geojson`

---

## Pipeline real (scripts numerados — a implementar)

Para migrar de datos sintéticos a datos reales, reemplazar con scripts idempotentes:

```
pipeline/
├── 00_descarga/        # Bajar DEM, OSM, catastro — documentar fuentes y fechas
├── 01_zonas.py         # Construir unidades de análisis (parcelas o grilla)
├── 02_normativa.py     # Unir zonificación digitalizada → S_norm por zona
├── 03_fisico.py        # Pendiente (DEM) + inundabilidad → S_fis por zona
├── 04_accesibilidad.py # Distancias a huella/vías/agua → S_acc por zona
├── 05_scoring.py       # Leer config.yaml, calcular IAT, aplicar overrides
├── 06_export.py        # Reproyectar a 4326, simplificar, exportar GeoJSON
├── config.yaml
└── requirements.txt
```

Cada script es **idempotente** — se puede re-ejecutar sin efecto acumulativo.

---

## Parámetros configurables (`config.yaml`)

Todos los parámetros de scoring y geografía viven en `config.yaml`. No se hardcodean en scripts.

| Sección | Parámetros |
|---------|-----------|
| `piloto` | nombre, bbox, crs_trabajo, crs_salida |
| `grilla` | tamano_m |
| `pesos` | w_norm, w_fis, w_acc |
| `umbrales.pendiente` | ideal_pct, max_pct |
| `umbrales.accesibilidad` | d0_huella_m, d0_vial_m, d0_agua_m |
| `categorias` | alta (umbral), media (umbral) |
| `rutas` | salida_geojson |
| `geografia` | oasis, localidades, rios, rutas_viales, elevacion, embalses |

---

## I/O

| Entrada | Descripción |
|---------|-------------|
| `config.yaml` | Parámetros + geografía sintética |
| DEM (futuro) | GeoTIFF EPSG:5343 |
| OSM (futuro) | GeoJSON / PBF Geofabrik |
| Catastro (futuro) | WFS / SHP IDE Mendoza |
| Zonificación (futuro) | SHP digitalizado en QGIS |

| Salida | Descripción |
|--------|-------------|
| `frontend/public/data/zonas.geojson` | Features con todos los campos del schema |

---

## CRS

- **Cálculos:** EPSG:5343 (POSGAR 2007 faja 3) — garantiza metros reales en Mendoza
- **Salida:** EPSG:4326 (WGS84) — requerido por MapLibre

---

## Correr el pipeline

```bash
cd pipeline
pip install -r requirements.txt
python generate_zones.py
```

El GeoJSON se escribe directamente en `frontend/public/data/zonas.geojson`.

---

*Ver también: [data.md](data.md) para fuentes · [scoring.md](scoring.md) para fórmulas*
