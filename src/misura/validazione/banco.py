"""Banco di validazione: copertura empirica vs dichiarata, con controllo negativo.

Passa le scene sintetiche nella pipeline e conta quante volte il valore vero cade
entro l'incertezza dichiarata (k*sigma). Con `con_dimensionale=False` si esegue il
**controllo negativo** (correzione E): si tratta il riferimento come esatto,
omettendo la sua tolleranza da Sigma; se la copertura non crolla, il test non
stava verificando nulla.

ONESTA' (correzione E): il rumore casuale e' generato e propagato con lo stesso
modello, quindi la sua copertura e' nominale per costruzione. Il banco verifica
che la propagazione sia implementata correttamente, NON che il modello descriva
la realta'. La validazione vera e' la questione aperta #3 e richiede il dataset
reale al calibro.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..grandezza import GrandezzaIncerta
from ..pipeline import SegmentoPixel, misura_da_scala
from ..riferimento import Riferimento, scala_da_lato_pixel
from .sintetico import ScenaSintetica, genera_scene, scenario_predefinito

PREMESSA_ONESTA = (
    "Il banco sintetico verifica che la propagazione dell'incertezza sia "
    "implementata correttamente, NON che il modello descriva la realta'. "
    "La validazione vera richiede il dataset reale al calibro (questione aperta #3)."
)


@dataclass(frozen=True)
class RisultatoBanco:
    n: int
    k: float
    copertura: float
    copertura_nominale: float
    con_dimensionale: bool


def copertura_nominale(k: float) -> float:
    """Copertura gaussiana bilaterale per k sigma: erf(k / sqrt(2))."""
    return math.erf(k / math.sqrt(2.0))


def _scala_scena(scena: ScenaSintetica, con_dimensionale: bool) -> GrandezzaIncerta:
    rif = scena.parametri.riferimento
    if not con_dimensionale:
        # controllo negativo: riferimento trattato come esatto (nessuna tolleranza)
        rif = Riferimento(rif.lato_mm, 0.0, "senza tolleranza (controllo negativo)")
    return scala_da_lato_pixel(rif, scena.lato_rif_px_oss, scena.parametri.sigma_lato_px)


def valuta_copertura(
    scene: Sequence[ScenaSintetica], k: float = 2.0, con_dimensionale: bool = True
) -> RisultatoBanco:
    if len(scene) == 0:
        raise ValueError("nessuna scena")
    dentro = 0
    for scena in scene:
        scala = _scala_scena(scena, con_dimensionale)
        misura = misura_da_scala(
            scala,
            SegmentoPixel(scena.lato_target_px_oss, scena.parametri.sigma_seg_px),
        )
        incertezza_espansa = k * misura.deviazione
        if abs(misura.valore - scena.lato_target_mm_vero) <= incertezza_espansa:
            dentro += 1
    return RisultatoBanco(
        n=len(scene),
        k=k,
        copertura=dentro / len(scene),
        copertura_nominale=copertura_nominale(k),
        con_dimensionale=con_dimensionale,
    )


def main() -> int:
    print(PREMESSA_ONESTA)
    print()
    scene = genera_scene(scenario_predefinito(), n=5000, seed=20260801)
    con = valuta_copertura(scene, k=2.0, con_dimensionale=True)
    senza = valuta_copertura(scene, k=2.0, con_dimensionale=False)
    print(f"scene: {con.n}, k = {con.k}, copertura nominale ~ {con.copertura_nominale:.3f}")
    print(f"  con tolleranza dimensionale (corr. B):   copertura = {con.copertura:.3f}")
    print(f"  SENZA (controllo negativo, corr. E):     copertura = {senza.copertura:.3f}")
    if senza.copertura < con.copertura:
        print("  -> il controllo negativo fa crollare la copertura: il test ha denti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
