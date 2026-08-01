"""Passo 2 — sistematici (correzione A): trattamenti opposti per tipo.

Il test che conta: i `SistematicoLimitato` gonfiano l'incertezza, il
`BiasCorreggibile` NON tocca la varianza.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from misura.grandezza import GrandezzaIncerta
from misura.osservazione import Osservazione
from misura.provenienza import DichiarataDaUtente
from misura.sistematici import BiasCorreggibile, SistematicoLimitato

positivi = st.floats(min_value=1e-3, max_value=1e3, allow_nan=False, allow_infinity=False)
finiti = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False, allow_infinity=False)


def test_limite_negativo_rifiutato() -> None:
    with pytest.raises(ValueError):
        SistematicoLimitato(-1.0)


def test_incertezza_bias_negativa_rifiutata() -> None:
    with pytest.raises(ValueError):
        BiasCorreggibile(valore=1.0, incertezza=-0.5)


@given(limite=positivi)
def test_limite_in_deviazione_standard_uniforme(limite: float) -> None:
    assert np.isclose(
        SistematicoLimitato(limite).incertezza_standard(), limite / math.sqrt(3.0)
    )


@given(valore=finiti, dev=positivi, limite=positivi)
def test_limitati_gonfiano_sigma(valore: float, dev: float, limite: float) -> None:
    g = GrandezzaIncerta.da_deviazione(valore, dev)
    oss = Osservazione(
        grandezza=g,
        provenienza=DichiarataDaUtente(),
        limitati=(SistematicoLimitato(limite),),
    )
    atteso = dev**2 + (limite / math.sqrt(3.0)) ** 2
    con = oss.grandezza_con_limitati()
    assert con.valore == valore  # il valore non cambia
    assert np.isclose(con.varianza, atteso)
    assert con.varianza > g.varianza  # gonfiata


@given(valore=finiti, dev=positivi, bias=finiti)
def test_il_bias_non_tocca_la_varianza(valore: float, dev: float, bias: float) -> None:
    g = GrandezzaIncerta.da_deviazione(valore, dev)
    oss = Osservazione(
        grandezza=g,
        provenienza=DichiarataDaUtente(),
        bias=BiasCorreggibile(valore=bias),
    )
    # con il solo bias e nessun limitato, la varianza resta quella casuale:
    # il bias non e' incertezza (correzione A)
    assert np.isclose(oss.grandezza_con_limitati().varianza, g.varianza)
