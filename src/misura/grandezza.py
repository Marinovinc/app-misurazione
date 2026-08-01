"""`GrandezzaIncerta`: il valore e la sua incertezza come un unico tipo.

L'incertezza non e' un campo accanto al valore ma parte del tipo, con le sue
operazioni. La propagazione e' al primo ordine (linearizzazione), sufficiente e
corretta finche' le incertezze restano piccole rispetto alle nonlinearita' — il
regime in cui lavora la misura. Le operazioni propagano le **sorgenti**, quindi
le correlazioni (incluso il modo comune) si conservano automaticamente.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .incertezza import (
    Sorgente,
    Termini,
    covarianza_di,
    sorgenti_da_covarianza,
    varianza_di,
)

Matrice = npt.NDArray[np.float64]


def _combina(
    t1: Termini, k1: float, t2: Termini, k2: float
) -> dict[Sorgente, float]:
    """Combinazione lineare k1*t1 + k2*t2 dei coefficienti, per sorgente."""
    out: dict[Sorgente, float] = {}
    for sorgente, coeff in t1.items():
        v = k1 * coeff
        if v != 0.0:
            out[sorgente] = out.get(sorgente, 0.0) + v
    for sorgente, coeff in t2.items():
        v = k2 * coeff
        if v != 0.0:
            out[sorgente] = out.get(sorgente, 0.0) + v
    return out


@dataclass(frozen=True, eq=False)
class GrandezzaIncerta:
    """Valore nominale + combinazione lineare di sorgenti d'errore."""

    valore: float
    termini: Mapping[Sorgente, float]

    @property
    def varianza(self) -> float:
        return varianza_di(self.termini)

    @property
    def deviazione(self) -> float:
        return math.sqrt(self.varianza)

    # --- costruttori ---------------------------------------------------------

    @staticmethod
    def costante(valore: float) -> GrandezzaIncerta:
        """Grandezza esatta: nessuna sorgente, varianza zero."""
        return GrandezzaIncerta(float(valore), {})

    @staticmethod
    def da_deviazione(
        valore: float, deviazione: float, nome: str = ""
    ) -> GrandezzaIncerta:
        """Grandezza con una **nuova** sorgente indipendente di data deviazione."""
        if deviazione < 0.0:
            raise ValueError("la deviazione non puo' essere negativa")
        if deviazione == 0.0:
            return GrandezzaIncerta(float(valore), {})
        return GrandezzaIncerta(float(valore), {Sorgente(nome): float(deviazione)})

    # --- operazioni (propagazione al primo ordine) ---------------------------

    def __add__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        g = _come_grandezza(altro)
        return GrandezzaIncerta(
            self.valore + g.valore, _combina(self.termini, 1.0, g.termini, 1.0)
        )

    __radd__ = __add__

    def __neg__(self) -> GrandezzaIncerta:
        return GrandezzaIncerta(-self.valore, _combina(self.termini, -1.0, {}, 0.0))

    def __sub__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        g = _come_grandezza(altro)
        return GrandezzaIncerta(
            self.valore - g.valore, _combina(self.termini, 1.0, g.termini, -1.0)
        )

    def __rsub__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        return _come_grandezza(altro).__sub__(self)

    def __mul__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        g = _come_grandezza(altro)
        # d(ab) = b*da + a*db
        return GrandezzaIncerta(
            self.valore * g.valore,
            _combina(self.termini, g.valore, g.termini, self.valore),
        )

    __rmul__ = __mul__

    def __truediv__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        g = _come_grandezza(altro)
        if g.valore == 0.0:
            raise ZeroDivisionError("divisione per una grandezza di valore nullo")
        # d(a/b) = da/b - a*db/b^2
        return GrandezzaIncerta(
            self.valore / g.valore,
            _combina(
                self.termini,
                1.0 / g.valore,
                g.termini,
                -self.valore / (g.valore * g.valore),
            ),
        )

    def __rtruediv__(self, altro: GrandezzaIncerta | float) -> GrandezzaIncerta:
        return _come_grandezza(altro).__truediv__(self)


def _come_grandezza(x: GrandezzaIncerta | float) -> GrandezzaIncerta:
    if isinstance(x, GrandezzaIncerta):
        return x
    return GrandezzaIncerta.costante(float(x))


# --- covarianza fra grandezze (meta' "in uscita" dell'interfaccia #2a) -------


def covarianza(a: GrandezzaIncerta, b: GrandezzaIncerta) -> float:
    return covarianza_di(a.termini, b.termini)


def covarianza_congiunta(grandezze: Sequence[GrandezzaIncerta]) -> Matrice:
    n = len(grandezze)
    m = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i, n):
            c = covarianza_di(grandezze[i].termini, grandezze[j].termini)
            m[i, j] = c
            m[j, i] = c
    return m


def da_covarianza(
    valori: Sequence[float], matrice: npt.ArrayLike, nome: str = "cov"
) -> list[GrandezzaIncerta]:
    """Costruisce grandezze correlate con la covarianza data (interfaccia #2a)."""
    righe = sorgenti_da_covarianza(matrice, nome)
    if len(valori) != len(righe):
        raise ValueError("numero di valori diverso dalla dimensione della covarianza")
    return [GrandezzaIncerta(float(v), t) for v, t in zip(valori, righe, strict=True)]
