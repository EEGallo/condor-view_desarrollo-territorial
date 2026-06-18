# Motor de Scoring — Índice de Aptitud Territorial (IAT)

Cada zona recibe un **IAT de 0 a 100** como suma ponderada de 3 sub-índices normalizados a [0, 1].

---

## Fórmula principal

```
IAT = 100 × (w_norm · S_norm + w_fis · S_fis + w_acc · S_acc)
```

### Pesos activos (`pipeline/config.yaml`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `w_norm` | 0.40 | Sub-índice normativo |
| `w_fis` | 0.30 | Sub-índice físico |
| `w_acc` | 0.30 | Sub-índice de accesibilidad |

Los pesos se configuran en `pipeline/config.yaml` — no tocar código para recalibrar.

---

## Categorías

| Categoría | Umbral IAT | Color |
|-----------|-----------|-------|
| `alta` | ≥ 70 | `#22c55e` |
| `media` | ≥ 40 | `#eab308` |
| `baja` | ≥ 0 | `#ef4444` |
| `no_apto` | override | `#374151` |

---

## S_norm — Sub-índice Normativo

Qué se puede construir según la ordenanza municipal.

| `uso_permitido` | S_norm |
|----------------|--------|
| `residencial` | 1.0 |
| `mixto` | 1.0 |
| `condicionado` | 0.5 |
| `agricola` | 0.3 |
| `reserva_turistica` | 0.2 |
| `reserva_natural` | 0.0 |
| `reserva_hidrica` | 0.0 |
| `rural` | 0.1 |

> Uso explícitamente prohibido o reserva → override IAT = 0 (regla dura, ver abajo).

---

## S_fis — Sub-índice Físico

Aptitud y seguridad del terreno. **Multiplicativo** — un terreno inundable no se "salva" por buena pendiente.

```
S_fis = pendiente_score × hidrico_score
```

### Pendiente (`pendiente_pct`)

Decaimiento lineal entre umbral ideal y máximo:

```
pendiente_score = 1.0                             si pendiente_pct ≤ 5.0%
pendiente_score = 1 - (p - 5) / (25 - 5)         si 5% < pendiente_pct ≤ 25%
pendiente_score = 0.0                             si pendiente_pct > 25%
```

| Parámetro | Valor |
|-----------|-------|
| `ideal_pct` | 5.0 |
| `max_pct` | 25.0 |

### Riesgo hídrico (`riesgo_hidrico`)

| Valor | hidrico_score |
|-------|--------------|
| `bajo` | 1.0 |
| `moderado` | 0.5 |
| `alto` | 0.0 |

---

## S_acc — Sub-índice de Accesibilidad

Cercanía a infraestructura que da valor. Decaimiento exponencial por distancia:

```
score_i = exp(-d_i / d0_i)
S_acc = promedio(score_huella, score_vial)
```

| Componente | Campo | `d0` (metros) | Descripción |
|------------|-------|--------------|-------------|
| Huella urbana | `dist_huella_m` | 8,000 | Distancia al límite urbano más cercano |
| Red vial principal | `dist_vial_m` | 5,000 | Distancia a ruta nacional / provincial |

> `d0` = distancia en la que el score cae a ~37% (1/e). Configurable en `config.yaml`.

---

## Reglas duras (override IAT = 0, categoría `no_apto`)

Independiente del puntaje calculado:

- Zona embalse (buffer alrededor de Los Reyunos, Valle Grande, El Nihuil, Agua del Toro)
- Reserva natural / área protegida
- Reserva hídrica
- `uso_permitido` explícitamente prohibido por ordenanza

---

## Flags

Condiciones que se agregan al array `flags` de cada zona. No modifican el IAT directamente.

| Flag | Condición de activación |
|------|------------------------|
| `pendiente_elevada` | pendiente_pct > 15% |
| `pendiente_critica` | pendiente_pct > 20% |
| `riesgo_hidrico_moderado` | riesgo hídrico moderado |
| `riesgo_hidrico_alto` | riesgo hídrico alto |
| `lejos_de_huella` | dist_huella_m > 15,000 |
| `sin_acceso_vial` | dist_vial_m > 10,000 |
| `uso_no_permitido` | uso_permitido en lista de prohibidos |
| `zona_montanosa` | elevacion_m > 1,500 |
| `altitud_extrema` | elevacion_m > 2,500 |
| `zona_desertica` | zona fuera del oasis, no montañosa |
| `reserva_natural` | override natural |
| `reserva_hidrica` | override hídrico |
| `zona_embalse` | dentro de buffer de embalse |

---

## Recalibración en cliente (frontend)

`WeightControls` permite ajustar los pesos `w_*` en el browser. El IAT se recalcula como:

```js
iat = Math.round(100 * (w_norm * s_norm + w_fis * s_fis + w_acc * s_acc))
```

Usa los `s_*` ya guardados en el GeoJSON — no requiere re-ejecutar el pipeline.

---

## Simulador de intervención (frontend)

Permite colocar infraestructura hipotética sobre el mapa (ruta, hub urbano, traza de agua) y recalcula el potencial en vivo. Una intervención cambia solo la **accesibilidad** — no la zonificación ni la pendiente, y respeta las reglas duras.

Para cada zona cercana a la intervención se recompone la distancia afectada y se recalcula `s_acc` con los parámetros publicados en `metadata.accesibilidad` del GeoJSON:

```js
// d_huella / d_vial / d_agua = min(distancia base, distancia a la intervención)
s_acc = 0.45·exp(-d_huella/8000) + 0.35·exp(-d_vial/5000) + 0.20·exp(-d_agua/6000)
iat   = Math.round(100 * (w_norm·s_norm + w_fis·s_fis + w_acc·s_acc))
```

El GeoJSON exporta las 3 distancias (`dist_huella_m`, `dist_vial_m`, `dist_agua_m`) y los params en `metadata.accesibilidad` para que el cliente recompute sin backend. El panel antes/después reporta zonas que suben de categoría, hectáreas desbloqueadas y delta de IAT del área impactada.

---

*Ver también: [pipeline.md](pipeline.md) para implementación Python · [frontend.md](frontend.md) para `WeightControls` e `InterventionControls`*
