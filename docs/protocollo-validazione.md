# Protocollo di validazione (§7.2, questione aperta #3)

Documento operativo: come si valida l'incertezza dichiarata contro il vero
misurato al calibro. Definirlo **subito** e' un requisito del concept, non un
rinvio: senza, la barra d'incertezza (§7.1) comunica fiducia falsa.

## Cosa si misura, e perche' due criteri

Il protocollo riporta **due** frazioni distinte, che non vanno confuse:

1. **Frazione entro tolleranza** — quante misure cadono entro ±T dal vero. E' il
   **criterio di accettazione** (§7.2), espresso come percentuale (es. "95% entro
   ±T"), **non** come errore medio: un errore medio basso con code lunghe perde la
   fiducia dell'utente al terzo utilizzo.

2. **Copertura dell'incertezza dichiarata** — quante volte il vero cade entro il
   ±X che l'app dichiara (k·σ). Misura l'**onesta'** del numero: se l'app dichiara
   ±10 mm, circa il 95% dei veri deve cadere entro 10 mm. Dichiarare ±10 quando la
   realta' e' ±25 e' peggio che non mostrare nulla.

Un sistema puo' passare l'una e fallire l'altra: essere accurato ma dichiarare
un'incertezza troppo stretta, o dichiarare onestamente un'incertezza larga che
pero' non basta alla tolleranza richiesta.

## Procedura per campione

1. **Riferimento** ArUco visibile e **complanare** al target (§5.3). Su superfici
   curve la proiezione e' distorta: fuori protocollo.
2. **Vero al calibro**, con la sua incertezza (il calibro e' uno strumento, non
   una verita' assoluta): entra nella banda di copertura.
3. **Annotazione del target** come estremi in pixel (segmentazione iniettata,
   confine fase 0).
4. Modalita' dichiarata, registro degli scarti compilato.

## Esecuzione

```bash
.venv/Scripts/python -m misura.validazione.protocollo
```

Con `dataset/` vuoto il protocollo lo dichiara e non finge un risultato.

## Cosa resta da decidere (prima di raccogliere davvero)

- **Numerosita' e stratificazione** del dataset: dimensioni oggetto, tipi di
  riferimento (tessera ID-1 / marker verificato / non verificato), distanze,
  dispositivi. La tolleranza va definita in **mm assoluti per punto** (§8), mai in
  percentuale globale.
- **Tolleranza di accettazione T e soglia** (default: 95% entro ±T). Vanno fissate
  per verticale, non in astratto.
- **Separazione train/validazione** se i dati serviranno anche a calibrare le
  scelte di modello euristiche (`sigma_lato`, `fattore_inflazione`): calibrare e
  validare sugli stessi dati richiude la circolarita' che la fase 0 ha aperto a
  fatica.
