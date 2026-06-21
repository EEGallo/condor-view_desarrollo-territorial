"""Tests del parser de indicadores normativos (Caso A).

Cubre los criterios de aceptación de la spec + los formatos reales observados en
el dump del FeatureServer IU_GC (PASO 0): coma decimal, sentinel "...", FOT>1.

Correr:  pipeline/.venv/bin/python -m pytest pipeline/tests/test_normativa_parser.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.normativa_parser import parse_indicador, resolver_indicador


# --- parse_indicador: criterios de aceptación de la spec ---

def test_fos_coma_decimal():
    assert parse_indicador("0,6", "fos") == 0.6


def test_fos_porcentaje_explicito():
    assert parse_indicador("60%", "fos") == 0.6


def test_fos_mayor_a_uno_sin_pct_es_porcentaje():
    assert parse_indicador("60", "fos") == 0.6


def test_fot_puede_ser_mayor_a_uno():
    assert parse_indicador("1,5", "fot") == 1.5


def test_fot_porcentaje():
    assert parse_indicador("150%", "fot") == 1.5


def test_altura_metros():
    assert parse_indicador("9 m", "altura") == 9.0


def test_altura_pisos_no_es_metros():
    w = []
    assert parse_indicador("PB+3", "altura", w) is None
    assert w  # warning registrado


def test_fos_sin_dato():
    assert parse_indicador("s/d", "fos") is None


def test_fot_none():
    assert parse_indicador(None, "fot") is None


def test_fos_basura_warning():
    w = []
    assert parse_indicador("abc", "fos", w) is None
    assert w


# --- formatos reales del dump IU_GC (PASO 0) ---

def test_real_fos_coma():
    assert parse_indicador("0,75", "fos") == 0.75


def test_real_fot_entero_grande():
    assert parse_indicador("8", "fot") == 8.0


def test_real_fot_coma():
    assert parse_indicador("4,50", "fot") == 4.5


def test_real_altura_entero():
    assert parse_indicador("18", "altura") == 18.0


def test_sentinel_tres_puntos_es_nulo():
    # "..." es el sentinel de dato faltante confirmado en IU_GC.
    assert parse_indicador("...", "fos") is None
    assert parse_indicador("...", "fot") is None
    assert parse_indicador("...", "altura") is None


# --- sanity de rangos ---

def test_fos_fuera_de_rango():
    w = []
    assert parse_indicador("250", "fos", w) is None  # 2.5 tras /100? no: 250>1 -> 2.5 -> fuera
    assert w


def test_fot_fuera_de_rango():
    w = []
    assert parse_indicador("99", "fot", w) is None
    assert w


# --- resolver_indicador ---

def test_resolver_primera_no_nula_y_difieren():
    r = resolver_indicador(["0,6", "0,4", None], "fos")
    assert r["valor"] == 0.6
    assert r["raw"] == ["0,6", "0,4", None]
    assert r["variantes_difieren"] is True


def test_resolver_todas_nulas():
    r = resolver_indicador([None, None, None], "fot")
    assert r["valor"] is None
    assert r["variantes_difieren"] is False


def test_resolver_iguales_no_difieren():
    r = resolver_indicador(["0,5", "0,50", "0,5"], "fos")
    assert r["valor"] == 0.5
    assert r["variantes_difieren"] is False


def test_resolver_real_iu_gc_difieren():
    # fos_1=0,75 > fos_2=0,70 > fos_3=0,65 (tiers reales)
    r = resolver_indicador(["0,75", "0,70", "0,65"], "fos")
    assert r["valor"] == 0.75
    assert r["variantes_difieren"] is True
    assert r["warnings"]


if __name__ == "__main__":
    import traceback

    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
