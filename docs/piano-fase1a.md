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

1. **Guscio SPA + router + PWA** (manifest, service worker offline).
2. **Screen 1–2–3** sul percorso oggetto, riusando il core.
3. **Regola di degrado esplicita** (l'incertezza-stima calcolata quando un riferimento c'e').
4. **Manichino Three.js** neutro + linee posizionabili + interazione bidirezionale.
5. **Modello misura** con provenienza/incertezza, input manuale §9.2, correzione, stati vuoti.
6. **Distinzione visiva** misurato/manuale/interpolato + badge provenienza.

Nessuna misura corporea prodotta in nessun passo.
