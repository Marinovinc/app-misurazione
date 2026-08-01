# Report fase 0 — La propagazione dell'incertezza è implementata correttamente?

**Data:** 1 agosto 2026 · **Riferimento:** `concept-app-misurazione.md` v1.2 · `docs/piano-fase0.md`

---

## Premessa di onestà — leggere prima dei numeri

**Questa fase 0 non dimostra che raggiungiamo ±X.** Il banco sintetico genera il
rumore con un modello e propaga l'incertezza con lo stesso modello: per la parte
di rumore **casuale** la copertura è nominale *per costruzione*. Il banco
verifica che l'**implementazione** della propagazione sia corretta, non che il
modello descriva la realtà.

La validazione vera è la **questione aperta #3** del concept e richiede un dataset
reale di oggetti a dimensione nota misurati al calibro. Finché quel dataset non
esiste, nessun numero di copertura qui dentro è una promessa di accuratezza sul
campo. Chi legge questo report e ne trae "l'app misura al 99,9%" lo sta leggendo
male: quel 99,9% è la copertura di un banco che valida se stesso sulla parte
casuale.

Ciò che il banco **sì** verifica in modo non circolare è la conversione
limite→incertezza dei sistematici, grazie al controllo negativo descritto sotto.

---

## La domanda

> Quando la libreria dichiara ±X, l'errore reale cade entro ±X al tasso
> dichiarato — anche sotto errore di scala di modo comune e sotto sistematici
> noti — e la propagazione è implementata correttamente?

## La risposta

**Sì, con una riserva esplicita sul significato del banco.** La propagazione è
implementata correttamente: correlazioni di modo comune, bias correggibile,
sistematici limitati e inflazione da scarti si propagano come atteso, tutto sotto
`mypy --strict` e verificato da 52 test (di cui diversi property-based su
Hypothesis). Il controllo negativo dimostra che la copertura non è un artefatto.

---

## Risultati del banco

Comando riproducibile:

```bash
.venv/Scripts/python -m misura.validazione.banco
```

Scenario predefinito: 5000 scene, riferimento marker stampato **non verificato**
(limite di stampa 1 mm su 50 mm), scala 0,25 mm/px, target 100 mm, rumore
d'angolo 0,3 px, rumore di segmentazione 0,5 px. Fattore di copertura k = 2.

| Configurazione | Copertura |
|---|---|
| Copertura nominale (gaussiana, k=2) | ~0,954 |
| **Con** tolleranza dimensionale del riferimento (corr. B) | **0,999** |
| **Senza** — controllo negativo (corr. E) | **0,201** |

### Lettura dei numeri

- **Il controllo negativo ha denti.** Omettere la tolleranza dimensionale del
  riferimento da Σ fa crollare la copertura da 0,999 a 0,201. Se non fosse
  crollata, il banco non starebbe verificando nulla: è la prova che la
  conversione limite→σ del riferimento (correzione B) sta facendo un lavoro
  reale, non decorativo.

- **A k=2 il banco sovra-copre (0,999 > 0,954), ed è corretto.** Nello scenario
  predefinito il sistematico di stampa domina, ed è modellato come **uniforme**
  su ±limite. Tutta la massa di un'uniforme sta entro ±√3·σ ≈ 1,73·σ < 2·σ:
  quindi a k=2, tarato sul gaussiano, quasi tutte le misure cadono dentro. La
  conversione limite→σ (σ = limite/√3, GUM tipo B) è **conservativa** in questo
  regime — una proprietà onesta da conoscere, non un bug.

---

## Cosa il nucleo garantisce (invarianti verificate dai test)

- **`Misura`/`GrandezzaIncerta` non esiste senza incertezza e provenienza** — nel
  tipo, non nella UI (§4.3, §9.4).
- **Modo comune (#2b)** — la scala dal riferimento è una sorgente condivisa; la
  somma di due misure che la condividono ha varianza *maggiore* del caso
  indipendente. Trattarle come indipendenti sottostima l'incertezza, ed è ciò che
  la fusione GLS con Σ congiunta impedisce.
- **Due specie di sistematici, trattamenti opposti (corr. A)** — `BiasCorreggibile`
  entra nel termine `b` e si sottrae; `SistematicoLimitato` gonfia Σ. Il vincolo è
  di tipo: passare un limitato a `b` **non compila** (mypy come oracolo, via
  `warn_unused_ignores`).
- **Il riferimento è una sorgente d'errore (corr. B)** — la tolleranza di stampa
  domina il rumore d'angolo di ~40× per un marker non verificato.
- **Esito a tre (#3)** — `EntroTolleranza | FuoriTolleranza | RifiutoMotivato`; il
  "dare un'idea" non è mai collassato nel rifiuto.
- **Regola dell'occluso per modalità** — certificata → rifiuto; stima → misura più
  larga; transizione mai automatica (serve `ConfermaUtente`).
- **Registro scarti (§6.3)** — criteri di scarto indipendenti dal risultato
  (guard strutturale); più scarti → incertezza non decrescente.

---

## Cosa NON è dimostrato e resta aperto

- **Accuratezza reale sul campo** — questione aperta #3: serve il dataset al
  calibro. Il banco non lo sostituisce.
- **Distorsione ottica** — dichiarata fuori perimetro fase 0 (corr. C); questione
  aperta #6 (profili di calibrazione per dispositivo).
- **Scelte di modello euristiche da calibrare** — `sigma_lato` del riferimento e
  `fattore_inflazione` degli scarti sono ragionevoli ma non tarati sui dati.
- **Rilevamento reale end-to-end** — il rilevamento ArUco è validato (Passo 5) ma
  il banco isola la propagazione e non stressa il rilevamento sotto sfocatura,
  illuminazione, occlusione parziale.

---

## Verifica

```bash
.venv/Scripts/python -m mypy      # strict, pulito
.venv/Scripts/python -m pytest    # 52 test verdi
```
