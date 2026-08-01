"""Verifica NEGATIVA di tipo (correzione A) — controllata da mypy, non a runtime.

Il nome senza prefisso ``test_`` fa si' che pytest non lo raccolga; mypy invece
lo analizza (rientra in ``files = [src, tests]``). Con ``warn_unused_ignores =
true``, se la chiamata marcata NON producesse davvero un errore di tipo, l'ignore
risulterebbe inutilizzato e mypy fallirebbe. Quindi: mypy pulito su questo file
== il termine `b` accetta solo `BiasCorreggibile`.
"""

from __future__ import annotations

from misura.fusione import correggi_bias
from misura.grandezza import GrandezzaIncerta
from misura.sistematici import BiasCorreggibile, SistematicoLimitato


def _scenari() -> None:
    g = GrandezzaIncerta.costante(90.0)

    # Consentito: un bias correggibile.
    correggi_bias(g, BiasCorreggibile(valore=-45.4))

    # Vietato a livello di tipo: un sistematico limitato non ha un valore da
    # sottrarre. Se questa riga smettesse di essere un errore, warn_unused_ignores
    # farebbe fallire mypy.
    correggi_bias(g, SistematicoLimitato(3.0))  # type: ignore[arg-type]
