"""Fase 1 — schema del dataset ground-truth: round-trip e caricamento."""

from __future__ import annotations

import math
from pathlib import Path

from misura.modalita import ModalitaCertificata
from misura.riferimento import marker_stampato_verificato
from misura.scarti import CriterioScarto, RegistroScarti, Scarto
from misura.validazione.dataset import (
    CampioneGroundTruth,
    MisuraCalibro,
    TargetAnnotato,
    campione_a_dict,
    campione_da_dict,
    carica_dataset,
    salva_campione,
)


def _campione() -> CampioneGroundTruth:
    return CampioneGroundTruth(
        id="campione-001",
        percorso_immagine="immagini/campione-001.png",
        riferimento=marker_stampato_verificato(50.0, 0.2),
        target=TargetAnnotato(100.0, 200.0, 500.0, 200.0, sigma_px=1.0),
        vero=MisuraCalibro(valore_mm=100.0, incertezza_mm=0.02),
        modalita=ModalitaCertificata(),
        scarti=RegistroScarti(
            tenuti=3, scarti=(Scarto("b", CriterioScarto.NITIDEZZA_INSUFFICIENTE),)
        ),
        descrizione="scatola su tavolo",
        metadati={"dispositivo": "test"},
    )


def test_lunghezza_px_annotata() -> None:
    assert math.isclose(TargetAnnotato(0.0, 0.0, 3.0, 4.0).lunghezza_px(), 5.0)


def test_round_trip_dict() -> None:
    c = _campione()
    ric = campione_da_dict(campione_a_dict(c))
    assert ric.id == c.id
    assert ric.vero.valore_mm == 100.0
    assert isinstance(ric.modalita, ModalitaCertificata)
    assert ric.scarti.tenuti == 3
    assert ric.scarti.scarti[0].criterio is CriterioScarto.NITIDEZZA_INSUFFICIENTE
    assert ric.metadati["dispositivo"] == "test"
    assert math.isclose(ric.riferimento.tolleranza_dim_mm, 0.2)


def test_salva_e_carica_dataset(tmp_path: Path) -> None:
    (tmp_path / "campioni").mkdir()
    salva_campione(_campione(), tmp_path / "campioni" / "campione-001.json")
    # un file di servizio con underscore va ignorato
    (tmp_path / "campioni" / "_bozza.json").write_text("{}", encoding="utf-8")

    campioni = carica_dataset(tmp_path)
    assert len(campioni) == 1
    assert campioni[0].id == "campione-001"


def test_dataset_assente_da_lista_vuota(tmp_path: Path) -> None:
    assert carica_dataset(tmp_path) == []
