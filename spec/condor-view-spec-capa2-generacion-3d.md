# Cóndor View — Spec Detallada: CAPA 2 (Generación 3D Procedural)

**Versión:** 1.0 (ejecutable, adaptada al stack real)
**Stack confirmado (post-Capa 1):** backend Python + FastAPI + shapely/pyproj/numpy · frontend MapLibre + **deck.gl** · CRS métrico **EPSG:5343** (POSGAR 2007 faja 2) · intercambio EPSG:4326.
**Entrada:** `PolygonContext` (schema 1.1, de la Capa 1). **Salida:** `SceneModel`.
**Convención `<TODO>`:** dato/decisión a confirmar; no inventar.

---

## 0. Encuadre (leer antes de codear)

- La Capa 2 genera un **escenario de ocupación normativamente válido**, no una predicción ni un diseño arquitectónico. Mensaje al usuario: *"así se podría ocupar esta zona respetando el PMOT"*.
- Las masas son **volúmenes LOD1** (prismas extruidos), no edificios reales.
- La credibilidad NO está en que sea lindo, sino en que **respeta las restricciones** (no invade retiros de cauce ni áreas protegidas del `PolygonContext`) y en que las alturas/ocupación **respetan FOS/FOT/altura** de la normativa. Eso es lo que la distingue de un render decorativo.
- Estás construyendo la Capa 2 antes que la Capa 3 (decisión tuya, ok). Por eso el contrato `SceneModel.metricas` se diseña ya como `ProposedLayout` válido para la Capa 3 → cuando la armes, se enchufa sin retrabajo.

---

## 1. Dónde corre

**Generación en el backend (Python/shapely); render en el frontend (deck.gl).**

Motivo: la generación de trazado, subdivisión de manzanas y lotes, y cálculo de masas es geometría no trivial. shapely/pyproj ya están en el backend (reusados de la Capa 1). Reimplementar esos algoritmos en JS sería duplicar y fragilizar. El frontend solo renderiza el `SceneModel` (GeoJSON 3D) con deck.gl.

```
PolygonContext (Capa 1) ──► POST /api/generate ──► SceneModel ──► deck.gl (render 3D)
                                   │
                                   └── metricas ──► (futuro) Capa 3 como ProposedLayout
```

---

## 2. Endpoint REST

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| `POST` | `/api/generate` | `{ "context": PolygonContext, "params": TrazadoParams }` | `SceneModel` |

- El frontend ya tiene el `PolygonContext` (de `/api/extract`); lo reenvía. No re-extraer.
- `params` opcional; si falta, usar defaults de §4.
- Degradación: si falta normativa (zona sin FOS/FOT por dato faltante), generar igual con valores default marcados y agregar `warning` (no romper).

---

## 3. Contrato de salida — `SceneModel` (Pydantic)

```jsonc
{
  "schema_version": "1.0",
  "crs": "EPSG:4326",
  "sistema": "damero",
  "calles":   { "type": "FeatureCollection", "features": [ /* LineString + ancho_m, jerarquia */ ] },
  "manzanas": { "type": "FeatureCollection", "features": [ /* Polygon + manzana_id */ ] },
  "lotes":    { "type": "FeatureCollection", "features": [ /* Polygon + lote_id, sup_m2, manzana_id, zona */ ] },
  "espacios_verdes": { "type": "FeatureCollection", "features": [ /* Polygon + sup_m2 */ ] },
  "masas": [
    {
      "lote_id": "M03-L07",
      "footprint": { "type": "Polygon", "coordinates": [...] },  // 4326
      "base_z_m": 765.2,          // cota del terreno (DEM) en la base
      "altura_m": 9.0,
      "n_pisos": 3,
      "uso": "residencial",
      "fos_aplicado": 0.40,
      "fot_aplicado": 0.58
    }
  ],
  "metricas": {                   // == ProposedLayout para la Capa 3
    "n_lotes": 120,
    "sup_total_m2": 408000,
    "sup_calles_m2": 102000,
    "sup_lotes_m2": 265000,
    "sup_verde_m2": 41000,
    "sup_verde_pct": 0.10,
    "ocupacion_propuesta": 0.42,  // Σ footprint / sup_total
    "fot_propuesto": 0.61,        // Σ sup_construible / sup_lotes
    "densidad_lotes_ha": 2.9
  },
  "restricciones_respetadas": ["retiro_cauce", "area_protegida"],
  "warnings": ["zona sin altura_max: se usó default 9m"]
}
```

Validar con Pydantic. Toda geometría de salida en **EPSG:4326**; toda la generación interna en **EPSG:5343**.

---

## 4. Parámetros — `TrazadoParams`

```yaml
sistema: damero            # MVP: solo damero. organico/lineal = fase futura.
orientacion_deg: null      # null => alinear al borde más largo del polígono
ancho_calle_m: 15          # calle local; ver jerarquía abajo
ancho_avenida_m: 25        # cada N manzanas, una avenida (opcional)
lado_manzana_m: 100        # damero clásico argentino (~100 m, estilo Mendoza)
frente_lote_m: 12          # frente típico de lote
fondo_lote_min_m: 25
reserva_verde_pct: 0.10    # <TODO: confirmar % exigido por loteo en Ord. 15214 / Ley 8051>
slope_max_buildable_pct: 15  # zonas con pendiente mayor => no se lotean
```

`<TODO: confirmar contra la ordenanza el % obligatorio de espacios verdes y de reserva para equipamiento en loteos; el default 10% es provisional.>`

---

## 5. Módulos y algoritmos

Estructura nueva en `backend/procedural/`:
```
procedural/
├── street_generator.py    # trazado de calles + manzanas
├── block_subdivider.py    # manzanas -> lotes
├── mass_generator.py      # lotes -> masas 3D (FOS/FOT/altura)
├── green_allocator.py     # reserva de espacios verdes
├── metrics.py             # cálculo de metricas (== ProposedLayout)
├── scene_exporter.py      # ensambla SceneModel, reproyecta a 4326
└── generate.py            # orquestador: generate(context, params) -> SceneModel
```

Todo el cómputo geométrico en **EPSG:5343** (reproyectar el polígono de entrada con pyproj).

### 5.1 `street_generator` (sistema = damero)
1. Reproyectar `polygon` a 5343. Calcular el **área urbanizable**:
   `urbanizable = polygon − buffers de restricción` (retiros de cauce, áreas protegidas tomadas de `context.normativa.restricciones` y `context.hidrografia`).
2. Determinar orientación: si `orientacion_deg` es null, usar el ángulo del borde más largo del minimum rotated rectangle del polígono.
3. Generar grilla de líneas (calles) paralelas y perpendiculares a esa orientación, separadas por `lado_manzana_m + ancho_calle_m`, cubriendo el bounding box rotado.
4. (Opcional) Cada `N` ejes, promover a avenida (`ancho_avenida_m`).
5. **Recortar** las calles a `urbanizable`. Las celdas resultantes = **manzanas** (restar el ancho de calle a cada celda con un buffer interno de `ancho_calle_m / 2`).
6. Descartar manzanas cuya área < umbral mínimo (ej. < 0.25 × manzana teórica) o totalmente fuera de `urbanizable`.
7. Marcar manzanas con `pendiente_media > slope_max_buildable_pct` (usar DEM si está disponible) como `no_edificable` → candidatas a espacio verde (las pasa `green_allocator`).

> MVP honesto: el damero es una grilla 2D + máscara de pendiente + drapeado sobre DEM. La adaptación real al relieve (calles siguiendo curvas de nivel) es del sistema `organico`, fase futura. No intentar terrain-driven layout en esta versión.

### 5.2 `block_subdivider`
Por cada manzana edificable:
1. Calcular su **oriented bounding box** (OBB).
2. Subdividir en lotes con frente `frente_lote_m` a lo largo del/los lados que dan a calle, y fondo hasta el eje medio de la manzana (subdivisión en tiras + corte por frente).
3. Descartar/fusionar residuos menores a `sup_min_lote_m2` de la zona (`context.normativa.zonas[].sup_min_lote_m2`). Si la zona no define mínimo → usar `frente_lote_m × fondo_lote_min_m`.
4. Asignar a cada lote su `zona` (la categoría del `PolygonContext` que cubre su centroide) → de ahí salen FOS/FOT/altura para la Capa de masas.

### 5.3 `green_allocator`
1. Sumar área de manzanas marcadas `no_edificable` (pendiente/restricción).
2. Si esa área < `reserva_verde_pct × sup_urbanizable`, convertir manzanas adicionales (preferentemente las de peor aptitud física) en `espacios_verdes` hasta alcanzar el %.
3. Output: `espacios_verdes` FeatureCollection + `sup_verde_m2`.

### 5.4 `mass_generator` (el que da valor normativo)
Por cada lote edificable, con `fos`, `fot`, `altura_max_m` de su zona:
1. **Footprint** = lote contraído para cubrir `fos` de su superficie (escalar por retiro perimetral, o `lot.buffer(-retiro)` ajustando hasta `area_footprint ≈ fos × sup_lote`). Si no entra un retiro coherente, escalar el polígono respecto del centroide.
2. **Pisos** = `n_pisos = floor(fot / fos)` (cuántas plantas para alcanzar el FOT dada la ocupación). Acotar por altura: `n_pisos = min(n_pisos, floor(altura_max_m / altura_piso))` con `altura_piso = 3 m`.
3. **Altura** = `n_pisos × 3 m`, nunca > `altura_max_m`.
4. **fot_aplicado** = `(footprint_area × n_pisos) / sup_lote` (el FOT realmente alcanzado, ≤ fot normativo).
5. **base_z_m** = cota del DEM en el centroide del footprint (si hay DEM; si no, 0 + warning).
6. `uso` = derivado del primer `uso_permitido` de la zona.

> Esta es la pieza que convierte el 3D en algo más que un dibujo: cada volumen es **el sobre normativo máximo** de ese lote. Si FOS/FOT vienen null (dato faltante de Capa 1), usar defaults marcados + warning.

### 5.5 `metrics`
Calcular exactamente los campos de `SceneModel.metricas` (§3). Verificar identidades:
`sup_calles + sup_lotes + sup_verde ≈ sup_total` (tolerancia 2%).
`ocupacion_propuesta = Σ footprint_area / sup_total`.
`fot_propuesto = Σ (footprint_area × n_pisos) / sup_lotes`.

### 5.6 `scene_exporter`
Reproyectar todas las geometrías a 4326, redondear coords a 6 decimales, simplificar (tolerancia ~0.5 m en 5343 antes de reproyectar), ensamblar y validar `SceneModel`.

---

## 6. Render en el frontend (deck.gl sobre MapLibre)

Componente nuevo `components/Scene3D/` que consume el `SceneModel`:

- **Masas (edificios):** `PolygonLayer` o `GeoJsonLayer` con `extruded: true`, `getElevation: d => d.altura_m`, `getFillColor` por `uso`. Posicionar la base con `base_z_m` (o drapear si se usa terreno).
- **Calles:** `PathLayer` con `getWidth: d => d.ancho_m`.
- **Manzanas / lotes:** `GeoJsonLayer` 2D (relleno tenue + borde) para contexto; togglear lotes on/off.
- **Espacios verdes:** `GeoJsonLayer` con relleno verde.
- **Terreno:** activar terrain de MapLibre (DEM) o `TerrainLayer` de deck.gl para que las masas se asienten sobre relieve.
- **Estética Observatory Noir:** fondo oscuro, masas en cian/gris translúcido, verdes en acento. Tooltip por lote: zona, FOS/FOT aplicado, altura, n_pisos.
- Toggle de capas (calles / lotes / masas / verdes) y un control de `sistema`/`params` que re-llama `/api/generate` (futuro: sliders).

CRITICAL UI: nada de `localStorage`/`sessionStorage`. Estado en React.

---

## 7. Criterios de aceptación

- [ ] `POST /api/generate` con un `PolygonContext` real de San Rafael → `SceneModel` válido (Pydantic) en tiempo razonable.
- [ ] **Ninguna** calle, lote o masa intersecta los buffers de restricción del `PolygonContext` (test geométrico: `intersection.area ≈ 0`).
- [ ] Toda masa cumple `altura_m ≤ altura_max_m` de su zona y `footprint_area ≤ fos × sup_lote` (tolerancia 2%).
- [ ] `metricas` satisface las identidades de §5.5 y es un `ProposedLayout` válido para la futura Capa 3.
- [ ] `sup_verde_pct ≥ reserva_verde_pct`.
- [ ] Si FOS/FOT/altura faltan en una zona, genera con defaults + `warning`, sin crash.
- [ ] El frontend renderiza masas 3D, calles y verdes; tooltip muestra los indicadores aplicados.

---

## 8. Tests sugeridos
- Polígono rectangular plano sin restricciones → grilla regular, N lotes esperado, ocupación ≈ fos.
- Polígono con buffer de cauce → masas y calles excluidas de ese buffer (área de intersección ≈ 0).
- Zona con `altura_max=9`, `fot=1.5`, `fos=0.5` → `n_pisos=3`, `altura=9`, `fot_aplicado≈1.5`.
- Zona con `fot` alto y `altura_max` baja → altura limita pisos; `fot_aplicado < fot`.
- DEM ausente → `base_z_m=0` + warning, sin crash.
- Normativa faltante → defaults + warning.

---

## 9. Límites conocidos y fases futuras
- **MVP = solo damero.** `organico` (trazado siguiendo curvas de nivel/cauces vía tensor fields) y `lineal` (sobre eje/ruta) son fases futuras.
- Subdivisión de lotes es geométrica simple (tiras sobre OBB), no optimiza esquinas ni lotes irregulares.
- Masas son LOD1 (prismas). LOD2/techos y arquitectura quedan fuera.
- **Alta fidelidad futura:** ArcGIS CityEngine (mismo ecosistema que UGDT, gramática CGA, calcula GFA/FAR) si se requiere calidad de presentación. No bloquea el MVP. Evaluar licencia académica Esri vía UTN.
- El trazado autogenerado es un **punto de partida normativo**, no un proyecto de loteo aprobable. Mantener el disclaimer.

---

## 10. Acción de Ema antes de ejecutar
1. Confirmar `reserva_verde_pct` (y reserva para equipamiento) según Ordenanza 15214 / Ley 8051 — define `green_allocator`.
2. Decidir defaults de `lado_manzana_m`, `frente_lote_m`, `ancho_calle_m` (los de §4 son razonables para arrancar).
3. Confirmar que el `PolygonContext` ya trae `restricciones` con geometría utilizable (si en la Capa 1 quedaron solo como porcentaje, hay que exponer la geometría del buffer para poder restarla acá).
```
