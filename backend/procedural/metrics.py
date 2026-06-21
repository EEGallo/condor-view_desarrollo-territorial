"""Métricas del SceneModel == ProposedLayout para Capa 3 (CAPA 2 §5.5).

Áreas en CRS métrico (5343), antes de reproyectar.
"""

from __future__ import annotations


def compute(sup_total: float, lotes: list[dict], espacios: list[dict],
            masas: list[dict]) -> dict:
    sup_lotes = sum(l["geom"].area for l in lotes)
    sup_verde = sum(e["geom"].area for e in espacios)
    # calles = residual (cierra la identidad calles+lotes+verde = total).
    sup_calles = max(0.0, sup_total - sup_lotes - sup_verde)

    sup_footprint = sum(m["footprint"].area for m in masas)
    sup_construible = sum(m["footprint"].area * m["n_pisos"] for m in masas)

    return {
        "n_lotes": len(lotes),
        "sup_total_m2": round(sup_total, 1),
        "sup_calles_m2": round(sup_calles, 1),
        "sup_lotes_m2": round(sup_lotes, 1),
        "sup_verde_m2": round(sup_verde, 1),
        "sup_verde_pct": round(sup_verde / sup_total, 3) if sup_total else 0.0,
        "ocupacion_propuesta": round(sup_footprint / sup_total, 3) if sup_total else 0.0,
        "fot_propuesto": round(sup_construible / sup_lotes, 3) if sup_lotes else 0.0,
        "densidad_lotes_ha": round(len(lotes) / (sup_total / 10000.0), 2) if sup_total else 0.0,
    }
