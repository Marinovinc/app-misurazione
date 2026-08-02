# misura — nucleo metrologico + app

**App online:** <https://marinovinc.github.io/app-misurazione/>

Client-only: il calcolo gira nel browser, **nessuna immagine lascia il
dispositivo** — non perché qualcuno prometta di non guardarla, ma perché non
esiste un server a cui possa arrivare. Funziona offline dopo la prima visita.

Cosa fa: misura un oggetto **piatto** partendo da un riferimento di dimensione
nota nella stessa foto (una tessera ID-1 — bancomat, fedeltà — viene
riconosciuta da sola). Ogni valore esce con la sua **incertezza** e la sua
**provenienza**, e quando la scala non è verificabile non esce nessun numero.

**Limiti dichiarati.** La misura vale per ciò che giace sul **piano del
riferimento**: un riferimento tenuto in mano, o più vicino alla fotocamera
dell'oggetto, produce un errore sistematico di qualche percento che nessuna
incertezza dichiarata cattura. La modalità «certificata» qui significa
acquisizione live in-app più due riferimenti distinti le cui scale concordano —
**non** promette l'1%, che richiederebbe anche cattura guidata e un profilo di
calibrazione per modello di dispositivo. L'incertezza dichiarata **non è ancora
calibrata** su un campione reale. Non idonea a fatturazione o usi con valore
legale.

## Aggiornare il sito

```bash
bash pubblica.sh
```

Ricostruisce il branch `gh-pages` dai file statici di `app/`, dopo aver
verificato il gate.

Nucleo per ricavare misure da immagini in cui **l'incertezza e la provenienza sono di prima
classe**: nessun numero secco, ogni misura porta con sé la sua incertezza e la sua origine.

La fase 0 costruisce solo il cuore metrologico, indipendente dal verticale. Nessuna AI, nessuna
cattura, nessuna UI. Vedi [docs/piano-fase0.md](docs/piano-fase0.md).

## Sviluppo

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest
.venv/Scripts/python -m mypy
```

Report del banco sintetico:

```bash
.venv/Scripts/python -m misura.validazione.banco
```

## App locale interattiva (fase 1)

Prima UI sopra il nucleo: carichi una foto con un marker ArUco, clicchi i due
estremi del target, e la misura viene calcolata dal vivo con incertezza ed esito.

```bash
.venv/Scripts/python -m pip install -e ".[app]"
.venv/Scripts/python app/server.py
# apri http://127.0.0.1:5000
```

Il riferimento ArUco e' rilevato davvero; i bordi del target sono i due click (la
segmentazione automatica e' fase successiva). Nessun dato lascia la macchina.

## Nota di onestà (fase 0)

Il banco sintetico verifica che la **propagazione dell'incertezza sia implementata
correttamente**, non che il modello descriva la realtà. La validazione vera richiede un dataset
reale misurato al calibro (questione aperta #3 del concept).
