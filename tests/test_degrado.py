"""Degrado esplicito da certificata a stima (§4.1): mai automatico."""

from __future__ import annotations

import pytest

from misura.esito import (
    MOTIVO_CONDIZIONI_NON_PIENE,
    ConfermaUtente,
    EntroTolleranza,
    RifiutoMotivato,
    Tolleranza,
    degrada_a_stima,
)
from misura.grandezza import GrandezzaIncerta
from misura.modalita import ModalitaCertificata, ModalitaStima
from misura.provenienza import MisurataDaApp, Provenienza

PROV: Provenienza = MisurataDaApp(ModalitaCertificata())
TOLL = Tolleranza(semiampiezza=20.0)
MISURA = GrandezzaIncerta.da_deviazione(242.5, 2.0)


def test_senza_conferma_non_esce_un_numero() -> None:
    """Il caso che la regola esiste per impedire: l'utente si aspetta una
    certificata e riceve una stima che ha lo stesso aspetto."""
    esito = degrada_a_stima(MISURA, PROV, TOLL, conferma=None)

    assert isinstance(esito, RifiutoMotivato)
    assert esito.motivo == MOTIVO_CONDIZIONI_NON_PIENE


def test_con_conferma_esce_la_misura_in_stima() -> None:
    esito = degrada_a_stima(
        MISURA, PROV, TOLL, ConfermaUtente("secondo riferimento assente")
    )

    assert isinstance(esito, EntroTolleranza)
    assert esito.misura.valore == 242.5


def test_il_degrado_non_cambia_i_numeri_solo_il_permesso_di_mostrarli() -> None:
    """L'incertezza in stima e' quella **calcolata** su questa configurazione,
    non una penalita' forfettaria applicata al degrado."""
    con = degrada_a_stima(MISURA, PROV, TOLL, ConfermaUtente("motivo"))

    assert isinstance(con, EntroTolleranza)
    assert con.incertezza_espansa == pytest.approx(2.0 * MISURA.deviazione)


def test_la_conferma_non_e_costruibile_per_sbaglio() -> None:
    """`ConfermaUtente` richiede una motivazione: un token vuoto costruito di
    passaggio non e' un'azione esplicita dell'utente."""
    with pytest.raises(TypeError):
        ConfermaUtente()  # type: ignore[call-arg]


def test_transizione_solo_verso_stima() -> None:
    """Non esiste la strada inversa: nessuna funzione promuove una stima a
    certificata, perche' nessuna conferma dell'utente puo' creare le condizioni
    di acquisizione che non ci sono state."""
    from misura import esito as modulo

    nomi = [n for n in dir(modulo) if "transizione" in n]
    assert nomi == ["transizione_certificata_a_stima"]
    assert isinstance(
        modulo.transizione_certificata_a_stima(ConfermaUtente("m")), ModalitaStima
    )
