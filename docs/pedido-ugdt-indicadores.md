# Pedido a la UGDT / Municipalidad de San Rafael — capa de indicadores urbanísticos

> **Para qué:** destrabar los campos **FOS / FOT / altura máxima** del análisis
> territorial de Cóndor View. Hoy salen "s/d" porque San Rafael no publica esos
> indicadores; el resto de los departamentos del AMM sí.

## Qué tenemos hoy

Cóndor View ya consume la capa de parcelas de San Rafael de la IDE Mendoza:

- `https://mpipgis1.mendoza.gov.ar/server/rest/services/Hosted/San_Rafael/FeatureServer/0`
- Trae el campo **`zona`** con 4 categorías gruesas: `URBANA`, `SUBURBANA`,
  `RURAL`, `SECANA` (+ vacío en algunas parcelas).
- **NO trae** FOS, FOT ni altura máxima.

Por eso el sistema funciona en **"Caso B"**: la categoría se resuelve contra una
tabla local (`pipeline/config/zonas.yaml`) que solo tiene uso, densidad y
superficie mínima (de la Ordenanza 12998, Anexo II). FOS/FOT/altura quedan en
`s/d` porque la Ordenanza los define "según zona" y no publica el número por
estas categorías gruesas.

## Qué pedir (opción A — la mejor)

**Una capa de parcelas con indicadores urbanísticos publicada en la IDE Mendoza**,
igual a las que YA existen para otros departamentos:

| Departamento | Servicio (modelo a replicar) |
|---|---|
| Capital | `Hosted/parcelas_indicadores_capital_v2` |
| Godoy Cruz | `Hosted/parcelas_indicadores_gc_v1` |
| Guaymallén | `Hosted/parcelas_indicadores_gllen_v2_2` |
| Las Heras | `Hosted/parcelas_con_zonificacion_lh_v1` |

Esas capas traen exactamente estos campos por parcela (verificado en Capital):

```
zona, fos_min, fos_max, fot_min, fot_max, altura_max, links_usos, zona_indic
```

**Pedido concreto:** que la UGDT publique `parcelas_indicadores_san_rafael`
(FeatureServer en la misma IDE) con, como mínimo, estos campos por parcela:

- `fos` (o `fos_min` / `fos_max`) — Factor de Ocupación del Suelo (0–1)
- `fot` (o `fot_min` / `fot_max`) — Factor de Ocupación Total
- `altura_max` — altura máxima permitida (metros)
- `zona` / `zona_indic` — la sub-zona normativa de detalle
- (opcional) `densidad`, `usos permitidos`

## Datos mínimos que necesitamos de vuelta

Con que nos pasen **esto** ya lo conectamos (1 cambio de config):

1. **URL del FeatureServer** y el **layer_id** (número de capa).
2. **Nombres exactos de los campos** de FOS, FOT y altura (tal cual figuran en
   *Fields* de la capa) — los formatos de valor (coma decimal, "%", "s/d") ya los
   maneja el parser.
3. Si requiere token de acceso, el token o el modo de auth.

## Opción B (si no pueden publicar la capa)

La **tabla de indicadores por sub-zona** de la Ordenanza de zonificación (la que
la Ord. 12998 menciona como "según zona" pero no incluye en el cuerpo), en
formato tabla/PDF legible, **+** confirmación de cómo se asigna cada parcela a su
sub-zona de detalle. Con eso poblamos `zonas.yaml` manualmente.

> Nota: la capa actual solo distingue 4 categorías gruesas (URBANA/SUBURBANA/
> RURAL/SECANA). Si los FOS/FOT varían por sub-zona más fina, hace falta ese
> nivel de detalle en la capa de parcelas para asignarlos bien (de ahí que la
> opción A sea la robusta).

## Qué pasa de nuestro lado cuando llegue

- Con la capa A: editamos `pipeline/config/sources.yaml` →
  `base_url` + `layer_id` + `field_map` (fos/fot/altura). El sistema pasa solo de
  **Caso B → Caso A** y los `s/d` se rellenan con el dato real del FeatureServer.
- El parser (`pipeline/lib/normativa_parser.py`) ya tolera valores STRING con
  coma decimal, "%", rangos y sentinels — no hay que tocar código.

## Lo que NO es un problema de datos faltantes

- **Riesgo hídrico "s/d"**: depende de la ubicación del polígono (no hay cauce
  cerca). Aparece al dibujar próximo a un río/canal. No requiere pedido.
- **Categoría "sin clasificar"**: parcelas con el campo `zona` vacío en el dato
  municipal. Solo la Muni puede completarlo en la capa de parcelas.
