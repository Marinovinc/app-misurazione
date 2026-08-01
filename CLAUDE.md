# app-misurazione — contesto di progetto

Comunicazione e documentazione **in italiano**.

## Cos'è

Nucleo metrologico + app: misure da immagini con **incertezza e provenienza di
prima classe**. Il numero non esiste mai da solo. Spec: `concept-app-misurazione.md` (v1.2).

## Vincoli non negoziabili (leggere prima di scrivere codice)

- **NESSUN NUMERO INVENTATO.** Un campo senza fonte reale resta **vuoto**. Mai un
  valore di riempimento, nemmeno in demo o negli screenshot. Se una schermata
  "funziona" solo riempiendo campi senza fonte, fermati e segnalalo.
- **NESSUNA MISURA CORPOREA prodotta dall'app.** Il core misura contorni planari
  con riferimento; **non** estrae circonferenze/altezze dal corpo (serve il
  modello parametrico, questione aperta #2, non risolta). Il corpo è **solo input
  manuale** dell'utente, marcato come tale, con la sua incertezza (§9.2, automisura
  ±40 mm). Le foto del corpo non producono numeri.
- **Provenienza visibile su ogni valore** (§9.4) e **incertezza col dato** (§4.3),
  non in un tooltip.
- **Due modalità** (certificata/stima) sono **tipi distinti**; la transizione non
  è mai automatica (serve un'azione esplicita dell'utente).
- **On-device:** nessuna immagine lascia il dispositivo; niente rete a runtime,
  telemetria, analytics, account. Segnalare ogni libreria che fa rete.

## Struttura e come si esegue

- Progetto in `C:\Users\marin\Progetti\app-misurazione` (git repo). Python venv in `.venv`.
- **Gate (deve restare verde):**
  `.venv\Scripts\python -m mypy` (strict, pulito) e `.venv\Scripts\python -m pytest`.
- **Core Python** `src/misura/` — fonte di verità (fase 0). **Banco:** `.venv\Scripts\python -m misura.validazione.banco`.
- **App locale** `.venv\Scripts\python app\server.py` → http://localhost:5000 (Flask, dev; ArUco via opencv).
- **Core JS client-only** `app/core.js` — port del percorso manuale; **deve coincidere numericamente col core Python**.

## Architettura (tre strati)

1. **Core Python** (`src/misura/`): incertezza affine a sorgenti condivise, fusione
   GLS, esito a tre, riferimento ArUco, banco sintetico. mypy strict, property test.
2. **App Flask** (`app/`): UI. Percorso ArUco → server (opencv). Percorso a **clic
   manuale** → calcolo **client-only** con `core.js`, nessun server.
3. **Core JS** (`app/core.js`): rispecchia il Python per il percorso manuale.

## Stato

- **Fase 0: COMPLETA** — nucleo verde, `docs/report-fase0.md`, `docs/piano-fase0.md`.
- **Dataset ground-truth**: struttura in `dataset/`, protocollo `docs/protocollo-validazione.md`
  (JSON in git, **niente database**; il DB è riservato al ciclo di apprendimento §9.4).
- **Fase 1a** (piano approvato `docs/piano-fase1a.md`): **fatti** — passo 1 (guscio SPA
  + router + PWA), riferimento a **clic manuale** (carta ID-1 85,60 mm / righello),
  **core JS client-only**. **Da fare** — passo 2 (acquisizione fotocamera/galleria →
  modalità certificata/stima), passo 3 (regola di degrado esplicita), passo 4
  (**manichino Three.js** stilizzato neutro fisso, input manuale), passi 5–6
  (modello misura con provenienza/incertezza, distinzione visiva misurato/manuale/interpolato).

## Pubblicazione (modello famiglia)

Client-only (HTML/CSS/JS, nessun backend) → repo GitHub **Marinovinc** → **GitHub
Pages** → **PWA**. Guida completa: `D:\Dev\PUBBLICAZIONE_APP_GUIDA.md`.
Obiettivo per app-misurazione: **versione solo-clic client-only pubblicabile** (il
core JS `app/core.js` è la base; l'ArUco automatico eventualmente con libreria JS).
Convenzioni: **limiti dichiarati** in UI e guida, **service worker versionato**
(nome cache = versione), file di lavoro con prefisso `_` (ignorati da git), test
**Playwright WebKit**, verifica sul **sito live** dopo il push.

## Riferimenti

`concept-app-misurazione.md` (spec, v1.2) · `docs/piano-fase0.md` ·
`docs/report-fase0.md` · `docs/piano-fase1a.md` · `docs/protocollo-validazione.md` ·
`esempi/demo.py`, `esempi/genera_campione.py`, `esempi/genera_marker.py`.
