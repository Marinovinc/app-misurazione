"""Smoke test del Passo 0: il pacchetto importa e il banco risponde."""

from __future__ import annotations

import misura
from misura.validazione import banco


def test_pacchetto_importa() -> None:
    assert misura.__version__ == "0.0.0"


def test_banco_main_ritorna_zero() -> None:
    assert banco.main() == 0
