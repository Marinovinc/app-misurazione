"""Fase 1 — test d'integrazione dell'app locale (Flask test client sul core reale)."""

from __future__ import annotations

import base64

import cv2
import numpy as np

from _aruco_util import immagine_marker


def _png_base64(immagine: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", immagine)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def test_flusso_analizza_e_misura() -> None:
    from app.server import app

    client = app.test_client()
    b64 = _png_base64(immagine_marker(200))

    r1 = client.post("/api/analizza", json={"immagine": b64})
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert "id" in d1
    assert len(d1["angoli"]) == 4

    r2 = client.post(
        "/api/misura",
        json={
            "id": d1["id"],
            "riferimento": {"tipo": "verificato", "lato_mm": 50.0, "tolleranza_mm": 0.2},
            "punti": [[50, 50], [448, 50]],  # ~398 px orizzontali
            "modalita": "stima",
            "tolleranza_mm": 20.0,
            "sigma_seg_px": 1.0,
        },
    )
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2["tipo"] in ("EntroTolleranza", "FuoriTolleranza")
    assert 80.0 < d2["valore_mm"] < 120.0  # ~100 mm


def test_analizza_senza_marker_da_422() -> None:
    from app.server import app

    client = app.test_client()
    b64 = _png_base64(np.full((100, 100), 255, np.uint8))
    r = client.post("/api/analizza", json={"immagine": b64})
    assert r.status_code == 422


def test_misura_certificata_senza_riferimento_rifiuta() -> None:
    from app.server import app

    client = app.test_client()
    r = client.post(
        "/api/misura",
        json={"id": "inesistente", "modalita": "certificata", "tolleranza_mm": 5.0},
    )
    assert r.status_code == 200
    assert r.get_json()["tipo"] == "RifiutoMotivato"
