# Pipeline de Datos — Cóndor View

Pipeline offline que genera el archivo `zonas.geojson` consumido por el frontend.

## Requisitos

- Python 3.11+
- Dependencias: `pip install -r requirements.txt`

## Uso

```bash
cd pipeline
python generate_zones.py
```

Genera `../frontend/public/data/zonas.geojson` con las zonas scored.

## Configuración

Editar `config.yaml` para cambiar:

- **Pesos del scoring** (`w_norm`, `w_fis`, `w_acc`) — deben sumar 1.0
- **Umbrales de pendiente** — ideal y máximo en porcentaje
- **Distancias de decaimiento** (`d0_*`) — para el sub-índice de accesibilidad
- **Categorías** — umbrales de IAT para alta/media/baja
- **Bounding box** del área piloto
- **CRS de trabajo** — sistema de coordenadas para cálculos métricos

## Estado actual (MVP)

El pipeline genera **datos sintéticos** que simulan:
- Zonificación (residencial/condicionado/reserva)
- Pendiente del terreno (gradiente con ruido)
- Riesgo hídrico (zona inundable al sur)
- Proximidad a huella urbana, red vial y red de agua

Para datos reales, reemplazar la generación sintética con:
1. Catastro de IDECOR (parcelas) o grilla sobre DEM real
2. Zonificación digitalizada de la ordenanza municipal
3. DEM del IGN (MDE-Ar 5m) para pendiente real
4. Capas hídricas provinciales para inundabilidad
5. OSM para red vial y huella urbana

## Esquema de salida

Cada feature en el GeoJSON:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | Identificador de zona (Z-0001) |
| `iat` | int | Índice de Aptitud Territorial (0-100) |
| `categoria` | string | alta / media / baja / no_apto |
| `s_norm` | float | Sub-índice normativo (0-1) |
| `s_fis` | float | Sub-índice físico (0-1) |
| `s_acc` | float | Sub-índice accesibilidad (0-1) |
| `uso_permitido` | string | Tipo de uso del suelo |
| `pendiente_pct` | float | Pendiente en porcentaje |
| `riesgo_hidrico` | string | bajo / medio / alto |
| `dist_huella_m` | int | Distancia a huella urbana (m) |
| `dist_vial_m` | int | Distancia a red vial (m) |
| `flags` | array | Alertas y banderas |
