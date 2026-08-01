"""Doppio riferimento (§5.3): la verifica che trasforma "a volte sbaglia del 6%"
in "a volte dice che non puo' misurare"."""

from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from misura.doppio_riferimento import (
    ScaleConcordi,
    ScaleDiscordi,
    confronta_scale,
    scala_o_rifiuto,
)
from misura.esito import RifiutoMotivato
from misura.grandezza import GrandezzaIncerta
from misura.modalita import ModalitaStima
from misura.provenienza import MisurataDaApp, Provenienza
from misura.riferimento import Riferimento, scala_da_lato_pixel

PROV: Provenienza = MisurataDaApp(ModalitaStima())


def test_scale_concordi_fondono_e_stringono_lincertezza() -> None:
    """Superata la verifica, la scala fusa e' piu' stretta di entrambe: la
    verifica non costa precisione, la produce (§9.2)."""
    prima = GrandezzaIncerta.da_deviazione(0.2853, 0.0020)
    seconda = GrandezzaIncerta.da_deviazione(0.2861, 0.0025)

    esito = confronta_scale(prima, seconda, PROV)

    assert isinstance(esito, ScaleConcordi)
    assert esito.scala.varianza < min(prima.varianza, seconda.varianza)
    assert min(prima.valore, seconda.valore) <= esito.scala.valore
    assert esito.scala.valore <= max(prima.valore, seconda.valore)


def test_scale_discordi_rifiutano_invece_di_misurare() -> None:
    prima = GrandezzaIncerta.da_deviazione(0.2853, 0.0020)
    seconda = GrandezzaIncerta.da_deviazione(0.3400, 0.0025)

    esito = confronta_scale(prima, seconda, PROV)

    assert isinstance(esito, ScaleDiscordi)
    assert esito.divergenza > esito.soglia
    rifiuto = scala_o_rifiuto(esito)
    assert isinstance(rifiuto, RifiutoMotivato)
    assert "0.2853" in rifiuto.motivo and "0.3400" in rifiuto.motivo


def test_discordi_non_espone_nessuna_scala() -> None:
    """Guard strutturale, gemello di quello in `scarti.py` (§6.3).

    Sapere che una delle due scale e' sbagliata senza sapere quale non autorizza
    a proseguire con una delle due. Se qualcuno aggiungesse a `ScaleDiscordi` un
    campo `scala` — magari "la piu' precisa delle due" — il sistema tornerebbe a
    confermare se stesso e questo test cadrebbe.
    """
    esito = confronta_scale(
        GrandezzaIncerta.da_deviazione(0.28, 0.002),
        GrandezzaIncerta.da_deviazione(0.34, 0.002),
        PROV,
    )
    assert isinstance(esito, ScaleDiscordi)
    assert not hasattr(esito, "scala")


def test_il_doppio_riferimento_smaschera_la_serie_sbagliata() -> None:
    """Il caso di §5.1 reso concreto.

    Le due serie della banconota da 100 euro hanno altezza 82 mm (ES1) e 77 mm
    (ES2): classificare la serie sbagliata sposta la scala del 6,5% in silenzio.
    Con un secondo riferimento in inquadratura quell'errore non e' piu' silenzioso
    — diventa un rifiuto.
    """
    tessera = Riferimento(85.60, 0.10, "tessera ID-1")
    scala_buona = scala_da_lato_pixel(tessera, 300.0, 2.5)

    banconota_es1 = Riferimento(82.0, 0.5, "100 euro, serie ES1 (altezza 82 mm)")
    # la banconota inquadrata e' in realta' ES2 (77 mm): stessi pixel, dimensione
    # dichiarata sbagliata -> scala sbagliata del 6,5%
    lato_px_reale = 77.0 / scala_buona.valore
    scala_sbagliata = scala_da_lato_pixel(banconota_es1, lato_px_reale, 2.5)

    esito = confronta_scale(scala_buona, scala_sbagliata, PROV)

    assert isinstance(esito, ScaleDiscordi)
    relativo = esito.divergenza / scala_buona.valore
    assert 0.05 < relativo < 0.08  # l'errore del 6,5% del concept


def test_confronto_simmetrico() -> None:
    a = GrandezzaIncerta.da_deviazione(0.2853, 0.0020)
    b = GrandezzaIncerta.da_deviazione(0.2861, 0.0025)

    ab = confronta_scale(a, b, PROV)
    ba = confronta_scale(b, a, PROV)

    assert isinstance(ab, ScaleConcordi) and isinstance(ba, ScaleConcordi)
    assert np.isclose(ab.scala.valore, ba.scala.valore)
    assert np.isclose(ab.scala.varianza, ba.scala.varianza)
    assert np.isclose(ab.divergenza, ba.divergenza)
    assert np.isclose(ab.soglia, ba.soglia)


def test_la_soglia_tiene_conto_delle_sorgenti_condivise() -> None:
    """La soglia esce dalla differenza, non da una costante.

    Due scale che condividono una sorgente hanno una differenza meno incerta di
    due scale indipendenti con le stesse deviazioni: la stessa divergenza puo'
    quindi essere accettabile fra scale indipendenti e inaccettabile fra scale
    correlate. Una soglia fissa in mm/px non saprebbe distinguerle.
    """
    comune = GrandezzaIncerta.da_deviazione(0.0, 0.0020, "modo_comune")
    indip_a = GrandezzaIncerta.da_deviazione(0.2853, 0.0020)
    indip_b = GrandezzaIncerta.da_deviazione(0.2861, 0.0020)
    corr_a = GrandezzaIncerta.costante(0.2853) + comune
    corr_b = GrandezzaIncerta.costante(0.2861) + comune

    fra_indipendenti = confronta_scale(indip_a, indip_b, PROV)
    fra_correlate = confronta_scale(corr_a, corr_b, PROV)

    assert fra_correlate.soglia < fra_indipendenti.soglia
    assert np.isclose(fra_indipendenti.divergenza, fra_correlate.divergenza)


def test_scale_identiche_esatte_non_fondono() -> None:
    """Differenza a varianza nulla: una grandezza scritta due volte, non due
    osservazioni. Fonderla sarebbe mal posto e non aggiungerebbe informazione."""
    a = GrandezzaIncerta.costante(0.2853)
    esito = confronta_scale(a, a, PROV)

    assert isinstance(esito, ScaleConcordi)
    assert esito.scala.valore == 0.2853
    assert esito.scala.varianza == 0.0


def test_scale_esatte_diverse_sono_discordi() -> None:
    """Senza incertezza la soglia e' zero: due valori esatti diversi non possono
    concordare."""
    esito = confronta_scale(
        GrandezzaIncerta.costante(0.2853), GrandezzaIncerta.costante(0.2854), PROV
    )
    assert isinstance(esito, ScaleDiscordi)


@given(
    valore=st.floats(min_value=0.05, max_value=5.0),
    scarto=st.floats(min_value=-0.004, max_value=0.004),
    dev_a=st.floats(min_value=1e-4, max_value=1e-2),
    dev_b=st.floats(min_value=1e-4, max_value=1e-2),
)
def test_proprieta_la_fusione_non_peggiora_mai(
    valore: float, scarto: float, dev_a: float, dev_b: float
) -> None:
    """Property: quando le scale concordano, la fusione non aumenta mai
    l'incertezza rispetto alla migliore delle due."""
    a = GrandezzaIncerta.da_deviazione(valore, dev_a)
    b = GrandezzaIncerta.da_deviazione(valore + scarto, dev_b)

    esito = confronta_scale(a, b, PROV)

    if isinstance(esito, ScaleConcordi):
        assert esito.scala.deviazione <= min(a.deviazione, b.deviazione) * (1 + 1e-9)


@given(
    valore=st.floats(min_value=0.05, max_value=5.0),
    scarto=st.floats(min_value=-1.0, max_value=1.0),
    dev=st.floats(min_value=1e-4, max_value=1e-2),
)
def test_proprieta_esito_coerente_con_la_soglia(
    valore: float, scarto: float, dev: float
) -> None:
    """Property: l'esito e' sempre la lettura diretta di divergenza vs soglia."""
    a = GrandezzaIncerta.da_deviazione(valore, dev)
    b = GrandezzaIncerta.da_deviazione(valore + scarto, dev)

    esito = confronta_scale(a, b, PROV)

    if isinstance(esito, ScaleDiscordi):
        assert esito.divergenza > esito.soglia
    else:
        assert esito.divergenza <= esito.soglia
