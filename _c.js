
const $ = s => document.querySelector(s);

// La modalita' NON e' una voce che l'utente sceglie: e' derivata dalle condizioni
// che l'app puo' davvero verificare (§4.1). Prima c'era un radio libero, e si
// poteva ottenere una scheda etichettata "Certificata" su una foto trascinata
// dalla galleria: il numero non era inventato, ma la provenienza si'.
//
// `origine` viene impostata dalla porta d'ingresso E confermata da come
// l'immagine e' effettivamente arrivata: l'app afferma "live" solo di cio' che
// ha catturato lei. Un <input type=file capture> aprirebbe la fotocamera di
// sistema e restituirebbe un file indistinguibile da uno d'archivio — per
// questo non viene usato.
const state = {
  origine:null,               // 'scatto' | 'archivio'
  dataUrl:null, natW:0, natH:0,
  rifA:[], rifB:[], punti:[],
  fase:'rifA',                // 'rifA' -> ('rifB') -> 'target'
  doppio:false,
};

const file=$('#file'), stage=$('#stage'), img=$('#img'), ov=$('#ov');
const hint=$('#hint'), reset=$('#reset'), btn=$('#misura'), err=$('#err');
const modo=$('#modo'), modoT=$('#modoT'), modoP=$('#modoP'), cond=$('#cond');
const portaScatto=$('#portaScatto'), portaArchivio=$('#portaArchivio'), ricomincia=$('#ricomincia');
const chkDoppio=$('#usaDoppio'), rifBoxB=$('#rifBoxB');

portaArchivio.addEventListener('click',()=>{ chiudiCam(); file.click(); });
portaScatto.addEventListener('click',()=>{ apriCam(); });
file.addEventListener('change',()=>{ if(file.files[0]){ impostaOrigine('archivio'); caricaFile(file.files[0]); } });

// un file trascinato e' per definizione d'archivio: stessa porta, stessa modalita'
;['dragover','dragenter'].forEach(e=>portaArchivio.addEventListener(e,ev=>{ev.preventDefault();portaArchivio.classList.add('over');}));
;['dragleave','drop'].forEach(e=>portaArchivio.addEventListener(e,ev=>{ev.preventDefault();portaArchivio.classList.remove('over');}));
portaArchivio.addEventListener('drop',ev=>{
  const f=ev.dataTransfer.files[0];
  if(f){ chiudiCam(); impostaOrigine('archivio'); caricaFile(f); }
});

function impostaOrigine(o){
  state.origine=o;
  portaScatto.setAttribute('aria-pressed', String(o==='scatto'));
  portaArchivio.setAttribute('aria-pressed', String(o==='archivio'));
  // Il doppio riferimento e' la condizione che rende possibile la certificata,
  // quindi con lo scatto in-app parte attivo — ma **solo finche' l'utente non si
  // e' espresso**. Chi ha un riferimento solo lo dice una volta, non a ogni
  // scatto: riproporglielo ogni volta trasformerebbe una verifica utile in un
  // ostacolo, e la strada piu' rapida per far ignorare un controllo e' imporlo.
  if(o==='scatto' && !chkDoppio.checked && !sceltaDoppioEspressa){ chkDoppio.checked=true; }
  state.doppio=chkDoppio.checked;
  rifBoxB.hidden=!state.doppio;
  ricomincia.hidden=false;
  aggiornaModo();
}

let sceltaDoppioEspressa=false;   // l'utente ha deciso lui: non si ridiscute
chkDoppio.addEventListener('change',()=>{
  sceltaDoppioEspressa=true;
  state.doppio=chkDoppio.checked;
  rifBoxB.hidden=!state.doppio;
  state.rifB=[];
  // non si ricomincia da capo: i clic gia' fatti sul riferimento A restano, e
  // si prosegue da dove si era. Perdere il lavoro fatto per aver cambiato idea
  // sulla verifica e' il modo piu' rapido di rendere la verifica antipatica.
  state.fase = state.rifA.length===2 ? (state.doppio?'rifB':'target') : 'rifA';
  $('#esito').innerHTML=''; err.hidden=true;
  render(); aggiornaBottone(); aggiornaHint(); aggiornaModo();
});

ricomincia.addEventListener('click',()=>{
  chiudiCam();
  state.origine=null; state.dataUrl=null;
  portaScatto.setAttribute('aria-pressed','false');
  portaArchivio.setAttribute('aria-pressed','false');
  file.value=''; img.removeAttribute('src'); stage.classList.remove('show');
  hint.hidden=true; $('#ora').hidden=true; $('#esito').innerHTML=''; err.hidden=true;
  ricomincia.hidden=true; modo.hidden=true;
  azzeraPunti();
});

// --- cattura in-app (getUserMedia). Il flusso video non lascia la pagina: il
// fotogramma finisce in un canvas locale e da li' nel calcolo, senza rete. ---
const cam=$('#cam'), video=$('#video'), capture=$('#capture'), camClose=$('#camClose');
const camres=$('#camres'), camsel=$('#camsel'), selCam=$('#selCam'), selFormato=$('#selFormato');
let stream=null;
async function apriCam(deviceId){
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    setHint('⚠ fotocamera non disponibile in questo browser: resta la scelta da archivio'); return;
  }
  if(stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; }
  // NIENTE height. Chiedere 1920x1080 a un sensore 4:3 lo fa **ritagliare in
  // verticale**: e' cosi' che si finisce a inquadrare il viso invece della
  // scena intera. Chiediamo larghezza alta e lasciamo che sia il dispositivo a
  // scegliere il formato, che e' quello col campo visivo piu' ampio.
  const vincoli = {width:{ideal:4096}};
  if(deviceId) vincoli.deviceId={exact:deviceId};
  else vincoli.facingMode={ideal:'environment'};
  // Molte webcam hanno il sensore 4:3 e in 16:9 ne usano solo una fascia
  // centrale: chiedere 4:3 restituisce il campo verticale che il 16:9 ritaglia.
  // Su un sensore nativo 16:9 non cambia nulla — per questo si puo' scegliere.
  const f=selFormato.value;
  if(f==='4-3') vincoli.aspectRatio={ideal:4/3};
  else if(f==='16-9') vincoli.aspectRatio={ideal:16/9};

  try{
    stream=await navigator.mediaDevices.getUserMedia({video:vincoli});
    video.srcObject=stream; cam.hidden=false;
    video.addEventListener('loadedmetadata',mostraFotogramma,{once:true});
    await elencaFotocamere();
  }catch(e){ setHint('⚠ fotocamera non disponibile: '+(e.message||e.name)); }
}
selFormato.addEventListener('change',()=>apriCam(selCam.value||undefined));

// La risoluzione ottenuta e quella massima dichiarata dal dispositivo: sono i
// due numeri che dicono se il campo visivo stretto viene dal formato scelto o
// e' semplicemente quello dell'obiettivo.
function mostraFotogramma(){
  let txt=`fotogramma ${video.videoWidth}×${video.videoHeight} px`;
  const track=stream&&stream.getVideoTracks()[0];
  if(track&&track.getCapabilities){
    try{
      const c=track.getCapabilities();
      if(c.width&&c.height) txt+=` · il dispositivo arriva a ${c.width.max}×${c.height.max}`;
    }catch(e){/* getCapabilities non ovunque */}
  }
  camres.textContent=txt;
}

// I nomi delle fotocamere sono leggibili solo dopo il consenso, quindi si
// elencano a stream aperto. Con una sola fotocamera il selettore non serve.
async function elencaFotocamere(){
  if(!navigator.mediaDevices.enumerateDevices) return;
  try{
    const tutti=await navigator.mediaDevices.enumerateDevices();
    const video_in=tutti.filter(d=>d.kind==='videoinput');
    camsel.hidden = video_in.length<2;
    if(video_in.length<2) return;
    selCam.innerHTML=video_in.map((d,i)=>
      `<option value="${d.deviceId}">${d.label||('fotocamera '+(i+1))}</option>`).join('');
    const attiva=stream&&stream.getVideoTracks()[0].getSettings().deviceId;
    if(attiva) selCam.value=attiva;
  }catch(e){ camsel.hidden=true; }
}
selCam.addEventListener('change',()=>apriCam(selCam.value));
function chiudiCam(){
  if(typeof fermaAutoscatto==='function') fermaAutoscatto();
  if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
  cam.hidden=true;
}
camClose.addEventListener('click',chiudiCam);
function scatta(){
  if(!video.videoWidth){ setHint('⚠ la fotocamera non è ancora pronta'); return; }
  const c=document.createElement('canvas');
  c.width=video.videoWidth; c.height=video.videoHeight;
  c.getContext('2d').drawImage(video,0,0);
  const dataUrl=c.toDataURL('image/png');
  chiudiCam();
  // l'origine 'scatto' si scrive QUI, non alla pressione della porta: e' l'unico
  // punto in cui l'app sa di aver catturato lei il fotogramma. Vale anche per
  // l'autoscatto: il fotogramma lo prende sempre l'app, dal proprio stream.
  impostaOrigine('scatto');
  state.dataUrl=dataUrl; img.src=dataUrl;
}
capture.addEventListener('click',scatta);

// Autoscatto: serve dove la fotocamera e' ferma e sei tu a doverti spostare.
// Su un telefono lo tieni in mano, quindi si mostra solo dove il puntatore e'
// fine (mouse), non su touch.
const SECONDI_AUTOSCATTO=15;
const autoscatto=$('#autoscatto'), conto=$('#conto');
let timerScatto=null;
autoscatto.hidden = window.matchMedia('(pointer: coarse)').matches;

autoscatto.addEventListener('click',()=>{
  if(timerScatto){ fermaAutoscatto(); return; }
  let restano=SECONDI_AUTOSCATTO;
  mostraConto(restano);
  autoscatto.textContent='annulla autoscatto';
  timerScatto=setInterval(()=>{
    restano-=1;
    if(restano<=0){ fermaAutoscatto(); scatta(); return; }
    mostraConto(restano);
  },1000);
});
function mostraConto(n){
  conto.hidden=false;
  conto.textContent=n;
  conto.classList.toggle('ultimi', n<=3);
}
function fermaAutoscatto(){
  if(timerScatto){ clearInterval(timerScatto); timerScatto=null; }
  conto.hidden=true; conto.classList.remove('ultimi');
  autoscatto.textContent='Autoscatto '+SECONDI_AUTOSCATTO+' s';
}

function caricaFile(f){
  const r=new FileReader();
  r.onload=()=>{ state.dataUrl=r.result; img.src=r.result; };
  r.readAsDataURL(f);
}
img.addEventListener('load',()=>{
  if(!state.dataUrl) return;
  state.natW=img.naturalWidth; state.natH=img.naturalHeight;
  ov.setAttribute('viewBox',`0 0 ${state.natW} ${state.natH}`);
  stage.classList.add('show');
  azzeraPunti();
  aggiornaModo();
  rilevaAutomatico();
});

// --- rilevamento automatico della tessera -----------------------------------
// Le dimensioni della ID-1 sono note, quindi il riferimento non ha bisogno di
// essere cliccato: si cerca un rettangolo con il rapporto giusto e si fittano i
// suoi quattro lati. E' molto piu' preciso del clic (l'errore scende da ~0,8% a
// ~0,01%) e soprattutto **elimina l'errore degli angoli arrotondati**, che nel
// percorso manuale vale il 3,7% e nessuno si accorge di commettere.
//
// Il candidato migliore viene usato subito, senza chiedere conferma — ma
// l'app mostra sempre **che cosa** ha riconosciuto: il quadrilatero resta
// disegnato e la scheda dichiara la provenienza. Automatico non vuol dire
// silenzioso: se avesse preso un libro al posto della tessera, si vede.
const LATO_MASSIMO_RILEVAMENTO = 1600;
function rilevaAutomatico(){
  if(!window.MisuraRileva || !state.dataUrl) return;
  try{
    const scala = Math.min(1, LATO_MASSIMO_RILEVAMENTO/Math.max(state.natW,state.natH));
    const cw = Math.round(state.natW*scala), ch = Math.round(state.natH*scala);
    const c = document.createElement('canvas');
    c.width=cw; c.height=ch;
    const ctx = c.getContext('2d', {willReadFrequently:true});
    ctx.drawImage(img,0,0,cw,ch);
    const dati = ctx.getImageData(0,0,cw,ch);

    const t0 = performance.now();
    const trovate = window.MisuraRileva.rilevaTessere(dati);
    const ms = Math.round(performance.now()-t0);
    if(!trovate.length){ state.rilevate=[]; aggiornaDiagnostica(); return; }

    // riporta le coordinate alla risoluzione piena
    const k = 1/scala;
    state.rilevate = trovate.slice(0,2).map(t=>({
      vertici: t.vertici.map(v=>[v[0]*k, v[1]*k]),
      estremi: t.estremiLatoLungo.map(v=>[v[0]*k, v[1]*k]),
      latoPx: t.latoLungoPx*k,
      sigmaPx: t.sigmaLatoPx*k,
      deviazione: t.deviazione,
      residuoPx: t.residuoPx*k,
    }));
    state.msRilevamento = ms;

    // il migliore diventa il riferimento A; se serve il secondo e ce n'e' un
    // altro, diventa B — sono due rettangoli distinti, quindi due riferimenti
    // distinti nel senso di §5.3
    state.rifA = state.rilevate[0].estremi.map(p=>p.slice());
    state.rifAauto = state.rilevate[0];
    $('#tipoA').value='id1_lungo'; $('#campoLatoA').style.display='none';
    if(state.doppio && state.rilevate[1]){
      state.rifB = state.rilevate[1].estremi.map(p=>p.slice());
      state.rifBauto = state.rilevate[1];
      $('#tipoB').value='id1_lungo'; $('#campoLatoB').style.display='none';
      state.fase='target';
    } else {
      state.fase = state.doppio ? 'rifB' : 'target';
    }
    render(); aggiornaBottone(); aggiornaHint(); aggiornaModo();
  }catch(e){ /* il rilevamento e' un aiuto: se fallisce restano i clic */ }
}

ov.addEventListener('click',ev=>{
  if(!state.dataUrl) return;
  const r=img.getBoundingClientRect();
  const p=[(ev.clientX-r.left)*state.natW/r.width,(ev.clientY-r.top)*state.natH/r.height];
  const lista = state.fase==='rifA' ? state.rifA : state.fase==='rifB' ? state.rifB : state.punti;
  if(lista.length>=2) lista.length=0;
  lista.push(p);
  // un clic sul riferimento sostituisce il rilevamento: da quel momento la
  // provenienza di quel riferimento e' manuale, con la sigma del clic
  if(state.fase==='rifA') state.rifAauto=null;
  if(state.fase==='rifB') state.rifBauto=null;
  if(lista.length===2){
    if(state.fase==='rifA') state.fase = state.doppio ? 'rifB' : 'target';
    else if(state.fase==='rifB') state.fase = 'target';
  }
  render(); aggiornaBottone(); aggiornaHint(); aggiornaModo();
});

reset.addEventListener('click',azzeraPunti);

function azzeraPunti(){
  state.rifA=[]; state.rifB=[]; state.punti=[]; state.fase='rifA';
  state.rifAauto=null; state.rifBauto=null; state.rilevate=[];
  $('#esito').innerHTML=''; err.hidden=true;
  render(); aggiornaBottone(); aggiornaHint();
}

function aggiornaBottone(){
  const rifPronti = state.rifA.length===2 && (!state.doppio || state.rifB.length===2);
  btn.disabled = !(state.dataUrl && rifPronti && state.punti.length===2);
  // il bottone dice cosa sta per succedere: dove la certificata era possibile e
  // non lo e' piu', non produce un numero ma l'offerta esplicita di degrado
  btn.textContent = richiedeDegrado() ? 'Prosegui in stima…' : 'Misura';
  reset.hidden = !(state.rifA.length || state.rifB.length || state.punti.length);

  // un bottone disabilitato senza spiegazione e' un vicolo cieco: dice cosa manca
  const manca=[];
  if(!state.dataUrl) manca.push("un'immagine");
  if(state.rifA.length<2) manca.push('i 2 clic sul riferimento A');
  if(state.doppio && state.rifB.length<2) manca.push('i 2 clic sul riferimento B');
  if(state.punti.length<2) manca.push("i 2 clic sull'oggetto da misurare");
  const nodo=$('#manca');
  nodo.hidden = manca.length===0;
  if(manca.length) nodo.innerHTML='Manca ancora: <b>'+manca.join('</b>, <b>')+'</b>.';
  aggiornaPassi();
}

// Barra dei passi: dove sei nel percorso, e cosa e' gia' fatto.
function aggiornaPassi(){
  const fatto = {
    immagine: !!state.dataUrl,
    rifA: state.rifA.length===2,
    rifB: state.doppio && state.rifB.length===2,
    target: state.punti.length===2,
    misura: !!$('#esito').querySelector('.card'),
  };
  const corrente = !state.dataUrl ? 'immagine'
    : state.fase==='rifA' ? 'rifA'
    : state.fase==='rifB' ? 'rifB'
    : state.punti.length<2 ? 'target' : 'misura';

  $('#passi').querySelectorAll('li').forEach(li=>{
    const p=li.dataset.p;
    li.className = p==='rifB' && !state.doppio ? 'saltato'
      : fatto[p] && p!==corrente ? 'fatto'
      : p===corrente ? 'corrente' : '';
    li.querySelector('.n').textContent = (li.className==='fatto') ? '✓'
      : ({immagine:'1',rifA:'2',rifB:'3',target:'4',misura:'5'})[p];
  });
}

function descrizioneRif(sel){
  const t=$(sel).value;
  if(t==='id1_lungo') return 'lato lungo della tessera · 85,60 mm';
  if(t==='id1_corto') return 'lato corto della tessera · 53,98 mm';
  return 'la dimensione nota che hai indicato';
}
// L'istruzione del momento, grande e sopra l'immagine. Il pallino ha il colore
// dei punti che stai per mettere, cosi' il legame col disegno e' immediato.
const ora=$('#ora'), oraT=$('#oraT'), oraS=$('#oraS'), oraPallino=$('#oraPallino'), oraAzione=$('#oraAzione');
function aggiornaHint(){
  if(!state.dataUrl){ ora.hidden=true; return; }
  ora.hidden=false; oraAzione.hidden=true;

  if(state.fase==='rifA'){
    oraPallino.style.background=colore('--accent');
    oraT.textContent='Clicca i 2 estremi del riferimento A';
    oraS.textContent='I due punti che delimitano '+descrizioneRif('#tipoA')+'. Clicca il più precisamente possibile: da questa distanza in pixel nasce tutta la scala.';
  } else if(state.fase==='rifB'){
    oraPallino.style.background=colore('--rifb');
    oraT.textContent='Clicca i 2 estremi del riferimento B';
    oraS.textContent='Dev\'essere un oggetto distinto dal primo — non l\'altro lato della stessa tessera, che condividerebbe piano e distorsione e concorderebbe anche sbagliando.';
    oraAzione.hidden=false;
    oraAzione.textContent='ne ho uno solo';
    oraAzione.onclick=()=>{ chkDoppio.checked=false; chkDoppio.dispatchEvent(new Event('change')); };
  } else {
    oraPallino.style.background=colore('--warn');
    oraT.textContent='Clicca i 2 estremi dell\'oggetto da misurare';
    oraS.textContent='La misura che ti serve, sullo stesso piano del riferimento. Poi premi il bottone in fondo.';
    if(state.punti.length===2){
      oraT.textContent='Tutto pronto: premi Misura';
      oraS.textContent='Puoi ancora correggere qualsiasi punto ricliccando, o azzerare tutto.';
    }
  }
}

// il campo "dimensione (mm)" esiste solo dove serve: per i formati normati la
// dimensione non si digita, e' quella e basta
function legaTipo(sel,campo){
  $(sel).addEventListener('change',()=>{
    $(campo).style.display = $(sel).value==='personalizzato' ? 'block' : 'none';
    aggiornaHint();
  });
}
legaTipo('#tipoA','#campoLatoA');
legaTipo('#tipoB','#campoLatoB');

function colore(nome){
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}
function segmento(punti,col,tratteggio){
  const r=state.natW*0.006+2;
  let s='';
  if(punti.length===2){ const[a,b]=punti;
    const d=tratteggio?` stroke-dasharray="${r*1.5} ${r}"`:'';
    s+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${col}" stroke-width="${r*0.5}"${d}/>`; }
  punti.forEach(p=>{ s+=`<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${col}" stroke="#fff" stroke-width="${r*0.35}"/>`; });
  return s;
}
function quadrilatero(q,col){
  if(!q) return '';
  const r=state.natW*0.006+2;
  const pts=q.vertici.map(v=>v.join(',')).join(' ');
  return `<polygon points="${pts}" fill="${col}" fill-opacity="0.10" stroke="${col}" `
    +`stroke-width="${r*0.3}" stroke-dasharray="${r*1.2} ${r*0.8}"/>`;
}
function render(){
  ov.innerHTML = quadrilatero(state.rifAauto, colore('--accent'))
               + quadrilatero(state.rifBauto, colore('--rifb'))
               + segmento(state.rifA, colore('--accent'), false)
               + segmento(state.rifB, colore('--rifb'), false)
               + segmento(state.punti, colore('--warn'), true);
  aggiornaDiagnostica();
}

// Quanti pixel misura ogni riferimento, e **quanto costa** in incertezza.
// Non c'e' una soglia inventata: il contributo e' semplicemente sigma/lato, il
// numero che poi entra davvero nel calcolo. Un riferimento piccolo nel
// fotogramma trasferisce il suo errore relativo tale e quale all'oggetto (§5.2),
// e questa riga e' il modo di vederlo prima di misurare, non dopo.
const SIGMA_CLIC_RIFERIMENTO_PX = 2.5;  // lo stesso default del core
function aggiornaDiagnostica(){
  const diag=$('#diag');
  const righe=[];
  const info=(nome,punti,col,auto)=>{
    if(punti.length!==2) return;
    const px=lungPx(...punti);
    const sigma = auto ? auto.sigmaPx : SIGMA_CLIC_RIFERIMENTO_PX;
    const rel=px>0 ? (sigma/px)*100 : 0;
    const fonte = auto
      ? `<span class="tag">rilevato · rapporto a ${(auto.deviazione*100).toFixed(2)}% da 1,586</span>`
      : '<span class="tag">cliccato</span>';
    righe.push(`<div class="r"><span class="puntino" style="background:${col}"></span>`
      +`${nome} <b>${px.toFixed(0)} px</b> → la scala eredita <b>±${rel.toFixed(rel<0.1?3:2)}%</b> `
      +`dalla localizzazione ${fonte}</div>`);
  };
  info('Riferimento A', state.rifA, colore('--accent'), state.rifAauto);
  info('Riferimento B', state.rifB, colore('--rifb'), state.rifBauto);
  if(state.punti.length===2)
    righe.push(`<div class="r"><span class="puntino" style="background:${colore('--warn')}"></span>`
      +`Oggetto <b>${lungPx(...state.punti).toFixed(0)} px</b></div>`);

  if(righe.length){
    const auto = state.rifAauto || state.rifBauto;
    righe.push('<div class="nota">'
      + (auto ? 'Il riferimento rilevato è localizzato sui bordi con precisione sub-pixel, e il vertice nasce dall'intersezione dei lati: gli angoli arrotondati non falsano più la misura. '
              : 'σ 2,5 px sul clic del riferimento. ')
      + 'Più pixel occupa il riferimento, meno incertezza porta: avvicinati, o usane uno più grande.</div>');
  }

  diag.innerHTML=righe.join('');
  diag.hidden = righe.length===0;
}
function setHint(a,b){ hint.hidden=false; hint.innerHTML = a + (b?` <span class="tag">${b}</span>`:''); }

// --- dichiarazione di modalita': sempre visibile, sempre PRIMA di misurare ---
// La transizione fra le due modalita' non e' mai automatica (§4.1). Qui non c'e'
// nemmeno una transizione: c'e' una constatazione, dichiarata prima del calcolo,
// di quale modalita' le condizioni attuali sostengono.
function modalitaCorrente(){
  return (state.origine==='scatto' && state.doppio) ? 'certificata' : 'stima';
}
function riga(stato,testo,nota){
  return `<li class="${stato}">${testo}${nota?` <span class="tag">${nota}</span>`:''}</li>`;
}
function aggiornaModo(esito){
  if(!state.origine){ modo.hidden=true; return; }
  modo.hidden=false;
  const cert = modalitaCorrente()==='certificata';
  const rifiutata = esito && esito.tipo==='RifiutoMotivato';
  const etichetta = cert ? '<span class="chip cert">Certificata</span>' : '<span class="chip stima">Stima</span>';
  modoT.innerHTML = rifiutata
    ? etichetta + '<span>tentata, ma la verifica non è passata: nessuna misura</span>'
    : etichetta + `<span>misurerà in modalità ${cert?'certificata':'stima'}</span>`;
  modoP.textContent = rifiutata
    ? "Le due scale non concordano: una delle due è sbagliata e l'app non può sapere quale. Correggi i riferimenti — devono essere oggetti distinti, di dimensione davvero nota, appoggiati sul piano che stai misurando — e rimisura."
    : cert
    ? "Certificata qui significa: acquisizione live catturata dall'app e due riferimenti distinti le cui scale concordano. Non promette l'1% — quello richiederebbe anche cattura guidata e un profilo di calibrazione per modello di dispositivo."
    : (state.origine==='archivio'
        ? "L'immagine viene dall'archivio: l'app non può affermare come e quando è stata scattata, quindi per questa immagine la modalità certificata non è disponibile."
        : "Hai scattato in-app, ma con un solo riferimento non c'è nulla da confrontare: senza quella verifica la misura resta una stima.");

  let h = riga(state.origine==='scatto'?'si':'no',
               'Acquisizione live, catturata dall\'app',
               state.origine==='scatto'?null:'immagine da archivio');
  h += riga(state.doppio?'si':'no',
            'Due riferimenti su oggetti distinti',
            state.doppio?null:'un solo riferimento');
  if(esito && esito.verifica_doppio_riferimento==='superata')
    h += riga('si','Le due scale concordano',`divergenza ${esito.divergenza_mm_px} ≤ soglia ${esito.soglia_mm_px} mm/px`);
  else if(esito && esito.tipo==='RifiutoMotivato' && esito.divergenza_mm_px)
    h += riga('no','Le due scale concordano',`divergenza ${esito.divergenza_mm_px} > soglia ${esito.soglia_mm_px} mm/px`);
  else
    h += riga(state.doppio?'attesa':'no','Le due scale concordano',
              state.doppio?'si verifica al momento della misura':'non verificabile con un solo riferimento');
  cond.innerHTML=h;
}

// Il calcolo e' interamente CLIENT-ONLY: `core.js`, nessuna richiesta di rete,
// nessun server. L'immagine non lascia il dispositivo perche' non va da nessuna
// parte — non perche' qualcuno promette di non guardarla.
// dichiarata, non `const`: viene usata anche dalla diagnostica, che sta più su
function lungPx(a,b){ return Math.hypot(b[0]-a[0],b[1]-a[1]); }

function optsSingolo(){
  return { tipo:$('#tipoA').value, latoPersonalizzato:parseFloat($('#latoA').value),
    latoRifPx:lungPx(...state.rifA), latoTargetPx:lungPx(...state.punti),
    sigmaRifPx: state.rifAauto ? state.rifAauto.sigmaPx : 2.5,
    sigmaSegPx:parseFloat($('#sigmaseg').value), tolleranzaMm:parseFloat($('#tolreq').value) };
}

// Il degrado esiste solo dove c'e' qualcosa da cui degradare. Con un'immagine
// d'archivio la stima e' la modalita' NATIVA (§4.1) e chiedere conferma sarebbe
// un avviso mostrato sempre — cioe' un avviso ignorato sempre (§4.3).
function richiedeDegrado(){
  return state.origine==='scatto' && !state.doppio;
}

// Offerta esplicita di degrado: mostra l'incertezza della stima **calcolata
// davvero** su questa configurazione, non una penalita' forfettaria, e non
// consegna nessun valore finche' l'utente non ha accettato.
function mostraOffertaDegrado(){
  const opts=optsSingolo();
  let prova;
  try{ prova=window.MisuraCore.misuraManuale(opts); }
  catch(e){ err.hidden=false; err.textContent=e.message||String(e); return; }

  const box=$('#esito');
  box.innerHTML=`<div class="card warn no-number">
    <div class="card-head"><span class="pill warn"><span class="dot"></span>Condizioni non piene</span><span class="chip cert">Certificata</span></div>
    <div class="refusal">La modalità certificata non è disponibile: manca il secondo riferimento.</div>
    <p class="whisper">Hai scattato in-app, ma con un solo riferimento non c'è nulla da confrontare: la verifica delle due scale non può essere fatta, e senza quella la misura è una stima.</p>
    <div class="meta">
      <div><div class="k">Incertezza se accetti la stima</div><div class="v">± ${prova.incertezza_espansa_mm.toFixed(1)} mm (k=2)</div></div>
      <div><div class="k">Tolleranza richiesta</div><div class="v">± ${prova.tolleranza_mm.toFixed(1)} mm</div></div>
      <div><div class="k">Esito che ne uscirebbe</div><div class="v">${prova.tipo==='EntroTolleranza'?'entro tolleranza':'fuori tolleranza'}</div></div>
    </div>
    <div class="cam-actions">
      <button class="go" id="accettaStima">Accetta la stima e misura</button>
      <button class="ghost" id="completaVerifica">Aggiungi il secondo riferimento</button>
    </div></div>`;

  $('#accettaStima').addEventListener('click',()=>{
    const conferma=window.MisuraCore.ConfermaUtente(
      'secondo riferimento assente: l\'utente ha accettato la stima al posto della certificata');
    const esito=window.MisuraCore.misuraDegradataAStima(opts, conferma);
    renderEsito(esito); aggiornaModo(esito);
  });
  $('#completaVerifica').addEventListener('click',()=>{
    chkDoppio.checked=true;
    chkDoppio.dispatchEvent(new Event('change'));
    box.innerHTML='';
  });
  box.scrollIntoView({behavior:'smooth',block:'nearest'});
}

btn.addEventListener('click',()=>{
  err.hidden=true;
  if(richiedeDegrado()){ mostraOffertaDegrado(); return; }
  const tolleranzaMm=parseFloat($('#tolreq').value);
  const sigmaSegPx=parseFloat($('#sigmaseg').value);
  let esito;
  try{
    if(state.doppio){
      esito=window.MisuraCore.misuraDoppioRiferimento({
        tipoA:$('#tipoA').value, latoPersonalizzatoA:parseFloat($('#latoA').value),
        latoRifAPx:lungPx(...state.rifA),
        tipoB:$('#tipoB').value, latoPersonalizzatoB:parseFloat($('#latoB').value),
        latoRifBPx:lungPx(...state.rifB),
        sigmaRifAPx: state.rifAauto ? state.rifAauto.sigmaPx : 2.5,
        sigmaRifBPx: state.rifBauto ? state.rifBauto.sigmaPx : 2.5,
        latoTargetPx:lungPx(...state.punti), sigmaSegPx, tolleranzaMm });
    } else {
      esito=window.MisuraCore.misuraManuale({
        tipo:$('#tipoA').value, latoPersonalizzato:parseFloat($('#latoA').value),
        latoRifPx:lungPx(...state.rifA),
        sigmaRifPx: state.rifAauto ? state.rifAauto.sigmaPx : 2.5,
        latoTargetPx:lungPx(...state.punti), sigmaSegPx, tolleranzaMm });
    }
  }catch(e){ err.hidden=false; err.textContent=e.message||String(e); return; }
  esito.modalita=modalitaCorrente();
  renderEsito(esito);
  aggiornaModo(esito);
});

function gauge(U,T){ const m=Math.max(T,U)*1.3; return {b:50-T/m*50, u:50-U/m*50}; }
function renderEsito(d){
  const modChip = d.modalita==='certificata'?'<span class="chip cert">Certificata</span>':'<span class="chip stima">Stima</span>';
  const box=$('#esito'); let h='';
  if(d.tipo==='RifiutoMotivato'){
    const verifica = d.divergenza_mm_px
      ? `<div class="meta"><div><div class="k">Divergenza fra le due scale</div><div class="v">${d.divergenza_mm_px} mm/px</div></div>
         <div><div class="k">Soglia di compatibilità (k=2)</div><div class="v">${d.soglia_mm_px} mm/px</div></div></div>` : '';
    h=`<div class="card crit no-number"><div class="card-head"><span class="pill crit"><span class="dot"></span>Non misurabile</span>${modChip}</div>
      <div class="readout"><span class="val">—</span></div>
      <div class="refusal">Nessun numero difendibile.</div>
      <div class="callout crit"><span class="ic">!</span><span>${d.motivo}</span></div>${verifica}</div>`;
  } else {
    const good=d.tipo==='EntroTolleranza', cls=good?'good':'warn';
    const g=gauge(d.incertezza_espansa_mm,d.tolleranza_mm);
    const gc=good?'var(--good)':'var(--warn)';
    h=`<div class="card ${cls}" style="--band-l:${g.b}%;--band-r:${g.b}%;--u-l:${g.u}%;--u-r:${g.u}%;">
      <div class="card-head"><span class="pill ${cls}"><span class="dot"></span>${good?'Entro tolleranza':'Fuori tolleranza'}</span>${modChip}</div>
      <div class="readout"><span class="val">${d.valore_mm.toFixed(1)}</span><span class="unit">mm</span><span class="pm">± ${d.incertezza_espansa_mm.toFixed(1)}</span></div>
      <p class="whisper">± ${d.incertezza_espansa_mm.toFixed(1)} mm è l'incertezza espansa (k=2, ~95%) — parte del dato, non della schermata.</p>
      <div class="gauge"><div class="track"><div class="band"></div><div class="center"></div><div class="bracket"></div></div>
        <div class="legend"><span><span style="display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;background:color-mix(in srgb,${gc} 26%,transparent);border:1.5px solid ${gc}"></span>incertezza <b>±${d.incertezza_espansa_mm.toFixed(1)}</b></span>
        <span>tolleranza richiesta <b>±${d.tolleranza_mm.toFixed(1)}</b></span></div></div>`;
    if(!good) h+=`<div class="callout"><span class="ic">→</span><span>${d.come_migliorare}</span></div>`;
    h+=`<div class="meta"><div><div class="k">Provenienza</div><div class="v">${d.provenienza}</div></div>
      <div><div class="k">Scala</div><div class="v">${d.scala_mm_px} ± ${d.scala_inc_mm_px} mm/px</div></div>
      <div><div class="k">Target</div><div class="v">${d.lato_target_px} px</div></div>`;
    // che la verifica sia stata superata e' un'informazione SUL DATO: e' cio' che
    // distingue una scala verificata da una semplicemente dichiarata
    if(d.verifica_doppio_riferimento==='superata')
      h+=`<div><div class="k">Doppio riferimento</div><div class="v">verificato · ${d.divergenza_mm_px} ≤ ${d.soglia_mm_px} mm/px</div></div>`;
    // la transizione di modalita' viaggia col dato, come l'incertezza (§4.3):
    // sopravvive allo screenshot e al copia-incolla
    if(d.degradata_da)
      h+=`<div><div class="k">Transizione di modalità</div><div class="v">da certificata a stima, su conferma esplicita</div></div>`;
    h+=`</div></div>`;
  }
  box.innerHTML=h; box.scrollIntoView({behavior:'smooth',block:'nearest'});
}

// --- router a hash + navigazione tra schermi ---
const schermi={home:'screen-home',oggetto:'screen-oggetto',corpo:'screen-corpo'};
const navback=$('#navback'), navtitle=$('#navtitle');
const titoli={home:'app-misurazione',oggetto:'Misura oggetto',corpo:'Misure corporee'};
function vai(nome){ location.hash = nome==='home' ? '' : '#/'+nome; }
function mostra(){
  const richiesto=(location.hash.replace('#/','')||'home');
  const attivo=schermi[richiesto]?richiesto:'home';
  Object.entries(schermi).forEach(([k,id])=>{ document.getElementById(id).hidden=(k!==attivo); });
  navback.hidden=(attivo==='home');
  navtitle.textContent=titoli[attivo];
  window.scrollTo(0,0);
}
window.addEventListener('hashchange',mostra);
navback.addEventListener('click',()=>vai('home'));
document.querySelectorAll('.task[data-go]').forEach(b=>b.addEventListener('click',()=>vai(b.dataset.go)));
mostra();

// --- service worker: offline, nessuna rete a runtime ---
if('serviceWorker' in navigator){ navigator.serviceWorker.register('/sw.js').catch(()=>{}); }
