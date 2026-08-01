"""Genera un marker ArUco grande e pulito, da mostrare a schermo intero (telefono)
o da stampare. Dizionario DICT_4X4_50, id 7 — lo stesso che l'app rileva.

    python esempi/genera_marker.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def main() -> int:
    lato = 760
    margine = 120  # quiet zone bianca: serve al rilevamento
    n = lato + 2 * margine
    vocab = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(vocab, 7, lato)
    tela = np.full((n, n), 255, np.uint8)
    tela[margine : margine + lato, margine : margine + lato] = marker

    uscita = Path(__file__).parent / "marker-4x4-id7.png"
    cv2.imwrite(str(uscita), tela)
    print(f"salvato: {uscita}  ({n}x{n}px, quiet zone {margine}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
