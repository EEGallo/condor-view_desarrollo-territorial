"""Tests CAPA 3 (§10-11). Determinísticos (sin LLM: degrada a detalle_tecnico).

Correr: PYTHONPATH=. pipeline/.venv/bin/python backend/diagnosis/tests/test_diagnose.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.pop("OPENAI_API_KEY", None)  # forzar redacción determinística en tests

from backend.diagnosis.diagnose import diagnose
from backend.diagnosis.schema import CheckResult, Fuente, ProposedLayout
from backend.diagnosis import validator

ZONA_URBANA = {
    "categoria": "URBANA", "uso_permitido": ["residencial_media", "comercial"],
    "fos": 0.60, "fot": 1.5, "altura_max_m": 12, "densidad": "alta",
    "sup_min_lote_m2": 200,
}
ZONA_RESERVA = {
    "categoria": "reserva_natural", "uso_permitido": ["reserva_natural"],
    "fos": None, "fot": None, "altura_max_m": None, "densidad": None,
    "sup_min_lote_m2": None,
}


def ctx(zona, restricciones=None, riesgo="bajo", pend=4.0):
    return {
        "polygon": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "normativa": {"modo": "tabla", "zonas": [zona], "restricciones": restricciones or []},
        "fisico": {"pendiente_media_pct": pend, "riesgo_hidrico": riesgo},
        "accesibilidad": {"dist_huella_urbana_m": 500, "dist_vial_principal_m": 100, "equipamiento": []},
        "hidrografia": [],
    }


def test_regla_dura_fuerza_no_apto():
    r = diagnose(ctx(ZONA_URBANA, restricciones=[{"tipo": "retiro_cauce", "geometria_afectada_pct": 12}]), None)
    assert r.estado_global == "no_apto", r.estado_global
    # aptitud se calcula igual (ejes separados)
    assert 0 <= r.indice_aptitud <= 100
    rh = next(c for c in r.checks if c.regla == "restriccion_hidrica")
    assert rh.resultado == "no_cumple" and rh.es_regla_dura


def test_area_protegida_no_apto_aunque_aptitud():
    r = diagnose(ctx(ZONA_RESERVA), None)
    assert r.estado_global == "no_apto"
    assert any(c.regla == "area_protegida" and c.resultado == "no_cumple" for c in r.checks)


def test_fos_excedido_observacion():
    layout = ProposedLayout(ocupacion_propuesta=0.65, fot_propuesto=1.0,
                            n_lotes=10, sup_lotes_m2=3000, sup_verde_pct=0.12,
                            densidad_lotes_ha=5)
    r = diagnose(ctx(ZONA_URBANA), layout)
    fos = next(c for c in r.checks if c.regla == "fos")
    assert fos.resultado == "observacion", fos.resultado
    assert "0.65" in fos.detalle_tecnico or "0.6" in fos.detalle_tecnico
    assert r.estado_global == "cumple_con_observaciones"


def test_sin_trazado_solo_aptitud():
    r = diagnose(ctx(ZONA_URBANA), None)
    assert r.evaluo_trazado is False
    assert any(c.regla == "fos" and c.resultado == "no_aplica" for c in r.checks)
    assert r.indice_aptitud > 0


def test_dato_faltante_no_aplica():
    z = dict(ZONA_URBANA, fos=None)
    layout = ProposedLayout(ocupacion_propuesta=0.5, n_lotes=10, sup_lotes_m2=3000, sup_verde_pct=0.12)
    r = diagnose(ctx(z), layout)
    fos = next(c for c in r.checks if c.regla == "fos")
    assert fos.resultado == "no_aplica"
    assert any("fos" in w for w in r.warnings)


def test_validator_detecta_contradiccion():
    # LLM "alucina" un cumple en un check no_cumple -> validator lo reemplaza.
    c = CheckResult(regla="fos", resultado="no_cumple", detalle_tecnico="Excede FOS.",
                    explicacion="La zona cumple plenamente con el FOS.",
                    fuente=Fuente(norma="Ordenanza 12998"))
    w = validator.validate([c], "no_cumple")
    assert any("contradec" in x for x in w), w
    assert c.explicacion == "Excede FOS."  # reemplazada por detalle técnico


def test_disclaimer_y_fuentes():
    r = diagnose(ctx(ZONA_URBANA), None)
    assert r.disclaimer
    for c in r.checks:
        if c.resultado not in ("cumple", "no_aplica"):
            assert c.fuente is not None, c.regla


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
