"""Protocollo di validazione sul dataset reale (§7.2, questione aperta #3).

Per ogni campione: rileva il riferimento ArUco dall'immagine reale, propaga la
scala (con la sua tolleranza dimensionale), misura il target annotato, applica
l'inflazione da scarti e confronta col vero al calibro.

Il criterio di accettazione e' espresso come **percentuale di misure entro
tolleranza** (§7.2: es. "95% entro l'1%"), non come errore medio: un errore medio
basso con code lunghe perde la fiducia dell'utente. Si riporta anche la copertura
dell'incertezza dichiarata (onesta': il ±X contiene davvero il vero?).

Questo modulo NON contiene un dataset: attende quello reale al calibro. Con
`dataset/` vuoto, il protocollo non ha nulla da validare — ed e' corretto cosi'.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from ..pipeline import SegmentoPixel, misura_da_scala
from ..riferimento import RiferimentoNonTrovato, lato_pixel_aruco, scala_da_lato_pixel
from .dataset import CampioneGroundTruth, carica_dataset


@dataclass(frozen=True)
class EsitoCampione:
    id: str
    rilevato: bool
    valore_mm: float
    incertezza_espansa_mm: float
    vero_mm: float
    errore_mm: float
    entro_dichiarata: bool
    entro_tolleranza: bool


@dataclass(frozen=True)
class RisultatoProtocollo:
    n_totali: int
    n_valutati: int
    non_rilevati: int
    k: float
    tolleranza_mm: float
    soglia_accettazione: float
    frazione_entro_dichiarata: float
    frazione_entro_tolleranza: float
    esiti: tuple[EsitoCampione, ...]

    @property
    def passa(self) -> bool:
        return (
            self.n_valutati > 0
            and self.frazione_entro_tolleranza >= self.soglia_accettazione
        )


def _carica_immagine(percorso: Path) -> Any:
    immagine = cv2.imread(str(percorso), cv2.IMREAD_GRAYSCALE)
    if immagine is None:
        raise FileNotFoundError(f"immagine non leggibile: {percorso}")
    return immagine


def esegui_protocollo(
    campioni: Sequence[CampioneGroundTruth],
    radice: Path,
    tolleranza_mm: float,
    k: float = 2.0,
    soglia_accettazione: float = 0.95,
    sigma_angolo_px: float = 0.5,
) -> RisultatoProtocollo:
    esiti: list[EsitoCampione] = []
    non_rilevati = 0

    for campione in campioni:
        immagine = _carica_immagine(radice / campione.percorso_immagine)
        try:
            lato_px = lato_pixel_aruco(immagine)
        except RiferimentoNonTrovato:
            non_rilevati += 1
            esiti.append(
                EsitoCampione(
                    id=campione.id,
                    rilevato=False,
                    valore_mm=math.nan,
                    incertezza_espansa_mm=math.nan,
                    vero_mm=campione.vero.valore_mm,
                    errore_mm=math.nan,
                    entro_dichiarata=False,
                    entro_tolleranza=False,
                )
            )
            continue

        sigma_lato = sigma_angolo_px * math.sqrt(2.0) / 2.0
        scala = scala_da_lato_pixel(campione.riferimento, lato_px, sigma_lato)
        misura = misura_da_scala(
            scala,
            SegmentoPixel(campione.target.lunghezza_px(), campione.target.sigma_px),
        )
        misura = campione.scarti.applica(misura)

        errore = misura.valore - campione.vero.valore_mm
        # banda dichiarata: incertezza della misura combinata con quella del calibro
        banda = k * math.sqrt(
            misura.varianza + campione.vero.incertezza_mm**2
        )
        esiti.append(
            EsitoCampione(
                id=campione.id,
                rilevato=True,
                valore_mm=misura.valore,
                incertezza_espansa_mm=k * misura.deviazione,
                vero_mm=campione.vero.valore_mm,
                errore_mm=errore,
                entro_dichiarata=abs(errore) <= banda,
                entro_tolleranza=abs(errore) <= tolleranza_mm,
            )
        )

    valutati = [e for e in esiti if e.rilevato]
    n_val = len(valutati)
    frazione_dich = (
        sum(1 for e in valutati if e.entro_dichiarata) / n_val if n_val else 0.0
    )
    frazione_toll = (
        sum(1 for e in valutati if e.entro_tolleranza) / n_val if n_val else 0.0
    )

    return RisultatoProtocollo(
        n_totali=len(campioni),
        n_valutati=n_val,
        non_rilevati=non_rilevati,
        k=k,
        tolleranza_mm=tolleranza_mm,
        soglia_accettazione=soglia_accettazione,
        frazione_entro_dichiarata=frazione_dich,
        frazione_entro_tolleranza=frazione_toll,
        esiti=tuple(esiti),
    )


def main() -> int:
    radice = Path("dataset")
    campioni = carica_dataset(radice)
    if not campioni:
        print(
            "0 campioni in dataset/campioni: il protocollo attende il dataset reale "
            "al calibro (questione aperta #3)."
        )
        return 0
    risultato = esegui_protocollo(campioni, radice, tolleranza_mm=10.0)
    print(f"campioni: {risultato.n_totali}, valutati: {risultato.n_valutati}")
    print(f"  entro tolleranza (+/-{risultato.tolleranza_mm} mm): "
          f"{risultato.frazione_entro_tolleranza:.3f} "
          f"(soglia {risultato.soglia_accettazione:.2f})")
    print(f"  copertura dichiarata (k={risultato.k}): "
          f"{risultato.frazione_entro_dichiarata:.3f}")
    print(f"  ESITO: {'PASSA' if risultato.passa else 'NON PASSA'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
