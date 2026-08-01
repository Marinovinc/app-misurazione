"""Generatore di scene sintetiche (Passo 7).

Lavora al livello geometrico/pixel: genera direttamente le osservazioni in pixel
del riferimento e del target, con geometria e camera note. Il rilevamento ArUco
reale e' gia' validato al Passo 5; qui si isola la **propagazione**.

Correzione C: **nessuna distorsione**. La pipeline non ha un modello di
intrinseci da correggere, quindi iniettare distorsione misurerebbe un errore su
cui non si ha leva. Fuori perimetro fase 0 (§3.3, questione aperta #6).

Correzione E, rottura parziale della circolarita'. Si separano due classi di
rumore:
- **casuale** (angoli, segmentazione): gaussiano, generato e propagato con lo
  stesso sigma -> circolare per costruzione, verifica solo l'implementazione;
- **sistematico realizzato**: l'errore di stampa del riferimento e' estratto
  come **valore concreto per scena** da un'uniforme su +/- limite, mentre la
  pipeline conosce solo il limite (via `Riferimento.dimensione_incerta`). Su
  molte scene la copertura diventa un test vero della conversione limite->sigma.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..riferimento import Riferimento, marker_stampato_non_verificato


@dataclass(frozen=True)
class ParametriScena:
    scala_vera_mm_px: float
    lato_target_mm: float
    riferimento: Riferimento
    sigma_lato_px: float
    sigma_seg_px: float


@dataclass(frozen=True)
class ScenaSintetica:
    parametri: ParametriScena
    lato_rif_px_oss: float
    lato_target_px_oss: float
    lato_target_mm_vero: float
    errore_stampa_mm: float  # sistematico realizzato: SOLO diagnostica, la pipeline non lo usa


def scenario_predefinito() -> ParametriScena:
    """Scenario in cui l'errore di stampa del riferimento domina il rumore casuale
    (e' il regime della correzione B, quello che il controllo negativo colpisce)."""
    return ParametriScena(
        scala_vera_mm_px=0.25,  # 0.25 mm/px
        lato_target_mm=100.0,
        riferimento=marker_stampato_non_verificato(50.0, 0.02),  # limite 1 mm
        sigma_lato_px=0.3,
        sigma_seg_px=0.5,
    )


def genera_scene(
    parametri: ParametriScena, n: int, seed: int
) -> list[ScenaSintetica]:
    """Genera `n` scene deterministiche (seed) dalle parametrizzazioni date."""
    rng = np.random.default_rng(seed)
    limite = parametri.riferimento.tolleranza_dim_mm
    scene: list[ScenaSintetica] = []
    for _ in range(n):
        # sistematico realizzato: errore di stampa uniforme su +/- limite
        u = float(rng.uniform(-limite, limite)) if limite > 0.0 else 0.0
        lato_rif_mm_reale = parametri.riferimento.lato_mm + u
        lato_rif_px_vero = lato_rif_mm_reale / parametri.scala_vera_mm_px
        lato_rif_px_oss = lato_rif_px_vero + float(rng.normal(0.0, parametri.sigma_lato_px))

        lato_target_px_vero = parametri.lato_target_mm / parametri.scala_vera_mm_px
        lato_target_px_oss = lato_target_px_vero + float(
            rng.normal(0.0, parametri.sigma_seg_px)
        )

        scene.append(
            ScenaSintetica(
                parametri=parametri,
                lato_rif_px_oss=lato_rif_px_oss,
                lato_target_px_oss=lato_target_px_oss,
                lato_target_mm_vero=parametri.lato_target_mm,
                errore_stampa_mm=u,
            )
        )
    return scene
