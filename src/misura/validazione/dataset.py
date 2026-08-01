"""Schema del dataset ground-truth (questione aperta #3, §7.2).

Un campione tiene insieme tutto cio' che serve per validare una misura contro il
vero misurato al calibro:

- l'immagine in cui il **riferimento** ArUco e' visibile (rilevato davvero);
- l'annotazione del **target** come estremi in pixel (coerente col confine
  'segmentazione iniettata': i due punti li mette un umano, non l'AI);
- il **vero** misurato al calibro, con la sua incertezza (anche il calibro e' uno
  strumento: e' un'osservazione, non una verita' assoluta);
- la modalita', il registro degli scarti, i metadati di acquisizione.

I campioni vivono su disco come JSON sotto `dataset/campioni/*.json`, con le
immagini sotto `dataset/immagini/` (percorso relativo alla radice del dataset).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..modalita import Modalita, ModalitaCertificata, ModalitaStima
from ..riferimento import Riferimento
from ..scarti import CriterioScarto, RegistroScarti, Scarto


@dataclass(frozen=True)
class MisuraCalibro:
    """Vero di riferimento misurato al calibro (mm), con la sua incertezza."""

    valore_mm: float
    incertezza_mm: float = 0.02  # tipica di un calibro digitale

    def __post_init__(self) -> None:
        if self.valore_mm <= 0.0:
            raise ValueError("il valore al calibro dev'essere positivo")
        if self.incertezza_mm < 0.0:
            raise ValueError("l'incertezza del calibro non puo' essere negativa")


@dataclass(frozen=True)
class TargetAnnotato:
    """Estremi del target in pixel (annotati) e incertezza di localizzazione."""

    x1: float
    y1: float
    x2: float
    y2: float
    sigma_px: float = 1.0

    def __post_init__(self) -> None:
        if self.sigma_px < 0.0:
            raise ValueError("sigma_px non puo' essere negativa")

    def lunghezza_px(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)


@dataclass(frozen=True)
class CampioneGroundTruth:
    id: str
    percorso_immagine: str
    riferimento: Riferimento
    target: TargetAnnotato
    vero: MisuraCalibro
    modalita: Modalita
    scarti: RegistroScarti = field(default_factory=lambda: RegistroScarti(tenuti=1))
    descrizione: str = ""
    metadati: Mapping[str, str] = field(default_factory=dict)


# --- (de)serializzazione ------------------------------------------------------


def _tag_da_modalita(modalita: Modalita) -> str:
    match modalita:
        case ModalitaCertificata():
            return "certificata"
        case ModalitaStima():
            return "stima"


def _modalita_da_tag(tag: str) -> Modalita:
    if tag == "certificata":
        return ModalitaCertificata()
    if tag == "stima":
        return ModalitaStima()
    raise ValueError(f"modalita' sconosciuta: {tag!r}")


def _registro_a_dict(reg: RegistroScarti) -> dict[str, Any]:
    return {
        "tenuti": reg.tenuti,
        "scarti": [
            {"id_scatto": s.id_scatto, "criterio": s.criterio.name} for s in reg.scarti
        ],
    }


def _registro_da_dict(d: Mapping[str, Any]) -> RegistroScarti:
    scarti = tuple(
        Scarto(str(s["id_scatto"]), CriterioScarto[str(s["criterio"])])
        for s in d.get("scarti", [])
    )
    return RegistroScarti(tenuti=int(d["tenuti"]), scarti=scarti)


def campione_a_dict(c: CampioneGroundTruth) -> dict[str, Any]:
    return {
        "id": c.id,
        "descrizione": c.descrizione,
        "percorso_immagine": c.percorso_immagine,
        "riferimento": {
            "lato_mm": c.riferimento.lato_mm,
            "tolleranza_dim_mm": c.riferimento.tolleranza_dim_mm,
            "descrizione": c.riferimento.descrizione,
        },
        "target_px": {
            "x1": c.target.x1,
            "y1": c.target.y1,
            "x2": c.target.x2,
            "y2": c.target.y2,
            "sigma_px": c.target.sigma_px,
        },
        "vero": {"valore_mm": c.vero.valore_mm, "incertezza_mm": c.vero.incertezza_mm},
        "modalita": _tag_da_modalita(c.modalita),
        "scarti": _registro_a_dict(c.scarti),
        "metadati": dict(c.metadati),
    }


def campione_da_dict(d: Mapping[str, Any]) -> CampioneGroundTruth:
    rif = d["riferimento"]
    tgt = d["target_px"]
    vero = d["vero"]
    return CampioneGroundTruth(
        id=str(d["id"]),
        descrizione=str(d.get("descrizione", "")),
        percorso_immagine=str(d["percorso_immagine"]),
        riferimento=Riferimento(
            lato_mm=float(rif["lato_mm"]),
            tolleranza_dim_mm=float(rif["tolleranza_dim_mm"]),
            descrizione=str(rif.get("descrizione", "")),
        ),
        target=TargetAnnotato(
            x1=float(tgt["x1"]),
            y1=float(tgt["y1"]),
            x2=float(tgt["x2"]),
            y2=float(tgt["y2"]),
            sigma_px=float(tgt.get("sigma_px", 1.0)),
        ),
        vero=MisuraCalibro(
            valore_mm=float(vero["valore_mm"]),
            incertezza_mm=float(vero.get("incertezza_mm", 0.02)),
        ),
        modalita=_modalita_da_tag(str(d["modalita"])),
        scarti=_registro_da_dict(d.get("scarti", {"tenuti": 1})),
        metadati={str(k): str(v) for k, v in dict(d.get("metadati", {})).items()},
    )


def salva_campione(c: CampioneGroundTruth, percorso: Path) -> None:
    percorso.write_text(
        json.dumps(campione_a_dict(c), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def carica_dataset(radice: Path) -> list[CampioneGroundTruth]:
    """Carica i campioni da `radice/campioni/*.json` (nomi con `_` iniziale saltati)."""
    cartella = radice / "campioni"
    if not cartella.is_dir():
        return []
    campioni: list[CampioneGroundTruth] = []
    for percorso in sorted(cartella.glob("*.json")):
        if percorso.name.startswith("_"):
            continue
        dati: Any = json.loads(percorso.read_text(encoding="utf-8"))
        campioni.append(campione_da_dict(dati))
    return campioni
