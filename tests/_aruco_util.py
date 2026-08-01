"""Utility di test: genera un'immagine con un marker ArUco.

Nome senza prefisso ``test_``: non e' raccolto da pytest, ma e' importabile dai
test ed e' controllato da mypy.
"""

from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt

Immagine = npt.NDArray[np.uint8]


def immagine_marker(lato_px: int, margine: int = 60, id_marker: int = 7) -> Immagine:
    """Marker ArUco DICT_4X4_50 di lato `lato_px`, su tela bianca con quiet zone."""
    vocabolario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(vocabolario, id_marker, lato_px)
    n = lato_px + 2 * margine
    tela = np.full((n, n), 255, np.uint8)
    tela[margine : margine + lato_px, margine : margine + lato_px] = marker
    return tela
