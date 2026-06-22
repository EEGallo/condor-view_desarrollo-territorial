# Cóndor View — Spec Detallada: CAPA 3 (Agente de Diagnóstico Normativo)

**Versión:** 1.0 (ejecutable)
**Stack confirmado:** backend Python + FastAPI · LLM = Claude vía Anthropic SDK (key en servidor) · Pydantic para schemas · CRS métrico EPSG:5343 / intercambio 4326.
**Entrada:** `PolygonContext` (Capa 1) + `ProposedLayout` opcional (= `SceneModel.metricas` de Capa 2).
**Salida:** `DiagnosticReport`.
**Convención `<TODO>`:** dato/decisión a confirmar; no inventar.

---

## 0. Principio rector (no negociable)

> **El motor de reglas determinístico decide `cumple / observación / no_cumple`. El LLM redacta y cita. El LLM NUNCA emite ni altera un veredicto.**

Esto es lo que vuelve el diagnóstico auditable y defendible ante un municipio o un abogado. Un LLM que "alucine" un *cumple* es un pasivo legal. Toda la arquitectura de abajo existe para sostener esta separación.

---

## 1. Dos preguntas distintas que NO hay que mezclar

La Capa 3 responde dos cosas separadas. Mantenerlas distintas es una decisión de diseño central:

- **Cumplimiento (legal, binario):** ¿esto respeta la norma? → motor de reglas → `cumple/observación/no_cumple`. Es pass/fail.
- **Aptitud (deseabilidad, 0–100):** ¿qué tan buena es esta zona para urbanizar? → modelo multicriterio (el del MVP) → `indice_aptitud`.

Una zona puede tener **aptitud alta pero no cumplir** (ej. excelente accesibilidad pero cae en retiro de cauce), o **cumplir pero baja aptitud** (legal pero mal servida). Si se colapsan en un solo número, el informe miente. Van separadas en el `DiagnosticReport`.

---

## 2. Dónde corre y endpoint

Backend FastAPI (el LLM necesita servidor por la API key). RESTful, consistente con Capas 1 y 2:

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| `POST` | `/api/diagnose` | `{ "context": PolygonContext, "proposed_layout": ProposedLayout | null }` | `DiagnosticReport` |

- Si `proposed_layout` es null → diagnostica solo la zona (aptitud + restricciones), sin evaluar un trazado concreto.
- Si viene (de la Capa 2) → además evalúa FOS/FOT/altura/reserva verde propuestos contra la norma.

---

## 3. Arquitectura interna

```
PolygonContext (+ ProposedLayout)
        │
        ▼
[rules_engine]  ── checks determinísticos ──►  list[CheckResult]   (decide)
        │
        ▼
[aptitude]      ── modelo multicriterio ────►  indice_aptitud      (decide)
        │
        ▼
[norm_retriever] ── recupera fragmentos de ordenanza por check ──► contexto normativo
        │
        ▼
[report_composer] ── Claude redacta narrativa POR check (slot-filling) ──► informe_narrativo
        │
        ▼
[validator]     ── consistencia narrativa↔checks + Pydantic ──►  DiagnosticReport
```

Módulos en `backend/diagnosis/`:
```
diagnosis/
├── rules_engine.py     # CÓDIGO TUYO — el corazón, determinístico
├── checks/             # un archivo por familia de checks
├── aptitude.py         # CÓDIGO TUYO — modelo multicriterio (reusa MVP)
├── norm_retriever.py   # retrieval v1 simple → LlamaIndex al vectorizar
├── report_composer.py  # Claude (Anthropic SDK) — solo redacta
├── validator.py        # CÓDIGO TUYO — consistencia + Pydantic
├── schema.py           # Pydantic: DiagnosticReport, CheckResult, Fuente
└── diagnose.py         # orquestador: diagnose(context, layout) -> DiagnosticReport
```

---

## 4. Motor de reglas (`rules_engine`) — CÓDIGO TUYO

Cada check es una función determinística pura. Firma:

```python
@dataclass
class Fuente:
    norma: str          # "Ordenanza 15214"
    articulo: str       # "Art. 12" | "<TODO>"

@dataclass
class CheckResult:
    regla: str                  # "fos", "uso_permitido", ...
    resultado: Literal["cumple","observacion","no_cumple","no_aplica"]
    es_regla_dura: bool         # True => puede forzar estado no_apto
    detalle_tecnico: str        # factual, generado por el motor (no por LLM)
    datos: dict                 # valores usados, para trazabilidad/XAI
    fuente: Fuente | None
```

### Catálogo de checks v1
| regla | dura | lógica (resumen) | fuente |
|---|---|---|---|
| `uso_permitido` | ✅ | el uso propuesto ∈ `zona.uso_permitido`; si no → no_cumple | Ord. 15214 |
| `area_protegida` | ✅ | el polígono intersecta área protegida/reserva → no_cumple | Ley 8051 / PMOT |
| `restriccion_hidrica` | ✅ | intersecta retiro de cauce/zona inundable (geometría del PolygonContext) | Ley 8051 / DGI |
| `fos` | ❌ | `proposed.ocupacion ≤ zona.fos` (+ tolerancia); excede → observación/no_cumple | Ord. 15214 |
| `fot` | ❌ | `proposed.fot_propuesto ≤ zona.fot` | Ord. 15214 |
| `altura` | ❌ | `proposed.altura_max ≤ zona.altura_max_m` | Ord. 15214 |
| `sup_min_lote` | ❌ | lotes ≥ `zona.sup_min_lote_m2` | Ord. 15214 |
| `densidad` | ❌ | `proposed.densidad_lotes_ha` coherente con `zona.densidad` | Ord. 15214 |
| `reserva_verde` | ❌ | `proposed.sup_verde_pct ≥ mínimo exigido` | Ord. 15214 / Ley 8051 |
| `aptitud_fisica` | ❌ | pendiente media ≤ umbral; si no → observación | (criterio técnico) |
| `riesgo_sismico` | ❌ (informativo) | siempre informa: zona de peligrosidad elevada → aplica INPRES-CIRSOC 103 | norma sísmica |

- Si falta un dato (FOS null por dato faltante de Capa 1) → `resultado="no_aplica"` + warning, nunca crash.
- `detalle_tecnico` lo escribe el motor con los números (ej. "ocupación propuesta 0.45 > FOS de zona 0.40"). El LLM después lo *redacta*, no lo *calcula*.

### `estado_global` (derivado, determinístico)
```
si algún check dura == no_cumple        -> "no_apto"
elif algún check == no_cumple           -> "no_cumple"
elif algún check == observacion         -> "cumple_con_observaciones"
else                                    -> "cumple"
```

`<TODO de Ema: confirmar el artículo de la Ord. 15214 para cada fuente, y el umbral de reserva_verde. Sin el articulado, fuente.articulo queda "<TODO>" pero el check funciona igual.>`

---

## 5. Aptitud (`aptitude`) — CÓDIGO TUYO

Reusar el modelo multicriterio del spec MVP (no reinventar):
```
indice_aptitud = 100 × (w_norm·S_norm + w_fis·S_fis + w_acc·S_acc)
pesos en config (default 0.40/0.30/0.30)
```
- `S_norm`: del uso permitido / restricciones (de los checks).
- `S_fis`: pendiente × riesgo hídrico (del PolygonContext).
- `S_acc`: accesibilidad → **acá entra pandana** (ver §8) o se reusa lo ya calculado en Capa 1.
- Si algún check duro da `no_cumple` → `indice_aptitud` se reporta igual, pero el `estado_global` manda. Son ejes separados (§1).

---

## 6. Retrieval normativo (`norm_retriever`)

- **v1 (ahora, sin vector DB):** corpus chico en `data/ordenanzas/` (texto plano por artículos). Para cada `CheckResult`, recuperar el fragmento por `fuente.norma`+`articulo` (lookup directo) o por keyword. Inyectar en el prompt.
- **v2 (futuro, al vectorizar):** **LlamaIndex** sobre el corpus (ingest → index → query). Misma interfaz `retrieve(check) -> list[fragmento]`, cambia la implementación detrás. Diseñar la interfaz ya para que el salto no toque el resto.

---

## 7. Composición del informe (`report_composer`) — Claude vía Anthropic SDK

**El LLM solo redacta. No decide.** Para que sea estructuralmente incapaz de contradecir un veredicto: **slot-filling por check**, no texto libre.

- Para cada `CheckResult`, se le pasa al modelo: `regla`, `resultado` (fijo), `detalle_tecnico`, `datos`, y el/los `fragmento(s)` normativos recuperados.
- Se le pide: redactar una explicación en lenguaje natural de **ese** check, citando **solo** la fuente provista, **respetando el resultado tal cual**.
- Reglas del prompt (system): no alterar veredictos; no inventar normas, artículos ni datos; si no hay fragmento, decir "fundamento normativo a confirmar"; tono técnico y neutral; sin promesas de aprobación.
- Modelo: `claude-...` (servidor). Salida estructurada (un texto por check) + un resumen ejecutivo final.

> El LLM nunca ve "libertad" para escribir el veredicto: lo recibe como dato inmutable y solo lo explica. Esa es la garantía de la XAI legal.

---

## 8. Qué sale de librería vs. qué es código tuyo

| Pieza | Origen | Nota |
|---|---|---|
| **Motor de reglas** (checks, estado_global) | **CÓDIGO TUYO** | El corazón. No existe librería que decida cumplimiento contra el PMOT. |
| **Validador de consistencia** narrativa↔checks | **CÓDIGO TUYO** | Garantiza que el LLM no se desvió. |
| Modelo de aptitud (multicriterio) | **CÓDIGO TUYO** | Reusa el del MVP. |
| Sub-score de accesibilidad | **pandana** | Métricas de accesibilidad / shortest paths sobre la red. O reusar lo de Capa 1. |
| Métricas de forma/densidad (si se usan) | **momepy** | Opcional, para enriquecer datos del informe. |
| Retrieval normativo (futuro) | **LlamaIndex** | Al vectorizar. v1 es lookup simple tuyo. |
| Redacción del informe | **Anthropic SDK (Claude)** | Solo redacta. |
| Orquestación (si se vuelve multi-paso) | **LangGraph** | Solo si el agente pasa a conversacional. MVP = one-shot. |
| Schemas / validación | **Pydantic** | DiagnosticReport, CheckResult. |

Foco de tu esfuerzo original: **motor de reglas + validador**. Todo lo demás se reutiliza.

---

## 9. Contrato de salida — `DiagnosticReport` (Pydantic)

```jsonc
{
  "schema_version": "1.0",
  "estado_global": "cumple_con_observaciones",   // cumple | cumple_con_observaciones | no_cumple | no_apto
  "indice_aptitud": 72,                            // 0-100, eje SEPARADO del cumplimiento
  "evaluo_trazado": true,                          // false si no vino ProposedLayout
  "checks": [
    {
      "regla": "fos",
      "resultado": "observacion",
      "es_regla_dura": false,
      "detalle_tecnico": "Ocupación propuesta 0.45 supera el FOS de zona 0.40.",
      "datos": { "ocupacion_propuesta": 0.45, "fos_zona": 0.40 },
      "fuente": { "norma": "Ordenanza 15214", "articulo": "<TODO>" },
      "explicacion": "Texto redactado por el LLM citando la fuente."
    }
  ],
  "riesgos": [
    { "tipo": "sismico", "nivel": "alto", "nota": "Aplica INPRES-CIRSOC 103." }
  ],
  "resumen_ejecutivo": "Párrafo del LLM, coherente con estado_global y checks.",
  "fuentes_citadas": ["Ordenanza 15214", "Ley 8051"],
  "warnings": ["altura: dato faltante, check no_aplica"],
  "disclaimer": "Diagnóstico orientativo. No reemplaza estudios profesionales ni la aprobación municipal."
}
```

Sin campo "probabilidad". Se entrega estado + aptitud + riesgos, todo trazable.

---

## 10. Criterios de aceptación

- [ ] Con un `PolygonContext` que viola una regla dura (ej. intersecta retiro de cauce), `estado_global = "no_apto"` **sin** intervención del LLM.
- [ ] El `report_composer` nunca cambia un `resultado`: test que compara `checks[].resultado` antes y después del LLM (deben ser idénticos).
- [ ] `validator` rechaza/flaggea cualquier `explicacion` que contradiga su `resultado`.
- [ ] Todo check con resultado ≠ `cumple`/`no_aplica` tiene `fuente` no vacía (aunque `articulo` sea `<TODO>`).
- [ ] `indice_aptitud` se calcula aunque `estado_global = no_apto` (ejes separados).
- [ ] `proposed_layout = null` → diagnostica zona sin checks de FOS/FOT/altura; no crashea.
- [ ] Dato faltante → check `no_aplica` + warning, sin crash.
- [ ] El `disclaimer` está siempre presente.

---

## 11. Tests sugeridos
- Violación dura (área protegida) → no_apto, aunque aptitud sea alta.
- FOS excedido → observación con `detalle_tecnico` correcto; LLM lo explica sin negarlo.
- Sin trazado → solo aptitud + restricciones.
- Mock del LLM devolviendo un veredicto contradictorio → `validator` lo detecta y falla el test (prueba de que la barrera funciona).
- Corpus sin el artículo → `fuente.articulo="<TODO>"`, explicación dice "a confirmar", sin inventar.

---

## 12. Límites y fases futuras
- MVP = **informe one-shot**, no asistente conversacional. El "asistente virtual" (consulta en lenguaje natural, simular cambios normativos) es fase futura → ahí entra **LangGraph** como orquestador de un agente multi-paso, con estos mismos checks expuestos como tools.
- Vectorización de la normativa → LlamaIndex, sin tocar el motor de reglas.
- Catálogo de checks v1 es mínimo; se amplía sin reescribir (cada check es una función independiente).

---

## 13. Acción de Ema antes de ejecutar
1. Armar `data/ordenanzas/` con el texto de la Ord. 15214 (y 12998 / Ley 8051) en formato consultable.
2. Confirmar el `articulo` de cada fuente del catálogo (§4) — opcional para arrancar; el motor corre con `<TODO>`.
3. Confirmar pesos del modelo de aptitud (default 0.40/0.30/0.30 del MVP).
4. Verificar que `PolygonContext` expone geometría de restricciones (mismo requisito que Capa 2) para los checks duros `restriccion_hidrica` y `area_protegida`.
```
