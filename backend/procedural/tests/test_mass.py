"""Tests de mass_generator (CAPA 2 §8) — sobre normativo por lote.

Correr:  PYTHONPATH=. pipeline/.venv/bin/python backend/procedural/tests/test_mass.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from shapely.geometry import box

from backend.procedural import mass_generator as mg


def _lote(sup=1000.0, zona=None):
    # box de área ~sup (lado = sqrt(sup)), en coords métricas plausibles SR.
    side = sup ** 0.5
    return {"lote_id": "M01-L01", "geom": box(2_500_000, 6_180_000,
                                              2_500_000 + side, 6_180_000 + side),
            "zona": zona}


def test_fot_alcanzable():
    # fos=0.5, fot=1.5, altura=9 -> n_pisos=3, altura=9, fot_apl≈1.5
    z = {"uso_permitido": "residencial_media", "fos": 0.5, "fot": 1.5, "altura_max_m": 9}
    masas, _ = mg.generate([_lote(zona=z)])
    m = masas[0]
    assert m["n_pisos"] == 3, m["n_pisos"]
    assert m["altura_m"] == 9.0, m["altura_m"]
    assert abs(m["fot_aplicado"] - 1.5) < 0.05, m["fot_aplicado"]
    assert abs(m["fos_aplicado"] - 0.5) < 0.05, m["fos_aplicado"]


def test_altura_limita_pisos():
    # fot alto, altura baja -> altura manda; fot_apl < fot
    z = {"uso_permitido": "comercial", "fos": 0.5, "fot": 3.0, "altura_max_m": 6}
    masas, _ = mg.generate([_lote(zona=z)])
    m = masas[0]
    assert m["n_pisos"] == 2, m["n_pisos"]      # floor(6/3)=2
    assert m["altura_m"] == 6.0, m["altura_m"]
    assert m["fot_aplicado"] < 3.0
    assert abs(m["fot_aplicado"] - 1.0) < 0.05, m["fot_aplicado"]


def test_defaults_cuando_falta_normativa():
    z = {"uso_permitido": "rural", "fos": None, "fot": None, "altura_max_m": None}
    masas, warns = mg.generate([_lote(zona=z)])
    assert masas[0]["altura_m"] <= mg.DEFAULT_ALTURA
    assert any("defaults" in w for w in warns), warns


def test_base_z_desde_dem():
    z = {"uso_permitido": "residencial", "fos": 0.4, "fot": 0.6, "altura_max_m": 9}
    masas, _ = mg.generate([_lote(zona=z)])
    # DEM presente -> base_z > 0 (San Rafael ~700m). Si falta DEM, 0 + warning.
    assert masas[0]["base_z_m"] >= 0.0


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn(); print("PASS", fn.__name__)
        except Exception:
            failed += 1; print("FAIL", fn.__name__); traceback.print_exc()
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
