"""Passo 5 — riferimento: rilevamento ArUco reale + tolleranza dimensionale (corr. B)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from misura.grandezza import GrandezzaIncerta
from misura.riferimento import (
    RiferimentoNonTrovato,
    marker_stampato_non_verificato,
    marker_stampato_verificato,
    lato_pixel_aruco,
    scala_da_lato_pixel,
    tessera_id1,
)

from _aruco_util import immagine_marker


def test_rileva_lato_pixel_reale() -> None:
    img = immagine_marker(200)
    lato = lato_pixel_aruco(img)
    assert abs(lato - 200.0) <= 2.0  # ~199 px, i corner cadono sul bordo esterno


def test_riferimento_non_trovato_solleva() -> None:
    tela = np.full((100, 100), 255, np.uint8)
    with pytest.raises(RiferimentoNonTrovato):
        lato_pixel_aruco(tela)


def test_lato_negativo_rifiutato() -> None:
    with pytest.raises(ValueError):
        marker_stampato_verificato(-10.0)


def test_scala_valore_e_incertezza() -> None:
    rif = marker_stampato_verificato(50.0, 0.2)
    scala = scala_da_lato_pixel(rif, 200.0, 0.5)
    assert np.isclose(scala.valore, 50.0 / 200.0)
    assert scala.varianza > 0.0


def test_correzione_B_non_verificato_piu_incerto_del_verificato() -> None:
    verificato = marker_stampato_verificato(50.0, 0.2)
    non_verificato = marker_stampato_non_verificato(50.0, 0.02)  # 1 mm di limite
    s_v = scala_da_lato_pixel(verificato, 200.0, 0.5)
    s_nv = scala_da_lato_pixel(non_verificato, 200.0, 0.5)
    assert s_nv.deviazione > s_v.deviazione


def test_correzione_B_tolleranza_dimensionale_domina_sugli_angoli() -> None:
    """Per un marker stampato non verificato, la tolleranza di stampa domina il
    rumore d'angolo: e' il punto della correzione B."""
    rif = marker_stampato_non_verificato(50.0, 0.02)  # limite 1 mm -> sigma 0.577 mm
    lato_px = 200.0
    sigma_lato = 0.5 * math.sqrt(2.0) / 2.0

    var_dim = (rif.dimensione_incerta() / GrandezzaIncerta.costante(lato_px)).varianza
    var_ang = (
        GrandezzaIncerta.costante(rif.lato_mm)
        / GrandezzaIncerta.da_deviazione(lato_px, sigma_lato)
    ).varianza

    assert var_dim > var_ang


def test_tessera_id1_dimensione_nota() -> None:
    rif = tessera_id1()
    assert np.isclose(rif.lato_mm, 85.60)
    assert rif.tolleranza_dim_mm < 0.5  # stretta
