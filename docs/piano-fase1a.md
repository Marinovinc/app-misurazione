# Piano fase 1a — Guscio dell'app e manichino

**Stato:** approvato (piano + lettura della degradazione). Il core di fase 0 e' la
fonte di verita': questa app lo usa, non lo duplica.
**Riferimento:** `concept-app-misurazione.md` v1.2 (§9, §10, §13), `docs/piano-fase0.md`.

## Cosa dimostra questa fase

Il flusso end-to-end navigabile e l'interazione col manichino, con ogni numero
dichiarato per quello che e'. **Non** dimostra che sappiamo misurare il corpo:
quella capacita' non esiste (questione aperta #2) e non va simulata.

## Vincoli assoluti

**Nessun numero inventato.** Il core misura contorni planari con riferimento; non
estrae circonferenze corporee. Quindi: nessuna misura corporea prodotta dall'app;
campi senza fonte **vuoti e visibilmente vuoti**; fonti ammesse solo (a) core su
oggetti planari con riferimento, (b) input manuale marcato; **provenienza visibile**
su ogni valore (§9.4), non in tooltip.

**Tutto on-device / niente rete.** Nessuna immagine lascia il dispositivo; niente
telemetria/analytics/crash reporting; niente account/login/persistenza remota.
Ogni libreria che fa rete va segnalata prima di aggiungerla (#7 bloccante, non
decisa: costruire il cloud significherebbe deciderla senza deciderla).

## Stack (confermato)

- **Frontend:** SPA vanilla a moduli ES + router a hash + piccolo store. Nessuna
  toolchain npm; servito dal Flask esistente, esteso.
- **3D:** Three.js **vendorizzato in locale** (nessun CDN a runtime).
- **Core:** servizio Flask locale (fase 0/1). L'app lo usa.
- **PWA:** manifest + service worker (offline, rafforza il "nulla esce").
- **On-device:** tenuto aperto, non costruito. Il core si divide in incertezza/
  fusione/esito (Python+numpy, portabile/Pyodide) e rilevamento ArUco (opencv, il
  pezzo nativo). Punto debole del web = on-device del rilevamento (Pyodide-opencv
  incerto, uscita: ArUco in JS). Fase successiva.

## Revisione del 1 agosto 2026 (decisioni prese in corso d'opera)

Tre scelte scostano da quanto scritto sotto, e prevalgono:

1. **"Certificata" ridefinita sul doppio riferimento.** Le quattro condizioni di
   §3.3 per l'1% (planare, riferimento complanare, cattura guidata, profilo di
   calibrazione per dispositivo) non sono soddisfacibili col clic manuale: gia'
   il solo riferimento, cliccato a mano su ~300 px, porta un errore relativo
   dello 0,8%. Nell'app a clic **certificata significa: acquisizione live
   catturata dall'app + due riferimenti su oggetti distinti + scale concordi**,
   e la UI dichiara esplicitamente che **non promette l'1%**.
   `ModalitaCertificata.tolleranza_relativa_obiettivo` resta invariata nel core:
   e' un attributo del dominio, non un'affermazione dell'interfaccia.
2. **ArUco fuori dall'interfaccia.** L'app e' interamente client-only, cosi'
   com'e' pubblicabile. Gli endpoint `/api/analizza` e `/api/misura` restano
   come strumento di sviluppo e validazione, con i loro test.
3. **Doppio riferimento anticipato** ai passi 2-3, perche' e' la condizione che
   rende possibile la certificata ridefinita.

## Le quattro schermate

1. **Scelta compito** — due voci oneste: *Misura oggetto planare* (usa il core) e
   *Misure corporee* (→ manichino a input manuale). Niente verticali inesistenti (#5).
2. **Acquisizione** — fotocamera → percorso **certificata** (riferimento obbligatorio);
   galleria → percorso **stima** (§4.1). **Nessuna transizione automatica di modalita'.**
3. **Risultato** — scheda a tre esiti, incertezza espansa k=2 dichiarata.
4. **Manichino** — stilizzato **neutro fisso** (non morfato dai dati), con linee di misura.

## Regola di degrado (lettura confermata)

Il core ricava la scala **solo** dal riferimento (niente IMU/depth). Quindi:

- Riferimento **assente** → vicolo cieco onesto in **entrambe** le modalita', nessun
  numero. La transizione resta comunque esplicita.
- Riferimento **presente** ma condizioni della certificata non piene (non complanare,
  singolo dove ne servirebbero due §5.3) → offerta esplicita "degrada a stima",
  mostrando l'incertezza piu' larga **calcolata davvero**. Mai automatica.

## Manichino (dettaglio)

- Linee **spostabili** = punto di misura (§10); la geometria **non emette valori**.
- Interazione **bidirezionale** corpo↔lista.
- Misura = `{valore, incertezza, provenienza}` **oppure vuota**; badge provenienza
  visibile; distinzione visiva misurato/manuale/interpolato.
- Correzione manuale marcata; input manuale = osservazione con incertezza §9.2
  (automisura non guidata ±40 mm, §9.1). Non verita'.
- Predisposto perche' la fonte diventi il modello parametrico (#2) senza rifare il
  manichino.

## Contratti dati verso il core

- **Oggetto:** riusa `/api/analizza` + `/api/misura`. Nessun numero corporeo passa di qui.
- **Corpo:** **nessuna chiamata al core.** Solo osservazioni manuali tipizzate lato client.

## Passi (un commit ciascuno; gate del core invariato)

0. **[fatto]** **Parita' `core.js` <-> core Python nel gate** (`tests/test_parita_js.py`,
   node esegue il core JS sugli stessi ingressi). Ha subito trovato una
   divergenza: `|| 2.5` al posto di `?? 2.5` sostituiva una sigma dichiarata a
   zero col default, gonfiando l'incertezza di un fattore 12.
1. **[fatto]** **Guscio SPA + router + PWA** (manifest, service worker offline).
2. **[fatto]** **Screen 1–2–3** sul percorso oggetto, con **acquisizione a due
   porte**: la modalita' non e' piu' una voce che l'utente sceglie, e' derivata
   dalle condizioni e dichiarata prima di misurare. Include il **doppio
   riferimento** (§5.3) nel core Python e nel port JS.
3. **[fatto]** **Regola di degrado esplicita** (`degrada_a_stima`): l'incertezza
   della stima calcolata davvero, e nessun valore prima della conferma.
4. **Manichino Three.js** neutro + linee posizionabili + interazione bidirezionale.
   Tre varianti da creare **noi** (uomo, donna, bambino); riferimento visivo
   indicato: `app.pickandpose.com`, piu' stilizzato. Posa articolabile ammessa
   (e' visualizzazione); morfologia morfata sui dati dell'utente **no**, e la
   geometria non emette valori.
5. **Modello misura** con provenienza/incertezza, input manuale §9.2, correzione, stati vuoti.
6. **Distinzione visiva** misurato/manuale/interpolato + badge provenienza.

Nessuna misura corporea prodotta in nessun passo.
