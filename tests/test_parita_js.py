"""Parita' numerica fra il core JS client-only e il core Python (fonte di verita').

`app/core.js` e' il port del percorso a clic manuale e gira sul dispositivo, dove
il core Python non arriva. Il vincolo dichiarato e' che i due producano lo
**stesso numero**: finche' nessuno lo verifica, e' una promessa, non un fatto.

Il test esegue davvero `app/core.js` con node sugli stessi ingressi che passa al
core Python, e confronta scala, incertezza espansa ed esito. La tabella dei
riferimenti manuali viene presa da `app.server`, non ricopiata: cosi' una
divergenza fra le due tabelle (85,60 cambiato di qua e non di la') fa fallire il
test invece di produrre in silenzio due scale diverse.

Copre entrambi i percorsi: riferimento singolo e **doppio riferimento** (§5.3),
dove il JS fonde due scale in forma chiusa e il Python passa dalla GLS generale
di `fusione.fondi` — due strade diverse allo stesso numero, che e' esattamente
il tipo di divergenza che questo test esiste per intercettare.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from misura.doppio_riferimento import (
    ScaleConcordi,
    ScaleDiscordi,
    confronta_scale,
)
from misura.esito import EntroTolleranza, FuoriTolleranza, Tolleranza, valuta
from misura.modalita import ModalitaStima
from misura.pipeline import SegmentoPixel, misura_da_scala
from misura.provenienza import MisurataDaApp, Provenienza
from misura.riferimento import Riferimento, scala_da_lato_pixel

_RADICE = Path(__file__).resolve().parent.parent
_CORE_JS = _RADICE / "app" / "core.js"

_PROV: Provenienza = MisurataDaApp(ModalitaStima())

# `core.js` e' uno script di pagina: si pubblica su `window`. Qui gli mettiamo
# davanti un `window` vuoto invece di modificarlo per il test — il file sotto
# esame dev'essere quello che gira in produzione, non una sua variante.
_PONTE_JS = """
globalThis.window = {};
require(%s);
const core = globalThis.window.MisuraCore;
const ingresso = JSON.parse(process.argv[2]);

const singoli = ingresso.singoli.map(c => {
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

const doppi = ingresso.doppi.map(c => {
  const e = core.misuraDoppioRiferimento({
    tipoA: c.tipo_a, latoPersonalizzatoA: c.lato_a_mm, latoRifAPx: c.lato_rif_a_px,
    tipoB: c.tipo_b, latoPersonalizzatoB: c.lato_b_mm, latoRifBPx: c.lato_rif_b_px,
    sigmaRifPx: c.sigma_rif_px,
    latoTargetPx: c.lato_target_px,
    sigmaSegPx: c.sigma_seg_px,
    tolleranzaMm: c.tolleranza_mm,
  });
  const comune = {
    tipo: e.tipo,
    divergenza_mm_px: parseFloat(e.divergenza_mm_px),
    soglia_mm_px: parseFloat(e.soglia_mm_px),
  };
  if (e.tipo === 'RifiutoMotivato') return Object.assign(comune, {motivo: e.motivo});
  return Object.assign(comune, {
    valore_mm: e.valore_mm,
    incertezza_espansa_mm: e.incertezza_espansa_mm,
    scala_mm_px: parseFloat(e.scala_mm_px),
    scala_inc_mm_px: parseFloat(e.scala_inc_mm_px),
  });
});

// guard strutturale: l'esito discorde non deve esporre nessuna scala
const discordi = core.confrontaScale(
  core.GrandezzaIncerta.daDeviazione(0.28, 0.002),
  core.GrandezzaIncerta.daDeviazione(0.34, 0.002));
const chiavi_discordi = Object.keys(discordi);

// degrado: senza conferma non esce un numero; con conferma esce lo stesso
// numero della misura non degradata (il degrado cambia il permesso, non i conti)
const optsDeg = {
  tipo:'id1_lungo', latoRifPx:300, sigmaRifPx:2.5,
  latoTargetPx:850, sigmaSegPx:1.0, tolleranzaMm:20.0,
};
const senza = core.misuraDegradataAStima(optsDeg, null);
const con = core.misuraDegradataAStima(optsDeg, core.ConfermaUtente('motivo'));
const diretta = core.misuraManuale(optsDeg);
const degrado = {
  senza_tipo: senza.tipo,
  senza_motivo: senza.motivo,
  senza_ha_valore: 'valore_mm' in senza,
  con_tipo: con.tipo,
  con_valore: con.valore_mm,
  con_modalita: con.modalita,
  con_degradata_da: con.degradata_da,
  diretta_valore: diretta.valore_mm,
  diretta_incertezza: diretta.incertezza_espansa_mm,
  con_incertezza: con.incertezza_espansa_mm,
};

process.stdout.write(JSON.stringify({singoli, doppi, chiavi_discordi, degrado}));
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

# Doppio riferimento: uno concorde (le due scale si fondono) e due discordi.
CASI_DOPPI: list[dict[str, Any]] = [
    {
        "nome": "due lati di riferimenti distinti, concordi: si fondono",
        "tipo_a": "id1_lungo",
        "lato_a_mm": 0.0,
        "lato_rif_a_px": 300.0,
        "tipo_b": "id1_corto",
        "lato_b_mm": 0.0,
        "lato_rif_b_px": 188.0,
        "sigma_rif_px": 2.5,
        "lato_target_px": 850.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 20.0,
    },
    {
        "nome": "riferimento dichiarato sbagliato: discordi, rifiuto",
        "tipo_a": "id1_lungo",
        "lato_a_mm": 0.0,
        "lato_rif_a_px": 300.0,
        "tipo_b": "personalizzato",
        "lato_b_mm": 100.0,
        "lato_rif_b_px": 300.0,
        "sigma_rif_px": 2.5,
        "lato_target_px": 850.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 20.0,
    },
    {
        "nome": "serie di banconota sbagliata (82 invece di 77 mm): discordi",
        "tipo_a": "id1_lungo",
        "lato_a_mm": 0.0,
        "lato_rif_a_px": 300.0,
        "tipo_b": "personalizzato",
        "lato_b_mm": 82.0,
        "lato_rif_b_px": 269.85981308411215,  # 77 mm alla scala del riferimento buono
        "sigma_rif_px": 2.5,
        "lato_target_px": 850.0,
        "sigma_seg_px": 1.0,
        "tolleranza_mm": 20.0,
    },
]


def _riferimento_da(tipo: str, lato_mm: float) -> Riferimento:
    """Riferimento manuale dalla tabella dell'app (non ricopiata qui)."""
    from app.server import _riferimento_manuale

    spec: dict[str, Any] = {"tipo": tipo}
    if tipo == "personalizzato":
        spec["lato_mm"] = lato_mm
    riferimento: Riferimento = _riferimento_manuale(spec)
    return riferimento


def _valuta_e_scheda(
    scala: Any, caso: dict[str, Any]
) -> dict[str, Any]:
    grandezza = misura_da_scala(
        scala, SegmentoPixel(caso["lato_target_px"], caso["sigma_seg_px"])
    )
    esito = valuta(grandezza, _PROV, Tolleranza(semiampiezza=caso["tolleranza_mm"]))
    assert isinstance(esito, EntroTolleranza | FuoriTolleranza)
    tipo = "EntroTolleranza" if isinstance(esito, EntroTolleranza) else "FuoriTolleranza"
    return {
        "tipo": tipo,
        "valore_mm": esito.misura.valore,
        "incertezza_espansa_mm": esito.incertezza_espansa,
        "scala_mm_px": scala.valore,
        "scala_inc_mm_px": scala.deviazione,
    }


def _atteso_python(caso: dict[str, Any]) -> dict[str, Any]:
    """Lo stesso percorso di `misuraManuale`, sul core Python."""
    riferimento = _riferimento_da(caso["tipo"], caso["lato_mm"])
    scala = scala_da_lato_pixel(riferimento, caso["lato_rif_px"], caso["sigma_rif_px"])
    return _valuta_e_scheda(scala, caso)


def _atteso_python_doppio(caso: dict[str, Any]) -> dict[str, Any]:
    """Lo stesso percorso di `misuraDoppioRiferimento`, sul core Python."""
    rif_a = _riferimento_da(caso["tipo_a"], caso["lato_a_mm"])
    rif_b = _riferimento_da(caso["tipo_b"], caso["lato_b_mm"])
    prima = scala_da_lato_pixel(rif_a, caso["lato_rif_a_px"], caso["sigma_rif_px"])
    seconda = scala_da_lato_pixel(rif_b, caso["lato_rif_b_px"], caso["sigma_rif_px"])

    confronto = confronta_scale(prima, seconda, _PROV)
    if isinstance(confronto, ScaleDiscordi):
        return {
            "tipo": "RifiutoMotivato",
            "motivo": confronto.motivo,
            "divergenza_mm_px": confronto.divergenza,
            "soglia_mm_px": confronto.soglia,
        }
    assert isinstance(confronto, ScaleConcordi)
    scheda = _valuta_e_scheda(confronto.scala, caso)
    scheda["divergenza_mm_px"] = confronto.divergenza
    scheda["soglia_mm_px"] = confronto.soglia
    return scheda


def _esegui_js(tmp_path: Path) -> dict[str, Any]:
    ponte = tmp_path / "ponte.cjs"
    ponte.write_text(_PONTE_JS % json.dumps(_CORE_JS.as_posix()), encoding="utf-8")
    ingresso = json.dumps({"singoli": CASI, "doppi": CASI_DOPPI})
    completato = subprocess.run(
        ["node", str(ponte), ingresso],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completato.returncode != 0:
        raise AssertionError(f"node ha fallito:\n{completato.stderr}")
    risultati: dict[str, Any] = json.loads(completato.stdout)
    return risultati


def _confronta_numeri(js: dict[str, Any], py: dict[str, Any], nome: str) -> None:
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
    assert js["scala_inc_mm_px"] == pytest.approx(py["scala_inc_mm_px"], abs=5e-5), (
        f"incertezza di scala diversa — {nome}"
    )


pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node non disponibile: la parita' JS<->Python non e' verificabile qui",
)


def test_parita_misura_manuale(tmp_path: Path) -> None:
    """Stessi ingressi ai due core: stesso valore, stessa incertezza, stesso esito."""
    ottenuti = _esegui_js(tmp_path)["singoli"]
    assert len(ottenuti) == len(CASI)

    for caso, js in zip(CASI, ottenuti, strict=True):
        _confronta_numeri(js, _atteso_python(caso), caso["nome"])


def test_parita_doppio_riferimento(tmp_path: Path) -> None:
    """La fusione in forma chiusa del JS e la GLS generale del Python devono dare
    lo stesso numero — e lo stesso rifiuto, con lo stesso testo."""
    ottenuti = _esegui_js(tmp_path)["doppi"]
    assert len(ottenuti) == len(CASI_DOPPI)

    for caso, js in zip(CASI_DOPPI, ottenuti, strict=True):
        py = _atteso_python_doppio(caso)
        nome = caso["nome"]

        assert js["tipo"] == py["tipo"], f"esito diverso — {nome}"
        assert js["divergenza_mm_px"] == pytest.approx(
            py["divergenza_mm_px"], abs=5e-5
        ), f"divergenza diversa — {nome}"
        assert js["soglia_mm_px"] == pytest.approx(py["soglia_mm_px"], abs=5e-5), (
            f"soglia diversa — {nome}"
        )
        if py["tipo"] == "RifiutoMotivato":
            # il motivo e' cio' che l'utente legge: dev'essere lo stesso testo
            # su entrambi i percorsi, non solo lo stesso numero.
            assert js["motivo"] == py["motivo"], f"motivo diverso — {nome}"
        else:
            _confronta_numeri(js, py, nome)


def test_almeno_un_caso_doppio_per_esito() -> None:
    """Il test di parita' non vale nulla se copre un solo ramo."""
    tipi = set()
    for caso in CASI_DOPPI:
        py = _atteso_python_doppio(caso)
        tipi.add(py["tipo"] == "RifiutoMotivato")
    assert tipi == {True, False}, "servono casi doppi sia concordi sia discordi"


def test_discordi_non_espone_scala_anche_in_js(tmp_path: Path) -> None:
    """Il guard strutturale di `doppio_riferimento.py` vale anche nel port JS:
    un esito discorde non deve offrire nessuna scala su cui proseguire."""
    chiavi = _esegui_js(tmp_path)["chiavi_discordi"]
    assert "scala" not in chiavi
    assert "motivo" in chiavi


def test_parita_degrado_esplicito(tmp_path: Path) -> None:
    """La regola di §4.1 dev'essere la stessa nei due core: senza conferma non
    esce un numero, con conferma esce **lo stesso** numero — il degrado cambia
    il permesso di mostrare la misura, non i conti che la producono."""
    from misura.esito import MOTIVO_CONDIZIONI_NON_PIENE

    d = _esegui_js(tmp_path)["degrado"]

    assert d["senza_tipo"] == "RifiutoMotivato"
    assert d["senza_ha_valore"] is False
    assert d["senza_motivo"] == MOTIVO_CONDIZIONI_NON_PIENE

    assert d["con_tipo"] in ("EntroTolleranza", "FuoriTolleranza")
    assert d["con_modalita"] == "stima"
    assert d["con_degradata_da"] == "certificata"
    assert d["con_valore"] == pytest.approx(d["diretta_valore"], rel=1e-12)
    assert d["con_incertezza"] == pytest.approx(d["diretta_incertezza"], rel=1e-12)


def test_js_di_pagina_sintatticamente_valido(tmp_path: Path) -> None:
    """La pagina non ha un compilatore davanti: un refuso nel JS inline la rompe
    in silenzio e il gate Python non se ne accorge. Qui node fa da parser."""
    pagina = (_RADICE / "app" / "index.html").read_text(encoding="utf-8")
    blocchi = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", pagina, re.S
    )
    assert blocchi, "nessuno script inline trovato in index.html"

    sorgente = tmp_path / "pagina.js"
    sorgente.write_text("\n".join(blocchi), encoding="utf-8")
    completato = subprocess.run(
        ["node", "--check", str(sorgente)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completato.returncode == 0, completato.stderr


def test_la_pagina_non_fa_rete() -> None:
    """L'app e' client-only: il calcolo gira in `core.js` e nessuna immagine
    lascia il dispositivo perche' non va da nessuna parte (§13.1).

    Il percorso ArUco resta disponibile come strumento di validazione lato
    server, ma fuori dall'interfaccia: se una fetch rientra nella pagina, la
    proprieta' "nulla esce" smette di valere e il gate deve dirlo.
    """
    pagina = (_RADICE / "app" / "index.html").read_text(encoding="utf-8")
    for vietato in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon", "/api/"):
        assert vietato not in pagina, f"la pagina non deve fare rete: trovato {vietato}"


def test_core_js_non_fa_rete() -> None:
    """Il core JS gira sul dispositivo: nessuna chiamata di rete, mai (§13.1).

    Guard testuale, non un'analisi statica: serve a far fallire il gate se
    qualcuno introduce una fetch nel core client-only, dove il vincolo
    'nessuna immagine lascia il dispositivo' e' l'intero punto.
    """
    sorgente = _CORE_JS.read_text(encoding="utf-8")
    for vietato in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon"):
        assert vietato not in sorgente, f"il core JS non deve fare rete: trovato {vietato}"


def test_nessun_percorso_assoluto_negli_asset() -> None:
    """L'app deve funzionare anche servita da una sottocartella.

    Su GitHub Pages vive in `/nome-repo/`, e un percorso assoluto come `/core.js`
    punta alla radice del dominio: l'app si romperebbe **solo una volta
    pubblicata**, che e' il posto peggiore per accorgersene. In locale, servita
    dalla radice, un percorso assoluto funziona benissimo e non segnala nulla.
    """
    pagina = (_RADICE / "app" / "index.html").read_text(encoding="utf-8")
    for attributo in ('href="/', "href='/", 'src="/', "src='/"):
        assert attributo not in pagina, f"percorso assoluto in index.html: {attributo}"

    sw = (_RADICE / "app" / "sw.js").read_text(encoding="utf-8")
    for assoluto in ("'/'", '"/"', "'/core.js'", "'/rileva.js'", "'/sw.js'"):
        assert assoluto not in sw, f"percorso assoluto in sw.js: {assoluto}"

    manifest = json.loads((_RADICE / "app" / "manifest.webmanifest").read_text(encoding="utf-8"))
    for chiave in ("start_url", "scope"):
        assert not manifest[chiave].startswith("/"), f"{chiave} assoluto nel manifest"
    for icona in manifest["icons"]:
        assert not icona["src"].startswith("/"), "icona con percorso assoluto"


def test_gli_asset_referenziati_esistono_davvero() -> None:
    """La cartella `app/` dev'essere pubblicabile cosi' com'e', senza il server.

    Il Flask locale serve i file con rotte esplicite, quindi un riferimento a un
    file mancante non si nota finche' non si pubblica come statico.
    """
    cartella = _RADICE / "app"
    pagina = (cartella / "index.html").read_text(encoding="utf-8")
    riferiti = set(re.findall(r'(?:src|href)="([^"#:]+)"', pagina))
    sw = (cartella / "sw.js").read_text(encoding="utf-8")
    riferiti |= {a for a in re.findall(r"'\./([^']+)'", sw) if a}

    for nome in sorted(riferiti):
        if nome in ("", "./"):
            continue
        assert (cartella / nome).is_file(), f"asset referenziato ma assente: app/{nome}"
