# Dataset ground-truth (questione aperta #3)

Struttura pronta ad accogliere il dataset reale di oggetti a dimensione nota
misurati al calibro, con cui si calibra e valida l'incertezza dichiarata (§7.2).
Finche' e' vuoto, il protocollo non ha nulla da validare — ed e' corretto cosi'.

## Layout

```
dataset/
  campioni/           # un JSON per campione (schema: dataset.py)
  immagini/           # le immagini referenziate da percorso_immagine
  template-campione.json   # modello da copiare in campioni/ (non caricato)
```

I file in `campioni/` con nome che inizia per `_` sono ignorati dal caricatore.

## Aggiungere un campione

1. Scatta l'immagine con il **riferimento** ArUco visibile e complanare al target,
   e salvala in `immagini/`.
2. Misura il target al **calibro** (il vero, con la sua incertezza).
3. Annota gli **estremi del target** in pixel (due punti).
4. Copia `template-campione.json` in `campioni/<id>.json` e compilalo.

## Eseguire il protocollo

```bash
.venv/Scripts/python -m misura.validazione.protocollo
```

Riporta la **percentuale di misure entro tolleranza** (criterio di accettazione
§7.2) e la copertura dell'incertezza dichiarata.

## Nota

Le immagini reali di persone o oggetti non vanno versionate alla leggera: valgono
le considerazioni GDPR della §13 del concept. Questa cartella e' pensata per
campioni di test (oggetti, non corpi); per i dati corpo servira' un trattamento
separato e on-device.
