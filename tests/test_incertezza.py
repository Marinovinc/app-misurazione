"""Passo 1 — invarianti della propagazione dell'incertezza.

Il test che conta (correzione D) e' quello sulla **somma** di misure che
condividono la scala: trattarle come indipendenti sottostima la varianza.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from misura.grandezza import (
    GrandezzaIncerta,
    covarianza,
    covarianza_congiunta,
    da_covarianza,
)

finiti = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)
positivi = st.floats(min_value=0.1, max_value=1e3, allow_nan=False, allow_infinity=False)
# Deviazioni a magnitudine FISICA (mm): sotto ~1e-3 non c'e' misura. Deviazioni
# subnormali (<~1e-154) fanno underfloware il quadrato nella rappresentazione a
# somma-di-quadrati; e' un limite noto e fuori dominio, non un difetto logico.
deviazioni = st.one_of(
    st.just(0.0),
    st.floats(min_value=1e-3, max_value=1e3, allow_nan=False, allow_infinity=False),
)


def test_costante_ha_varianza_zero() -> None:
    assert GrandezzaIncerta.costante(3.5).varianza == 0.0


@given(valore=finiti, deviazione=deviazioni)
def test_da_deviazione_riporta_la_deviazione(valore: float, deviazione: float) -> None:
    g = GrandezzaIncerta.da_deviazione(valore, deviazione)
    assert g.valore == valore
    if deviazione == 0.0:
        assert g.deviazione == 0.0
    else:
        assert np.isclose(g.deviazione, deviazione, rtol=1e-12, atol=0.0)


@given(valore=finiti, deviazione=positivi, k=finiti)
def test_scalatura_lineare_sulla_deviazione(
    valore: float, deviazione: float, k: float
) -> None:
    g = GrandezzaIncerta.da_deviazione(valore, deviazione)
    scalata = g * k
    assert np.isclose(scalata.deviazione, abs(k) * deviazione)


@given(sigma=positivi, p1=positivi, p2=positivi, s_val=positivi)
def test_modo_comune_somma_e_linvariante_portante(
    sigma: float, p1: float, p2: float, s_val: float
) -> None:
    """Due misure che condividono la scala: la SOMMA ha varianza MAGGIORE del
    caso indipendente. E' qui che ignorare la correlazione sottostima."""
    scala = GrandezzaIncerta.da_deviazione(s_val, sigma, "scala")
    m1 = scala * p1
    m2 = scala * p2

    somma = m1 + m2
    var_indipendente = m1.varianza + m2.varianza  # cio' che farebbe chi ignora la correlazione

    # covarianza positiva -> la somma reale supera la somma "indipendente"
    assert covarianza(m1, m2) > 0.0
    assert somma.varianza > var_indipendente
    # identita' esatta: Var(m1+m2) = Var(m1)+Var(m2)+2Cov(m1,m2)
    assert np.isclose(somma.varianza, var_indipendente + 2.0 * covarianza(m1, m2))


@given(sigma=positivi, p1=positivi, p2=positivi, s_val=positivi)
def test_modo_comune_rapporto_direzione_innocua(
    sigma: float, p1: float, p2: float, s_val: float
) -> None:
    """Il rapporto di due misure che condividono la scala: la scala si cancella.
    Direzione corretta ma innocua: da sola non protegge da nulla, serve accanto
    al test sulla somma. Lo verifico contro il caso indipendente (l'affermazione
    vera), non con un atol assoluto fragile alla cancellazione numerica."""
    scala = GrandezzaIncerta.da_deviazione(s_val, sigma, "scala")
    m1 = scala * p1
    m2 = scala * p2
    r_correlato = m1 / m2

    # stesse marginali, ma sorgenti indipendenti
    m1_indip = GrandezzaIncerta.da_deviazione(m1.valore, m1.deviazione)
    m2_indip = GrandezzaIncerta.da_deviazione(m2.valore, m2.deviazione)
    r_indip = m1_indip / m2_indip

    assert np.isclose(r_correlato.valore, p1 / p2)
    assert r_indip.deviazione > 0.0
    # con la scala condivisa il residuo e' cancellazione numerica: trascurabile
    assert r_correlato.deviazione <= 1e-9 * r_indip.deviazione


@given(n=st.integers(min_value=1, max_value=4), dati=st.data())
def test_covarianza_roundtrip(n: int, dati: st.DataObject) -> None:
    """Interfaccia #2a: costruire da covarianza e riesportarla la conserva."""
    piatta = dati.draw(
        st.lists(
            st.floats(min_value=-3.0, max_value=3.0, allow_nan=False, allow_infinity=False),
            min_size=n * n,
            max_size=n * n,
        )
    )
    a = np.array(piatta, dtype=np.float64).reshape(n, n)
    sigma = a @ a.T  # semidefinita positiva per costruzione
    grandezze = da_covarianza([0.0] * n, sigma)
    ricostruita = covarianza_congiunta(grandezze)
    assert np.allclose(ricostruita, sigma, atol=1e-6, rtol=1e-6)
