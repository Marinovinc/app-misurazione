"""Esito di una misura: tre esiti, non due.

    EsitoMisura = EntroTolleranza | FuoriTolleranza | RifiutoMotivato

- `EntroTolleranza`: la misura sta entro la tolleranza richiesta.
- `FuoriTolleranza`: misura **valida** ma fuori tolleranza, con l'indicazione di
  cosa la migliorerebbe (§7.1, modalita' archivio). E' il caso "dare un'idea" di
  §11 e non va **mai** collassato nel rifiuto.
- `RifiutoMotivato`: non e' possibile produrre un numero difendibile.

La tolleranza e' una semi-ampiezza **assoluta** in mm a un dato livello di
copertura (§8: mai una percentuale globale). Una misura la rispetta se la sua
incertezza espansa k*sigma non supera la semi-ampiezza.

Regola del riferimento occluso, derivata dalla modalita' (#3): in certificata si
rifiuta (degradare a stima in silenzio e' il peccato contro cui e' scritta §4.1);
in stima si misura con incertezza piu' larga. La transizione tra modalita' non e'
mai automatica: richiede un'azione esplicita dell'utente, qui resa un token
`ConfermaUtente` che il chiamante deve costruire deliberatamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from .grandezza import GrandezzaIncerta
from .modalita import Modalita, ModalitaCertificata, ModalitaStima
from .provenienza import Provenienza


@dataclass(frozen=True)
class Tolleranza:
    """Semi-ampiezza assoluta richiesta (mm) a un fattore di copertura k."""

    semiampiezza: float
    copertura_k: float = 2.0  # k=2 ~ 95% per una gaussiana

    def __post_init__(self) -> None:
        if self.semiampiezza <= 0.0:
            raise ValueError("la semi-ampiezza dev'essere positiva")
        if self.copertura_k <= 0.0:
            raise ValueError("il fattore di copertura dev'essere positivo")


@dataclass(frozen=True)
class EntroTolleranza:
    misura: GrandezzaIncerta
    provenienza: Provenienza
    tolleranza: Tolleranza

    @property
    def incertezza_espansa(self) -> float:
        return self.tolleranza.copertura_k * self.misura.deviazione


@dataclass(frozen=True)
class FuoriTolleranza:
    misura: GrandezzaIncerta
    provenienza: Provenienza
    tolleranza: Tolleranza
    come_migliorare: str

    @property
    def incertezza_espansa(self) -> float:
        return self.tolleranza.copertura_k * self.misura.deviazione


@dataclass(frozen=True)
class RifiutoMotivato:
    motivo: str


EsitoMisura = EntroTolleranza | FuoriTolleranza | RifiutoMotivato

MOTIVO_OCCLUSO_CERTIFICATA = (
    "riferimento occluso in modalita' certificata: degradare a stima richiede "
    "un'azione esplicita dell'utente, non avviene in automatico"
)


def _messaggio_miglioramento(espansa: float, richiesta: float) -> str:
    return (
        f"incertezza attuale +/-{espansa:.1f} mm, richiesta +/-{richiesta:.1f} mm: "
        "servono osservazioni aggiuntive (nuove angolazioni) per ridurla"
    )


def valuta(
    misura: GrandezzaIncerta, provenienza: Provenienza, tolleranza: Tolleranza
) -> EntroTolleranza | FuoriTolleranza:
    """Classifica una misura valida come entro o fuori tolleranza.

    Non restituisce mai un rifiuto: qui la misura esiste. Il rifiuto nasce a
    monte (riferimento occluso in certificata, riferimenti divergenti, ...).
    """
    espansa = tolleranza.copertura_k * misura.deviazione
    if espansa <= tolleranza.semiampiezza:
        return EntroTolleranza(misura, provenienza, tolleranza)
    return FuoriTolleranza(
        misura,
        provenienza,
        tolleranza,
        _messaggio_miglioramento(espansa, tolleranza.semiampiezza),
    )


def gestisci_riferimento_occluso(
    modalita: Modalita,
    provenienza: Provenienza,
    tolleranza: Tolleranza,
    misura_stima: GrandezzaIncerta | None = None,
) -> EsitoMisura:
    """Applica la regola del riferimento occluso in funzione della modalita'."""
    match modalita:
        case ModalitaCertificata():
            return RifiutoMotivato(MOTIVO_OCCLUSO_CERTIFICATA)
        case ModalitaStima():
            if misura_stima is None:
                return RifiutoMotivato(
                    "riferimento occluso e nessuna stima disponibile"
                )
            return valuta(misura_stima, provenienza, tolleranza)
        case _:
            assert_never(modalita)


@dataclass(frozen=True)
class ConfermaUtente:
    """Token di un'azione esplicita dell'utente.

    Esiste per rendere impossibile una transizione di modalita' 'per svista':
    non c'e' conversione implicita da certificata a stima; passa solo di qui, e
    questo token va costruito deliberatamente dal chiamante.
    """

    motivazione: str


def transizione_certificata_a_stima(conferma: ConfermaUtente) -> ModalitaStima:
    """Unica via da certificata a stima. Richiede un `ConfermaUtente` esplicito;
    il parametro non e' opzionale, quindi la transizione non e' mai automatica."""
    _ = conferma
    return ModalitaStima()


MOTIVO_CONDIZIONI_NON_PIENE = (
    "condizioni della modalita' certificata non piene: misurare in stima "
    "richiede un'azione esplicita dell'utente, non avviene in automatico"
)


def degrada_a_stima(
    misura: GrandezzaIncerta,
    provenienza: Provenienza,
    tolleranza: Tolleranza,
    conferma: ConfermaUtente | None,
) -> EsitoMisura:
    """Misura in stima quando la certificata era possibile ma non e' disponibile.

    Generalizza `gestisci_riferimento_occluso` al caso in cui a mancare non e' il
    riferimento ma una delle altre condizioni (il secondo riferimento di §5.3).
    La forma della regola e' la stessa e per la stessa ragione: **il degrado non
    e' un ripiego automatico**. Senza conferma non esce un numero, esce un
    rifiuto — perche' un numero in stima presentato dove l'utente si aspettava
    una certificata e' esattamente il fraintendimento che §4.1 chiama il rischio
    principale.

    `conferma` e' opzionale nella firma proprio per poter rappresentare la sua
    assenza; il degrado, pero', passa comunque dall'unica via che esiste.
    """
    if conferma is None:
        return RifiutoMotivato(MOTIVO_CONDIZIONI_NON_PIENE)
    transizione_certificata_a_stima(conferma)
    return valuta(misura, provenienza, tolleranza)
