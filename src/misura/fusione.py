"""Fusione per minimi quadrati generalizzati (GLS).

Fondere piu' osservazioni della stessa grandezza:

    stima = (Hᵀ Σ⁻¹ H)⁻¹ Hᵀ Σ⁻¹ (z − b)

dove Σ e' la covarianza **congiunta** — con le correlazioni di modo comune, non
solo le diagonali (#2b) — e `b` sono i soli bias correggibili (#2c, correzione A).
Per la fusione di un'unica grandezza scalare, H e' una colonna di uni e la stima
e' la media pesata generalizzata; il risultato e' assemblato come combinazione
lineare delle grandezze, cosi' conserva la decomposizione in sorgenti e la sua
varianza coincide con (Hᵀ Σ⁻¹ H)⁻¹.

Trattare come indipendenti osservazioni correlate **sottostima** l'incertezza:
e' esattamente cio' che l'uso di Σ congiunta impedisce.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .grandezza import GrandezzaIncerta, covarianza_congiunta
from .osservazione import Osservazione
from .sistematici import BiasCorreggibile


def correggi_bias(grandezza: GrandezzaIncerta, bias: BiasCorreggibile) -> GrandezzaIncerta:
    """Applica ``z − b`` propagando l'incertezza del bias.

    Accetta **solo** `BiasCorreggibile`: e' il punto in cui la correzione A vive
    nel sistema di tipi. Passare un `SistematicoLimitato` dev'essere un errore di
    mypy, non un controllo a runtime — perche' un limitato non ha un valore da
    sottrarre, va gonfiato in Sigma (vedi `Osservazione.grandezza_con_limitati`).
    """
    corretta = grandezza - bias.valore
    if bias.incertezza > 0.0:
        corretta = corretta + GrandezzaIncerta.da_deviazione(0.0, bias.incertezza, "bias")
    return corretta


def _grandezza_efficace(oss: Osservazione) -> GrandezzaIncerta:
    """Grandezza casuale + limitati (in Sigma) + incertezza del bias.

    Il **valore** del bias non entra qui (non e' incertezza): viene sottratto
    nella fusione tramite il termine `b`.
    """
    g = oss.grandezza_con_limitati()
    if oss.bias is not None and oss.bias.incertezza > 0.0:
        g = g + GrandezzaIncerta.da_deviazione(0.0, oss.bias.incertezza, "bias")
    return g


def fondi(osservazioni: Sequence[Osservazione]) -> GrandezzaIncerta:
    """Fonde osservazioni della stessa grandezza scalare via GLS."""
    if len(osservazioni) == 0:
        raise ValueError("nessuna osservazione da fondere")

    grandezze = [_grandezza_efficace(o) for o in osservazioni]
    bias = np.array(
        [o.bias.valore if o.bias is not None else 0.0 for o in osservazioni],
        dtype=np.float64,
    )

    if len(osservazioni) == 1:
        return grandezze[0] - float(bias[0])

    sigma = covarianza_congiunta(grandezze)
    uni = np.ones(len(grandezze), dtype=np.float64)
    # x = Σ⁻¹ 1 ; pesi = x / (1ᵀ Σ⁻¹ 1)
    x = np.linalg.solve(sigma, uni)
    denom = float(uni @ x)
    if denom <= 0.0:
        raise ValueError("covarianza non definita positiva: fusione mal posta")
    pesi = x / denom

    stima = GrandezzaIncerta.costante(0.0)
    for peso, grandezza, b in zip(pesi, grandezze, bias, strict=True):
        stima = stima + float(peso) * (grandezza - float(b))
    return stima
