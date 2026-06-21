# Cóndor View — Spec Detallada: CAPA 1 (Extracción)

**Versión:** 1.0 (refinamiento ejecutable)
**Decisiones congeladas:** deck.gl sobre MapLibre · RAG sin vector DB (vectorización futura) · backend RESTful (Next.js Route Handlers ahora → FastAPI cuando pese) · diagnóstico en servidor.
**Convención `<TODO>`:** dato real que Ema confirma contra el portal. No inventar.

---

## 0. Corrección de arquitectura respecto del borrador

En el borrador dijimos "extracción en el cliente". Al detallar aparecen dos motivos para que **la extracción viva en el backend REST** (que igual ibas a tener):

1. **CORS:** el FeatureServer de ArcGIS de la UGDT casi seguro **no permite llamadas directas desde el navegador**. Hay que proxearlo por el backend.
2. **Raster:** derivar pendiente/hidrología del DEM es procesamiento de raster, inviable/pesado en el browser.

**Resultado:** el cliente dibuja el polígono y orquesta; el **backend hace la extracción** y devuelve el `PolygonContext`. Las operaciones geométricas livianas (área, buffers simples con `turf.js`) sí pueden quedar en cliente. Esto no contradice tu decisión — la refuerza: el backend RESTful es justamente lo que resuelve CORS y raster.

---

## 1. Endpoints REST de esta capa

Diseño RESTful. En el MVP se implementan como Route Handlers de Next.js; el contrato no cambia si después migran a FastAPI.

| Método | Ruta | Entrada | Salida | Notas |
|---|---|---|---|---|
| `GET` | `/api/zonas` | `?bbox=minLon,minLat,maxLon,maxLat` | GeoJSON normalizado de zonificación | Proxy + normalización de la UGDT. Cacheable. |
| `GET` | `/api/equipamiento` | `?bbox=...&tipos=escuela,hospital,...` | GeoJSON de PDI | Vía Overpass (OSM). |
| `GET` | `/api/terrain` | `?bbox=...` | `{ pendiente_media, pendiente_max, riesgo_hidrico, ... }` | DEM → pendiente/hidro. |
| `POST` | `/api/extract` | `{ polygon: GeoJSON }` | `PolygonContext` | **Orquesta** los anteriores y fusiona. Endpoint principal de la Capa 1. |

`/api/extract` es el que consume el frontend. Los otros tres son sub-recursos reutilizables (y testeables por separado).

---

## 2. Configuración (resuelve la incertidumbre de field names)

El truco para no quedar bloqueados por los nombres reales de los campos del FeatureServer: un **mapa de campos** en config. Ema lo completa una sola vez al ver los *Fields* de la capa.

`data/config/sources.yaml`
```yaml
arcgis:
  base_url: "<TODO: https://HOST/server/rest/services/SERVICIO>"
  zonificacion:
    layer_id: "<TODO: id numérico de la capa de zonificación>"
    auth: none            # none | token
    field_map:            # campo_real_arcgis -> nombre canónico
      categoria: "<TODO: campo de categoría de zona>"
      fos: "<TODO o null si no existe>"
      fot: "<TODO o null>"
      altura_max: "<TODO o null>"
      densidad: "<TODO o null>"
      uso: "<TODO o null>"
  restricciones:
    layer_id: "<TODO o null si no hay capa separada>"
  catastro:
    layer_id: "<TODO o null>"

overpass:
  endpoint: "https://overpass-api.de/api/interpreter"
  tipos:
    escuela:   'amenity~"school|kindergarten|college|university"'
    hospital:  'amenity~"hospital|clinic|doctors"'
    salud:     'amenity~"pharmacy"'
    banco:     'amenity~"bank|atm"'
    policia:   'amenity="police"'
    municipal: 'office="government"'
    plaza:     'leisure~"park|playground"'

terrain:
  dem_provider: opentopography   # opentopography | ign
  opentopo_dataset: COP30        # Copernicus DEM 30m (fallback al MDE-Ar 5m del IGN si se gestiona)
  opentopo_api_key: "<TODO: key gratuita de OpenTopography>"

crs:
  exchange: "EPSG:4326"
  metric: "<TODO: faja POSGAR de Mendoza, p.ej. EPSG:22192 (faja 2)>"
```

> La presencia o ausencia de `fos/fot/altura` en `field_map` es lo que dispara el **Caso A vs B** (sección 5). Si son `null`, se usa `zonas.yaml`.

---

## 3. Contrato de salida — `PolygonContext`

(Refinado respecto del borrador; este es el schema autoritativo de la Capa 1.)

```jsonc
{
  "schema_version": "1.1",
  "polygon": { "type": "Polygon", "coordinates": [/* 4326 */] },
  "bbox": [minLon, minLat, maxLon, maxLat],
  "area_ha": 45.2,
  "crs_metric": "EPSG:22192",

  "normativa": {
    "modo": "atributos | tabla",        // A = atributos, B = tabla (zonas.yaml)
    "zonas": [
      {
        "categoria": "interface_ambiental_rural_II",
        "uso_permitido": ["residencial_baja"],
        "fos": 0.40, "fot": 0.60, "altura_max_m": 9, "densidad": "baja",
        "sup_min_lote_m2": 2500,
        "cobertura_pct": 80,            // % del polígono que cae en esta zona
        "source": "UGDT/ArcGIS",
        "fetch_date": "2026-06-21T..."
      }
    ],
    "restricciones": [
      { "tipo": "retiro_cauce", "geometria_afectada_pct": 12, "source": "..." }
    ]
  },

  "fisico": {
    "pendiente_media_pct": 4.1,
    "pendiente_max_pct": 12.0,
    "riesgo_hidrico": "bajo",            // bajo | medio | alto
    "dem_source": "OpenTopography COP30",
    "fetch_date": "..."
  },

  "hidrografia": [
    { "tipo": "canal|rio|cauce", "nombre": "...", "dist_m": 120, "source": "OSM" }
  ],

  "accesibilidad": {
    "dist_huella_urbana_m": 600,
    "dist_vial_principal_m": 120,
    "equipamiento": [
      { "tipo": "escuela", "nombre": "...", "dist_m": 800, "source": "OSM" }
    ]
  },

  "parcelas": [ { "id": "...", "sup_m2": 5000, "source": "UGDT/ArcGIS" } ],

  "warnings": [ "terrain: DEM no disponible, riesgo_hidrico=null" ]
}
```

Validar con **Zod** (TS) en el borde del endpoint. Toda capa lleva `source` + `fetch_date`. Si una fuente falla, su campo va `null` y se agrega un `warning`; **no se rompe** la respuesta.

---

## 4. Módulos y lógica

Estructura en `packages/extraction/`:
```
extraction/
├── arcgisClient.ts      # consulta FeatureServer (zonas, restricciones, catastro)
├── overpassClient.ts    # consulta Overpass (equipamiento, hidrografía, vial)
├── terrainClient.ts     # DEM -> pendiente, riesgo hídrico
├── normativaResolver.ts # Caso A/B -> normaliza zonas
├── normalize.ts         # fusiona todo en PolygonContext, recorta, distancias
├── schema.ts            # Zod del PolygonContext
└── index.ts             # extract(polygon) -> PolygonContext
```

### 4.1 `arcgisClient`
Consulta de features que intersecan el polígono:
```
GET {base_url}/{layer_id}/query
  ?geometry={polygonEsriJSON}
  &geometryType=esriGeometryPolygon
  &spatialRel=esriSpatialRelIntersects
  &inSR=4326&outSR=4326
  &outFields=*
  &where=1=1
  &f=geojson
```
- Si el server **no soporta `f=geojson`** (ArcGIS viejo), usar `f=json` y convertir con `@terraformer/arcgis` o `arcgis-to-geojson-utils`.
- Si `auth: token`, primero obtener token y pasarlo como `&token=`.
- Para simplificar, se puede consultar por **bbox** (`esriGeometryEnvelope`) y recortar después con turf.

### 4.2 `overpassClient`
Overpass QL por bbox (orden Overpass: `sur,oeste,norte,este`):
```overpassql
[out:json][timeout:25];
(
  nwr["amenity"~"school|hospital|clinic|bank|police"]({{bbox}});
  nwr["leisure"~"park|playground"]({{bbox}});
  way["waterway"]({{bbox}});
  way["highway"~"primary|secondary|trunk"]({{bbox}});
);
out center geom;
```
- Convertir respuesta con `osmtogeojson`.
- `out center` da centroides para ways/relations (suficiente para distancias).

### 4.3 `terrainClient`
- OpenTopography: `GET https://portal.opentopography.org/API/globaldem?demtype=COP30&south=&north=&west=&east=&outputFormat=GTiff&API_Key=...`
- Derivar pendiente con `geotiff` (lectura) + cálculo de gradiente, o delegar a un **servicio Python (rasterio + numpy `slope`)** — esta es la primera pieza candidata a FastAPI.
- `riesgo_hidrico` v1: combinar proximidad a cauce (de OSM) + cota relativa baja respecto del entorno. Definición fina = `<TODO>`.

### 4.4 `normativaResolver` — **Caso A / Caso B**
```
para cada zona devuelta por arcgisClient:
  categoria = feature[field_map.categoria]
  si field_map.fos/fot/altura NO son null:        # CASO A
      tomar fos/fot/altura/densidad de los atributos del feature
      modo = "atributos"
  si no:                                          # CASO B
      buscar categoria en data/config/zonas.yaml
      tomar fos/fot/altura/densidad/uso/sup_min de ahí
      modo = "tabla"
      si la categoria NO está en zonas.yaml -> warning + campos null
  calcular cobertura_pct (área de intersección zona∩polígono / área polígono)
```
- Caso A: cero transcripción manual, el dato fluye del FeatureServer.
- Caso B: requiere `zonas.yaml` poblado con la Ordenanza 15214 (plantilla en §6).

### 4.5 `normalize`
- Reproyectar a `crs.metric` para áreas y distancias (usar `proj4`).
- Recortar todas las capas al polígono (turf `intersect`/`booleanIntersects`).
- Calcular distancias mínimas a vial principal, huella urbana, cauces, y a cada tipo de equipamiento.
- Ensamblar y validar contra Zod.

---

## 5. Flujo de `/api/extract`

```
1. recibir { polygon }, validar GeoJSON, calcular bbox + area_ha
2. en paralelo (Promise.allSettled):
     a. arcgisClient(zonas, restricciones, catastro)
     b. overpassClient(equipamiento, hidrografia, vial)
     c. terrainClient(bbox)
3. normativaResolver  -> zonas normalizadas (A o B)
4. normalize          -> recortes, distancias, reproyección
5. validar PolygonContext (Zod); adjuntar warnings de fuentes caídas
6. responder 200 con PolygonContext
```
- `Promise.allSettled` para degradación elegante: si Overpass o el DEM fallan, el resto responde igual.
- Cachear `/api/zonas` y `/api/terrain` por bbox (son estables).

---

## 6. Plantilla `data/config/zonas.yaml` (solo si Caso B)

Si la capa **no** trae FOS/FOT como atributos, poblar esto desde la Ordenanza 15214. Pegame la tabla de indicadores y la estructuro yo.
```yaml
zonas:
  urbana_consolidada:
    uso_permitido: [residencial_media, comercial]
    fos: 0.60
    fot: 1.5
    altura_max_m: 12
    densidad: media
    sup_min_lote_m2: 300
    fuente: "Ordenanza 15214, art. <TODO>"
  urbana_no_consolidada:
    uso_permitido: [residencial_baja, residencial_media]
    fos: 0.50
    fot: 1.0
    altura_max_m: 9
    densidad: baja
    sup_min_lote_m2: 500
    fuente: "Ordenanza 15214, art. <TODO>"
  interface_periurbano:
    uso_permitido: [residencial_baja]
    fos: 0.40
    fot: 0.6
    altura_max_m: 9
    densidad: baja
    sup_min_lote_m2: 2500
    fuente: "Ordenanza 15214, art. <TODO>"
  # ...resto de categorías del PMOT
```

---

## 7. Criterios de aceptación

- [ ] `POST /api/extract` con un polígono de prueba en San Rafael devuelve `PolygonContext` válido (Zod) en < ~5 s.
- [ ] `normativa.modo` refleja correctamente A o B según `sources.yaml`.
- [ ] Cada zona trae `cobertura_pct` y la suma de coberturas ≈ 100%.
- [ ] Toda capa lleva `source` y `fetch_date`.
- [ ] Si se apaga Overpass o el DEM (simular), responde 200 con `warnings` y los campos en `null`.
- [ ] `/api/zonas`, `/api/equipamiento`, `/api/terrain` funcionan y se testean por separado.
- [ ] Distancias y áreas calculadas en CRS métrico (no en grados).

---

## 8. Tests sugeridos
- Fixture de polígono conocido (guardar respuesta del FeatureServer para test offline).
- Test de Caso A: `field_map` con fos/fot → zonas con valores de atributos.
- Test de Caso B: `field_map` con nulls → zonas resueltas desde `zonas.yaml`; categoría faltante → warning.
- Test de degradación: mock de Overpass caído → `warnings` presente, sin throw.

---

## 9. Lo que destraba todo (acción de Ema)
1. Abrir `.../rest/services` → servicio de OT/San Rafael → `FeatureServer` → capa de **zonificación** → sección **Fields**.
2. Anotar: `layer_id`, nombre del campo de **categoría**, y si existen campos **FOS/FOT/altura/densidad** (define Caso A o B).
3. Completar `sources.yaml`. Si Caso B, pasarme la tabla de la Ordenanza 15214.

> Con eso, esta spec queda 100% ejecutable en Claude Code.
