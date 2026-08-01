"""Passo 2 — le due modalita' sono tipi distinti e non intercambiabili (§4.1)."""

from __future__ import annotations

from misura.modalita import ModalitaCertificata, ModalitaStima


def test_modalita_sono_tipi_distinti() -> None:
    cert = ModalitaCertificata()
    stima = ModalitaStima()
    assert not isinstance(cert, ModalitaStima)
    assert not isinstance(stima, ModalitaCertificata)


def test_nessuna_relazione_di_sottotipo() -> None:
    # Non una sottoclasse dell'altra: nessuna conversione implicita per ereditarieta'.
    assert not issubclass(ModalitaCertificata, ModalitaStima)
    assert not issubclass(ModalitaStima, ModalitaCertificata)


def test_contratto_riferimento() -> None:
    assert ModalitaCertificata.richiede_riferimento is True
    assert ModalitaStima.richiede_riferimento is False


def test_target_di_tolleranza_coerenti_col_concept() -> None:
    assert ModalitaCertificata().tolleranza_relativa_obiettivo <= 0.01
    assert ModalitaStima().tolleranza_relativa_obiettivo >= 0.10
