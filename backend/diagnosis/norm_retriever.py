"""Retrieval normativo v1 (CAPA 3 §6) — lookup simple por keyword.

Corpus en data/ordenanzas/ (texto plano). Interfaz retrieve(check) -> list[str]
estable para migrar a LlamaIndex (v2) sin tocar el resto.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "ordenanzas"

# norma -> archivo de corpus
NORMA_FILE = {
    "Ordenanza 12998": "ordenanza_12998.txt",
    "Ordenanza 15214": "ordenanza_15214.txt",
}

# regla -> keywords a buscar en el corpus
KEYWORDS = {
    "fos": ["factor de ocupación del suelo", "f.o.s", "fos"],
    "fot": ["factor de ocupación total", "f.o.t", "fot"],
    "altura": ["altura"],
    "sup_min_lote": ["superficie mínima", "sup. min", "superficie min"],
    "densidad": ["densidad"],
    "reserva_verde": ["espacio verde", "equipamiento", "espacios verdes"],
    "uso_permitido": ["uso del suelo", "zonificación", "área urbana"],
    "restriccion_hidrica": ["cauce", "retiro", "inundable", "hídric"],
    "area_protegida": ["reserva", "área protegida", "ambiental"],
}


@lru_cache(maxsize=8)
def _load(fname: str) -> str:
    p = CORPUS_DIR / fname
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def retrieve(regla: str, norma: str | None, max_frags: int = 1) -> list[str]:
    if not norma:
        return []
    fname = NORMA_FILE.get(norma) or NORMA_FILE.get(norma.split(" /")[0])
    if not fname:
        return []  # p.ej. Ley 8051 / INPRES no están en el corpus -> "a confirmar"
    text = _load(fname)
    if not text:
        return []
    low = text.lower()
    frags: list[str] = []
    for kw in KEYWORDS.get(regla, []):
        i = low.find(kw.lower())
        if i >= 0:
            frag = text[max(0, i - 120): i + 260]
            frag = re.sub(r"\s+", " ", frag).strip()
            frags.append(frag)
            if len(frags) >= max_frags:
                break
    return frags
