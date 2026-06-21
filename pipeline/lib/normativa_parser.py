"""Parser robusto de indicadores normativos (FOS/FOT/altura) — Caso A.

La capa de zonificación de UGDT/Mendoza trae los indicadores como STRING, no
numéricos. Formatos observados (PASO 0, dump real del FeatureServer IU_GC de
Godoy Cruz, mismo esquema):

  zonific    : "Centro Civico", "Comercial Mixta", ... (categoría)
  fos_1/2/3  : "0,75", "0,80", "0,70"   (coma decimal, 0..1)  + sentinel "..."
  fot_1/2/3  : "4,50", "8", "6,40"      (coma decimal, PUEDE ser >1) + "..."
  altura_max : "18", "24", "30"         (metros, entero) + "..."

Las 3 variantes de FOS/FOT difieren entre sí (son tiers, p.ej. por altura/uso);
su semántica exacta NO está confirmada -> se preserva el crudo y se marca.

Nunca lanza excepción: caso no contemplado -> None + warning con el valor crudo.
"""

from __future__ import annotations

import re

# Sentinels de dato faltante (case-insensitive, tras strip).
# "..." y "…" confirmados en el dump real de IU_GC.
NULL_TOKENS = {"", "-", "...", "…", "s/d", "n/d", "sd", "nd", "sin dato"}

# Primer número con signo/decimal opcional. Se corre DESPUÉS de coma->punto.
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")

# Patrón de pisos ("PB+3", "Nº pisos", "3 pisos") -> NO interpretar como metros.
_PISOS_RE = re.compile(r"pb\s*\+|\bpisos?\b|n[º°o]\s*pisos", re.IGNORECASE)


def parse_indicador(
    raw: "str | None", kind: str, warnings: "list[str] | None" = None
) -> "float | None":
    """kind ∈ {'fos','fot','altura'}. Devuelve float normalizado o None.

    Reglas en el docstring del módulo y en la spec del Caso A.
    """

    def warn(msg: str) -> None:
        if warnings is not None:
            warnings.append(msg)

    if raw is None:
        return None

    s = str(raw).strip()
    if s.lower() in NULL_TOKENS:
        return None

    # Pisos: no es metros -> resolver aparte.
    if kind == "altura" and _PISOS_RE.search(s):
        warn(f"altura: patrón de pisos no interpretable como metros: {raw!r}")
        return None

    has_pct = "%" in s
    s_norm = s.replace(",", ".")  # coma decimal -> punto
    m = _NUM_RE.search(s_norm)
    if m is None:
        warn(f"{kind}: sin número parseable en {raw!r}")
        return None

    try:
        val = float(m.group())
    except ValueError:
        warn(f"{kind}: número inválido en {raw!r}")
        return None

    # '%' explícito divide (vale para fos y fot).
    if kind in ("fos", "fot") and has_pct:
        val = val / 100.0

    if kind == "fos":
        # FOS ∈ [0,1]. ">1 sin %" se asume porcentaje ("60" -> 0.6).
        if not has_pct and val > 1:
            val = val / 100.0
        if not (0.0 <= val <= 1.0):
            warn(f"fos fuera de [0,1]: {raw!r} -> {val}")
            return None
        return val

    if kind == "fot":
        # FOT puede ser >1; NO dividir salvo '%' explícito.
        if not (0.0 < val <= 10.0):
            warn(f"fot fuera de (0,10]: {raw!r} -> {val}")
            return None
        return val

    if kind == "altura":
        # Metros.
        if not (0.0 < val <= 200.0):
            warn(f"altura fuera de (0,200]: {raw!r} -> {val}")
            return None
        return val

    warn(f"kind desconocido '{kind}' para {raw!r}")
    return None


def resolver_indicador(valores: "list[str | None]", kind: str) -> dict:
    """Selecciona el valor canónico entre las 3 variantes, sin colapsar silencioso.

    Returns {'valor': float|None, 'raw': [...], 'variantes_difieren': bool,
             'warnings': [...]}.

    Regla provisional: canónico = primera variante no nula parseable
    (fos_1/fot_1 = caso base). PENDIENTE confirmar si las variantes son por
    uso/sector. Las 3 crudas se preservan SIEMPRE (trazabilidad / XAI legal).
    """
    warnings: list[str] = []
    parsed = [parse_indicador(v, kind, warnings) for v in valores]
    no_nulos = [p for p in parsed if p is not None]

    valor = next((p for p in parsed if p is not None), None)
    distintos = {round(p, 6) for p in no_nulos}
    variantes_difieren = len(distintos) > 1
    if variantes_difieren:
        warnings.append(
            f"{kind}: variantes difieren {list(valores)!r} -> {no_nulos}; "
            "se usa la 1ra (caso base, semántica sin confirmar)"
        )

    return {
        "valor": valor,
        "raw": list(valores),
        "variantes_difieren": variantes_difieren,
        "warnings": warnings,
    }
