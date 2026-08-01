"""Demo end-to-end del nucleo reale: dalla scala all'esito, con incertezza e
provenienza. Non e' l'app: e' il core che l'app userebbe, reso osservabile.

    python esempi/demo.py
"""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np

from misura.esito import (
    EntroTolleranza,
    FuoriTolleranza,
    RifiutoMotivato,
    Tolleranza,
    gestisci_riferimento_occluso,
    valuta,
)
from misura.modalita import ModalitaCertificata, ModalitaStima
from misura.pipeline import SegmentoPixel, misura_da_scala
from misura.provenienza import MisurataDaApp
from misura.riferimento import marker_stampato_verificato, scala_da_immagine


def _immagine_marker(lato_px: int = 200, margine: int = 60) -> np.ndarray:
    vocab = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(vocab, 7, lato_px)
    n = lato_px + 2 * margine
    tela = np.full((n, n), 255, np.uint8)
    tela[margine : margine + lato_px, margine : margine + lato_px] = marker
    return tela


def _scheda(esito: object) -> dict[str, Any]:
    if isinstance(esito, EntroTolleranza):
        return {
            "tipo": "EntroTolleranza",
            "valore_mm": round(esito.misura.valore, 1),
            "incertezza_espansa_mm": round(esito.incertezza_espansa, 1),
            "tolleranza_mm": esito.tolleranza.semiampiezza,
            "provenienza": type(esito.provenienza).__name__,
        }
    if isinstance(esito, FuoriTolleranza):
        return {
            "tipo": "FuoriTolleranza",
            "valore_mm": round(esito.misura.valore, 1),
            "incertezza_espansa_mm": round(esito.incertezza_espansa, 1),
            "tolleranza_mm": esito.tolleranza.semiampiezza,
            "come_migliorare": esito.come_migliorare,
        }
    if isinstance(esito, RifiutoMotivato):
        return {"tipo": "RifiutoMotivato", "motivo": esito.motivo}
    return {"tipo": "sconosciuto"}


def main() -> int:
    img = _immagine_marker()
    rif = marker_stampato_verificato(50.0, 0.2)  # 50 mm, verificato al calibro
    scala = scala_da_immagine(img, rif)  # rilevamento ArUco reale -> mm/px

    prov = MisurataDaApp(ModalitaStima())

    # A) misura netta, entro tolleranza
    misura_a = misura_da_scala(scala, SegmentoPixel(398.0, 1.0))
    esito_a = valuta(misura_a, prov, Tolleranza(semiampiezza=20.0))

    # B) segmentazione incerta -> valida ma fuori tolleranza, con guida
    misura_b = misura_da_scala(scala, SegmentoPixel(398.0, 20.0))
    esito_b = valuta(misura_b, prov, Tolleranza(semiampiezza=5.0))

    # C) modalita' certificata + riferimento occluso -> rifiuto
    esito_c = gestisci_riferimento_occluso(
        ModalitaCertificata(),
        MisurataDaApp(ModalitaCertificata()),
        Tolleranza(semiampiezza=5.0),
    )

    schede = {
        "scala_mm_px": round(scala.valore, 4),
        "scala_incertezza_mm_px": round(scala.deviazione, 4),
        "A_entro_tolleranza": _scheda(esito_a),
        "B_fuori_tolleranza": _scheda(esito_b),
        "C_rifiuto_certificata": _scheda(esito_c),
    }
    print(json.dumps(schede, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
