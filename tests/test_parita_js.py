"""Parita' numerica fra il core JS client-only e il core Python (fonte di verita').

`app/core.js` e' il port del percorso a clic manuale e gira sul dispositivo, dove
il core Python non arriva. Il vincolo dichiarato e' che i due producano lo
**stesso numero**: finche' nessuno lo verifica, e' una promessa, non un fatto.

Il test esegue davvero `app/core.js` con node sugli stessi ingressi che passa al
core Python, e confronta scala, incertezza espansa ed esito. La tabella dei
riferimenti manuali viene presa da `app.server`, non ricopiata: cosi' una
divergenza fra le due tabelle (85,60 cambiato di qua e non di la') fa fallire il
test invece di produrre in silenzio due scale diverse.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from misura.esito import EntroTolleranza, FuoriTolleranza, Tolleranza, valuta
from misura.modalita import ModalitaStima
from misura.pipeline import SegmentoPixel, misura_da_scala
from misura.provenienza import MisurataDaApp
from misura.riferimento import Riferimento, scala_da_lato_pixel

_RADICE = Path(__file__).resolve().parent.parent
_CORE_JS = _RADICE / "app" / "core.js"

# `core.js` e' uno script di pagina: si pubblica su `window`. Qui gli mettiamo
# davanti un `window` vuoto invece di modificarlo per il test — il file sotto
# esame dev'essere quello che gira in produzione, non una sua variante.
_PONTE_JS = """
globalThis.window = {};
require(%s);
const core = globalThis.window.MisuraCore;
const casi = JSON.parse(process.argv[2]);
const esiti = casi.map(c => {
  const e = core.misuraManuale({
    tipo: c.tipo,
    latoPersonalizzato: c.lato_mm,
    latoRifPx: c.lato_rif_px,
    sigmaRifPx: c.sigma_rif_px,
    latoTargetPx: c.lato_target_px,
    sigmaSegPx: c.sigma_seg_px,
    tolleranzaMm: c.tolleranza_mm,
  });
  return {
    tipo: e.tipo,
    valore_mm: e.valore_mm,
    incertezza_espansa_mm: e.incertezza_espansa_mm,
    scala_mm_px: parseFloat(e.scala_mm_px),
    scala_inc_mm_px: parseFloat(e.scala_inc_mm_px),
  };
});
process.stdout.write(JSON.stringify(esiti));
"""

# Casi condivisi dai due core. Coprono i tre tipi di riferimento manuale, un
# esito entro e uno fuori tolleranza, e il caso a sigma nulla — dove un default
# applicato in un core e non nell'altro produrrebbe due numeri diversi.
CASI: list[dict[str, Any]] = [
    {
        "nome": "id1 lato lungo, riferimento grande nel fotogramma",
        "tipo": "id1_lungo",
        "lato_mm": 0.0,
        "lato_rif_px": 300.0,
        "sigma_rif_px": 2.5,
        "lato_target_px": 850.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 20.0,
    },
    {
        "nome": "id1 lato corto, riferimento piccolo: fuori tolleranza",
        "tipo": "id1_corto",
        "lato_mm": 0.0,
        "lato_rif_px": 120.0,
        "sigma_rif_px": 2.5,
        "lato_target_px": 400.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 5.0,
    },
    {
        "nome": "dimensione nota da righello",
        "tipo": "personalizzato",
        "lato_mm": 200.0,
        "lato_rif_px": 640.0,
        "sigma_rif_px": 2.5,
        "lato_target_px": 1500.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 50.0,
    },
    {
        "nome": "sigma nulla: resta solo la tolleranza dimensionale",
        "tipo": "id1_lungo",
        "lato_mm": 0.0,
        "lato_rif_px": 300.0,
        "sigma_rif_px": 0.0,
        "lato_target_px": 850.0,
        "sigma_seg_px": 0.0,
        "tolleranza_mm": 20.0,
    },
    {
        "nome": "tolleranza stretta su riferimento ampio",
        "tipo": "id1_lungo",
        "lato_mm": 0.0,
        "lato_rif_px": 900.0,
        "sigma_rif_px": 1.0,
        "lato_target_px": 300.0,
        "sigma_seg_px": 0.5,
        "tolleranza_mm": 0.2,
    },
]


def _riferimento_di(caso: dict[str, Any]) -> Riferimento:
    """Riferimento manuale dalla tabella dell'app (non ricopiata qui)."""
    from app.server import _riferimento_manuale

    spec: dict[str, Any] = {"tipo": caso["tipo"]}
    if caso["tipo"] == "personalizzato":
        spec["lato_mm"] = caso["lato_mm"]
    riferimento: Riferimento = _riferimento_manuale(spec)
    return riferimento


def _atteso_python(caso: dict[str, Any]) -> dict[str, Any]:
    """Lo stesso percorso di `misuraManuale`, sul core Python."""
    riferimento = _riferimento_di(caso)
    scala = scala_da_lato_pixel(
        riferimento, caso["lato_rif_px"], caso["sigma_rif_px"]
    )
    grandezza = misura_da_scala(
        scala, SegmentoPixel(caso["lato_target_px"], caso["sigma_seg_px"])
    )
    esito = valuta(
        grandezza,
        MisurataDaApp(ModalitaStima()),
        Tolleranza(semiampiezza=caso["tolleranza_mm"]),
    )
    tipo = "EntroTolleranza" if isinstance(esito, EntroTolleranza) else "FuoriTolleranza"
    assert isinstance(esito, EntroTolleranza | FuoriTolleranza)
    return {
        "tipo": tipo,
        "valore_mm": esito.misura.valore,
        "incertezza_espansa_mm": esito.incertezza_espansa,
        "scala_mm_px": scala.valore,
        "scala_inc_mm_px": scala.deviazione,
    }


def _esegui_js(tmp_path: Path) -> list[dict[str, Any]]:
    ponte = tmp_path / "ponte.mjs.cjs"
    ponte.write_text(_PONTE_JS % json.dumps(_CORE_JS.as_posix()), encoding="utf-8")
    completato = subprocess.run(
        ["node", str(ponte), json.dumps(CASI)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completato.returncode != 0:
        raise AssertionError(f"node ha fallito:\n{completato.stderr}")
    risultati: list[dict[str, Any]] = json.loads(completato.stdout)
    return risultati


pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node non disponibile: la parita' JS<->Python non e' verificabile qui",
)


def test_parita_misura_manuale(tmp_path: Path) -> None:
    """Stessi ingressi ai due core: stesso valore, stessa incertezza, stesso esito."""
    ottenuti = _esegui_js(tmp_path)
    assert len(ottenuti) == len(CASI)

    for caso, js in zip(CASI, ottenuti, strict=True):
        py = _atteso_python(caso)
        nome = caso["nome"]

        assert js["tipo"] == py["tipo"], f"esito diverso — {nome}"
        assert js["valore_mm"] == pytest.approx(py["valore_mm"], rel=1e-12), (
            f"valore diverso — {nome}"
        )
        assert js["incertezza_espansa_mm"] == pytest.approx(
            py["incertezza_espansa_mm"], rel=1e-12
        ), f"incertezza diversa — {nome}"
        # la scala esce dal JS gia' arrotondata a 4 decimali (e' cio' che l'app
        # mostra): il confronto e' stretto quanto quell'arrotondamento consente.
        assert js["scala_mm_px"] == pytest.approx(py["scala_mm_px"], abs=5e-5), (
            f"scala diversa — {nome}"
        )
        assert js["scala_inc_mm_px"] == pytest.approx(
            py["scala_inc_mm_px"], abs=5e-5
        ), f"incertezza di scala diversa — {nome}"


def test_core_js_non_fa_rete() -> None:
    """Il core JS gira sul dispositivo: nessuna chiamata di rete, mai (§13.1).

    Guard testuale, non un'analisi statica: serve a far fallire il gate se
    qualcuno introduce una fetch nel core client-only, dove il vincolo
    'nessuna immagine lascia il dispositivo' e' l'intero punto.
    """
    sorgente = _CORE_JS.read_text(encoding="utf-8")
    for vietato in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon"):
        assert vietato not in sorgente, f"il core JS non deve fare rete: trovato {vietato}"
