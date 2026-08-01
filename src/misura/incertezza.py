"""Rappresentazione affine dell'incertezza a sorgenti condivise.

Una grandezza incerta e' un valore nominale piu' una combinazione lineare di
**sorgenti d'errore indipendenti** a varianza unitaria: l'ampiezza sta nei
coefficienti, l'identita' della sorgente distingue cio' che e' indipendente da
cio' che e' condiviso. Condividere una sorgente e' il modo in cui si rappresenta
l'errore di scala di **modo comune** (tutte le misure di una stessa immagine
condividono il fattore di scala, quindi sono correlate per costruzione).

Questo modulo contiene la sorgente e la matematica pura sui coefficienti; il tipo
`GrandezzaIncerta` con le sue operazioni vive in `grandezza.py`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Vettore = npt.NDArray[np.float64]


@dataclass(frozen=True, eq=False)
class Sorgente:
    """Token d'identita' di una sorgente d'errore indipendente, varianza unitaria.

    L'uguaglianza e' per identita' di istanza (``eq=False``): due ``Sorgente``
    costruite separatamente sono non correlate; la *stessa* istanza condivisa
    introduce correlazione. Il nome e' solo per diagnostica.
    """

    nome: str = ""


# Combinazione lineare di sorgenti: sorgente -> coefficiente di sensibilita'.
Termini = Mapping[Sorgente, float]


def varianza_di(termini: Termini) -> float:
    """Varianza = somma dei coefficienti al quadrato (sorgenti a varianza 1)."""
    return sum((coeff * coeff for coeff in termini.values()), 0.0)


def covarianza_di(a: Termini, b: Termini) -> float:
    """Covarianza fra due grandezze = somma sui soli termini **condivisi**."""
    piccolo, grande = (a, b) if len(a) <= len(b) else (b, a)
    totale = 0.0
    for sorgente, coeff in piccolo.items():
        altro = grande.get(sorgente)
        if altro is not None:
            totale += coeff * altro
    return totale


def sorgenti_da_covarianza(
    matrice: npt.ArrayLike, nome: str = "cov"
) -> list[dict[Sorgente, float]]:
    """Decompone una matrice di covarianza in sorgenti indipendenti.

    Restituisce, per ogni riga, la combinazione lineare di sorgenti fresche tale
    che la covarianza congiunta ricostruita eguagli ``matrice``. Usa la
    decomposizione spettrale (robusta anche per matrici semidefinite), non la
    Cholesky che richiederebbe definita positiva. E' la meta' "in ingresso"
    dell'interfaccia a covarianza (#2a).
    """
    m = np.asarray(matrice, dtype=np.float64)
    if m.ndim != 2 or m.shape[0] != m.shape[1]:
        raise ValueError("la covarianza dev'essere una matrice quadrata")
    if not np.allclose(m, m.T):
        raise ValueError("la matrice di covarianza dev'essere simmetrica")

    autoval, autovett = np.linalg.eigh(m)
    scala = max(1.0, float(np.max(np.abs(autoval)))) if autoval.size else 1.0
    if bool(np.any(autoval < -1e-9 * scala)):
        raise ValueError("la matrice di covarianza non e' semidefinita positiva")

    radici = np.sqrt(np.clip(autoval, 0.0, None))
    fattore = autovett * radici  # fattore @ fattore.T == matrice
    n = m.shape[0]
    fonti = [Sorgente(f"{nome}[{k}]") for k in range(n)]

    righe: list[dict[Sorgente, float]] = []
    for i in range(n):
        riga: dict[Sorgente, float] = {}
        for k in range(n):
            coeff = float(fattore[i, k])
            if coeff != 0.0:
                riga[fonti[k]] = coeff
        righe.append(riga)
    return righe
