"""Registro degli scarti (§6.3).

Due principi del concept, resi struttura:

1. **Lo scarto si decide su criteri indipendenti dal risultato** — nitidezza,
   angolo di base, confidenza del marker, residuo di riproiezione — valutati
   *prima* di guardare cosa fa la misura. Eliminare una foto perche' *peggiora la
   stima* e' un errore metodologico: il sistema conferma se stesso e l'incertezza
   mostrata si restringe artificialmente. Qui il guard e' strutturale:
   `CriterioScarto` e' un insieme **chiuso** di ragioni indipendenti dal
   risultato; non esiste un membro "disaccordo con la stima".

2. **Ogni scarto va contato.** Cinque scatti di cui tre buttati non danno la
   stessa incertezza di tre scatti buoni al primo colpo: il conteggio degli
   scarti **gonfia** l'incertezza riportata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .grandezza import GrandezzaIncerta


class CriterioScarto(Enum):
    """Ragioni di scarto, tutte **indipendenti dal risultato** (§6.3).

    L'assenza deliberata di un criterio tipo "disaccordo con la stima" e' il guard
    metodologico: aggiungerne uno romperebbe il test che pinna questo invariante.
    """

    NITIDEZZA_INSUFFICIENTE = "nitidezza insufficiente"
    ANGOLO_BASE_FUORI_RANGE = "angolo di base fuori range"
    MARKER_BASSA_CONFIDENZA = "marker rilevato a bassa confidenza"
    RESIDUO_RIPROIEZIONE_ALTO = "residuo di riproiezione alto"


@dataclass(frozen=True)
class Scarto:
    id_scatto: str
    criterio: CriterioScarto


@dataclass(frozen=True)
class RegistroScarti:
    """Scatti tenuti e scarti registrati, con il criterio oggettivo di ciascuno."""

    tenuti: int
    scarti: tuple[Scarto, ...] = ()

    def __post_init__(self) -> None:
        if self.tenuti < 1:
            raise ValueError("serve almeno uno scatto tenuto per riportare una misura")

    @property
    def n_scartati(self) -> int:
        return len(self.scarti)

    @property
    def n_totali(self) -> int:
        return self.tenuti + self.n_scartati

    def conteggio_per_criterio(self) -> dict[CriterioScarto, int]:
        conteggio: dict[CriterioScarto, int] = {}
        for scarto in self.scarti:
            conteggio[scarto.criterio] = conteggio.get(scarto.criterio, 0) + 1
        return conteggio

    def fattore_inflazione(self) -> float:
        """Fattore >= 1 che cresce con la frazione di scarti.

        sqrt(totali / tenuti): con zero scarti vale 1, e cresce all'aumentare
        degli scarti a parita' di tenuti. E' una scelta di modello da calibrare
        col banco (come sigma_lato del riferimento), non una legge fisica.
        """
        return math.sqrt(self.n_totali / self.tenuti)

    def applica(self, grandezza: GrandezzaIncerta) -> GrandezzaIncerta:
        """Gonfia l'incertezza riportata del fattore di inflazione.

        Aggiunge una sorgente **indipendente** dimensionata a portare la
        deviazione a f * deviazione, senza toccare le sorgenti condivise (quindi
        senza contaminare le correlazioni a monte). Da usare come passo terminale
        sulla misura riportata.
        """
        f = self.fattore_inflazione()
        if f <= 1.0:
            return grandezza
        extra = grandezza.deviazione * math.sqrt(f * f - 1.0)
        if extra == 0.0:
            return grandezza
        return grandezza + GrandezzaIncerta.da_deviazione(0.0, extra, "inflazione_scarti")
