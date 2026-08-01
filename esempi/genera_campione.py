"""Genera un'immagine di prova per l'app: un marker ArUco (50 mm) e un oggetto
da misurare, con i due estremi da cliccare evidenziati.

    python esempi/genera_campione.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from misura.riferimento import lato_pixel_aruco


def main() -> int:
    larghezza, altezza = 900, 520
    tela = np.full((altezza, larghezza, 3), 255, np.uint8)

    # marker ArUco 4x4, id 7, 200 px, con quiet zone bianca
    vocab = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(vocab, 7, 200)
    tela[60:260, 60:260] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    cv2.putText(tela, "ArUco 50 mm", (60, 288), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (120, 120, 120), 1, cv2.LINE_AA)

    # oggetto target: rettangolo, lato lungo ~398 px (-> ~100 mm)
    x1, x2, y1, y2 = 340, 738, 360, 430
    cv2.rectangle(tela, (x1, y1), (x2, y2), (74, 74, 74), -1)
    ym = (y1 + y2) // 2
    for x in (x1, x2):
        cv2.drawMarker(tela, (x, ym), (210, 120, 0), cv2.MARKER_TILTED_CROSS, 24, 2)
    cv2.putText(tela, "clicca i due estremi (lato lungo)", (x1, y2 + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 120, 0), 1, cv2.LINE_AA)

    uscita = Path(__file__).parent / "campione-demo.png"
    cv2.imwrite(str(uscita), tela)

    # verifica che sia misurabile
    grigia = cv2.cvtColor(tela, cv2.COLOR_BGR2GRAY)
    lato_px = lato_pixel_aruco(grigia)
    print(f"salvato: {uscita}")
    print(f"marker rilevato: lato {lato_px:.1f} px  ->  scala ~{50.0 / lato_px:.4f} mm/px")
    print(f"target ~{x2 - x1} px  ->  atteso ~{(x2 - x1) * 50.0 / lato_px:.1f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
