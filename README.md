# misura — nucleo metrologico (fase 0)

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

## Nota di onestà (fase 0)

Il banco sintetico verifica che la **propagazione dell'incertezza sia implementata
correttamente**, non che il modello descriva la realtà. La validazione vera richiede un dataset
reale misurato al calibro (questione aperta #3 del concept).
