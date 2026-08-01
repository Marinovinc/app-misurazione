"""`Osservazione`: una grandezza misurata con la sua provenienza e i suoi
sistematici.

Tiene insieme i tre ingredienti che la fusione (Passo 3) dovra' combinare:
- la grandezza casuale (valore + incertezza con le sue sorgenti e correlazioni);
- gli eventuali `SistematicoLimitato`, che **gonfiano** l'incertezza;
- l'eventuale `BiasCorreggibile`, che **non** e' incertezza e va sottratto.

La distinzione della correzione A e' gia' visibile qui: `grandezza_con_limitati`
piega dentro l'incertezza i soli sistematici limitati; il bias resta fuori,
esposto separatamente perche' lo tratti la fusione.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grandezza import GrandezzaIncerta
from .provenienza import Provenienza
from .sistematici import BiasCorreggibile, SistematicoLimitato


@dataclass(frozen=True)
class Osservazione:
    grandezza: GrandezzaIncerta
    provenienza: Provenienza
    bias: BiasCorreggibile | None = None
    limitati: tuple[SistematicoLimitato, ...] = field(default=())

    def grandezza_con_limitati(self) -> GrandezzaIncerta:
        """Grandezza casuale + i `SistematicoLimitato` come sorgenti INDIPENDENTI.

        Ogni limitato aggiunge una sorgente fresca di deviazione limite/sqrt(3):
        gonfia Sigma senza toccare il valore. Il `BiasCorreggibile` **non** entra
        qui: non e' rumore a media zero, e trattarlo come tale tirerebbe la stima
        nella direzione sbagliata.
        """
        g = self.grandezza
        for s in self.limitati:
            g = g + GrandezzaIncerta.da_deviazione(0.0, s.incertezza_standard(), "limitato")
        return g
