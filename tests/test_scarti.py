"""Passo 6 — registro degli scarti: conteggio, guard metodologico, monotonicita'."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from misura.grandezza import GrandezzaIncerta
from misura.scarti import CriterioScarto, RegistroScarti, Scarto

positivi = st.floats(min_value=1e-2, max_value=1e3, allow_nan=False, allow_infinity=False)
interi = st.integers(min_value=1, max_value=10)
n_scarti = st.integers(min_value=0, max_value=10)


def _scarti(n: int) -> tuple[Scarto, ...]:
    return tuple(
        Scarto(f"s{i}", CriterioScarto.NITIDEZZA_INSUFFICIENTE) for i in range(n)
    )


def test_tenuti_zero_rifiutato() -> None:
    with pytest.raises(ValueError):
        RegistroScarti(tenuti=0)


def test_criteri_di_scarto_sono_indipendenti_dal_risultato() -> None:
    """Guard metodologico: l'insieme e' chiuso e nessun criterio dipende dal
    risultato. Un futuro 'DISACCORDO_RISULTATO' romperebbe questo test."""
    attesi = {
        "NITIDEZZA_INSUFFICIENTE",
        "ANGOLO_BASE_FUORI_RANGE",
        "MARKER_BASSA_CONFIDENZA",
        "RESIDUO_RIPROIEZIONE_ALTO",
    }
    assert {c.name for c in CriterioScarto} == attesi


def test_zero_scarti_non_cambia_l_incertezza() -> None:
    g = GrandezzaIncerta.da_deviazione(100.0, 2.0)
    reg = RegistroScarti(tenuti=3)
    assert reg.fattore_inflazione() == 1.0
    assert np.isclose(reg.applica(g).deviazione, g.deviazione)


def test_conteggio_per_criterio() -> None:
    scarti = (
        Scarto("a", CriterioScarto.NITIDEZZA_INSUFFICIENTE),
        Scarto("b", CriterioScarto.NITIDEZZA_INSUFFICIENTE),
        Scarto("c", CriterioScarto.MARKER_BASSA_CONFIDENZA),
    )
    reg = RegistroScarti(tenuti=2, scarti=scarti)
    conteggio = reg.conteggio_per_criterio()
    assert conteggio[CriterioScarto.NITIDEZZA_INSUFFICIENTE] == 2
    assert conteggio[CriterioScarto.MARKER_BASSA_CONFIDENZA] == 1
    assert reg.n_totali == 5


@given(tenuti=interi, dev=positivi, k=n_scarti)
def test_monotonicita_piu_scarti_non_riduce_l_incertezza(
    tenuti: int, dev: float, k: int
) -> None:
    """Property test portante: aggiungere uno scarto non fa MAI scendere
    l'incertezza riportata (§6.3)."""
    g = GrandezzaIncerta.da_deviazione(100.0, dev)
    reg_k = RegistroScarti(tenuti=tenuti, scarti=_scarti(k))
    reg_k1 = RegistroScarti(tenuti=tenuti, scarti=_scarti(k + 1))
    dev_k = reg_k.applica(g).deviazione
    dev_k1 = reg_k1.applica(g).deviazione
    assert dev_k1 >= dev_k - 1e-12
    assert dev_k >= dev - 1e-12  # e mai sotto l'incertezza di partenza


@given(tenuti=interi, dev=positivi, k=n_scarti)
def test_inflazione_porta_a_f_per_deviazione(tenuti: int, dev: float, k: int) -> None:
    g = GrandezzaIncerta.da_deviazione(100.0, dev)
    reg = RegistroScarti(tenuti=tenuti, scarti=_scarti(k))
    atteso = g.deviazione * reg.fattore_inflazione()
    assert np.isclose(reg.applica(g).deviazione, atteso)
    assert reg.applica(g).valore == g.valore  # il valore non cambia
