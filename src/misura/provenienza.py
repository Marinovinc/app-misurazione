"""Provenienza su ogni valore (§9.4).

Ogni misura in uscita porta la sua origine: serve a chi deve decidere di quale
numero fidarsi. E' il principio dell'incertezza che viaggia col dato (§4.3)
applicato alla fonte.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modalita import Modalita


@dataclass(frozen=True)
class MisurataDaApp:
    """Misurata dall'app, in una delle due modalita' (che resta allegata)."""

    modalita: Modalita


@dataclass(frozen=True)
class DichiarataDaUtente:
    """Inserita dall'utente. `guidata` distingue l'automisura guidata (§9.1,
    ~10 mm) da quella non guidata (~40 mm): non e' l'incertezza in se', che vive
    nella grandezza, ma il come e' stata ottenuta."""

    guidata: bool = False


@dataclass(frozen=True)
class InferitaDaModello:
    """Inferita da un modello (es. il manichino parametrico)."""

    nome_modello: str = ""


Provenienza = MisurataDaApp | DichiarataDaUtente | InferitaDaModello
