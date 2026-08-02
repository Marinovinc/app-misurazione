"""Rilevamento automatico della tessera (app/rileva.js), eseguito con node.

Il rilevatore non ha una controparte Python: e' codice che gira solo sul
dispositivo. Senza un banco pero' resterebbe fuori da ogni verifica, ed e' il
pezzo che decide la scala — cioe' il fattore che moltiplica ogni misura.

Le scene sono sintetiche e generate nel test: un rettangolo di rapporto ID-1 di
cui si conosce la posizione esatta dei bordi, in varie condizioni. Nota sugli
attesi: un rettangolo i cui pixel vanno da x0 a x1 ha i bordi geometrici a
x0-0,5 e x1+0,5, quindi lato = x1-x0+1. Sbagliare quel +1 fa sembrare il
rilevatore affetto da un bias che invece sta nel banco.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

_RADICE = Path(__file__).resolve().parent.parent
_RILEVA_JS = _RADICE / "app" / "rileva.js"

_BANCO_JS = """
const R = require(%s);

function scena({w=900,h=700,W=300,raggio=11,theta=0,cx=450,cy=350,sfondo=235,carta=60}){
  const H = W/(85.60/53.98);
  const data = new Uint8ClampedArray(w*h*4);
  const ct=Math.cos(-theta), st=Math.sin(-theta);
  for(let y=0;y<h;y++) for(let x=0;x<w;x++){
    const dx=x-cx, dy=y-cy;
    const u=dx*ct-dy*st, v=dx*st+dy*ct;
    const au=Math.abs(u), av=Math.abs(v), hw=W/2, hh=H/2;
    let dentro;
    if(au<=hw-raggio || av<=hh-raggio) dentro=(au<=hw && av<=hh);
    else dentro = Math.hypot(au-(hw-raggio), av-(hh-raggio))<=raggio;
    const val = dentro?carta:sfondo;
    const i=(y*w+x)*4;
    data[i]=val; data[i+1]=val; data[i+2]=val; data[i+3]=255;
  }
  return {data,width:w,height:h};
}

const casi = JSON.parse(process.argv[2]);
const esiti = casi.map(c => {
  const trovate = R.rilevaTessere(scena(c.scena));
  if(!trovate.length) return {trovato:false};
  const t = trovate[0];
  return {
    trovato: true, quanti: trovate.length,
    lato: t.latoLungoPx, rapporto: t.rapporto, deviazione: t.deviazione,
    sigma: t.sigmaLatoPx, sigmaFit: t.sigmaFitPx, residuo: t.residuoPx,
    haScala: 'sigmaLatoPx' in t,
  };
});
process.stdout.write(JSON.stringify(esiti));
"""

# `atteso` = lato lungo in pixel dei bordi geometrici (vedi docstring)
CASI: list[dict[str, Any]] = [
    {"nome": "assiale, angoli vivi", "scena": {"W": 300, "raggio": 0}, "atteso": 301.0},
    {"nome": "assiale, angoli arrotondati", "scena": {"W": 300, "raggio": 11}, "atteso": 301.0},
    {"nome": "ruotata 12 gradi", "scena": {"W": 300, "raggio": 11, "theta": 0.2094}, "atteso": 300.0},
    {"nome": "ruotata 33 gradi", "scena": {"W": 300, "raggio": 11, "theta": 0.5760}, "atteso": 300.0},
    {"nome": "piccola nel fotogramma", "scena": {"W": 140, "raggio": 5}, "atteso": 141.0},
    {"nome": "chiara su sfondo scuro", "scena": {"W": 300, "raggio": 11, "sfondo": 40, "carta": 220}, "atteso": 301.0},
    {"nome": "poco contrasto", "scena": {"W": 300, "raggio": 11, "sfondo": 150, "carta": 110}, "atteso": 301.0},
]

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node non disponibile: il rilevatore non e' verificabile qui",
)


def _esegui(casi: list[dict[str, Any]], tmp_path: Path) -> list[dict[str, Any]]:
    banco = tmp_path / "banco.cjs"
    banco.write_text(_BANCO_JS % json.dumps(_RILEVA_JS.as_posix()), encoding="utf-8")
    completato = subprocess.run(
        ["node", str(banco), json.dumps(casi)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completato.returncode != 0:
        raise AssertionError(f"node ha fallito:\n{completato.stderr}")
    risultati: list[dict[str, Any]] = json.loads(completato.stdout)
    return risultati


def test_rileva_il_rettangolo_e_ne_misura_il_lato(tmp_path: Path) -> None:
    """Tolleranza 1 px: il clic manuale ne sbaglia ~2,5, e l'arrotondamento ~10."""
    esiti = _esegui(CASI, tmp_path)
    for caso, e in zip(CASI, esiti, strict=True):
        assert e["trovato"], f"nessun candidato — {caso['nome']}"
        scarto = e["lato"] - caso["atteso"]
        assert abs(scarto) <= 1.0, (
            f"{caso['nome']}: lato {e['lato']:.2f} px contro {caso['atteso']} attesi "
            f"(scarto {scarto:+.2f} px)"
        )


def test_gli_angoli_arrotondati_non_accorciano_il_lato(tmp_path: Path) -> None:
    """Il motivo per cui il rilevamento batte il clic non e' la mano ferma.

    Una ID-1 ha gli angoli con raggio 3,18 mm: chi clicca l'angolo prende dove
    inizia la curva e accorcia il lato del ~3,7%. Qui i lati si fittano e si
    intersecano, quindi il vertice e' quello teorico: lo stesso rettangolo con
    angoli vivi e con angoli arrotondati deve dare **lo stesso** lato.
    """
    vivi, tondi = _esegui([
        {"nome": "vivi", "scena": {"W": 300, "raggio": 0}},
        {"nome": "tondi", "scena": {"W": 300, "raggio": 15}},   # 5% del lato: oltre il 3,7% reale
    ], tmp_path)
    assert vivi["trovato"] and tondi["trovato"]
    assert abs(vivi["lato"] - tondi["lato"]) <= 0.5, (
        f"l'arrotondamento sposta il lato: {vivi['lato']:.2f} contro {tondi['lato']:.2f}"
    )


def test_incertezza_dichiarata_molto_sotto_il_clic_ma_non_nulla(tmp_path: Path) -> None:
    """L'incertezza deve essere calcolata, non zero e non ottimistica.

    Zero sarebbe una fiducia falsa (§7.2): resta almeno la quantizzazione del
    pixel, e il termine di obliquita' cresce con la deviazione dal rapporto ID-1.
    """
    (e,) = _esegui([{"nome": "x", "scena": {"W": 300, "raggio": 11, "theta": 0.2094}}], tmp_path)
    assert e["sigma"] > 0.0
    assert e["sigma"] < 2.5, "il rilevamento deve battere il clic manuale"
    assert e["sigma"] >= e["sigmaFit"], "l'obliquita' non puo' ridurre l'incertezza"


def test_il_rilevatore_non_fa_rete() -> None:
    """Gira sul dispositivo sulle immagini dell'utente: non deve uscire nulla."""
    sorgente = _RILEVA_JS.read_text(encoding="utf-8")
    for vietato in ("fetch(", "XMLHttpRequest", "WebSocket", "navigator.sendBeacon", "import("):
        assert vietato not in sorgente, f"il rilevatore non deve fare rete: trovato {vietato}"
