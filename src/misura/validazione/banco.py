"""Banco di validazione sintetico.

Stub del Passo 0: il banco vero (copertura empirica vs dichiarata, sistematici
realizzati, controllo negativo) arriva al Passo 7. Qui esiste solo il punto di
ingresso, così il comando `python -m misura.validazione.banco` è già cablato.
"""

from __future__ import annotations

PREMESSA_ONESTA = (
    "Il banco sintetico verifica che la propagazione dell'incertezza sia "
    "implementata correttamente, NON che il modello descriva la realta'. "
    "La validazione vera richiede il dataset reale al calibro (questione aperta #3)."
)


def main() -> int:
    """Punto di ingresso del banco. Al Passo 0 non esegue ancora scene."""
    print(PREMESSA_ONESTA)
    print("Banco vuoto: le scene sintetiche arrivano al Passo 7.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
