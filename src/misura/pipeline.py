"""Pipeline: riferimento -> scala (modo comune) -> misure -> esito.

I bordi del target sono **iniettati** come segmenti in pixel (la segmentazione AI
e' fuori perimetro fase 0). Ogni misura condivide la stessa scala, quindi le
misure di una stessa immagine sono correlate per costruzione (modo comune).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .esito import EsitoMisura, Tolleranza, valuta
from .grandezza import GrandezzaIncerta
from .modalita import Modalita
from .provenienza import MisurataDaApp
from .riferimento import Immagine, Riferimento, scala_da_immagine


@dataclass(frozen=True)
class SegmentoPixel:
    """Bordo del target iniettato: lunghezza in pixel e incertezza di segmentazione."""

    lunghezza_px: float
    sigma_px: float

    def __post_init__(self) -> None:
        if self.lunghezza_px < 0.0:
            raise ValueError("la lunghezza in pixel non puo' essere negativa")
        if self.sigma_px < 0.0:
            raise ValueError("l'incertezza di segmentazione non puo' essere negativa")


def misura_da_scala(scala: GrandezzaIncerta, segmento: SegmentoPixel) -> GrandezzaIncerta:
    """Lunghezza metrica = scala * lunghezza in pixel. Condivide la scala."""
    lunghezza_px = GrandezzaIncerta.da_deviazione(
        segmento.lunghezza_px, segmento.sigma_px, "segmentazione"
    )
    return scala * lunghezza_px


def grandezze_segmenti(
    scala: GrandezzaIncerta, segmenti: Sequence[SegmentoPixel]
) -> list[GrandezzaIncerta]:
    return [misura_da_scala(scala, s) for s in segmenti]


def misura_segmenti(
    scala: GrandezzaIncerta,
    segmenti: Sequence[SegmentoPixel],
    modalita: Modalita,
    tolleranza: Tolleranza,
) -> list[EsitoMisura]:
    provenienza = MisurataDaApp(modalita)
    return [valuta(g, provenienza, tolleranza) for g in grandezze_segmenti(scala, segmenti)]


def misura_da_immagine(
    immagine: Immagine,
    riferimento: Riferimento,
    segmenti: Sequence[SegmentoPixel],
    modalita: Modalita,
    tolleranza: Tolleranza,
    sigma_angolo_px: float = 0.5,
) -> list[EsitoMisura]:
    """End-to-end: rileva il riferimento, propaga la scala di modo comune, valuta."""
    scala = scala_da_immagine(immagine, riferimento, sigma_angolo_px)
    return misura_segmenti(scala, segmenti, modalita, tolleranza)
