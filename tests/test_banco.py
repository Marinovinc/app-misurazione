"""Passo 7 — banco sintetico: copertura, controllo negativo (corr. E), determinismo."""

from __future__ import annotations

import math

import numpy as np
import pytest

from misura.validazione.banco import (
    copertura_nominale,
    valuta_copertura,
)
from misura.validazione.sintetico import genera_scene, scenario_predefinito

SEED = 20260801


def test_copertura_nominale_e_erf() -> None:
    assert np.isclose(copertura_nominale(2.0), math.erf(2.0 / math.sqrt(2.0)))
    assert 0.95 < copertura_nominale(2.0) < 0.96


def test_con_dimensionale_non_crolla() -> None:
    scene = genera_scene(scenario_predefinito(), n=2000, seed=SEED)
    r = valuta_copertura(scene, k=2.0, con_dimensionale=True)
    # sistematico uniforme dominante -> a k=2 il banco sovra-copre, mai crolla
    assert r.copertura >= 0.95


def test_controllo_negativo_fa_crollare_la_copertura() -> None:
    """Correzione E: omettere la tolleranza del riferimento da Sigma fa crollare
    la copertura. Se non crollasse, il banco non starebbe verificando nulla."""
    scene = genera_scene(scenario_predefinito(), n=2000, seed=SEED)
    con = valuta_copertura(scene, k=2.0, con_dimensionale=True)
    senza = valuta_copertura(scene, k=2.0, con_dimensionale=False)
    assert senza.copertura < 0.5
    assert con.copertura - senza.copertura > 0.4


def test_determinismo_stesso_seed() -> None:
    a = genera_scene(scenario_predefinito(), n=500, seed=7)
    b = genera_scene(scenario_predefinito(), n=500, seed=7)
    assert [s.lato_target_px_oss for s in a] == [s.lato_target_px_oss for s in b]
    assert [s.errore_stampa_mm for s in a] == [s.errore_stampa_mm for s in b]


def test_scene_vuote_rifiutate() -> None:
    with pytest.raises(ValueError):
        valuta_copertura([], k=2.0)
