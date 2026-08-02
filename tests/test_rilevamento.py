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


_BANCO_OMOGRAFIA = """
const R = require(%s);
// vista prospettica nota: si proietta il piano della tessera con un'omografia
// scelta, poi si verifica che il rilevatore la inverta e restituisca i mm veri.
const H = [2.4, 0.35, 120, -0.28, 2.15, 90, 0.0009, 0.0004];
const proj = p => {
  const d = H[6]*p[0] + H[7]*p[1] + 1;
  return [(H[0]*p[0]+H[1]*p[1]+H[2])/d, (H[3]*p[0]+H[4]*p[1]+H[5])/d];
};
const piano = [[0,0],[85.60,0],[85.60,53.98],[0,53.98]];
const vertici = piano.map(proj);
const a = [10,10], b = [70,40];
const vera = Math.hypot(b[0]-a[0], b[1]-a[1]);
const m = R.misuraSulPiano({vertici, lungoDaPrimoVertice:true}, proj(a), proj(b), 0.03, 1.0);

// confronto col metodo a scala unica (media dei lati opposti)
const l1 = Math.hypot(vertici[1][0]-vertici[0][0], vertici[1][1]-vertici[0][1]);
const l2 = Math.hypot(vertici[2][0]-vertici[3][0], vertici[2][1]-vertici[3][1]);
const scala = 85.60 / ((l1+l2)/2);
const pa = proj(a), pb = proj(b);
const scalare = scala * Math.hypot(pb[0]-pa[0], pb[1]-pa[1]);

process.stdout.write(JSON.stringify({
  vera, omografia: m.mm, sigma: m.sigmaMm, scalare,
}));
"""


def test_omografia_misura_esatta_dove_la_scala_unica_sbaglia(tmp_path: Path) -> None:
    """Una scala unica mm/px vale solo per una ripresa frontale.

    Appena la camera e' inclinata il piano si proietta con fattori diversi punto
    per punto, e un oggetto lontano dalla tessera viene convertito con la scala
    sbagliata. Con i quattro vertici il piano si rettifica e l'errore prospettico
    sparisce — non si riduce, sparisce, perche' e' geometria esatta.
    """
    banco = tmp_path / "omografia.cjs"
    banco.write_text(_BANCO_OMOGRAFIA % json.dumps(_RILEVA_JS.as_posix()), encoding="utf-8")
    completato = subprocess.run(
        ["node", str(banco)], capture_output=True, text=True, timeout=60, check=False
    )
    assert completato.returncode == 0, completato.stderr
    d = json.loads(completato.stdout)

    assert d["omografia"] == pytest.approx(d["vera"], abs=1e-6)
    # e il metodo che sostituisce sbaglia in modo tutt'altro che trascurabile
    errore_scalare = abs(d["scalare"] - d["vera"]) / d["vera"]
    assert errore_scalare > 0.02, (
        "se la scala unica non sbagliasse, questo test non proverebbe nulla: "
        f"errore {errore_scalare:.4%}"
    )
    assert d["sigma"] > 0.0


_BANCO_AMBIGUO = """
const R = require(%s);
const RAP = 85.60/53.98;
function rett(d,w,cx,cy,W,H,theta,valore){
  const ct=Math.cos(-theta), st=Math.sin(-theta);
  for(let y=0;y<700;y++) for(let x=0;x<w;x++){
    const dx=x-cx, dy=y-cy;
    const u=dx*ct-dy*st, v=dx*st+dy*ct;
    if(Math.abs(u)<=W/2 && Math.abs(v)<=H/2){
      const i=(y*w+x)*4; d[i]=valore; d[i+1]=valore; d[i+2]=valore;
    }
  }
}
const w=900,h=700;
const data=new Uint8ClampedArray(w*h*4);
for(let i=0;i<w*h;i++){ data[i*4]=235; data[i*4+1]=235; data[i*4+2]=235; data[i*4+3]=255; }
rett(data,w,560,300,420,420/RAP,0.08,95);   // "libro": stesso rapporto, piu' grande
rett(data,w,180,560,200,200/RAP,0.12,60);   // tessera vera
const c = R.rilevaTessere({data,width:w,height:h});
process.stdout.write(JSON.stringify({
  quanti: c.length,
  lati: c.map(x => x.latoLungoPx),
  deviazioni: c.map(x => x.deviazione),
}));
"""


def test_due_rettangoli_compatibili_restano_entrambi_candidati(tmp_path: Path) -> None:
    """La trappola di classificazione di §5.1, in versione geometrica.

    Un libro tascabile ha spesso lo stesso rapporto d'aspetto di una tessera
    ID-1: **nessuna geometria puo' distinguerli**. Scegliendo il piu' grande, un
    rilevatore automatico prende il libro e la scala esce sbagliata del 110% —
    in silenzio, con un numero dall'aria perfettamente normale.

    Il rilevatore non puo' risolverlo, ma non deve nasconderlo: deve restituire
    **tutti** i candidati compatibili, cosi' che l'interfaccia possa dichiarare
    l'ambiguita' e lasciare correggere. Se un giorno questo test trovasse un solo
    candidato, l'app tornerebbe a scegliere senza dirlo.
    """
    banco = tmp_path / "ambiguo.cjs"
    banco.write_text(_BANCO_AMBIGUO % json.dumps(_RILEVA_JS.as_posix()), encoding="utf-8")
    completato = subprocess.run(
        ["node", str(banco)], capture_output=True, text=True, timeout=60, check=False
    )
    assert completato.returncode == 0, completato.stderr
    d = json.loads(completato.stdout)

    assert d["quanti"] >= 2, "i candidati ambigui devono restare tutti disponibili"
    lati = sorted(d["lati"])
    assert lati[0] == pytest.approx(200, abs=2)
    assert lati[-1] == pytest.approx(420, abs=2)
    # entrambi passano il filtro sul rapporto: e' proprio questo a renderli
    # indistinguibili, e il motivo per cui la scelta va dichiarata
    assert all(dev < 0.05 for dev in d["deviazioni"])
