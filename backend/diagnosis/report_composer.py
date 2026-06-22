"""Redacción del informe (CAPA 3 §7) — OpenAI GPT, SOLO redacta.

NOTA: el spec especifica Claude/Anthropic; por indicación del usuario se usa
OpenAI GPT (key en OPENAI_API_KEY). El LLM nunca decide ni altera veredictos:
recibe `resultado` como dato inmutable y solo lo explica (slot-filling por check).
Si no hay key o la API falla -> redacción determinística (detalle_tecnico) + warning.
"""

from __future__ import annotations

import json
import os
from typing import Any

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM = (
    "Sos un asistente técnico que redacta diagnósticos normativos de urbanismo "
    "en español rioplatense, tono técnico y neutral. REGLAS INNEGOCIABLES: "
    "(1) NO alteres ni inventes veredictos: el campo 'resultado' de cada check es "
    "inmutable, solo lo explicás. (2) NO inventes normas, artículos ni datos: citá "
    "únicamente los fragmentos provistos; si no hay fragmento, escribí 'fundamento "
    "normativo a confirmar'. (3) No prometas aprobación municipal. (4) Para cada "
    "check, una explicación breve (1-3 frases) coherente con su 'resultado' y su "
    "'detalle_tecnico'. Devolvé EXCLUSIVAMENTE JSON válido."
)


def _template_resumen(estado: str, aptitud: int, checks: list) -> str:
    n_obs = sum(1 for c in checks if c.resultado == "observacion")
    n_nc = sum(1 for c in checks if c.resultado == "no_cumple")
    return (
        f"Estado normativo: {estado.replace('_', ' ')}. Índice de aptitud "
        f"territorial: {aptitud}/100. {n_nc} incumplimiento(s) y {n_obs} "
        f"observación(es) detectadas. Diagnóstico orientativo."
    )


def compose(
    checks: list, retrieved: dict[str, list[str]], estado: str, aptitud: int
) -> tuple[dict[str, str], str, list[str]]:
    fallback_expl = {c.regla: c.detalle_tecnico for c in checks}
    fallback_resumen = _template_resumen(estado, aptitud, checks)

    if not os.environ.get("OPENAI_API_KEY"):
        return fallback_expl, fallback_resumen, [
            "report: OPENAI_API_KEY ausente -> redacción determinística (sin LLM)"
        ]

    try:
        from openai import OpenAI

        client = OpenAI()
        payload: dict[str, Any] = {
            "estado_global": estado,
            "indice_aptitud": aptitud,
            "checks": [
                {
                    "regla": c.regla,
                    "resultado": c.resultado,
                    "detalle_tecnico": c.detalle_tecnico,
                    "datos": c.datos,
                    "fuente": c.fuente.model_dump() if c.fuente else None,
                    "fragmentos": retrieved.get(c.regla, []),
                }
                for c in checks
            ],
        }
        user = (
            "Datos del diagnóstico (veredictos ya decididos, inmutables):\n"
            + json.dumps(payload, ensure_ascii=False)
            + "\n\nDevolvé JSON: {\"explicaciones\": {<regla>: <texto>}, "
            "\"resumen_ejecutivo\": <texto>}"
        )
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        expl_in = data.get("explicaciones", {}) or {}
        explicaciones = {
            c.regla: (expl_in.get(c.regla) or c.detalle_tecnico) for c in checks
        }
        resumen = data.get("resumen_ejecutivo") or fallback_resumen
        return explicaciones, resumen, []
    except Exception as exc:
        return fallback_expl, fallback_resumen, [
            f"report: LLM no disponible ({exc}) -> redacción determinística"
        ]
