"""Passo 4 — esito a tre e regola del riferimento occluso per modalita' (#3)."""

from __future__ import annotations

from misura.esito import (
    ConfermaUtente,
    EntroTolleranza,
    FuoriTolleranza,
    RifiutoMotivato,
    Tolleranza,
    gestisci_riferimento_occluso,
    transizione_certificata_a_stima,
    valuta,
)
from misura.grandezza import GrandezzaIncerta
from misura.modalita import ModalitaCertificata, ModalitaStima
from misura.provenienza import MisurataDaApp

PROV = MisurataDaApp(ModalitaStima())
TOLL = Tolleranza(semiampiezza=10.0, copertura_k=2.0)


def test_tolleranza_non_positiva_rifiutata() -> None:
    import pytest

    with pytest.raises(ValueError):
        Tolleranza(semiampiezza=0.0)


def test_entro_tolleranza() -> None:
    misura = GrandezzaIncerta.da_deviazione(100.0, 3.0)  # espansa 6 <= 10
    esito = valuta(misura, PROV, TOLL)
    assert isinstance(esito, EntroTolleranza)
    assert esito.incertezza_espansa == 6.0


def test_fuori_tolleranza_porta_la_misura_e_la_guida() -> None:
    misura = GrandezzaIncerta.da_deviazione(100.0, 8.0)  # espansa 16 > 10
    esito = valuta(misura, PROV, TOLL)
    assert isinstance(esito, FuoriTolleranza)
    # non e' un rifiuto: la misura c'e' ancora
    assert esito.misura.valore == 100.0
    assert esito.come_migliorare  # guida non vuota
    assert not isinstance(esito, RifiutoMotivato)


def test_i_tre_esiti_sono_tipi_distinti() -> None:
    entro = valuta(GrandezzaIncerta.da_deviazione(100.0, 1.0), PROV, TOLL)
    fuori = valuta(GrandezzaIncerta.da_deviazione(100.0, 8.0), PROV, TOLL)
    rifiuto = RifiutoMotivato("x")
    assert isinstance(entro, EntroTolleranza)
    assert isinstance(fuori, FuoriTolleranza)
    assert not isinstance(fuori, EntroTolleranza)
    assert not isinstance(rifiuto, (EntroTolleranza, FuoriTolleranza))


def test_occluso_in_certificata_e_rifiuto() -> None:
    esito = gestisci_riferimento_occluso(ModalitaCertificata(), PROV, TOLL)
    assert isinstance(esito, RifiutoMotivato)
    assert "certificata" in esito.motivo


def test_occluso_in_stima_misura_con_incertezza_larga() -> None:
    misura_larga = GrandezzaIncerta.da_deviazione(100.0, 4.0)  # espansa 8 <= 10
    esito = gestisci_riferimento_occluso(
        ModalitaStima(), PROV, TOLL, misura_stima=misura_larga
    )
    # non e' un rifiuto: in stima si misura, con incertezza piu' larga
    assert isinstance(esito, (EntroTolleranza, FuoriTolleranza))
    assert not isinstance(esito, RifiutoMotivato)


def test_occluso_in_stima_senza_misura_e_rifiuto() -> None:
    esito = gestisci_riferimento_occluso(ModalitaStima(), PROV, TOLL)
    assert isinstance(esito, RifiutoMotivato)


def test_transizione_richiede_conferma_esplicita() -> None:
    nuova = transizione_certificata_a_stima(ConfermaUtente("l'utente accetta la stima"))
    assert isinstance(nuova, ModalitaStima)
