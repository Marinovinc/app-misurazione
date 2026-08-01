"""Doppio riferimento: la scala **verificata**, non dichiarata (§5.3).

Con due riferimenti in inquadratura si calcola la scala da entrambi e le si
confronta. Se divergono oltre soglia l'app rifiuta la misura invece di
restituire un numero: e' il modo piu' economico per trasformare "a volte sbaglia
del 6%" in "a volte dice che non puo' misurare".

**La soglia non e' un numero scelto a mano.** Le due scale sono grandezze
incerte; la loro differenza propaga da se' le sorgenti, incluse quelle
condivise. Sono compatibili se

    |s1 - s2|  <=  k * u(s1 - s2)

cioe' il test di compatibilita' GUM, con lo stesso k=2 gia' usato per
l'incertezza espansa (§4.3). Se il riferimento e' unico, quel test non esiste e
l'errore di scala resta invisibile: e' precisamente il caso delle due serie di
banconote da 100 euro (§5.1), dove sbagliare serie costa il 6,5% in silenzio.

Concordi, le due scale vengono **fuse** per minimi quadrati generalizzati: la
scala risultante ha incertezza minore di entrambe (§9.2, due osservazioni
indipendenti mediocri battono una buona). La verifica quindi non costa
precisione, la produce.

**Perche' questo non viola il guard di `scarti.py` (§6.3).** Li' l'invariante e'
che uno scatto non si scarta perche' *disaccorda col risultato*: un sistema che
elimina cio' che lo contraddice conferma se stesso e restringe artificialmente
l'incertezza. Qui non si scarta niente e non si sceglie la scala "migliore" — si
rifiuta **l'intera misura**. La differenza e' resa strutturale: `ScaleDiscordi`
non espone nessuna scala, quindi non c'e' modo di proseguire con una delle due.
"""

from __future__ import annotations

from dataclasses import dataclass

from .esito import RifiutoMotivato
from .fusione import fondi
from .grandezza import GrandezzaIncerta
from .osservazione import Osservazione
from .provenienza import Provenienza

COPERTURA_COMPATIBILITA_K = 2.0
"""Stesso k dell'incertezza espansa: la soglia di compatibilita' e' il medesimo
livello di copertura applicato alla differenza, non un parametro indipendente."""


@dataclass(frozen=True)
class ScaleConcordi:
    """Le due scale sono compatibili: fuse in una scala unica, piu' stretta.

    `divergenza` e `soglia` restano allegate perche' il fatto che la verifica sia
    stata **superata** e' un'informazione sul dato, non un dettaglio interno: e'
    cio' che distingue una scala verificata da una semplicemente dichiarata.
    """

    scala: GrandezzaIncerta
    divergenza: float
    soglia: float


@dataclass(frozen=True)
class ScaleDiscordi:
    """Le due scale non sono compatibili: nessun numero difendibile.

    Deliberatamente **senza** un campo `scala`: sapere che una delle due e'
    sbagliata senza sapere quale non autorizza a usarne una.
    """

    prima: GrandezzaIncerta
    seconda: GrandezzaIncerta
    divergenza: float
    soglia: float

    @property
    def motivo(self) -> str:
        return (
            f"i due riferimenti danno scale che non concordano: "
            f"{self.prima.valore:.4f} e {self.seconda.valore:.4f} mm/px, "
            f"divergenza {self.divergenza:.4f} oltre la soglia di compatibilita' "
            f"{self.soglia:.4f} (k={COPERTURA_COMPATIBILITA_K:g}). Una delle due e' "
            f"sbagliata e non e' possibile sapere quale: rifare lo scatto con "
            f"entrambi i riferimenti complanari all'oggetto"
        )


EsitoDoppioRiferimento = ScaleConcordi | ScaleDiscordi


def confronta_scale(
    prima: GrandezzaIncerta,
    seconda: GrandezzaIncerta,
    provenienza: Provenienza,
    copertura_k: float = COPERTURA_COMPATIBILITA_K,
) -> EsitoDoppioRiferimento:
    """Test di compatibilita' GUM fra due scale, e fusione GLS se lo superano."""
    if copertura_k <= 0.0:
        raise ValueError("il fattore di copertura dev'essere positivo")

    differenza = prima - seconda
    divergenza = abs(differenza.valore)
    soglia = copertura_k * differenza.deviazione

    if divergenza > soglia:
        return ScaleDiscordi(prima, seconda, divergenza, soglia)

    # Differenza a varianza nulla: le due scale non sono due osservazioni
    # indipendenti ma la stessa grandezza scritta due volte. Fonderle sarebbe
    # mal posto (Sigma singolare) e non aggiungerebbe informazione.
    if differenza.varianza == 0.0:
        return ScaleConcordi(prima, divergenza, soglia)

    fusa = fondi(
        [
            Osservazione(prima, provenienza),
            Osservazione(seconda, provenienza),
        ]
    )
    return ScaleConcordi(fusa, divergenza, soglia)


def scala_o_rifiuto(
    esito: EsitoDoppioRiferimento,
) -> GrandezzaIncerta | RifiutoMotivato:
    """Adatta l'esito del confronto alla pipeline di misura."""
    match esito:
        case ScaleConcordi():
            return esito.scala
        case ScaleDiscordi():
            return RifiutoMotivato(esito.motivo)
