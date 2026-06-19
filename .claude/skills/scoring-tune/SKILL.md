---
name: scoring-tune
description: Ajusta el modelo de scoring multicriterio (IAT) de Cóndor View — pesos, umbrales y categorías en config.yaml, manteniendo consistencia con el cálculo en 05_scoring.py y los controles del frontend (WeightControls.tsx). Úsala cuando el usuario quiera cambiar cómo se pondera la aptitud territorial, recategorizar zonas o calibrar umbrales de pendiente/accesibilidad.
---

# Ajustar el scoring (IAT)

Fórmula (`pipeline/05_scoring.py`):

```
IAT = 100 × (w_norm·S_norm + w_fis·S_fis + w_acc·S_acc)
```

Más reglas duras que fuerzan `IAT = 0` (override) y generan 13 flags.
Categoría se asigna por umbral sobre el IAT.

## Parámetros (en `pipeline/config.yaml`)

```yaml
pesos:        # DEBEN sumar 1.0
  w_norm: 0.40   # normativo (zonificación/uso de suelo)
  w_fis:  0.30   # físico (pendiente, riesgo hídrico)
  w_acc:  0.30   # accesibilidad (huella urbana, vial, agua)

umbrales:
  pendiente:
    ideal_pct: 5.0    # pendiente óptima
    max_pct:  25.0    # por encima → penaliza fuerte / no apto
  accesibilidad:      # distancias de decaimiento (m)
    d0_huella_m: 8000
    d0_vial_m:   5000
    d0_agua_m:   6000

categorias:   # umbral inferior de IAT por clase
  alta:  70
  media: 40
  baja:   0
```

## Reglas al ajustar

- **Pesos siempre suman 1.0.** Tras editar, verificar:
  ```bash
  cd pipeline && uv run python -c "import yaml;p=yaml.safe_load(open('config.yaml'))['pesos'];print('suma',sum(p.values()))"
  ```
- Cambiar **pesos / umbrales / categorías** NO requiere re-descargar ni re-grillar.
  Basta re-correr las dos últimas etapas:
  ```bash
  uv run python 05_scoring.py && uv run python 06_export.py
  ```
  (ver skill `run-pipeline` para el DAG completo).
- Tras re-exportar, validar rangos y categorías (ver skill `geo-validate`).

## Consistencia con el frontend

`frontend/components/WeightControls.tsx` permite al usuario ajustar pesos en
vivo sobre el mapa (recalcula IAT en el cliente). **Si cambiás la fórmula o el
significado de los pesos en `05_scoring.py`, actualizá también el cálculo en el
frontend** — de lo contrario el "qué pasa si" interactivo diverge del pipeline.

Antes de tocar el cálculo, leé ambos lados:
- `pipeline/05_scoring.py` (fuente de verdad, datos exportados)
- `frontend/components/WeightControls.tsx` (recálculo interactivo)

Mantener idénticos: la combinación lineal, las reglas duras de override y los
cortes de categoría (`categorias` en config ↔ lógica de color/leyenda del frontend).
