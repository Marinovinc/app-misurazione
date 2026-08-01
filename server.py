"""App locale interattiva sopra il nucleo metrologico.

Non e' parte della libreria `misura`: e' una thin UI che la usa. Carichi una foto
con un marker ArUco, clicchi i due estremi del target, e il core reale calcola la
misura con la sua incertezza, provenienza ed esito.

    pip install -e ".[app]"
    python app/server.py
    # apri http://127.0.0.1:5000
"""

from __future__ import annotations

import base64
import hashlib
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from flask import Flask, jsonify, request

from misura.esito import (
    EntroTolleranza,
    FuoriTolleranza,
    RifiutoMotivato,
    Tolleranza,
    gestisci_riferimento_occluso,
    valuta,
)
from misura.modalita import Modalita, ModalitaCertificata, ModalitaStima
from misura.pipeline import SegmentoPixel, misura_da_scala
from misura.provenienza import MisurataDaApp
from misura.riferimento import (
    Riferimento,
    RiferimentoNonTrovato,
    lato_pixel_da_angoli,
    marker_stampato_non_verificato,
    marker_stampato_verificato,
    rileva_marker,
    scala_da_lato_pixel,
    tessera_id1,
)

app = Flask(__name__)
_INDEX = Path(__file__).parent / "index.html"

# store in memoria: id immagine -> angoli del marker + lato in pixel
_ANALISI: dict[str, dict[str, Any]] = {}


def _decodifica(dato: str) -> np.ndarray:
    if "," in dato:
        dato = dato.split(",", 1)[1]  # scarta il prefisso data:URL
    grezzo = np.frombuffer(base64.b64decode(dato), dtype=np.uint8)
    immagine = cv2.imdecode(grezzo, cv2.IMREAD_GRAYSCALE)
    if immagine is None:
        raise ValueError("immagine non decodificabile")
    return immagine


def _riferimento(spec: dict[str, Any]) -> Riferimento:
    tipo = spec.get("tipo", "verificato")
    if tipo == "id1":
        return tessera_id1()
    lato = float(spec["lato_mm"])
    if tipo == "verificato":
        return marker_stampato_verificato(lato, float(spec.get("tolleranza_mm", 0.2)))
    if tipo == "non_verificato":
        return marker_stampato_non_verificato(lato, float(spec.get("frazione", 0.02)))
    raise ValueError(f"tipo di riferimento sconosciuto: {tipo!r}")


def _modalita(tag: str) -> Modalita:
    return ModalitaCertificata() if tag == "certificata" else ModalitaStima()


@app.get("/")
def index() -> str:
    # letta a ogni richiesta: in sviluppo basta un refresh, niente restart
    return _INDEX.read_text(encoding="utf-8")


@app.post("/api/analizza")
def analizza() -> Any:
    corpo = request.get_json(force=True)
    try:
        immagine = _decodifica(corpo["immagine"])
    except (KeyError, ValueError) as errore:
        return jsonify({"errore": str(errore)}), 400
    try:
        angoli = rileva_marker(immagine)
    except RiferimentoNonTrovato as errore:
        return jsonify({"errore": str(errore)}), 422
    id_immagine = hashlib.sha1(corpo["immagine"].encode()).hexdigest()[:16]
    _ANALISI[id_immagine] = {
        "angoli": angoli,
        "lato_px": lato_pixel_da_angoli(angoli),
    }
    altezza, larghezza = immagine.shape[:2]
    return jsonify(
        {
            "id": id_immagine,
            "larghezza": int(larghezza),
            "altezza": int(altezza),
            "angoli": angoli.tolist(),
            "lato_px": round(float(_ANALISI[id_immagine]["lato_px"]), 2),
        }
    )


def _scheda(esito: object, extra: dict[str, Any]) -> dict[str, Any]:
    base = dict(extra)
    if isinstance(esito, EntroTolleranza):
        base.update(
            tipo="EntroTolleranza",
            valore_mm=round(esito.misura.valore, 1),
            incertezza_espansa_mm=round(esito.incertezza_espansa, 1),
            tolleranza_mm=esito.tolleranza.semiampiezza,
        )
    elif isinstance(esito, FuoriTolleranza):
        base.update(
            tipo="FuoriTolleranza",
            valore_mm=round(esito.misura.valore, 1),
            incertezza_espansa_mm=round(esito.incertezza_espansa, 1),
            tolleranza_mm=esito.tolleranza.semiampiezza,
            come_migliorare=esito.come_migliorare,
        )
    elif isinstance(esito, RifiutoMotivato):
        base.update(tipo="RifiutoMotivato", motivo=esito.motivo)
    return base


@app.post("/api/misura")
def misura() -> Any:
    corpo = request.get_json(force=True)
    analisi = _ANALISI.get(corpo.get("id", ""))
    modalita = _modalita(corpo.get("modalita", "stima"))
    tolleranza = Tolleranza(semiampiezza=float(corpo.get("tolleranza_mm", 20.0)))
    prov = MisurataDaApp(modalita)

    if analisi is None:
        # nessun riferimento rilevato: la regola dell'occluso decide per modalita'
        esito = gestisci_riferimento_occluso(modalita, prov, tolleranza)
        return jsonify(_scheda(esito, {"modalita": corpo.get("modalita", "stima")}))

    riferimento = _riferimento(corpo["riferimento"])
    sigma_lato = 0.5 * math.sqrt(2.0) / 2.0
    scala = scala_da_lato_pixel(riferimento, float(analisi["lato_px"]), sigma_lato)

    (x1, y1), (x2, y2) = corpo["punti"]
    lato_target_px = math.hypot(float(x2) - float(x1), float(y2) - float(y1))
    grandezza = misura_da_scala(
        scala, SegmentoPixel(lato_target_px, float(corpo.get("sigma_seg_px", 1.0)))
    )
    esito = valuta(grandezza, prov, tolleranza)

    return jsonify(
        _scheda(
            esito,
            {
                "modalita": corpo.get("modalita", "stima"),
                "provenienza": "Misurata dall'app",
                "scala_mm_px": round(scala.valore, 4),
                "scala_inc_mm_px": round(scala.deviazione, 4),
                "lato_rif_px": round(float(analisi["lato_px"]), 1),
                "lato_target_px": round(lato_target_px, 1),
            },
        )
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
