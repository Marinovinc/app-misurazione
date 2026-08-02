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

// Stesso fattore di copertura del core (k=2, ~95%): le verifiche qui sotto
// usano il medesimo criterio di compatibilita' del doppio riferimento, cioe'
// "lo scarto non supera k volte la propria incertezza". Non e' un parametro
// indipendente e non va regolato a parte.
const COPERTURA_K = 2.0;

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
    lungoDaPrimoVertice: lungoOrizzontale,
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
function candidatiDaMaschera(catene, w, h, areaMinima, tolleranzaRapporto, mag, fuori, diag) {
  for (const catena of catene) {
    diag.contorni++;
    const eps = Math.max(1.5, catena.length * 0.015);
    const p = semplificaChiusa(catena, eps);
    if (p.length !== 4) { diag.nonQuadrilateri++; continue; }
    if (!convesso(p)) { diag.nonConvessi++; continue; }
    if (areaPoligono(p) < areaMinima) { diag.troppoPiccoli++; continue; }
    diag.quadrilateri++;

    const raffinato = raffinaQuadrilatero(catena, p, mag, w, h);
    if (!raffinato) { diag.fitFallito++; continue; }

    const valutato = valutaQuadrilatero(raffinato.vertici, raffinato.residuo, raffinato.puntiPerLato);
    if (!valutato) { diag.fitFallito++; continue; }
    if (valutato.deviazione > tolleranzaRapporto) {
      // il piu' informativo di tutti: c'era un rettangolo, ma il rapporto non e'
      // quello di una ID-1. Serve a distinguere "non vedo niente" da "vedo, ma
      // non e' una tessera" — due problemi con rimedi opposti
      diag.rapportoSbagliato++;
      if (valutato.deviazione < diag.miglioreDeviazione) {
        diag.miglioreDeviazione = valutato.deviazione;
        diag.miglioreRapporto = valutato.rapporto;
        diag.miglioreLatoPx = valutato.latoLungoPx;
      }
      continue;
    }
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
  // Otsu separa **due** popolazioni. Una scena reale ne ha molte — tavolo,
  // sfondo, oggetti, ombre — e la soglia migliore per isolare la tessera puo'
  // cadere lontano da quella globale. Si prova una scala di livelli: costa
  // qualche decimo di secondo e recupera i casi in cui la tessera non e' il
  // contrasto dominante dell'immagine.
  const percentile = frazione => {
    const h2 = new Float64Array(256);
    for (let i = 0; i < grigi.length; i += 3) h2[Math.max(0, Math.min(255, Math.round(grigi[i])))]++;
    let tot = 0; for (let i = 0; i < 256; i++) tot += h2[i];
    let acc = 0;
    for (let i = 0; i < 256; i++) { acc += h2[i]; if (acc >= tot * frazione) return i; }
    return 128;
  };
  const livelli = o.livelli ?? [base, base - 30, base + 30, base - 60, base + 60,
                                percentile(0.25), percentile(0.5), percentile(0.75)];

  const perimetroMinimo = Math.max(40, Math.round((w + h) * 0.06));
  const areaMinima = w * h * areaMinimaFrazione;
  const candidati = [];
  const diag = {contorni:0, nonQuadrilateri:0, nonConvessi:0, troppoPiccoli:0,
                quadrilateri:0, fitFallito:0, rapportoSbagliato:0,
                miglioreDeviazione:Infinity, miglioreRapporto:null, miglioreLatoPx:null,
                sogliaOtsu:base, areaMinima, larghezza:w, altezza:h};
  for (const soglia of livelli) {
    if (soglia <= 1 || soglia >= 254) continue;
    // la tessera puo' essere scura su chiaro o chiara su scuro: si provano
    // entrambe le polarita' invece di assumerne una
    for (const invertita of [false, true]) {
      const m = maschera(grigi, soglia, invertita);
      const catene = contorni(m, w, h, perimetroMinimo);
      candidatiDaMaschera(catene, w, h, areaMinima, tolleranzaRapporto, mag, candidati, diag);
    }
  }

  candidati.sort((a, b) => b.punteggio - a.punteggio);
  const tenuti = deduplica(candidati);
  tenuti.diagnostica = diag;      // perche' non ha trovato nulla, quando non trova nulla
  return tenuti;
}

// Lo stesso rettangolo emerge da piu' soglie, ogni volta con un bordo un po'
// diverso. Fra queste versioni si tiene quella che **aderisce meglio ai bordi**
// — residuo del fit piu' basso — non quella con l'area maggiore: il punteggio
// premia l'area perche' serve a scegliere fra oggetti *diversi*, ma fra due
// letture dello stesso oggetto il piu' grande e' semplicemente quello con la
// soglia piu' generosa, cioe' il piu' sbagliato.
function centro(c) {
  return [c.vertici.reduce((s, v) => s + v[0], 0) / 4,
          c.vertici.reduce((s, v) => s + v[1], 0) / 4];
}
function deduplica(lista) {
  const gruppi = [];
  for (const c of lista) {
    const [cx, cy] = centro(c);
    const g = gruppi.find(gr => {
      const [tx, ty] = centro(gr[0]);
      return Math.hypot(cx - tx, cy - ty) < 0.25 * Math.sqrt(c.area);
    });
    if (g) g.push(c); else gruppi.push([c]);
  }
  return gruppi.map(g => g.reduce((a, b) =>
    (b.residuoPx < a.residuoPx - 1e-9) ? b
    : (Math.abs(b.residuoPx - a.residuoPx) < 1e-9 && b.deviazione < a.deviazione) ? b
    : a));
}

// --- 11. omografia: misurare sul piano invece che con una scala unica --------
//
// Una scala scalare (mm/px) presuppone che il fattore di conversione sia lo
// stesso ovunque nel fotogramma. E' vero solo se la ripresa e' perfettamente
// frontale: appena la camera e' inclinata, la parte piu' vicina del piano
// appare ingrandita e quella lontana rimpicciolita, e un oggetto **lontano
// dalla tessera** viene misurato con la scala sbagliata. Mediare i lati opposti
// compensa il primo ordine sulla tessera, non sul resto della scena.
//
// Con i quattro vertici e le dimensioni note si ricava invece l'omografia che
// porta il piano della tessera nell'immagine. Invertendola, ogni punto del
// **piano** si converte in millimetri esatti, ovunque si trovi. Vale solo per
// cio' che giace su quel piano: e' la stessa condizione di sempre (§5.3), ma
// qui almeno la prospettiva non aggiunge errore.

// Risolve A x = b con eliminazione di Gauss e pivot parziale.
function risolvi(A, b) {
  const n = b.length;
  const M = A.map((riga, i) => riga.concat([b[i]]));
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    }
    if (Math.abs(M[pivot][col]) < 1e-12) return null;   // sistema singolare
    [M[col], M[pivot]] = [M[pivot], M[col]];
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = M[r][col] / M[col][col];
      if (f === 0) continue;
      for (let c = col; c <= n; c++) M[r][c] -= f * M[col][c];
    }
  }
  return M.map((riga, i) => riga[n] / riga[i]);   // Gauss-Jordan: resta la diagonale
}

// Omografia immagine -> piano (mm) da 4 corrispondenze.
function omografia(daImmagine, aPiano) {
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = daImmagine[i], [X, Y] = aPiano[i];
    A.push([x, y, 1, 0, 0, 0, -X * x, -X * y]); b.push(X);
    A.push([0, 0, 0, x, y, 1, -Y * x, -Y * y]); b.push(Y);
  }
  const h = risolvi(A, b);
  return h ? h.concat([1]) : null;
}

function applica(h, p) {
  const den = h[6] * p[0] + h[7] * p[1] + 1;
  if (Math.abs(den) < 1e-12) return null;
  return [(h[0] * p[0] + h[1] * p[1] + h[2]) / den,
          (h[3] * p[0] + h[4] * p[1] + h[5]) / den];
}

// Angoli della tessera nel piano, in millimetri: il lato lungo e' 85,60 e il
// corto 53,98, e quale dei due parta dal primo vertice lo dice il rilevatore.
function pianoTessera(lungoDaPrimoVertice) {
  const L = 85.60, C = 53.98;
  return lungoDaPrimoVertice
    ? [[0, 0], [L, 0], [L, C], [0, C]]
    : [[0, 0], [C, 0], [C, L], [0, L]];
}

function areaConSegno(p) {
  let s = 0;
  for (let i = 0; i < p.length; i++) {
    const q = p[(i + 1) % p.length];
    s += p[i][0] * q[1] - q[0] * p[i][1];
  }
  return s / 2;
}

/**
 * Angoli del piano nell'ordine che **corrisponde** ai vertici rilevati.
 *
 * Il rilevatore restituisce i quattro vertici in ordine ciclico, ma il verso di
 * percorrenza dipende da come il contorno e' stato tracciato: accoppiarli a un
 * rettangolo scritto a mano produce un'omografia che manda ogni angolo su
 * quello sbagliato. Per le sole distanze l'effetto e' mascherato — una
 * riflessione le conserva — ma la **posa** ne esce con la normale rovesciata, e
 * le altezze diventano negative. Qui il verso del piano viene allineato a
 * quello dell'immagine.
 */
function pianoPerTessera(candidato) {
  const piano = pianoTessera(candidato.lungoDaPrimoVertice !== false);
  const versoImmagine = Math.sign(areaConSegno(candidato.vertici));
  const versoPiano = Math.sign(areaConSegno(piano));
  if (versoImmagine !== 0 && versoImmagine !== versoPiano) {
    // Si **specchia** il rettangolo, non si inverte l'ordine dei vertici:
    // ruotare la sequenza cambierebbe anche quale lato del piano corrisponde al
    // primo lato in immagine, scambiando 85,60 con 53,98. L'errore che ne segue
    // e' subdolo, perche' le proporzioni restano credibili — le dimensioni
    // escono divise e moltiplicate per 1,586, e il volume resta plausibile.
    return piano.map(p => [p[0], -p[1]]);
  }
  return piano;
}

/**
 * Lunghezza in mm di un segmento che giace sul piano della tessera, con la sua
 * incertezza propagata numericamente: si perturba ogni coordinata d'ingresso
 * della propria sigma e si somma in quadratura l'effetto sul risultato. E' il
 * jacobiano calcolato per differenze finite, non una stima a occhio.
 */
function misuraSulPiano(tessera, a, b, sigmaVertice, sigmaPunto) {
  const piano = pianoPerTessera(tessera);
  const lunghezza = (vertici, pa, pb) => {
    const h = omografia(vertici, piano);
    if (!h) return null;
    const A = applica(h, pa), B = applica(h, pb);
    if (!A || !B) return null;
    return Math.hypot(B[0] - A[0], B[1] - A[1]);
  };

  const base = lunghezza(tessera.vertici, a, b);
  if (base === null) return null;

  const delta = 0.25;   // px: abbastanza piccolo per la derivata, grande per il rumore numerico
  let varianza = 0;
  for (let i = 0; i < 4; i++) for (let c = 0; c < 2; c++) {
    const mossi = tessera.vertici.map(v => v.slice());
    mossi[i][c] += delta;
    const l = lunghezza(mossi, a, b);
    if (l === null) return null;
    const derivata = (l - base) / delta;
    varianza += (derivata * sigmaVertice) ** 2;
  }
  for (const quale of [0, 1]) for (let c = 0; c < 2; c++) {
    const pa = a.slice(), pb = b.slice();
    (quale === 0 ? pa : pb)[c] += delta;
    const l = lunghezza(tessera.vertici, pa, pb);
    if (l === null) return null;
    const derivata = (l - base) / delta;
    varianza += (derivata * sigmaPunto) ** 2;
  }
  return { mm: base, sigmaMm: Math.sqrt(varianza) };
}

// --- 12. focale del dispositivo da una vista del rettangolo ------------------
//
// I due punti di fuga delle coppie di lati opposti corrispondono a direzioni
// che nel mondo sono **ortogonali**. Con pixel quadrati e centro ottico al
// centro del fotogramma, l'ortogonalita' impone
//
//     (v1 - c) . (v2 - c) + f^2 = 0        ->    f^2 = -(v1 - c).(v2 - c)
//
// (Zhang & He, whiteboard scanning). Se il prodotto scalare non e' negativo la
// configurazione e' degenere: succede quando la vista e' quasi frontale, i lati
// opposti restano quasi paralleli e i punti di fuga scappano all'infinito. In
// quel caso la focale **non e' determinabile**, e va detto invece di produrre
// un numero qualsiasi.
//
// Attenzione a cosa NON da'. Una focale nota non fornisce la scala: una scatola
// piccola vicina e una grande lontana proiettano la stessa immagine anche con
// la calibrazione perfetta (§3.1). Serve a ricavare la **terza dimensione** e a
// correggere la geometria, non a sostituire il riferimento.

function intersezioneRette(p1, p2, p3, p4) {
  const a1 = p2[1] - p1[1], b1 = p1[0] - p2[0], c1 = a1 * p1[0] + b1 * p1[1];
  const a2 = p4[1] - p3[1], b2 = p3[0] - p4[0], c2 = a2 * p3[0] + b2 * p3[1];
  const det = a1 * b2 - a2 * b1;
  if (Math.abs(det) < 1e-9) return null;
  return [(b2 * c1 - b1 * c2) / det, (a1 * c2 - a2 * c1) / det];
}

function focaleDaVertici(vertici, larghezza, altezza) {
  const cx = larghezza / 2, cy = altezza / 2;
  const fuga1 = intersezioneRette(vertici[0], vertici[1], vertici[3], vertici[2]);
  const fuga2 = intersezioneRette(vertici[1], vertici[2], vertici[0], vertici[3]);
  if (!fuga1 || !fuga2) return null;
  const prodotto = (fuga1[0] - cx) * (fuga2[0] - cx) + (fuga1[1] - cy) * (fuga2[1] - cy);
  if (prodotto >= 0) return null;
  return Math.sqrt(-prodotto);
}

/**
 * Focale in pixel con la sua incertezza, propagata perturbando i vertici.
 * `null` quando la vista non la determina — che e' un esito legittimo, non un
 * errore: significa "questo scatto non serve alla calibrazione, fanne un altro
 * piu' inclinato".
 */
function stimaFocale(vertici, larghezza, altezza, sigmaVertice) {
  const base = focaleDaVertici(vertici, larghezza, altezza);
  if (base === null || !isFinite(base) || base <= 0) return null;

  const delta = 0.25;
  let varianza = 0;
  for (let i = 0; i < 4; i++) for (let c = 0; c < 2; c++) {
    const mossi = vertici.map(v => v.slice());
    mossi[i][c] += delta;
    const f = focaleDaVertici(mossi, larghezza, altezza);
    if (f === null) return null;                 // al bordo della degenerazione
    varianza += (((f - base) / delta) * sigmaVertice) ** 2;
  }
  const sigma = Math.sqrt(varianza);
  return { fPx: base, sigmaPx: sigma, relativa: sigma / base };
}

/**
 * Fonde piu' stime della focale: media pesata sull'inverso della varianza, che
 * per grandezze indipendenti e' la stessa cosa che fa la GLS del core.
 *
 * Gli scarti si decidono su criteri **indipendenti dal risultato** (§6.3): una
 * stima entra o no in base a quanto e' incerta *lei*, mai in base a quanto si
 * discosta dalle altre. Scartare cio' che disaccorda restringerebbe
 * l'incertezza in modo artificiale, e il numero finale confermerebbe se stesso.
 * Gli scarti vengono contati e riportati.
 */
function fondiFocali(stime, incertezzaRelativaMassima) {
  const limite = incertezzaRelativaMassima ?? 0.08;
  const tenute = [], scartate = [];
  for (const s of stime) {
    if (!s) { scartate.push('vista non determinante'); continue; }
    if (s.relativa > limite) { scartate.push('stima troppo incerta'); continue; }
    tenute.push(s);
  }
  if (!tenute.length) return { fPx: null, tenute: 0, scartate: scartate.length, scartate_motivi: scartate };

  let pesi = 0, somma = 0;
  for (const s of tenute) {
    const p = 1 / (s.sigmaPx * s.sigmaPx);
    pesi += p; somma += p * s.fPx;
  }
  const fPx = somma / pesi;
  const sigmaPx = Math.sqrt(1 / pesi);
  // dispersione osservata fra le stime: se e' molto maggiore dell'incertezza
  // dichiarata, il modello sta sottostimando qualcosa (tipicamente la
  // distorsione, che qui non e' modellata). Si riporta, non si nasconde.
  const media = fPx;
  const disp = tenute.length > 1
    ? Math.sqrt(tenute.reduce((a, s) => a + (s.fPx - media) ** 2, 0) / (tenute.length - 1))
    : 0;
  return {
    fPx, sigmaPx, relativa: sigmaPx / fPx,
    dispersionePx: disp,
    coerenza: disp > 0 && sigmaPx > 0 ? disp / (sigmaPx * Math.sqrt(tenute.length)) : 1,
    tenute: tenute.length, scartate: scartate.length, scartate_motivi: scartate,
  };
}

// --- 13. la terza dimensione: altezze fuori dal piano ------------------------
//
// La base di una scatola appoggiata sul tavolo giace sul piano del riferimento,
// quindi l'omografia la misura gia'. L'altezza no: esce dal piano, e nessuna
// omografia la raggiunge. Con la focale si ricava la **posa** del piano
// rispetto alla camera, e da li' l'altezza di un vertice che sta sulla
// verticale sopra un punto noto della base.
//
// La verticale e' la normale al piano d'appoggio, non la verticale dell'immagine:
// se il tavolo e' storto o la scatola e' inclinata, il numero e' l'altezza
// rispetto al piano — ed e' l'unica che questa geometria puo' definire.

function _matVec(M, v) {
  return [M[0][0]*v[0] + M[0][1]*v[1] + M[0][2]*v[2],
          M[1][0]*v[0] + M[1][1]*v[1] + M[1][2]*v[2],
          M[2][0]*v[0] + M[2][1]*v[1] + M[2][2]*v[2]];
}
function _croce(a, b) {
  return [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]];
}
function _norma(v) { return Math.hypot(v[0], v[1], v[2]); }
function _perScalare(v, k) { return [v[0]*k, v[1]*k, v[2]*k]; }

/**
 * Posa del piano (rotazione + traslazione rispetto alla camera) dall'omografia
 * piano->immagine e dalla focale. G e' l'omografia in forma di 9 numeri.
 */
function posaDaOmografia(G, fPx, cx, cy) {
  const Kinv = [[1/fPx, 0, -cx/fPx], [0, 1/fPx, -cy/fPx], [0, 0, 1]];
  const a1 = _matVec(Kinv, [G[0], G[3], G[6]]);
  const a2 = _matVec(Kinv, [G[1], G[4], G[7]]);
  const a3 = _matVec(Kinv, [G[2], G[5], G[8]]);
  const n1 = _norma(a1), n2 = _norma(a2);
  if (n1 < 1e-12 || n2 < 1e-12) return null;
  const lambda = 2 / (n1 + n2);            // media delle due normalizzazioni
  let r1 = _perScalare(a1, lambda), r2 = _perScalare(a2, lambda);
  let t = _perScalare(a3, lambda);
  if (t[2] < 0) { r1 = _perScalare(r1, -1); r2 = _perScalare(r2, -1); t = _perScalare(t, -1); }
  return { r1, r2, r3: _croce(r1, r2), t };
}

/**
 * Altezza sul piano del punto immagine `cima`, sapendo che sta sulla verticale
 * sopra il punto del piano (X, Y). Due equazioni di proiezione, una incognita:
 * si risolve ai minimi quadrati invece di scegliere quale delle due usare.
 */
function altezzaSulPiano(posa, fPx, cx, cy, X, Y, cima) {
  const { r1, r2, r3, t } = posa;
  const b = [X*r1[0] + Y*r2[0] + t[0], X*r1[1] + Y*r2[1] + t[1], X*r1[2] + Y*r2[2] + t[2]];
  const u = cima[0] - cx, v = cima[1] - cy;
  const A1 = fPx*r3[0] - u*r3[2], c1 = u*b[2] - fPx*b[0];
  const A2 = fPx*r3[1] - v*r3[2], c2 = v*b[2] - fPx*b[1];
  const den = A1*A1 + A2*A2;
  if (den < 1e-12) return null;            // spigolo lungo la linea di vista
  return (A1*c1 + A2*c2) / den;
}

/**
 * Altezza con incertezza, propagata perturbando sia i vertici della tessera
 * (che determinano piano e focale) sia il punto di cima.
 *
 * La focale viene stimata dalla **stessa** tessera che fornisce la scala: un
 * errore sui suoi vertici entra quindi due volte, una per il piano e una per la
 * focale. Propagare numericamente sull'ingresso comune, invece di sommare in
 * quadratura due contributi calcolati a parte, tiene conto della correlazione
 * anziche' ignorarla — trattare come indipendenti cose che non lo sono
 * sottostima l'incertezza.
 */
function altezzaConIncertezza(verticiTessera, pianoTessera, basePiano, cima,
                              larghezza, altezza, sigmaVertice, sigmaCima) {
  const cx = larghezza / 2, cy = altezza / 2;
  const calcola = (vt, pc) => {
    const f = focaleDaVertici(vt, larghezza, altezza);
    if (f === null) return null;
    const G = omografia(pianoTessera, vt);
    if (!G) return null;
    const posa = posaDaOmografia(G, f, cx, cy);
    if (!posa) return null;
    return altezzaSulPiano(posa, f, cx, cy, basePiano[0], basePiano[1], pc);
  };

  const base = calcola(verticiTessera, cima);
  if (base === null || !isFinite(base)) return null;

  const delta = 0.25;
  let varianza = 0;
  for (let i = 0; i < 4; i++) for (let c = 0; c < 2; c++) {
    const mossi = verticiTessera.map(v => v.slice());
    mossi[i][c] += delta;
    const h = calcola(mossi, cima);
    if (h === null) return null;
    varianza += (((h - base) / delta) * sigmaVertice) ** 2;
  }
  for (let c = 0; c < 2; c++) {
    const pc = cima.slice();
    pc[c] += delta;
    const h = calcola(verticiTessera, pc);
    if (h === null) return null;
    varianza += (((h - base) / delta) * sigmaCima) ** 2;
  }
  return { mm: base, sigmaMm: Math.sqrt(varianza) };
}

// --- 14. la scatola e' davvero appoggiata su quel piano? ---------------------
//
// Tutta la misura poggia su un'ipotesi che l'utente dichiara e l'app finora
// accettava: che la scatola stia sullo **stesso piano** della tessera. Se non e'
// vero — scatola su un rialzo, tessera su un libro, oggetto inclinato — le
// dimensioni escono sbagliate di parecchi percento **senza che nulla lo
// segnali**, ed e' lo stesso meccanismo del riferimento tenuto in mano.
//
// Un parallelepipedo pero' e' ridondante: otto vertici per tre dimensioni. La
// ridondanza si spende in verifiche, e ognuna produce uno **scarto in
// millimetri** che si confronta con la propria incertezza — non con una soglia
// scelta a mano.
//
// COSA QUESTE VERIFICHE NON CATTURANO, e va detto perche' e' il caso peggiore:
// una scatola **sollevata parallelamente** al piano (su un rialzo, un altro
// libro, un pallet) supera tutte e tre le prove. Rettificata, la sua base resta
// un rettangolo perfetto, le facce tornano, le altezze concordano: e'
// internamente coerente, semplicemente e' una scatola *piu' grande* su quel
// piano. Dall'immagine i due casi sono **indistinguibili** — e' l'ambiguita' di
// scala di §3.1 applicata alla profondita', e nessun controllo geometrico la
// risolve. Sul banco un rialzo di appena 5 mm passa senza che nulla si muova.
// Resta una condizione che l'utente deve garantire, non una che l'app verifica:
// va detto nell'interfaccia, non nascosto dietro un esito verde.
//
// 1. **Base rettangolare.** Rettificata sul piano, la base deve avere angoli
//    retti. Se la base non giace sul piano, l'omografia la deforma in un
//    quadrilatero storto.
// 2. **Facce verticali coerenti.** Riportando i vertici superiori alla quota
//    misurata, le loro coordinate sul piano devono coincidere con quelle della
//    base: e' il residuo di riproiezione del parallelepipedo.
// 3. **Altezze concordi.** I quattro spigoli devono dare la stessa altezza; se
//    divergono, la scatola e' inclinata o non e' un parallelepipedo.

function _angoloTraLati(a, b, c) {
  const u = [a[0] - b[0], a[1] - b[1]], v = [c[0] - b[0], c[1] - b[1]];
  const nu = Math.hypot(u[0], u[1]), nv = Math.hypot(v[0], v[1]);
  if (nu < 1e-9 || nv < 1e-9) return null;
  const cos = Math.max(-1, Math.min(1, (u[0]*v[0] + u[1]*v[1]) / (nu*nv)));
  return Math.acos(cos) * 180 / Math.PI;
}

/** Scarti dai 90 gradi dei quattro angoli della base rettificata. */
function ortogonalitaBase(basePiano) {
  const scarti = [];
  for (let i = 0; i < 4; i++) {
    const a = _angoloTraLati(basePiano[(i + 3) % 4], basePiano[i], basePiano[(i + 1) % 4]);
    if (a === null) return null;
    scarti.push(a - 90);
  }
  return scarti;
}

/**
 * Interseca il raggio visivo del punto `p` col piano a quota `h` e restituisce
 * le coordinate (X, Y) sul piano. Serve a riportare giu' i vertici superiori.
 */
function puntoSulPianoAQuota(posa, fPx, cx, cy, p, h) {
  const { r1, r2, r3, t } = posa;
  const d = [(p[0] - cx) / fPx, (p[1] - cy) / fPx, 1];
  // X*r1 + Y*r2 + h*r3 + t = s*d  ->  tre equazioni, incognite X, Y, s
  const o = [t[0] + h*r3[0], t[1] + h*r3[1], t[2] + h*r3[2]];
  const M = [[r1[0], r2[0], -d[0]], [r1[1], r2[1], -d[1]], [r1[2], r2[2], -d[2]]];
  const sol = risolvi(M, [-o[0], -o[1], -o[2]]);
  if (!sol || !isFinite(sol[0]) || !isFinite(sol[1])) return null;
  return [sol[0], sol[1]];
}

/**
 * Verifica che la scatola sia coerente con l'ipotesi dichiarata. Restituisce
 * gli scarti misurati e la loro soglia di compatibilita', derivata propagando
 * l'incertezza dei punti — stesso criterio del doppio riferimento (§5.3):
 * compatibile se lo scarto non supera k volte la propria incertezza.
 */
function verificaScatola(opts) {
  const { verticiTessera, pianoTessera, baseImg, cimaImg,
          larghezza, altezza, sigmaVertice, sigmaPunto } = opts;
  const k = opts.coperturaK ?? COPERTURA_K;
  const cx = larghezza / 2, cy = altezza / 2;

  const misura = (vt, bi, ci) => {
    const f = focaleDaVertici(vt, larghezza, altezza);
    if (f === null) return null;
    const H = omografia(vt, pianoTessera);
    const G = omografia(pianoTessera, vt);
    if (!H || !G) return null;
    const posa = posaDaOmografia(G, f, cx, cy);
    if (!posa) return null;
    const base = bi.map(p => applica(H, p));
    if (base.some(p => !p)) return null;
    const alt = [];
    for (let i = 0; i < 4; i++) {
      const h = altezzaSulPiano(posa, f, cx, cy, base[i][0], base[i][1], ci[i]);
      if (h === null) return null;
      alt.push(h);
    }
    const hMedia = alt.reduce((a, b) => a + b, 0) / 4;
    const ort = ortogonalitaBase(base);
    if (!ort) return null;
    // residuo: i vertici superiori riportati alla quota media devono cadere
    // sopra quelli di base
    let residuo = 0;
    for (let i = 0; i < 4; i++) {
      const q = puntoSulPianoAQuota(posa, f, cx, cy, ci[i], hMedia);
      if (!q) return null;
      residuo = Math.max(residuo, Math.hypot(q[0] - base[i][0], q[1] - base[i][1]));
    }
    const dispAlt = Math.sqrt(alt.reduce((a, b) => a + (b - hMedia) ** 2, 0) / 4);
    return {
      ortogonalitaMax: Math.max(...ort.map(Math.abs)),
      residuoMm: residuo,
      dispersioneAltezzeMm: dispAlt,
    };
  };

  const base = misura(verticiTessera, baseImg, cimaImg);
  if (!base) return null;

  // incertezza degli scarti: si perturbano tutti gli ingressi
  const delta = 0.25;
  const chiavi = ['ortogonalitaMax', 'residuoMm', 'dispersioneAltezzeMm'];
  const varianze = { ortogonalitaMax: 0, residuoMm: 0, dispersioneAltezzeMm: 0 };
  const perturba = (lista, i, c, sigma) => {
    const vt = verticiTessera.map(v => v.slice());
    const bi = baseImg.map(v => v.slice());
    const ci = cimaImg.map(v => v.slice());
    ({ tessera: vt, base: bi, cima: ci })[lista][i][c] += delta;
    const m = misura(vt, bi, ci);
    if (!m) return;
    for (const ch of chiavi) varianze[ch] += (((m[ch] - base[ch]) / delta) * sigma) ** 2;
  };
  for (let i = 0; i < 4; i++) for (let c = 0; c < 2; c++) {
    perturba('tessera', i, c, sigmaVertice);
    perturba('base', i, c, sigmaPunto);
    perturba('cima', i, c, sigmaPunto);
  }

  const esiti = {};
  const motivi = [];
  for (const ch of chiavi) {
    const u = Math.sqrt(varianze[ch]);
    const soglia = k * u;
    const superato = base[ch] <= soglia;
    esiti[ch] = { scarto: base[ch], soglia, superato };
    if (!superato) motivi.push(ch);
  }
  return {
    coerente: motivi.length === 0,
    ortogonalita: esiti.ortogonalitaMax,
    residuoFacce: esiti.residuoMm,
    altezzeConcordi: esiti.dispersioneAltezzeMm,
    motivi,
    spiegazione: motivi.length === 0 ? null : (
      'la scatola non e\' coerente con l\'ipotesi che sia appoggiata sul piano '
      + 'del riferimento: ' + motivi.map(m => ({
        ortogonalitaMax: 'la base rettificata non ha angoli retti',
        residuoMm: 'le facce verticali non tornano sopra la base',
        dispersioneAltezzeMm: 'i quattro spigoli danno altezze diverse',
      })[m]).join('; ')
      + '. Cause tipiche: scatola inclinata rispetto al piano della tessera, '
      + 'oggetto non parallelepipedo, oppure punti cliccati sugli spigoli sbagliati'
    ),
  };
}

// diagonale del formato 35 mm: serve solo a rendere leggibile il numero
const DIAGONALE_35MM = 43.27;
function equivalente35(fPx, larghezza, altezza) {
  return DIAGONALE_35MM * fPx / Math.hypot(larghezza, altezza);
}

const API = { rilevaTessere, RAPPORTO_ID1, omografia, applica, misuraSulPiano,
  focaleDaVertici, stimaFocale, fondiFocali, equivalente35, pianoPerTessera,
  posaDaOmografia, altezzaSulPiano, altezzaConIncertezza, verificaScatola,
  _interni: { aGrigi, sfoca, otsu, maschera, gradiente, contorni,
              semplifica, semplificaChiusa, fitRetta, intersezione, areaPoligono, convesso } };

if (typeof window !== 'undefined') window.MisuraRileva = API;
if (typeof module !== 'undefined' && module.exports) module.exports = API;
