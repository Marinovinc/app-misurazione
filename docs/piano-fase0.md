# Piano fase 0 — Nucleo metrologico

**Stato:** approvato. Incorpora le cinque correzioni (A–E) della revisione.
**Riferimento:** `concept-app-misurazione.md` v1.2.

---

## Domanda a cui la fase 0 risponde

> Quando la libreria dichiara ±X, l'errore reale cade entro ±X al tasso dichiarato —
> anche sotto **errore di scala di modo comune** e sotto **sistematici noti** —
> *e la propagazione dell'incertezza è implementata correttamente?*

Il deliverable è una libreria tipata (`mypy --strict` pulito) più un report del banco
sintetico. **Non** è un binario, non è un verticale, non c'è AI, non c'è cattura, non c'è UI.

### Cosa la fase 0 NON dimostra (correzione E)

Il banco sintetico genera il rumore con un modello e propaga l'incertezza con lo stesso
modello: la copertura risulta nominale **per costruzione**. Il banco verifica che
l'**implementazione** della propagazione sia corretta, non che il modello descriva la
realtà. La validazione vera è la **questione aperta #3** del concept e richiede il dataset
reale misurato al calibro. Questo va scritto in apertura di `docs/report-fase0.md`, esplicito
e non minimizzato.

**Rottura parziale della circolarità (correzione E).** Si separano due classi di rumore:

- **Rumore casuale** (pixel gaussiano): resta circolare per costruzione, verifica solo
  l'implementazione della propagazione lineare.
- **Sistematici realizzati** (inclinazione del piano del riferimento, errore di stampa della
  dimensione): iniettati come **valore concreto per scena**, estratto da una distribuzione,
  mentre la pipeline conosce solo il **limite**. Su molte scene la copertura diventa un test
  vero della conversione limite→Σ.
- **Controllo negativo:** si riesegue il banco omettendo il `SistematicoLimitato` da Σ e si
  verifica che la copertura **crolli**. Se non crolla, il test non stava verificando nulla.

---

## Invarianti che il nucleo impone (dal concept)

1. **`Misura` non esiste senza incertezza e provenienza** (§4.3, §9.4). Nel tipo, non nella UI.
2. **Le due modalità sono tipi distinti, non un booleano** (§4.1). Non confondibili, non
   auto-convertibili.
3. **Il banco di validazione è in fase 0** (§7.2), non rinviato.

---

## Modello dell'incertezza (correzioni A, B, D)

### Incertezza come tipo, rappresentazione affine (#2a, #2b)

Una grandezza incerta è un **valore nominale + combinazione lineare di sorgenti indipendenti**.
La covarianza — inclusa quella incrociata — si *deriva*. Il costruttore accetta *e* restituisce
covarianza (#2a), ma internamente traccia le sorgenti (#2b): è l'unico modo di rappresentare
l'errore di scala di **modo comune** (tutte le misure della stessa immagine condividono il
fattore di scala, quindi sono correlate per costruzione).

### Due specie di sistematici, trattamenti opposti (correzione A)

Distinti **a livello di tipo**:

| Tipo | Cosa sai | Trattamento |
|---|---|---|
| `BiasCorreggibile` | segno e magnitudine stimabili (es. §9.1: fianchi autodichiarati −4,54 cm) | entra in **b**, si **sottrae** |
| `SistematicoLimitato` | esiste, ne stimi un **limite superiore**, ma non il valore in *questa* osservazione (non-complanarità, distorsione non corretta) | **non** si sottrae: si converte in incertezza standard e **gonfia Σ** |

**Vincolo di tipo non negoziabile:** il termine `b` del GLS accetta **solo** `BiasCorreggibile`.
Passare un `SistematicoLimitato` a `b` dev'essere un **errore di tipo**, non una violazione di
convenzione. Correggere per qualcosa che non si può osservare produce una stima falsamente
centrata con incertezza falsamente stretta — il fallimento contro cui è scritto il concept.

### Il riferimento è esso stesso una sorgente d'errore (correzione B)

L'incertezza di scala **non** viene solo dal rumore di localizzazione degli angoli. La dimensione
nota del riferimento **non è nota esattamente**; per un marker ArUco stampato la tolleranza di
stampa è probabilmente il termine **dominante** ("adatta alla pagina" sbaglia dell'1–3% in
silenzio — è la trappola delle due serie di banconote §5.1 in versione tipografica). La dimensione
del riferimento è una **sorgente indipendente di prima classe**, con tolleranza dipendente dal tipo:

| Riferimento | Tolleranza dimensionale |
|---|---|
| Tessera ID-1 (ISO/IEC 7810) | stretta |
| Marker stampato **non** verificato | larga, **dichiarata** |
| Marker stampato e verificato al calibro | stretta |

Questa tolleranza entra nel fattore di scala, quindi è anch'essa **modo comune**.

### Motore di fusione: GLS (#2b + #2c)

`stima = (Hᵀ Σ⁻¹ H)⁻¹ Hᵀ Σ⁻¹ (z − b)`
dove Σ porta le correlazioni di modo comune (#2b) e `b` **solo** i `BiasCorreggibile` (#2c, A).

---

## Distorsione: fuori perimetro fase 0 (correzione C)

La pipeline non ha un modello di intrinseci/distorsione da correggere. Iniettare distorsione nelle
scene sintetiche misurerebbe un errore su cui non si ha leva. **Scelta (b): la distorsione è
esclusa dalle scene sintetiche e dichiarata fuori perimetro fase 0**, annotata nel report. Coerente
con §3.3 e con la questione aperta #6 (profili di calibrazione per dispositivo).

---

## Esito a tre (correzione #3 originale)

`EsitoMisura = EntroTolleranza | FuoriTolleranza | RifiutoMotivato`

- **EntroTolleranza** — misura entro la tolleranza richiesta.
- **FuoriTolleranza** — misura valida ma fuori tolleranza, con `come_migliorare` (§7.1 modalità
  archivio). È il caso "dare un'idea" di §11: **mai** collassato nel rifiuto.
- **RifiutoMotivato** — non è possibile produrre un numero difendibile.

**Riferimento occluso, regola derivata dalla modalità:**

- Modalità **certificata** + occluso → `RifiutoMotivato` (degradare a stima in silenzio è il
  peccato contro cui è scritta §4.1).
- Modalità **stima** + occluso → misura con incertezza più larga.
- **La transizione tra modalità non è mai automatica:** richiede un'azione esplicita dell'utente.

---

## Struttura del pacchetto

```
app-misurazione/
  pyproject.toml            # Python >=3.12; deps + [tool.mypy] strict + [tool.pytest]
  src/misura/
    incertezza.py           # (1) Distribuzione affine con sorgenti condivise
    grandezza.py            # (1) GrandezzaIncerta: valore + incertezza come tipo con operazioni
    provenienza.py          # (2) Provenienza: misurata | dichiarata | inferita
    modalita.py             # (2) ModalitaCertificata / ModalitaStima — tipi distinti
    sistematici.py          # (A) BiasCorreggibile / SistematicoLimitato — tipi disgiunti
    osservazione.py         # (2) Osservazione: valore + covarianza + sistematici
    fusione.py              # (3) GLS: b accetta solo BiasCorreggibile; Σ correlata
    esito.py                # (4) EsitoMisura a tre
    riferimento.py          # (5,B) scala: rumore angoli + tolleranza dimensionale (modo comune)
    pipeline.py             # (5) riferimento -> scala -> misure -> esito
    scarti.py               # (6) RegistroScarti: scarto+criterio; conteggio -> incertezza
    validazione/
      sintetico.py          # (7,C,E) scene note; rumore casuale + sistematici realizzati; NO distorsione
      banco.py              # (7,E) % entro tolleranza; copertura vs dichiarata; controllo negativo
  tests/                    # property-based (hypothesis) + unit
  docs/
    piano-fase0.md          # questo documento
    report-fase0.md         # prodotto al Passo 8
```

> Nota di consolidamento: la configurazione `mypy --strict` sta in `[tool.mypy]` dentro
> `pyproject.toml` invece che in un `mypy.ini` separato — un file in meno, stessa severità.

---

## Sequenza — un commit per passo; ogni passo chiude con `mypy --strict` pulito e `pytest` verde. Tutto `@dataclass(frozen=True)`.

- **Passo 0 — Scaffold.** `pyproject.toml`, config strict, pacchetto, comando unico, smoke test.
- **Passo 1 — Incertezza come tipo.** Rappresentazione affine + `GrandezzaIncerta`.
  *Property test (D):* **entrambi** i test di modo comune — il rapporto con scala condivisa ha
  varianza *minore* (direzione innocua), e soprattutto la **somma** ha varianza *maggiore* del caso
  indipendente (l'invariante che conta: è lì che la correlazione ignorata sottostima).
- **Passo 2 — Provenienza, modalità, sistematici, osservazione.** Include `sistematici.py` (A):
  `BiasCorreggibile` e `SistematicoLimitato` disgiunti.
- **Passo 3 — Fusione GLS.** `b` tipato per accettare solo `BiasCorreggibile`.
  *Test:* fondere correlate come indipendenti **sottostima**; bias noto spostato e corretto;
  un `SistematicoLimitato` passato a `b` **non compila** (verifica mypy, non runtime).
- **Passo 4 — Esito a tre.** Regola occluso per modalità; nessuna transizione automatica.
- **Passo 5 — Riferimento e pipeline.** (B) scala = f(rumore angoli, tolleranza dimensionale del
  riferimento) come sorgente condivisa. Segmentazione dei bordi **iniettata** come input.
- **Passo 6 — Registro degli scarti.** Il conteggio gonfia l'incertezza.
  *Property test:* monotonicità — più scarti → incertezza **non** minore.
- **Passo 7 — Generatore sintetico + banco.** (C) niente distorsione. (E) rumore casuale +
  sistematici realizzati + controllo negativo.
- **Passo 8 — La risposta.** `docs/report-fase0.md` con la premessa E in apertura. Commit. Fine.

---

## Stack

Python ≥3.12 (locale: 3.13; 3.12 non installato — deviazione dichiarata), `mypy --strict`,
`@dataclass(frozen=True)`, `numpy`, `opencv-contrib-python` (ArUco, installato al Passo 5),
`pytest`, `hypothesis`. Il porting on-device è decisione separata e successiva.
