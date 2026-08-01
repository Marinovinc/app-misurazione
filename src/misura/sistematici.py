"""Due specie di sistematici, trattamenti opposti (correzione A).

La distinzione e' a livello di **tipo**, non di convenzione:

- `BiasCorreggibile`: noto, con segno e magnitudine stimabili (es. §9.1, la
  circonferenza fianchi autodichiarata sottostimata di 4,54 cm). Entra nel
  termine `b` del GLS e si **sottrae**.
- `SistematicoLimitato`: sai che c'e' e ne stimi un **limite** superiore, ma non
  il valore in *questa* osservazione (non-complanarita' del riferimento,
  distorsione non corretta). **Non** si sottrae: si converte in incertezza
  standard e **gonfia Sigma**.

Sono tipi **disgiunti**, senza base comune: e' cosi' che al Passo 3 il termine
`b` della fusione puo' accettare solo `BiasCorreggibile` a livello di tipo.
Passare un `SistematicoLimitato` a `b` dev'essere un errore di mypy, non un bug a
runtime: correggere per cio' che non si osserva produce una stima falsamente
centrata con incertezza falsamente stretta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BiasCorreggibile:
    """Scostamento sistematico noto dell'osservazione rispetto al vero.

    Convenzione di segno: ``valore = osservato - vero``. Una sottostima (§9.1,
    osservato < vero) da' `valore` **negativo**; la fusione calcola ``z - b`` e
    quindi corregge verso l'alto. `incertezza` e' l'incertezza sulla stima del
    bias stesso, che la fusione propaga come sorgente indipendente.
    """

    valore: float
    incertezza: float = 0.0

    def __post_init__(self) -> None:
        if self.incertezza < 0.0:
            raise ValueError("l'incertezza del bias non puo' essere negativa")


@dataclass(frozen=True)
class SistematicoLimitato:
    """Sistematico di cui si conosce solo un limite: |errore| <= limite."""

    limite: float

    def __post_init__(self) -> None:
        if self.limite < 0.0:
            raise ValueError("il limite non puo' essere negativo")

    def incertezza_standard(self) -> float:
        """Limite -> deviazione standard, trattamento GUM di tipo B.

        In assenza d'altra informazione, distribuzione uniforme su
        [-limite, +limite]: sigma = limite / sqrt(3).
        """
        return self.limite / math.sqrt(3.0)
