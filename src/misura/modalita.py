"""Le due modalita' come **tipi distinti**, non un booleano (§4.1).

Il rischio nominato nel concept e' che l'utente non distingua le due modalita',
perche' entrambe restituiscono un numero ugualmente autorevole. La difesa parte
dal dominio: sono due tipi diversi, non convertibili l'uno nell'altro. Nessuna
funzione qui trasforma una modalita' nell'altra: la transizione richiede
un'azione esplicita dell'utente (imposta al Passo 4), mai automatica.

Il "riferimento obbligatorio" della modalita' certificata e' dichiarato qui come
contratto e diventa un campo `Riferimento` non opzionale al Passo 5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ModalitaCertificata:
    """Live, guidata; riferimento obbligatorio; oggetto planare; target <1%."""

    richiede_riferimento: ClassVar[bool] = True
    tolleranza_relativa_obiettivo: float = 0.01


@dataclass(frozen=True)
class ModalitaStima:
    """Anche archivio; riferimento opzionale; oggetto qualsiasi; target 10-20%."""

    richiede_riferimento: ClassVar[bool] = False
    tolleranza_relativa_obiettivo: float = 0.15


Modalita = ModalitaCertificata | ModalitaStima
