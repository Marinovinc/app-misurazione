"""Passo 5 — pipeline: scala di modo comune -> misure -> esito."""

from __future__ import annotations

import numpy as np

from misura.esito import EntroTolleranza, FuoriTolleranza, Tolleranza
from misura.grandezza import GrandezzaIncerta, covarianza
from misura.modalita import ModalitaStima
from misura.pipeline import (
    SegmentoPixel,
    grandezze_segmenti,
    misura_da_immagine,
    misura_da_scala,
)
from misura.riferimento import marker_stampato_verificato

from _aruco_util import immagine_marker


def test_misura_lunghezza_metrica() -> None:
    scala = GrandezzaIncerta.da_deviazione(0.25, 0.001, "scala")  # 0.25 mm/px
    g = misura_da_scala(scala, SegmentoPixel(lunghezza_px=400.0, sigma_px=1.0))
    assert np.isclose(g.valore, 100.0)  # 400 px * 0.25 mm/px


def test_misure_condividono_la_scala() -> None:
    scala = GrandezzaIncerta.da_deviazione(0.25, 0.01, "scala")
    gs = grandezze_segmenti(
        scala, [SegmentoPixel(400.0, 1.0), SegmentoPixel(200.0, 1.0)]
    )
    assert covarianza(gs[0], gs[1]) > 0.0  # modo comune presente


def test_end_to_end_da_immagine() -> None:
    img = immagine_marker(200)
    rif = marker_stampato_verificato(50.0, 0.2)  # scala ~ 50/199 mm/px
    segmenti = [SegmentoPixel(lunghezza_px=398.0, sigma_px=1.0)]
    esiti = misura_da_immagine(
        img, rif, segmenti, ModalitaStima(), Tolleranza(semiampiezza=20.0)
    )
    assert len(esiti) == 1
    esito = esiti[0]
    assert isinstance(esito, (EntroTolleranza, FuoriTolleranza))
    # 398 px * (50 / ~199) mm/px ~ 100 mm
    assert 95.0 <= esito.misura.valore <= 105.0
