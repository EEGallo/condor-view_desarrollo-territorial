# Cóndor View — Especificaciones Técnicas del MVP

**Versión:** 0.1 (borrador para inicio de desarrollo)
**Producto:** Índice de Aptitud Territorial — mapa web interactivo
**Objetivo del MVP:** puntuar las zonas no desarrolladas de *una* ciudad piloto según su aptitud para inversión inmobiliaria, combinando normativa, riesgo físico y accesibilidad. Sin machine learning: análisis multicriterio ponderado, transparente y explicable.

---

## 1. Principios de diseño

1. **Datos primero.** No se escribe código del motor hasta confirmar catastro + zonificación del piloto (compuerta de Semana 1–2).
2. **Sin backend.** Todo el cómputo es offline; el frontend sólo sirve archivos estáticos. Costo de hosting ≈ 0.
3. **Explicabilidad = producto.** Cada puntaje debe poder auditarse. El "por qué" se muestra siempre.
4. **Área chica.** El polígono piloto se limita a lo que sea digitalizable a mano (pocos km²).
5. **El demo es portfolio.** Debe poder embeberse en la página `/condor-view`.

---

## 2. Arquitectura

```
┌─────────────────────────────────────────┐
│  PIPELINE OFFLINE (Python, corre 1 vez)  │
│  Datos crudos → procesamiento → scoring  │
│  Salida: zonas.geojson (estático)        │
└──────────────────┬──────────────────────┘
                   │  (commit / deploy)
                   ▼
┌─────────────────────────────────────────┐
│  FRONTEND (Next.js + MapLibre, Vercel)   │
│  Carga zonas.geojson → mapa interactivo  │
│  Click en zona → panel con desglose      │
└─────────────────────────────────────────┘
```

No hay base de datos ni API en el MVP. El "modelo" es un archivo GeoJSON precalculado.

---

## 3. Capas de datos (resumen)

| Capa | Fuente | Formato | Estado |
|---|---|---|---|
| Basemap satelital | Sentinel-2 / OSM | raster / tiles | Listo |
| Pendiente | IGN MDE-Ar 5m (o SRTM 30m) | GeoTIFF | Listo |
| Inundabilidad | Derivada del DEM + hídricos provinciales | GeoTIFF | Medio |
| Red vial / huella urbana | OpenStreetMap (Geofabrik) | GeoJSON | Listo |
| Parcelas / catastro | IDECOR (Córdoba) / IDE provincial | WFS / shp | **Compuerta** |
| Zonificación / usos | Ordenanza municipal | digitalización manual QGIS | **Trabajo pesado** |

> **CRS de trabajo:** POSGAR 2007 / faja correspondiente (EPSG según provincia) para cálculos métricos; reproyectar a **EPSG:4326 (WGS84)** sólo en la exportación final para el frontend.

---

## 4. Unidad de análisis

El territorio piloto se divide en **zonas de análisis**. Dos opciones:

- **A — Parcelas catastrales** (preferida si el catastro está disponible y limpio): cada parcela vacante es una zona. Máxima granularidad y realismo comercial.
- **B — Grilla regular** (fallback): grilla de p. ej. 100×100 m sobre el polígono. Útil si el catastro no llega a tiempo; permite avanzar igual.

Decisión se toma al cerrar la compuerta de datos.

---

## 5. Motor de scoring (el núcleo)

Cada zona recibe un **Índice de Aptitud Territorial (IAT)** de 0 a 100, como suma ponderada de 3 sub-índices normalizados a [0, 1]:

```
IAT = 100 × (w_norm · S_norm + w_fis · S_fis + w_acc · S_acc)

  con  w_norm + w_fis + w_acc = 1   (pesos configurables)
  pesos iniciales sugeridos: 0.40 / 0.30 / 0.30
```

### 5.1 Sub-índice Normativo (S_norm)
Qué se puede construir según la ordenanza.
- Uso residencial/mixto permitido → 1.0
- Uso restringido/condicionado → 0.5
- Uso prohibido / área de reserva → 0.0
- (Opcional v1.1: modular por FOS/FOT / densidad permitida.)

### 5.2 Sub-índice Físico (S_fis)
Aptitud y seguridad del terreno. Combina dos factores:
- **Pendiente** (desde DEM): ideal < 5% (=1.0), penalizar linealmente hasta > 15% (=0.0).
- **Riesgo hídrico** (inundabilidad): fuera de zona inundable (=1.0), en zona inundable (=0.0 ó penalización fuerte).
- `S_fis = pendiente_score × hidrico_score` (multiplicativo: un terreno inundable no se "salva" por tener buena pendiente).

### 5.3 Sub-índice de Accesibilidad (S_acc)
Cercanía a lo que da valor. Por distancia euclidiana o de red:
- Distancia a la huella urbana consolidada (más cerca = mejor).
- Distancia a red vial principal.
- Distancia a red de agua (si hay dato).
- Normalizar cada distancia con decaimiento (p. ej. `score = exp(-d / d0)`) y promediar.

### 5.4 Reglas duras (override)
Independiente del puntaje, marcar como **NO APTO (IAT=0, flag rojo)**:
- Área protegida / reserva ambiental.
- Uso explícitamente prohibido por ordenanza.

> Los pesos `w_*` y los umbrales se exponen como **parámetros** del pipeline (archivo `config.yaml`) para poder recalibrarlos con un urbanista sin tocar código.

---

## 6. Pipeline de datos (Python)

**Stack:** Python 3.11+, `geopandas`, `rasterio`, `shapely`, `numpy`, `pyproj`, `rioxarray` (opcional). QGIS para digitalización manual y QA visual.

Pasos (scripts numerados, idempotentes):

```
00_descarga/         # bajar DEM, OSM, catastro; documentar fuentes y fechas
01_zonas.py          # construir unidades de análisis (parcelas o grilla)
02_normativa.py      # unir zonificación digitalizada → S_norm por zona
03_fisico.py         # pendiente (DEM) + inundabilidad → S_fis por zona
04_accesibilidad.py  # distancias a huella/vías/agua → S_acc por zona
05_scoring.py        # leer config.yaml, calcular IAT, aplicar overrides
06_export.py         # reproyectar a 4326, simplificar geometría, exportar GeoJSON
```

**Salida:** `frontend/public/data/zonas.geojson`

---

## 7. Esquema de salida (GeoJSON)

Cada feature:

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": {
    "id": "A-14",
    "iat": 78,
    "categoria": "alta",            // alta | media | baja | no_apto
    "s_norm": 1.0,
    "s_fis": 0.82,
    "s_acc": 0.55,
    "uso_permitido": "residencial",
    "pendiente_pct": 3.1,
    "riesgo_hidrico": "bajo",
    "dist_agua_m": 400,
    "dist_huella_m": 600,
    "dist_vial_m": 120,
    "flags": ["sin_acceso_pavimentado"]
  }
}
```

Reglas: geometría simplificada (tolerancia ~1–2 m) para peso liviano; máximo de decimales en coords (6); `iat` redondeado a entero.

---

## 8. Frontend (Next.js + MapLibre)

**Stack:** Next.js (App Router), MapLibre GL JS, Tailwind. Sin login, sin estado servidor.

Componentes:
- `<MapView>` — carga `zonas.geojson`, pinta zonas con color por `categoria` (escala: rojo→amarillo→verde), basemap satelital de fondo.
- `<ZonePanel>` — al hacer click en una zona, panel lateral con el IAT grande + desglose de los 3 sub-índices + flags. Este es el "momento wow": muestra el *por qué*.
- `<Legend>` — leyenda de la escala de color.
- `<WeightControls>` (opcional v1.1) — sliders para `w_*` que recalculan el IAT en el cliente a partir de los `s_*` ya guardados (no requiere recomputar el pipeline). Demuestra el valor "evaluá distintos escenarios".

Interacciones mínimas: hover resalta zona; click abre panel; zoom/pan estándar.

Estética: alineada al sistema "Observatory Noir" del sitio (dark theme, acentos cian/amarillo). Reusar tokens de diseño existentes.

---

## 9. Estructura del repositorio

```
condor-view-mvp/
├── pipeline/
│   ├── 00_descarga/ ... 06_export.py
│   ├── config.yaml          # pesos, umbrales, rutas, CRS
│   ├── requirements.txt
│   └── README.md            # cómo correr el pipeline + fuentes de datos
├── frontend/
│   ├── app/
│   ├── components/          # MapView, ZonePanel, Legend
│   ├── public/data/zonas.geojson
│   └── ...
└── docs/
    └── fuentes-datos.md     # links, formatos, fechas, licencias
```

---

## 10. Primer sprint (backlog para arrancar ya)

| # | Tarea | Resultado | Bloqueante |
|---|---|---|---|
| 1 | Elegir ciudad piloto y polígono | Bounding box definido | — |
| 2 | **Compuerta de datos:** conseguir catastro + ordenanza del piloto | Confirmación SÍ/NO. Si NO → cambiar piloto | Sí (todo depende) |
| 3 | Descargar DEM (IGN) y OSM del área | Datos crudos en `00_descarga/` | — |
| 4 | Decidir unidad de análisis (parcela vs grilla) | `01_zonas.py` funcionando | Dep. #2 |
| 5 | Digitalizar zonificación del polígono en QGIS | Shapefile de usos | Dep. #2 |
| 6 | Implementar `03_fisico.py` (pendiente) | S_fis por zona | Dep. #3,#4 |
| 7 | Esqueleto frontend con GeoJSON dummy | Mapa que pinta zonas | — (en paralelo) |

> Las tareas 3, 6 y 7 pueden avanzar en paralelo a la compuerta #2 usando datos de prueba, **pero no se invierte en el motor completo de scoring hasta cerrar #2.**

---

## 11. Definición de "terminado" (MVP)

El MVP está listo cuando:
1. Un mapa web muestra el polígono piloto coloreado por IAT.
2. Al clickear cualquier zona, aparece el desglose explicable (3 sub-índices + flags).
3. Los pesos están documentados y fueron revisados con al menos un urbanista.
4. Se puede sentar a un desarrollador/inversor real frente al demo.

**Métrica de éxito (negocio, no técnica):** que ese usuario diga *"esto cambiaría mi decisión de compra / pagaría por esto."*

---

## 12. Fuera de alcance (fases futuras, no tocar ahora)
Machine learning / predicción temporal · gemelo digital 3D · asistente conversacional · multi-ciudad · redes completas de infraestructura · cuentas de usuario · app móvil.

---

## 13. Riesgos abiertos
- **R1 (alto):** catastro o zonificación no disponibles para el piloto → mitiga: compuerta #2, fallback a grilla, elegir Córdoba (IDECOR).
- **R2 (medio):** acceso al MDE del IGN para uso no académico estaba en migración (fin 2025) → verificar estado; alternativa SRTM/Copernicus global.
- **R3 (medio):** pesos del scoring arbitrarios → mitiga: validación con urbanista antes de mostrar a clientes.
