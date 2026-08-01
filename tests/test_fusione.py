"""Passo 3 — fusione GLS: media pesata, correzione del bias, e il caso di modo
comune in cui ignorare la correlazione sottostima (#2b)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from misura.fusione import correggi_bias, fondi
from misura.grandezza import GrandezzaIncerta
from misura.modalita import ModalitaStima
from misura.osservazione import Osservazione
from misura.provenienza import MisurataDaApp
from misura.sistematici import BiasCorreggibile

RADICE = Path(__file__).resolve().parent.parent
FILE_NEGATIVO = RADICE / "tests" / "_vincolo_bias_negativo.py"


def _oss(g: GrandezzaIncerta, bias: BiasCorreggibile | None = None) -> Osservazione:
    return Osservazione(
        grandezza=g, provenienza=MisurataDaApp(ModalitaStima()), bias=bias
    )


def test_fusione_indipendente_e_media_a_varianza_inversa() -> None:
    g1 = GrandezzaIncerta.da_deviazione(100.0, 2.0)
    g2 = GrandezzaIncerta.da_deviazione(103.0, 1.0)
    fusa = fondi([_oss(g1), _oss(g2)])

    v1, v2 = 4.0, 1.0
    atteso_val = (100.0 / v1 + 103.0 / v2) / (1.0 / v1 + 1.0 / v2)
    atteso_var = 1.0 / (1.0 / v1 + 1.0 / v2)
    assert np.isclose(fusa.valore, atteso_val)
    assert np.isclose(fusa.varianza, atteso_var)


def test_correggi_bias_sposta_il_centro() -> None:
    # osservato 90, sottostima di 4.54 (b = osservato - vero = -4.54) -> vero ~ 94.54
    g = GrandezzaIncerta.da_deviazione(90.0, 1.0)
    corretta = correggi_bias(g, BiasCorreggibile(valore=-4.54))
    assert np.isclose(corretta.valore, 94.54)


def test_fondi_applica_il_bias() -> None:
    g = GrandezzaIncerta.da_deviazione(90.0, 1.0)
    fusa = fondi([_oss(g, bias=BiasCorreggibile(valore=-4.54))])
    assert np.isclose(fusa.valore, 94.54)


def test_bias_con_incertezza_gonfia_la_varianza() -> None:
    g = GrandezzaIncerta.da_deviazione(90.0, 1.0)
    senza = correggi_bias(g, BiasCorreggibile(valore=-4.54, incertezza=0.0))
    con = correggi_bias(g, BiasCorreggibile(valore=-4.54, incertezza=2.0))
    assert np.isclose(senza.varianza, 1.0)
    assert np.isclose(con.varianza, 1.0 + 4.0)


def test_modo_comune_la_fusione_indipendente_sottostima() -> None:
    """Due misure della stessa lunghezza che condividono il fattore di scala.
    La fusione corretta (Sigma congiunta) da' varianza MAGGIORE della fusione
    ingenua che le tratta come indipendenti."""
    scala = GrandezzaIncerta.da_deviazione(1.0, 0.02, "scala")  # 2% comune
    pix = 100.0
    g1 = scala * pix + GrandezzaIncerta.da_deviazione(0.0, 0.5)  # ~100
    g2 = scala * pix + GrandezzaIncerta.da_deviazione(0.0, 0.5)  # ~100

    fusa = fondi([_oss(g1), _oss(g2)])

    # fusione ingenua (indipendenza): 1 / (1/v1 + 1/v2)
    var_ingenua = 1.0 / (1.0 / g1.varianza + 1.0 / g2.varianza)

    assert fusa.varianza > var_ingenua
    # controvalore atteso: pesi 0.5, Var = 0.5 v + 0.5 cov
    v = g1.varianza
    cov = (pix * 0.02) ** 2
    assert np.isclose(fusa.varianza, 0.5 * v + 0.5 * cov)


def test_il_termine_b_accetta_solo_bias_correggibile() -> None:
    """mypy come oracolo: sul file dei vincoli negativi deve promuovere pulito.
    Se un SistematicoLimitato fosse accettato al posto di un bias, l'ignore
    mirato diventerebbe inutilizzato e (warn_unused_ignores) mypy fallirebbe."""
    res = subprocess.run(
        [sys.executable, "-m", "mypy", str(FILE_NEGATIVO)],
        cwd=RADICE,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
