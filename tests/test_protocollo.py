"""Fase 1 — protocollo di validazione end-to-end su un mini-dataset reale.

Genera un'immagine ArUco reale e annota un target la cui lunghezza in pixel
corrisponde a un vero noto: verifica il plumbing (carica -> rileva -> misura ->
confronta -> aggrega), non l'accuratezza sul campo.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from misura.modalita import ModalitaStima
from misura.riferimento import lato_pixel_aruco, marker_stampato_verificato
from misura.validazione.dataset import (
    CampioneGroundTruth,
    MisuraCalibro,
    TargetAnnotato,
    salva_campione,
)
from misura.validazione.protocollo import esegui_protocollo

from _aruco_util import immagine_marker


def _prepara_dataset(radice: Path) -> tuple[float, float]:
    (radice / "campioni").mkdir()
    (radice / "immagini").mkdir()

    lato_marker_px = 200
    img = immagine_marker(lato_marker_px)
    cv2.imwrite(str(radice / "immagini" / "c1.png"), img)

    # scala vera dall'immagine: 50 mm / lato rilevato
    lato_rilevato = lato_pixel_aruco(img)
    scala_vera = 50.0 / lato_rilevato  # mm/px
    lung_target_px = 398.0
    vero_mm = lung_target_px * scala_vera  # target coerente con la scala vera

    campione = CampioneGroundTruth(
        id="c1",
        percorso_immagine="immagini/c1.png",
        riferimento=marker_stampato_verificato(50.0, 0.2),
        target=TargetAnnotato(50.0, 50.0, 50.0 + lung_target_px, 50.0, sigma_px=1.0),
        vero=MisuraCalibro(valore_mm=vero_mm, incertezza_mm=0.02),
        modalita=ModalitaStima(),
    )
    salva_campione(campione, radice / "campioni" / "c1.json")
    return vero_mm, scala_vera


def test_protocollo_end_to_end(tmp_path: Path) -> None:
    from misura.validazione.dataset import carica_dataset

    vero_mm, _ = _prepara_dataset(tmp_path)
    campioni = carica_dataset(tmp_path)
    assert len(campioni) == 1

    risultato = esegui_protocollo(campioni, tmp_path, tolleranza_mm=5.0, k=2.0)
    assert risultato.n_valutati == 1
    assert risultato.non_rilevati == 0

    esito = risultato.esiti[0]
    assert esito.rilevato
    # la misura ricostruisce il vero entro pochi mm (plumbing corretto)
    assert abs(esito.valore_mm - vero_mm) < 5.0
    assert risultato.frazione_entro_tolleranza == 1.0
    assert risultato.passa


def test_protocollo_dataset_vuoto(tmp_path: Path) -> None:
    risultato = esegui_protocollo([], tmp_path, tolleranza_mm=5.0)
    assert risultato.n_valutati == 0
    assert not risultato.passa
