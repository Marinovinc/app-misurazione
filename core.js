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
  // `??` e non `||`: uno zero dichiarato e' un valore, non un campo mancante.
  const k = coperturaK ?? 2.0;
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

// --- doppio riferimento: la scala VERIFICATA, non dichiarata (§5.3) -----------
// Due riferimenti in inquadratura -> due scale -> si confrontano. La soglia non
// e' un numero scelto a mano: le due scale sono grandezze incerte e la loro
// differenza propaga da se' le sorgenti, incluse quelle condivise. Sono
// compatibili se |s1-s2| <= k*u(s1-s2) — il test GUM, con lo stesso k=2
// dell'incertezza espansa.
//
// Concordi, si FONDONO (GLS): la scala risultante e' piu' stretta di entrambe,
// quindi la verifica non costa precisione, la produce.
// Discordi, si rifiuta l'INTERA misura: `ScaleDiscordi` non espone nessuna scala,
// perche' sapere che una delle due e' sbagliata senza sapere quale non autorizza
// a proseguire con una delle due.
const COPERTURA_COMPATIBILITA_K = 2.0;

function covarianza(a, b) {
  let s = 0;
  for (const [sorgente, ca] of a.termini) {
    const cb = b.termini.get(sorgente);
    if (cb !== undefined) s += ca * cb;
  }
  return s;
}

function _motivoDiscordi(prima, seconda, divergenza, soglia, k) {
  return `i due riferimenti danno scale che non concordano: `
    + `${prima.valore.toFixed(4)} e ${seconda.valore.toFixed(4)} mm/px, `
    + `divergenza ${divergenza.toFixed(4)} oltre la soglia di compatibilita' `
    + `${soglia.toFixed(4)} (k=${k}). Una delle due e' sbagliata e non e' possibile `
    + `sapere quale: rifare lo scatto con entrambi i riferimenti complanari all'oggetto`;
}

function confrontaScale(prima, seconda, coperturaK) {
  const k = coperturaK ?? COPERTURA_COMPATIBILITA_K;
  if (k <= 0) throw new Error('il fattore di copertura dev\'essere positivo');

  const differenza = prima.sub(seconda);
  const divergenza = Math.abs(differenza.valore);
  const soglia = k * differenza.deviazione;

  if (divergenza > soglia) {
    return { tipo: 'ScaleDiscordi', prima, seconda, divergenza, soglia,
             motivo: _motivoDiscordi(prima, seconda, divergenza, soglia, k) };
  }
  // differenza a varianza nulla: la stessa grandezza scritta due volte, non due
  // osservazioni. Fonderla sarebbe mal posto e non aggiungerebbe informazione.
  if (differenza.varianza === 0) {
    return { tipo: 'ScaleConcordi', scala: prima, divergenza, soglia };
  }
  // GLS a due: pesi = Sigma^-1 1 / (1' Sigma^-1 1). In forma chiusa il
  // denominatore e' proprio la varianza della differenza (v1+v2-2c).
  const v1 = prima.varianza, v2 = seconda.varianza, c = covarianza(prima, seconda);
  const denom = v1 + v2 - 2 * c;
  const fusa = prima.mul((v2 - c) / denom).add(seconda.mul((v1 - c) / denom));
  return { tipo: 'ScaleConcordi', scala: fusa, divergenza, soglia };
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
  // `??` e non `||`: con `||` una sigma dichiarata a 0 (falsy) veniva sostituita
  // dal default, gonfiando l'incertezza di un fattore 12 senza dirlo. Il core
  // Python rispetta lo zero; qui deve farlo anche il JS.
  const scala = scalaDaLatoPixel(rif.latoMm, rif.tolleranzaMm, opts.latoRifPx, opts.sigmaRifPx ?? 2.5);
  const misura = misuraDaScala(scala, opts.latoTargetPx, opts.sigmaSegPx ?? 1.0);
  const esito = valuta(misura, opts.tolleranzaMm, 2.0);
  esito.scala_mm_px = scala.valore.toFixed(4);
  esito.scala_inc_mm_px = scala.deviazione.toFixed(4);
  esito.lato_target_px = opts.latoTargetPx.toFixed(1);
  esito.provenienza = "Misurata dall'app";
  return esito;
}

// misura con DUE riferimenti: la scala passa prima dalla verifica di §5.3.
// Se i due riferimenti non concordano non esce un numero, esce un rifiuto.
function misuraDoppioRiferimento(opts) {
  const rifA = riferimentoManuale(opts.tipoA, opts.latoPersonalizzatoA);
  const rifB = riferimentoManuale(opts.tipoB, opts.latoPersonalizzatoB);
  const sigmaRif = opts.sigmaRifPx ?? 2.5;
  const prima = scalaDaLatoPixel(rifA.latoMm, rifA.tolleranzaMm, opts.latoRifAPx, sigmaRif);
  const seconda = scalaDaLatoPixel(rifB.latoMm, rifB.tolleranzaMm, opts.latoRifBPx, sigmaRif);

  const confronto = confrontaScale(prima, seconda, opts.coperturaK);
  if (confronto.tipo === 'ScaleDiscordi') {
    return {
      tipo: 'RifiutoMotivato',
      motivo: confronto.motivo,
      divergenza_mm_px: confronto.divergenza.toFixed(4),
      soglia_mm_px: confronto.soglia.toFixed(4),
      provenienza: "Misurata dall'app",
    };
  }

  const misura = misuraDaScala(confronto.scala, opts.latoTargetPx, opts.sigmaSegPx ?? 1.0);
  const esito = valuta(misura, opts.tolleranzaMm, 2.0);
  esito.scala_mm_px = confronto.scala.valore.toFixed(4);
  esito.scala_inc_mm_px = confronto.scala.deviazione.toFixed(4);
  esito.lato_target_px = opts.latoTargetPx.toFixed(1);
  esito.provenienza = "Misurata dall'app";
  // la verifica superata e' un'informazione SUL DATO, non un dettaglio interno:
  // e' cio' che distingue una scala verificata da una dichiarata.
  esito.verifica_doppio_riferimento = 'superata';
  esito.divergenza_mm_px = confronto.divergenza.toFixed(4);
  esito.soglia_mm_px = confronto.soglia.toFixed(4);
  return esito;
}

window.MisuraCore = {
  GrandezzaIncerta, scalaDaLatoPixel, misuraDaScala, valuta, misuraManuale,
  confrontaScale, misuraDoppioRiferimento, COPERTURA_COMPATIBILITA_K,
};
