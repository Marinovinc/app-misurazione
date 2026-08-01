"""Riferimento di scala: rilevamento ArUco reale + tolleranza dimensionale (corr. B).

La scala non nasce solo dal rumore di localizzazione degli angoli: la dimensione
nota del riferimento **non e' nota esattamente**. Per un marker stampato la
tolleranza di stampa ("adatta alla pagina" sbaglia dell'1-3% in silenzio) e'
spesso il termine dominante — la trappola delle due serie di banconote (§5.1) in
versione tipografica. Qui la dimensione del riferimento e' una **sorgente
indipendente di prima classe**, con ampiezza dipendente dal tipo di riferimento.

La scala risultante (mm per pixel) e' la sorgente di **modo comune** condivisa da
tutte le misure estratte dalla stessa immagine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from .grandezza import GrandezzaIncerta

Immagine = npt.NDArray[np.uint8]
Vettore = npt.NDArray[np.float64]


class RiferimentoNonTrovato(Exception):
    """Nessun marker ArUco rilevato nell'immagine (riferimento assente/occluso)."""


@dataclass(frozen=True)
class Riferimento:
    """Oggetto di scala noto.

    `lato_mm` e' la dimensione fisica nominale; `tolleranza_dim_mm` la
    semi-ampiezza (limite) della sua incertezza dimensionale, convertita in
    deviazione standard con il trattamento GUM di tipo B (uniforme, limite/sqrt3),
    coerente con `SistematicoLimitato`.
    """

    lato_mm: float
    tolleranza_dim_mm: float
    descrizione: str = ""

    def __post_init__(self) -> None:
        if self.lato_mm <= 0.0:
            raise ValueError("il lato del riferimento dev'essere positivo")
        if self.tolleranza_dim_mm < 0.0:
            raise ValueError("la tolleranza dimensionale non puo' essere negativa")

    def dimensione_incerta(self) -> GrandezzaIncerta:
        sigma = self.tolleranza_dim_mm / math.sqrt(3.0)
        return GrandezzaIncerta.da_deviazione(self.lato_mm, sigma, "dim_riferimento")


def tessera_id1() -> Riferimento:
    """Tessera ID-1 (ISO/IEC 7810): 85,60 x 53,98 mm, rigida, tolleranza stretta.

    Dimensione unica in tutto il mondo (nessuna classificazione, nessuna serie):
    usiamo il lato lungo come scala.
    """
    return Riferimento(85.60, 0.10, "tessera ID-1 (ISO/IEC 7810)")


def marker_stampato_non_verificato(lato_mm: float, frazione: float = 0.02) -> Riferimento:
    """Marker stampato ma NON verificato: tolleranza larga e dichiarata.

    `frazione` e' l'errore di stampa plausibile (default 2%): e' il termine che
    spesso domina la scala.
    """
    return Riferimento(lato_mm, frazione * lato_mm, "marker stampato non verificato")


def marker_stampato_verificato(lato_mm: float, tolleranza_mm: float = 0.2) -> Riferimento:
    """Marker stampato e verificato al calibro: tolleranza stretta."""
    return Riferimento(lato_mm, tolleranza_mm, "marker stampato e verificato al calibro")


def rileva_marker(immagine: Immagine, dizionario: int | None = None) -> Vettore:
    """Rileva il primo marker ArUco e restituisce i suoi 4 angoli (x, y) in pixel.

    Parametri piu' permissivi del default per reggere foto reali (webcam, marker
    piccolo o lontano, illuminazione varia) e rifinitura sub-pixel degli angoli
    per la precisione della scala.
    """
    codice = cv2.aruco.DICT_4X4_50 if dizionario is None else dizionario
    vocabolario = cv2.aruco.getPredefinedDictionary(codice)
    parametri = cv2.aruco.DetectorParameters()
    parametri.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parametri.minMarkerPerimeterRate = 0.02  # marker piu' piccoli/lontani (default 0.03)
    parametri.adaptiveThreshWinSizeMin = 3
    parametri.adaptiveThreshWinSizeMax = 43
    parametri.adaptiveThreshWinSizeStep = 10
    rilevatore = cv2.aruco.ArucoDetector(vocabolario, parametri)
    angoli, ids, _ = rilevatore.detectMarkers(immagine)
    if ids is None or len(angoli) == 0:
        raise RiferimentoNonTrovato("nessun marker ArUco rilevato")
    return np.asarray(angoli[0][0], dtype=np.float64)


def lato_pixel_da_angoli(angoli: Vettore) -> float:
    """Lato medio in pixel dai 4 angoli del marker."""
    lati = [float(np.linalg.norm(angoli[i] - angoli[(i + 1) % 4])) for i in range(4)]
    return sum(lati) / 4.0


def lato_pixel_aruco(immagine: Immagine, dizionario: int | None = None) -> float:
    """Rileva il primo marker ArUco e restituisce il lato medio in pixel."""
    return lato_pixel_da_angoli(rileva_marker(immagine, dizionario))


def scala_da_lato_pixel(
    riferimento: Riferimento, lato_pixel: float, sigma_lato_pixel: float
) -> GrandezzaIncerta:
    """Scala (mm/pixel) da due sorgenti indipendenti: tolleranza dimensionale del
    riferimento (corr. B) e rumore di localizzazione degli angoli."""
    dimensione = riferimento.dimensione_incerta()
    lato = GrandezzaIncerta.da_deviazione(lato_pixel, sigma_lato_pixel, "angoli_riferimento")
    return dimensione / lato


def scala_da_immagine(
    immagine: Immagine,
    riferimento: Riferimento,
    sigma_angolo_px: float = 0.5,
    dizionario: int | None = None,
) -> GrandezzaIncerta:
    """Rileva l'ArUco e ne ricava la scala di modo comune.

    Il lato e' la media di 4 lati, ciascuno differenza di due angoli:
    sigma_lato ~ sigma_angolo * sqrt(2) / sqrt(4). E' una scelta di modello da
    calibrare col banco (Passo 7)."""
    lato_px = lato_pixel_aruco(immagine, dizionario)
    sigma_lato = sigma_angolo_px * math.sqrt(2.0) / 2.0
    return scala_da_lato_pixel(riferimento, lato_px, sigma_lato)
