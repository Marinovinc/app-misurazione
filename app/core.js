// Nucleo metrologico in JavaScript — client-only, nessun server.
//
// Rispecchia il core Python di fase 0, che resta la FONTE DI VERITA' e il banco
// di validazione (src/misura/, mypy --strict, property test, banco sintetico).
// Ogni numero prodotto qui deve coincidere con quello del core Python.
//
// Copre il percorso a clic manuale: scala da un riferimento di dimensione nota
// (due punti) e misura del target (due punti), con incertezza ed esito a tre.

// --- incertezza: rappresentazione affine a sorgenti condivise -----------------
// Una grandezza e' un valore nominale + combinazione lineare di sorgenti
// indipendenti a varianza unitaria; l'ampiezza sta nei coefficienti, l'identita'
// della sorgente distingue cio' che e' indipendente da cio' che e' condiviso.
let _idSorgente = 0;
function nuovaSorgente() { return ++_idSorgente; }

class GrandezzaIncerta {
  constructor(valore, termini) {
    this.valore = valore;
    this.termini = termini || new Map(); // sorgente(int) -> coefficiente
  }
  get varianza() { let s = 0; for (const c of this.termini.values()) s += c * c; return s; }
  get deviazione() { return Math.sqrt(this.varianza); }

  static costante(v) { return new GrandezzaIncerta(v, new Map()); }
  static daDeviazione(valore, deviazione) {
    if (deviazione < 0) throw new Error('deviazione negativa');
    if (deviazione === 0) return new GrandezzaIncerta(valore, new Map());
    const m = new Map(); m.set(nuovaSorgente(), deviazione);
    return new GrandezzaIncerta(valore, m);
  }
  _combina(k1, t2, k2) {
    const out = new Map();
    for (const [s, c] of this.termini) { const v = k1 * c; if (v !== 0) out.set(s, (out.get(s) || 0) + v); }
    for (const [s, c] of t2) { const v = k2 * c; if (v !== 0) out.set(s, (out.get(s) || 0) + v); }
    return out;
  }
  add(o) { o = _come(o); return new GrandezzaIncerta(this.valore + o.valore, this._combina(1, o.termini, 1)); }
  sub(o) { o = _come(o); return new GrandezzaIncerta(this.valore - o.valore, this._combina(1, o.termini, -1)); }
  mul(o) { o = _come(o); return new GrandezzaIncerta(this.valore * o.valore, this._combina(o.valore, o.termini, this.valore)); }
  div(o) {
    o = _come(o);
    if (o.valore === 0) throw new Error('divisione per una grandezza di valore nullo');
    return new GrandezzaIncerta(this.valore / o.valore,
      this._combina(1 / o.valore, o.termini, -this.valore / (o.valore * o.valore)));
  }
}
function _come(x) { return (x instanceof GrandezzaIncerta) ? x : GrandezzaIncerta.costante(x); }

// --- riferimento: la tolleranza dimensionale e' una sorgente (correzione B) ----
function dimensioneIncerta(latoMm, tolleranzaDimMm) {
  const sigma = tolleranzaDimMm / Math.sqrt(3); // limite -> deviazione (GUM tipo B)
  return GrandezzaIncerta.daDeviazione(latoMm, sigma);
}
function scalaDaLatoPixel(latoMm, tolleranzaDimMm, latoPixel, sigmaLatoPixel) {
  const dimensione = dimensioneIncerta(latoMm, tolleranzaDimMm);
  const lato = GrandezzaIncerta.daDeviazione(latoPixel, sigmaLatoPixel);
  return dimensione.div(lato); // mm per pixel (sorgente di scala)
}

// --- misura: lunghezza metrica = scala * lunghezza in pixel --------------------
function misuraDaScala(scala, lunghezzaPx, sigmaPx) {
  const lp = GrandezzaIncerta.daDeviazione(lunghezzaPx, sigmaPx);
  return scala.mul(lp);
}

// --- esito a tre: entro / fuori tolleranza (il rifiuto nasce a monte) ----------
function valuta(misura, semiampiezzaMm, coperturaK) {
  const k = coperturaK || 2.0;
  const espansa = k * misura.deviazione;
  const entro = espansa <= semiampiezzaMm;
  return {
    tipo: entro ? 'EntroTolleranza' : 'FuoriTolleranza',
    valore_mm: misura.valore,
    incertezza_espansa_mm: espansa,
    tolleranza_mm: semiampiezzaMm,
    come_migliorare: entro ? null
      : `incertezza attuale ±${espansa.toFixed(1)} mm, richiesta ±${semiampiezzaMm.toFixed(1)} mm: `
        + `servono osservazioni aggiuntive (nuove angolazioni) per ridurla`,
  };
}

// dimensioni note dei riferimenti a clic (mm), con tolleranza dimensionale
function riferimentoManuale(tipo, latoPersonalizzato) {
  if (tipo === 'id1_lungo') return { latoMm: 85.60, tolleranzaMm: 0.10 };
  if (tipo === 'id1_corto') return { latoMm: 53.98, tolleranzaMm: 0.10 };
  return { latoMm: latoPersonalizzato, tolleranzaMm: 0.5 };
}

// misura completa a clic manuale, tutta lato client
function misuraManuale(opts) {
  const rif = riferimentoManuale(opts.tipo, opts.latoPersonalizzato);
  const scala = scalaDaLatoPixel(rif.latoMm, rif.tolleranzaMm, opts.latoRifPx, opts.sigmaRifPx || 2.5);
  const misura = misuraDaScala(scala, opts.latoTargetPx, opts.sigmaSegPx || 1.0);
  const esito = valuta(misura, opts.tolleranzaMm, 2.0);
  esito.scala_mm_px = scala.valore.toFixed(4);
  esito.scala_inc_mm_px = scala.deviazione.toFixed(4);
  esito.lato_target_px = opts.latoTargetPx.toFixed(1);
  esito.provenienza = "Misurata dall'app";
  return esito;
}

window.MisuraCore = { GrandezzaIncerta, scalaDaLatoPixel, misuraDaScala, valuta, misuraManuale };
