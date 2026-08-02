// Rilevamento automatico di un riferimento rettangolare (tessera ID-1).
//
// Client-only, nessuna dipendenza, nessuna rete: e' scritto a mano come il resto
// del core perche' una libreria di visione vendorizzata peserebbe piu' dell'app
// intera e non sarebbe sotto il nostro gate.
//
// Perche' vale la pena. Cliccare a mano gli estremi di una tessera costa due
// errori: il tremolio del clic (sigma ~2,5 px) e soprattutto gli **angoli
// arrotondati** (raggio 3,18 mm sulla ID-1), che portano ad accorciare il lato
// di ~3 mm, cioe' il 3,7%. Qui i vertici non si cercano: si **fittano i quattro
// lati** sui punti di bordo e si intersecano a due a due. Le rette sono definite
// dai tratti rettilinei, quindi l'intersezione restituisce il **vertice teorico**
// dello spigolo vivo — l'arrotondamento sparisce per costruzione invece di
// dover essere evitato dall'utente.
//
// L'incertezza non e' inventata: viene dal **residuo del fit** delle rette, cioe'
// da quanto i punti di bordo si discostano davvero dalla retta che li descrive.

// rapporto d'aspetto ISO/IEC 7810 ID-1: 85,60 / 53,98
const RAPPORTO_ID1 = 85.60 / 53.98;   // 1.58577...

// --- 1. scala di grigi -------------------------------------------------------
function aGrigi(dati, larghezza, altezza) {
  const g = new Float32Array(larghezza * altezza);
  for (let i = 0, p = 0; i < g.length; i++, p += 4) {
    g[i] = 0.299 * dati[p] + 0.587 * dati[p + 1] + 0.114 * dati[p + 2];
  }
  return g;
}

// --- 2. sfocatura gaussiana separabile (5 tap, sigma ~1) ---------------------
const NUCLEO = [1 / 16, 4 / 16, 6 / 16, 4 / 16, 1 / 16];
function sfoca(src, w, h) {
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0;
    for (let k = -2; k <= 2; k++) {
      const xx = Math.min(w - 1, Math.max(0, x + k));
      s += src[y * w + xx] * NUCLEO[k + 2];
    }
    tmp[y * w + x] = s;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let s = 0;
    for (let k = -2; k <= 2; k++) {
      const yy = Math.min(h - 1, Math.max(0, y + k));
      s += tmp[yy * w + x] * NUCLEO[k + 2];
    }
    out[y * w + x] = s;
  }
  return out;
}

// --- 3. binarizzazione a piu' livelli ---------------------------------------
// Non si cercano i bordi ma le **regioni**: un bordo di Canny e' una linea
// spessa un pixel, e tracciarne il contorno significa girarci intorno andata e
// ritorno invece di seguirla. Con una maschera piena il contorno di una regione
// e' esattamente il suo perimetro, che e' cio' che serve.
//
// La soglia **non** e' adattiva a finestra locale: dentro una regione uniforme
// piu' grande della finestra la media locale coincide col pixel e non classifica
// niente — ed e' esattamente il caso di una tessera che riempie il fotogramma.
// Si parte da Otsu (due popolazioni: oggetto e sfondo) e si prova anche qualche
// livello attorno, perche' una sola soglia sbaglia appena la scena si complica.
function otsu(g) {
  const hist = new Float64Array(256);
  for (let i = 0; i < g.length; i++) {
    hist[Math.max(0, Math.min(255, Math.round(g[i])))]++;
  }
  const totale = g.length;
  let somma = 0;
  for (let i = 0; i < 256; i++) somma += i * hist[i];
  let sommaB = 0, pesoB = 0, migliore = 128, varMax = -1;
  for (let t = 0; t < 256; t++) {
    pesoB += hist[t];
    if (pesoB === 0) continue;
    const pesoF = totale - pesoB;
    if (pesoF === 0) break;
    sommaB += t * hist[t];
    const mB = sommaB / pesoB, mF = (somma - sommaB) / pesoF;
    const varTra = pesoB * pesoF * (mB - mF) * (mB - mF);
    if (varTra > varMax) { varMax = varTra; migliore = t; }
  }
  return migliore;
}

// Magnitudo del gradiente: serve per agganciare i lati al bordo **vero**.
// Il contorno binario cade su un pixel intero, e da che parte cada dipende
// dalla polarita' della maschera: tracciando la regione si sta un pixel
// dentro, tracciando lo sfondo attorno si sta un pixel fuori. Un bias di un
// pixel per lato e' costante e non si nota, che e' precisamente cio' che lo
// rende pericoloso. Il massimo del gradiente non ha questa ambiguita'.
function gradiente(g, w, h) {
  const mag = new Float32Array(w * h);
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    const gx = -g[i - w - 1] - 2 * g[i - 1] - g[i + w - 1]
               + g[i - w + 1] + 2 * g[i + 1] + g[i + w + 1];
    const gy = -g[i - w - 1] - 2 * g[i - w] - g[i - w + 1]
               + g[i + w - 1] + 2 * g[i + w] + g[i + w + 1];
    mag[i] = Math.hypot(gx, gy);
  }
  return mag;
}

function campionaBilineare(m, w, h, x, y) {
  if (x < 0 || y < 0 || x > w - 2 || y > h - 2) return 0;
  const x0 = Math.floor(x), y0 = Math.floor(y);
  const fx = x - x0, fy = y - y0, i = y0 * w + x0;
  return m[i] * (1 - fx) * (1 - fy) + m[i + 1] * fx * (1 - fy)
       + m[i + w] * (1 - fx) * fy + m[i + w + 1] * fx * fy;
}

// Sposta un punto sul massimo del gradiente lungo la normale al lato, con
// interpolazione parabolica a tre campioni: e' la posizione sub-pixel del bordo.
function agganciaAlBordo(p, nx, ny, mag, w, h) {
  // finestra +/-3: con una soglia lontana da quella ideale la maschera puo'
  // staccarsi dal bordo di due-tre pixel, e una finestra stretta non lo recupera
  let migliore = 0, vMax = -1;
  for (let t = -3; t <= 3; t++) {
    const v = campionaBilineare(mag, w, h, p[0] + t * nx, p[1] + t * ny);
    if (v > vMax) { vMax = v; migliore = t; }
  }
  if (migliore <= -3 || migliore >= 3) return p;      // massimo fuori finestra
  const a = campionaBilineare(mag, w, h, p[0] + (migliore - 1) * nx, p[1] + (migliore - 1) * ny);
  const b = vMax;
  const c = campionaBilineare(mag, w, h, p[0] + (migliore + 1) * nx, p[1] + (migliore + 1) * ny);
  const den = a - 2 * b + c;
  let d = migliore;
  if (Math.abs(den) > 1e-9) {
    const corr = 0.5 * (a - c) / den;
    if (Math.abs(corr) <= 1) d = migliore + corr;
  }
  return [p[0] + d * nx, p[1] + d * ny];
}

function maschera(g, soglia, invertita) {
  const m = new Uint8Array(g.length);
  for (let i = 0; i < g.length; i++) {
    const scuro = g[i] < soglia;
    m[i] = (invertita ? !scuro : scuro) ? 1 : 0;
  }
  return m;
}

// --- 4. tracciamento del contorno di una regione (Moore + criterio di Jacob) -
const VICINI = [[1,0],[1,1],[0,1],[-1,1],[-1,0],[-1,-1],[0,-1],[1,-1]];
function tracciaDa(bin, w, h, sx, sy, visto) {
  const catena = [];
  let cx = sx, cy = sy, dir = 0;
  const limite = 8 * (w + h);
  for (let passi = 0; passi < limite; passi++) {
    catena.push([cx, cy]);
    visto[cy * w + cx] = 1;
    let avanzato = false;
    for (let k = 0; k < 8; k++) {
      const d = (dir + 6 + k) % 8;          // riparti ruotando indietro di 90°
      const nx = cx + VICINI[d][0], ny = cy + VICINI[d][1];
      if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
      if (bin[ny * w + nx]) { cx = nx; cy = ny; dir = d; avanzato = true; break; }
    }
    if (!avanzato) break;                    // pixel isolato
    // Su una regione piena il contorno e' chiuso appena si torna al punto di
    // partenza. Il criterio di Jacob (stessa posizione **e** stessa direzione)
    // qui chiuderebbe solo al secondo giro, restituendo l'anello percorso due
    // volte — e un rettangolo percorso due volte si semplifica in otto vertici.
    if (cx === sx && cy === sy && catena.length > 2) break;
  }
  return catena;
}
function contorni(bin, w, h, minPunti) {
  const visto = new Uint8Array(w * h);
  const trovati = [];
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    // parti solo dalle transizioni sfondo->regione, cioe' dai bordi veri
    if (!bin[i] || visto[i] || bin[i - 1]) continue;
    const catena = tracciaDa(bin, w, h, x, y, visto);
    if (catena.length >= minPunti) trovati.push(catena);
  }
  return trovati;
}

// --- 7. semplificazione poligonale (Douglas-Peucker) -------------------------
function distanzaPuntoRetta(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const den = Math.hypot(dx, dy);
  if (den === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  return Math.abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / den;
}
function semplifica(punti, eps) {
  if (punti.length < 3) return punti.slice();
  let imax = 0, dmax = 0;
  const a = punti[0], b = punti[punti.length - 1];
  for (let i = 1; i < punti.length - 1; i++) {
    const d = distanzaPuntoRetta(punti[i], a, b);
    if (d > dmax) { dmax = d; imax = i; }
  }
  if (dmax <= eps) return [a, b];
  return semplifica(punti.slice(0, imax + 1), eps)
    .slice(0, -1)
    .concat(semplifica(punti.slice(imax), eps));
}

// Douglas-Peucker su una curva **chiusa**. Applicarlo direttamente spezzerebbe
// in due il lato su cui cade il punto di partenza, producendo un pentagono al
// posto di un quadrilatero: si taglia prima l'anello nei due punti piu' lontani
// fra loro, che su un rettangolo sono due vertici opposti.
function semplificaChiusa(catena, eps) {
  const n = catena.length;
  if (n < 4) return catena.slice();
  const a = catena[0];
  let iLontano = 0, dMax = -1;
  for (let i = 1; i < n; i++) {
    const d = (catena[i][0] - a[0]) ** 2 + (catena[i][1] - a[1]) ** 2;
    if (d > dMax) { dMax = d; iLontano = i; }
  }
  const primaMeta = semplifica(catena.slice(0, iLontano + 1), eps);
  const secondaMeta = semplifica(catena.slice(iLontano).concat([catena[0]]), eps);
  return primaMeta.slice(0, -1).concat(secondaMeta.slice(0, -1));
}

// --- 8. geometria di supporto ------------------------------------------------
function areaPoligono(p) {
  let s = 0;
  for (let i = 0; i < p.length; i++) {
    const q = p[(i + 1) % p.length];
    s += p[i][0] * q[1] - q[0] * p[i][1];
  }
  return Math.abs(s) / 2;
}
function convesso(p) {
  let segno = 0;
  for (let i = 0; i < p.length; i++) {
    const a = p[i], b = p[(i + 1) % p.length], c = p[(i + 2) % p.length];
    const z = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
    if (z !== 0) {
      if (segno === 0) segno = Math.sign(z);
      else if (Math.sign(z) !== segno) return false;
    }
  }
  return true;
}

// Retta ai minimi quadrati totali (PCA) sui punti di un lato: restituisce un
// punto medio, la direzione, e il **residuo RMS** — che e' l'incertezza vera di
// quel bordo, misurata sui dati e non assunta.
function fitRetta(punti) {
  const n = punti.length;
  let mx = 0, my = 0;
  for (const p of punti) { mx += p[0]; my += p[1]; }
  mx /= n; my /= n;
  let sxx = 0, syy = 0, sxy = 0;
  for (const p of punti) {
    const dx = p[0] - mx, dy = p[1] - my;
    sxx += dx * dx; syy += dy * dy; sxy += dx * dy;
  }
  // Autovettore principale della covarianza 2x2. La forma (lam - syy, sxy)
  // degenera a (0,0) proprio sui lati **verticali** — dove sxy = 0 e lam = syy —
  // e ripiegare su un default orizzontale darebbe una retta perpendicolare a
  // quella vera. Quando la covarianza incrociata e' trascurabile l'asse
  // principale e' gia' uno dei due assi: si sceglie quello con varianza maggiore.
  const tr = sxx + syy, det = sxx * syy - sxy * sxy;
  const lam = tr / 2 + Math.sqrt(Math.max(0, tr * tr / 4 - det));
  let vx, vy;
  if (Math.abs(sxy) > 1e-9 * (Math.abs(sxx) + Math.abs(syy) + 1)) {
    vx = lam - syy; vy = sxy;
  } else if (sxx >= syy) {
    vx = 1; vy = 0;
  } else {
    vx = 0; vy = 1;
  }
  const norma = Math.hypot(vx, vy); vx /= norma; vy /= norma;
  // residuo: distanza dei punti dalla retta (componente ortogonale)
  let s2 = 0;
  for (const p of punti) {
    const d = (p[0] - mx) * (-vy) + (p[1] - my) * vx;
    s2 += d * d;
  }
  return { px: mx, py: my, vx, vy, residuo: Math.sqrt(s2 / n) };
}

function intersezione(r1, r2) {
  const den = r1.vx * (-r2.vy) - r1.vy * (-r2.vx);
  if (Math.abs(den) < 1e-9) return null;   // lati paralleli: nessun vertice
  const bx = r2.px - r1.px, by = r2.py - r1.py;
  const t = (bx * (-r2.vy) - by * (-r2.vx)) / den;
  return [r1.px + t * r1.vx, r1.py + t * r1.vy];
}

// --- 9. raffinamento: dai 4 vertici approssimati ai 4 vertici veri ----------
// Per ogni lato si prendono i punti del contorno **escludendo le estremita'**
// (dove lo spigolo e' arrotondato), si fitta la retta, e i vertici nascono
// dall'intersezione delle rette adiacenti.
function distanzaSegmento(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

// I vertici di Douglas-Peucker sbagliano di parecchi pixel, e usarli per
// spartire il contorno fa finire punti di un lato nel fit di quello accanto:
// la retta si inclina e l'intersezione scivola in fuori, con un bias
// sistematico di qualche pixel — proprio l'errore che il rilevamento doveva
// eliminare. Qui i punti vengono **riassegnati al lato piu' vicino** e i lati
// rifittati, due o tre volte: le rette convergono su quelle vere e i vertici
// DP servono solo come innesco.
function raffinaQuadrilatero(catena, verticiIniziali, mag, w, h) {
  let vertici = verticiIniziali.map(v => [v[0], v[1]]);
  let residuo = 0, puntiPerLato = 0;

  for (let iterazione = 0; iterazione < 3; iterazione++) {
    const gruppi = [[], [], [], []];
    const normali = [];
    for (let k = 0; k < 4; k++) {
      const a = vertici[k], b = vertici[(k + 1) % 4];
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
      normali.push([-(b[1] - a[1]) / L, (b[0] - a[0]) / L]);
    }
    for (const p of catena) {
      let lato = -1, distanza = Infinity;
      for (let k = 0; k < 4; k++) {
        const d = distanzaSegmento(p, vertici[k], vertici[(k + 1) % 4]);
        if (d < distanza) { distanza = d; lato = k; }
      }
      const a = vertici[lato], b = vertici[(lato + 1) % 4];
      const lunghezza = Math.hypot(b[0] - a[0], b[1] - a[1]);
      // scarta i punti vicini ai vertici: e' li' che vive l'arrotondamento
      const margine = Math.max(2, lunghezza * 0.15);
      if (Math.hypot(p[0] - a[0], p[1] - a[1]) < margine) continue;
      if (Math.hypot(p[0] - b[0], p[1] - b[1]) < margine) continue;
      // e i punti troppo lontani dal lato: non gli appartengono
      if (distanza > Math.max(3, lunghezza * 0.08)) continue;
      // dal pixel binario al bordo vero, sub-pixel
      gruppi[lato].push(agganciaAlBordo(p, normali[lato][0], normali[lato][1], mag, w, h));
    }

    const rette = [];
    for (let k = 0; k < 4; k++) {
      if (gruppi[k].length < 5) return null;
      rette.push(fitRetta(gruppi[k]));
    }
    const nuovi = [];
    for (let k = 0; k < 4; k++) {
      const v = intersezione(rette[(k + 3) % 4], rette[k]);
      if (!v) return null;
      nuovi.push(v);
    }
    vertici = nuovi;
    residuo = rette.reduce((s, r) => s + r.residuo, 0) / 4;
    puntiPerLato = gruppi.reduce((s, g) => s + g.length, 0) / 4;
  }
  return { vertici, residuo, puntiPerLato };
}

// Incertezza del lato rilevato, **derivata** e non assunta.
//
// Ogni punto di bordo contribuisce con la dispersione maggiore fra due termini:
// il residuo misurato del fit, e la quantizzazione del pixel (una distribuzione
// uniforme di ampiezza 1 px ha deviazione 1/sqrt(12) = 0,289). Una retta fittata
// su n punti localizza il bordo sqrt(n) volte meglio del singolo punto, e la
// lunghezza del lato dipende da due intersezioni indipendenti, da cui sqrt(2).
const QUANTIZZAZIONE_PX = 1 / Math.sqrt(12);
function sigmaFit(residuo, puntiPerLato) {
  const perPunto = Math.max(residuo, QUANTIZZAZIONE_PX);
  return Math.SQRT2 * perPunto / Math.sqrt(Math.max(1, puntiPerLato));
}

// Il fit da solo dichiarerebbe ~0,01%, e sarebbe una fiducia falsa: e' la
// precisione con cui si localizza un bordo, non l'incertezza della misura.
// Manca tutto cio' che la geometria della ripresa aggiunge — e la parte che
// **si puo' misurare** e' l'obliquita': un rettangolo di rapporto noto visto di
// sbieco proietta un rapporto diverso, quindi lo scarto osservato dal valore
// ID-1 e' una stima diretta di quanto la vista non sia frontale, e di quanto la
// scala ricavata dal lato ne risenta.
//
// Restano fuori la distorsione dell'obiettivo e la non complanarita' col
// bersaglio: nessuna delle due e' osservabile da una sola tessera, e la seconda
// e' il bias piu' grosso di tutti (§5.3). Per questo la scala rilevata resta
// una misura da verificare con un secondo riferimento, non una certezza.
function sigmaLato(residuo, puntiPerLato, latoPx, deviazioneRapporto) {
  const fit = sigmaFit(residuo, puntiPerLato);
  const obliquita = latoPx * deviazioneRapporto;
  return Math.hypot(fit, obliquita);
}

// --- 10. il rilevatore -------------------------------------------------------
function lato(a, b) { return Math.hypot(b[0] - a[0], b[1] - a[1]); }

function valutaQuadrilatero(v, residuo, puntiPerLato) {
  const l = [lato(v[0], v[1]), lato(v[1], v[2]), lato(v[2], v[3]), lato(v[3], v[0])];
  // lati opposti: la media compensa al primo ordine la prospettiva
  const a = (l[0] + l[2]) / 2, b = (l[1] + l[3]) / 2;
  const lungo = Math.max(a, b), corto = Math.min(a, b);
  if (corto <= 0) return null;
  const rapporto = lungo / corto;
  const deviazione = Math.abs(rapporto - RAPPORTO_ID1) / RAPPORTO_ID1;
  // indici dei due vertici che delimitano un lato lungo, per la scala
  const lungoOrizzontale = a >= b;
  const estremi = lungoOrizzontale ? [v[0], v[1]] : [v[1], v[2]];
  return {
    vertici: v, latoLungoPx: lungo, latoCortoPx: corto, rapporto, deviazione,
    estremiLatoLungo: estremi, residuoPx: residuo,
    sigmaLatoPx: sigmaLato(residuo, puntiPerLato, lungo, deviazione),
    sigmaFitPx: sigmaFit(residuo, puntiPerLato),
    puntiPerLato,
    area: areaPoligono(v),
  };
}

/**
 * Cerca rettangoli con rapporto compatibile con una tessera ID-1.
 * `immagine` = {data, width, height} (una ImageData va bene tale e quale).
 * Restituisce i candidati ordinati dal piu' promettente.
 */
function candidatiDaMaschera(catene, w, h, areaMinima, tolleranzaRapporto, mag, fuori) {
  for (const catena of catene) {
    const eps = Math.max(1.5, catena.length * 0.015);
    const p = semplificaChiusa(catena, eps);
    if (p.length !== 4 || !convesso(p) || areaPoligono(p) < areaMinima) continue;

    const raffinato = raffinaQuadrilatero(catena, p, mag, w, h);
    if (!raffinato) continue;

    const valutato = valutaQuadrilatero(raffinato.vertici, raffinato.residuo, raffinato.puntiPerLato);
    if (!valutato || valutato.deviazione > tolleranzaRapporto) continue;
    // preferisci il rapporto giusto, poi l'area: un candidato grande e con il
    // rapporto esatto e' molto piu' probabilmente la tessera di uno piccolo
    valutato.punteggio = Math.sqrt(valutato.area) * Math.exp(-valutato.deviazione * 8);
    fuori.push(valutato);
  }
}

function rilevaTessere(immagine, opzioni) {
  const o = opzioni || {};
  const tolleranzaRapporto = o.tolleranzaRapporto ?? 0.18;  // ammette obliquita' moderata
  const areaMinimaFrazione = o.areaMinimaFrazione ?? 0.002;
  const w = immagine.width, h = immagine.height;

  const grigi = sfoca(aGrigi(immagine.data, w, h), w, h);
  const mag = gradiente(grigi, w, h);
  const base = otsu(grigi);
  const livelli = o.livelli ?? [base, base - 25, base + 25];

  const perimetroMinimo = Math.max(40, Math.round((w + h) * 0.06));
  const areaMinima = w * h * areaMinimaFrazione;
  const candidati = [];
  for (const soglia of livelli) {
    if (soglia <= 1 || soglia >= 254) continue;
    // la tessera puo' essere scura su chiaro o chiara su scuro: si provano
    // entrambe le polarita' invece di assumerne una
    for (const invertita of [false, true]) {
      const m = maschera(grigi, soglia, invertita);
      const catene = contorni(m, w, h, perimetroMinimo);
      candidatiDaMaschera(catene, w, h, areaMinima, tolleranzaRapporto, mag, candidati);
    }
  }

  candidati.sort((a, b) => b.punteggio - a.punteggio);
  return deduplica(candidati);
}

// Lo stesso rettangolo emerge da piu' soglie: si tiene una volta sola, quella
// col punteggio migliore.
function deduplica(lista) {
  const tenuti = [];
  for (const c of lista) {
    const cx = c.vertici.reduce((s, v) => s + v[0], 0) / 4;
    const cy = c.vertici.reduce((s, v) => s + v[1], 0) / 4;
    const vicino = tenuti.some(t => {
      const tx = t.vertici.reduce((s, v) => s + v[0], 0) / 4;
      const ty = t.vertici.reduce((s, v) => s + v[1], 0) / 4;
      return Math.hypot(cx - tx, cy - ty) < 0.25 * Math.sqrt(c.area);
    });
    if (!vicino) tenuti.push(c);
  }
  return tenuti;
}

const API = { rilevaTessere, RAPPORTO_ID1,
  _interni: { aGrigi, sfoca, otsu, maschera, gradiente, contorni,
              semplifica, semplificaChiusa, fitRetta, intersezione, areaPoligono, convesso } };

if (typeof window !== 'undefined') window.MisuraRileva = API;
if (typeof module !== 'undefined' && module.exports) module.exports = API;
