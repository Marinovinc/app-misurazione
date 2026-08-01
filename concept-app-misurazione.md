# App di misurazione da immagini — documento di concept

**Versione:** 1.2 — 1 agosto 2026
**Stato:** base di lavoro per la fase di progettazione. Contiene decisioni prese, vincoli verificati e questioni ancora aperte.

---

## 1. Obiettivo

Sviluppare un'applicazione che ricavi misure metriche di oggetti, ambienti e corpi a partire da fotografie e video acquisiti con smartphone, senza hardware dedicato.

La scelta dell'approccio fotografico non è di ripiego: è la risposta a un vincolo di mercato preciso, documentato nella sezione 2. Le soluzioni basate su sensori di profondità funzionano bene ma solo su una minoranza di dispositivi. L'approccio da immagine funziona ovunque, e in più permette di lavorare su materiale già esistente o inviato da terzi.

---

## 2. Screening di mercato

### 2.1 Le due piattaforme

**Apple.** Vantaggio hardware consolidato. Il LiDAR misura le distanze con luce laser ed è presente sui modelli Pro dal 2020 (iPhone 12 Pro, iPad Pro). Sopra c'è RoomPlan, API Swift basata su ARKit che genera planimetrie 3D con dimensioni e tipologia dei mobili, producendo un modello parametrico di pareti, porte, finestre e arredi esportabile in USD/USDZ verso Cinema 4D, Shapr3D o AutoCAD.

L'app di misura di sistema si chiama **Metro** (Measure) ed è preinstallata su tutti gli iPhone e iPad recenti. Usa ARKit per rilevare le superfici; sui modelli Pro con LiDAR rileva i bordi più rapidamente e misura l'altezza delle persone.

**Android.** Nessun equivalente universale.

- Google ha rimosso l'app **Measure** dal Play Store nel 2021, dichiarando di non poterne più sostenere la manutenzione e rimandando alle alternative di terze parti. Non è mai stata sostituita. Sui Pixel oggi non esiste app di misura di sistema.
- Samsung ha **Quick Measure** (distanza, area, misura 3D, lunghezza tra due punti), ma non è preinstallata — va scaricata dall'AR Zone — e richiede un sensore ToF. Samsung ha rimosso il ToF dopo il Note 20 Ultra, sostituendolo con un laser di autofocus. L'app risulta incompatibile con la maggior parte dei telefoni Samsung.
- Google offre agli sviluppatori la **Depth API** di ARCore, supportata solo su un sottoinsieme dei dispositivi ARCore.

**Conseguenza strategica.** Su iOS esiste una capacità di misura garantita e gratuita su ogni dispositivo: bisogna offrire qualcosa che Metro non fa. Su Android il campo è vuoto ma il parco dispositivi è eterogeneo e non consente di promettere precisione costante. L'approccio da immagine aggira entrambi i problemi.

### 2.2 Categorie di soluzioni esistenti

| Categoria | Esempi | Note |
|---|---|---|
| Righelli AR consumer | AR Ruler, Smart Measure, SmartRuler | Gratuiti, spesso con pubblicità |
| Planimetrie / edilizia | magicplan, Canvas, SiteScape, Matterport | magicplan: immobiliare, restauro, assicurazioni. Canvas: scan-to-CAD con conversione umana in 1–2 giorni |
| Scansione 3D | Polycam, Scaniverse, KIRI Engine, RealityScan | iOS + Android, LiDAR dove disponibile |
| Logistica | vMeasure, Optioryx Flux, CargoMatrix | Vedi 2.3 |
| Corpo / moda | 3DLOOK, Mirrorsize | Misure da due foto |
| Calzature | Findmeashoe, Aetrex SizeRight, Snapfeet, MS ShoeSizer | Verticale maturo e affollato |
| Sanità | imito, CARES4WOUNDS, eKare inSight | Misura di ferite croniche |

### 2.3 Il riferimento professionale in logistica

vMeasure usa il LiDAR di iPhone 15 Pro e successivi per dimensionare colli con precisione dichiarata fino a ±0,2 pollici (circa 5 mm) in meno di un secondo: la point cloud viene elaborata per rilevare i contorni, si estraggono L/W/H, si genera un'immagine annotata con bounding box per l'audit trail e i dati si sincronizzano con WMS o software di spedizione.

Optioryx Flux funziona su dispositivi con LiDAR o ToF: iPad Pro 2020+, iPhone 13 Pro+, Zebra TC53/58.

**Dato di calibrazione delle aspettative:** ±5 mm su un collo da 30 cm equivale all'1,7% — cioè la soluzione professionale con sensore laser dedicato non raggiunge l'1% su oggetti piccoli.

---

## 3. Vincoli fisici

### 3.1 L'ambiguità di scala

Una fotografia non contiene informazioni metriche. Una scatola piccola vicina e una grande lontana producono la stessa immagine. Serve sempre una fonte di scala esterna. Le opzioni:

1. **Oggetto di riferimento di dimensione nota** — marker fiduciale, banconota, tessera, foglio A4. Robusto, spiegabile, indipendente dall'hardware.
2. **Stima metrica della profondità con AI** — Depth Anything V2, Depth Pro, Metric3D, UniDepth. Nessun riferimento richiesto, ma vedi 3.2.
3. **Fotogrammetria multi-scatto** — ricostruisce la geometria ma sempre a meno di un fattore di scala: serve comunque un riferimento oppure i dati inerziali.

### 3.2 Accuratezza reale dei modelli AI

Benchmark 2025 su 93 immagini con ground truth misurato:

| Metodo | MAE | Errore relativo |
|---|---|---|
| Depth Anything V2 | 0,454 m | 0,211 |
| Metric3D v2 | 0,867 m | 0,285 |
| ML Depth Pro | 1,127 m | 0,336 |
| ZoeDepth | 3,087 m | 1,068 |
| Baseline geometrico ChARUCO | 0,505 m | 0,282 |

Due letture importanti. Primo: il modello migliore ha un errore relativo del **21%**, un ordine di grandezza sopra il target professionale. Secondo: il **baseline geometrico con marker è alla pari col miglior modello AI**, con una frazione della complessità e con errori prevedibili anziché imprevedibili.

Il problema strutturale dei modelli metrici monoculari è la generalizzazione: l'accuratezza resta confinata ai domini di training e degrada su domini non visti anche con gap moderati.

Studio comparativo su app di scansione: Polycam Pro ha mostrato un errore medio del 42,58% contro il 10,36% di Scaniverse su un modello architettonico in scala. I Gaussian splat sembrano fotorealistici ma non sono metricamente affidabili.

### 3.3 Perché <1% non è raggiungibile su foto arbitrarie

Il fattore limitante non è la risoluzione del sensore ma le incognite geometriche. Le foto d'archivio ne aggiungono di irrisolvibili: intrinseci sconosciuti o assenti dagli EXIF, crop e ritocchi che invalidano la focale, distorsione dell'obiettivo non corretta. Quest'ultima non è nemmeno costante per dispositivo: dipende dalla profondità di campo, e per distanze oggetto sotto il metro diventa una causa maggiore di errore.

**L'1% è raggiungibile solo in un regime ristretto con quattro condizioni simultanee:**

1. Misura planare — contorno di un oggetto piatto, non le tre dimensioni di un solido
2. Riferimento obbligatorio e complanare con l'oggetto
3. Cattura guidata live, con verifica di perpendicolarità, distanza e nitidezza
4. Profilo di calibrazione per modello di dispositivo

---

## 4. Decisioni prese

### 4.1 Due modalità dichiarate, mai mescolate

| | Modalità certificata | Modalità stima |
|---|---|---|
| Acquisizione | Live, guidata | Anche archivio |
| Riferimento | Obbligatorio | Opzionale |
| Oggetto | Planare / quasi-planare | Qualsiasi |
| Target | <1% | 10–20% |
| Uso | Decisioni professionali | Triage, preventivi di massima |

Il rischio principale è che l'utente non distingua le due modalità, perché entrambe restituiscono un numero che appare ugualmente autorevole.

### 4.2 Architettura: geometria per la scala, AI per la segmentazione

L'errore classico è scegliere tra geometria e AI. La combinazione corretta le usa per compiti diversi:

- **Scala** dal riferimento geometrico — robusto e verificabile
- **Segmentazione** dall'AI — individuare i bordi dell'oggetto, che è il vero attrito per l'utente
- **Depth AI** come fallback dichiarato quando il riferimento non è visibile

### 4.3 L'incertezza fa parte del dato

Ogni misura viene restituita con la sua incertezza, mai come numero secco. Motivazioni convergenti:

- Un modello AI produce sempre un numero plausibile anche quando sbaglia del 30%: è il principale rischio reputazionale
- "42 cm" con un avviso accanto viene letto come 42. "42 ± 4 cm" non si può fraintendere
- Un avviso mostrato sempre viene ignorato sempre (assuefazione agli alert)

**L'incertezza deve viaggiare col dato, non con la schermata:** filigrana sull'immagine annotata, colonna dedicata nell'export, campo `estimated: true` nel payload API, etichetta nel PDF. È l'unica forma che sopravvive allo screenshot e al copia-incolla.

**Mostrare l'incertezza sempre, anche in modalità certificata,** con valori diversi. Se comparisse solo in assenza di riferimento, l'utente dedurrebbe per contrasto che con il riferimento il numero è esatto.

### 4.4 Perimetro logistica: solo uso interno

**Decisione: nessun uso per fatturazione.** Le misure in logistica servono a "dare un'idea".

Motivo: quando il costo di un servizio logistico è determinato dalle dimensioni, è un requisito di legge che lo strumento sia legal-for-trade. Chi usa una macchina non certificata può incorrere in multe pesanti, confisca dello strumento o chiusura dell'attività. Le certificazioni rilevanti sono NTEP (USA), Measurement Canada (Canada), OIML (61 stati membri), MID (UE).

Soglie certificate di riferimento: OIML ±5 mm su L/W e ±2 mm in altezza; NTEP ±0,2" su L/W e ±0,1" in altezza.

**Tutela operativa:** export etichettati come non idonei alla fatturazione, nessuna integrazione diretta verso i moduli di billing dei TMS. La certificazione riguarda l'uso, non l'intenzione dello sviluppatore: se un 3PL fattura con la nostra app il problema normativo è suo, ma il nostro prodotto ne è lo strumento.

Nota da un brevetto sui dimensionatori mobili: anche con certificazione, i dimensionatori mobili hanno tolleranze variabili perché lo stesso oggetto misurato da due posizioni diverse comporta angoli e distanze differenti.

---

## 5. Sistema di riferimento

### 5.1 Banconote — valutate e sconsigliate come soluzione primaria

Pro: unico oggetto di dimensione certificata che l'utente ha già in tasca, rettangolo con rapporto d'aspetto noto (utile per l'omografia), texture ricca.

Contro, in ordine di gravità:

**Trappola di classificazione.** Le banconote vanno prima riconosciute. In euro: €5 = 120×62, €10 = 127×67, €20 = 133×72, €50 = 140×77. Per €100 e €200 **circolano in parallelo due serie con dimensioni diverse**: nella serie Europa l'altezza è passata da 82 a 77 mm. Un €100 verde può quindi essere 147×82 o 147×77 — errore di scala del **6,5%** se l'app sbaglia serie, silenzioso e plausibile.

Il rapporto d'aspetto non basta a disambiguare: €20 = 1,847, €50 = 1,818, €100 ES2 = 1,909, €100 ES1 = 1,793. La distanza €20/€50 è dell'1,6%, dentro il rumore della stima prospettica. Serve un classificatore su colore e design, che diventa punto di guasto critico della catena metrologica.

**Problema fisico.** Fibra di cotone: si piega, si arriccia, si consuma ai bordi. Una nota non piana produce sottostima sistematica della scala.

**Problema legale — da verificare con un legale.** Le banconote euro portano la costellazione EURion, parte del Counterfeit Deterrence System: diversi software e scanner rifiutano di trattare immagini di banconote. Impatta l'elaborazione cloud e la costruzione di un dataset di training. Vanno inoltre verificate le regole BCE sulla riproduzione.

**Problema di UX.** Chiedere di esibire contanti in magazzino o in cantiere non è un'esperienza brillante.

### 5.2 Scala di riferimenti raccomandata

Il riferimento va scelto in funzione della dimensione dell'oggetto, perché ogni errore di localizzazione dei bordi viene amplificato dal rapporto tra le due scale. Un €20 da 133 mm che misura un oggetto da 1 m amplifica l'errore di 7,5 volte: per l'1% sull'oggetto servirebbe lo 0,13% sulla banconota, non realistico.

| Dimensione oggetto | Riferimento |
|---|---|
| Fino a ~30 cm | Tessera ID-1 (ISO/IEC 7810: 85,60 × 53,98 mm) o banconota |
| Fino a ~1,5 m | Foglio A4 (210 × 297 mm) |
| Oltre | Marker ArUco stampato A4/A3 |

**La tessera ID-1 è preferibile alla banconota** su oggetti piccoli: dimensione unica in tutto il mondo (nessuna classificazione, nessuna serie, nessuna valuta) e rigida, quindi resta piana. Non serve la carta di credito: va bene una tessera fedeltà, dei trasporti, della biblioteca — evitando ogni questione di privacy sui dati di pagamento.

Per il tier professionale a <1% il marker ArUco resta la strada obbligata: dimensione esatta, correzione d'errore, rilevamento sub-pixel degli angoli.

### 5.3 Regole operative

- Il riferimento va sul **piano che si sta misurando**. Su superfici curve (torace, rotoli, sacchi) la tessera è tangente al piano e la sua proiezione è distorta.
- **Doppio riferimento per validazione:** con due riferimenti in inquadratura si calcola la scala da entrambi e si confrontano. Se divergono oltre soglia, l'app rifiuta la misura invece di restituire un numero. È il modo più economico per trasformare "a volte sbaglia del 6%" in "a volte dice che non può misurare".

---

## 6. Acquisizione multi-vista

### 6.1 Cosa dà

- **Sblocca la terza dimensione** — una foto singola con marker misura bene solo ciò che giace nel piano del riferimento
- **Rende l'incertezza calcolabile** — dal bundle adjustment escono residui e quindi una covarianza: incertezza misurata sui dati, non stimata. Possibile anche il leave-one-out: ricalcolare escludendo una vista alla volta
- **Permette l'autocalibrazione** — con abbastanza viste si stimano focale e distorsione dalla scena

**Il multi-vista non risolve la scala.** Il riferimento serve comunque, ma basta **in una sola vista**: la scala si propaga attraverso la ricostruzione. L'utente può quindi togliere il riferimento dopo il primo scatto.

### 6.2 Video vs foto

Il video migliora la **cattura**, le foto restano migliori per la **precisione**.

Vantaggi del video:
- Elimina il problema dell'angolo di base: tra fotogrammi contigui cambia pochissimo, il tracking è molto più facile del matching a base larga
- Trasforma lo scarto in selezione: da centinaia di fotogrammi si scelgono i migliori con criteri positivi
- Chiusura d'anello: se l'utente completa il giro, si ottiene un vincolo geometrico forte contro la deriva
- **Se girato dentro l'app, dà accesso all'IMU** — stima di scala metrica senza riferimento fisico, potenzialmente sufficiente per la modalità stima

Costi del video:
- **Rolling shutter** — i sensori leggono riga per riga; in movimento la geometria del fotogramma è deformata. Errore sistematico, non rumore
- **Risoluzione e compressione** — un fotogramma 4K è ~8 MP contro i 48 di uno still, e la compressione inter-frame degrada proprio i bordi netti
- Volume dati e costo di elaborazione

**Architettura raccomandata:** video come scheletro geometrico, still ad alta risoluzione come ancore metriche. Durante la ripresa l'app scatta automaticamente foto a piena risoluzione nei momenti buoni — camera quasi ferma, buona parallasse, riferimento visibile. Nei momenti di quasi-immobilità il rolling shutter è trascurabile.

Il video d'archivio ricade nella modalità stima: niente IMU, intrinseci sconosciuti, compressione già applicata.

Precedente in letteratura: Wound3DAssist genera modelli 3D accurati da brevi riprese video a mano libera, con misure automatiche indipendenti dal punto di vista e accuratezza millimetrica, in valutazioni complete sotto i venti minuti.

### 6.3 Selezione degli scatti — avvertenza metodologica

**Lo scarto va deciso su criteri indipendenti dal risultato:** nitidezza, angolo di base, marker rilevato con confidenza, residuo di riproiezione. Valutati *prima* di guardare cosa fa la misura.

Eliminare una foto perché *peggiora la stima* è un errore metodologico serio: se il criterio di esclusione è il disaccordo con il risultato corrente, il sistema conferma se stesso e l'incertezza mostrata si restringe artificialmente. Ogni scarto va contato: cinque scatti di cui tre buttati non danno la stessa incertezza di tre scatti buoni al primo colpo.

---

## 7. Interfaccia di guida alla cattura

### 7.1 L'indicatore di progresso

**La barra deve rappresentare l'incertezza corrente rispetto alla tolleranza richiesta,** non "foto 3 di 5". Una barra procedurale promette un traguardo sconosciuto e arriva al 100% anche quando la misura non converge.

Quattro requisiti:

1. **Deve poter tornare indietro.** L'incertezza non scende in modo monotono. La metafora giusta è il misuratore, non il caricamento
2. **Scala compressa.** L'incertezza cala circa con la radice del numero di osservazioni: mappare il riempimento sul logaritmo del rapporto tra incertezza corrente e obiettivo
3. **Due indicatori distinti** — precisione e copertura angolare. Si può avere bassa varianza su una ricostruzione parziale
4. **Rilevatore di stallo.** Se due scatti consecutivi migliorano l'incertezza sotto soglia, la scena non converge (tipicamente superfici senza texture: cartone bianco, film estensibile). L'app deve dichiararlo, non chiedere una sesta foto inutile

Guida direttiva, non descrittiva: "spostati due passi a destra", non "aggiungi angolazioni". L'angolo di base utile è indicativamente 15–30°: sotto la triangolazione è mal condizionata, sopra fallisce il matching. Budget di cattura: cinque scatti come tetto.

In modalità archivio lo stesso meccanismo diventa un referto: "con queste foto arrivo a ±34 mm; per scendere a ±10 serve uno scatto da questa angolazione".

### 7.2 Calibrazione dell'incertezza — requisito non rinviabile

Se l'app dichiara ±10 mm, su un campione di test reale circa il 95% delle misure deve cadere davvero entro 10 mm. Dichiarare ±10 quando la realtà è ±25 significa costruire un'interfaccia che comunica fiducia falsa — peggio che non mostrare nulla, perché l'utente ci baserà decisioni.

**Protocollo di validazione da definire subito**, con dataset di oggetti a dimensione nota misurati al calibro. Criterio di accettazione espresso come **percentuale di misure entro tolleranza** (es. "95% entro l'1%"), non come errore medio: un errore medio dell'1% con code lunghe perde la fiducia dell'utente al terzo utilizzo.

---

## 8. Tolleranze per verticale

| Caso d'uso | Tolleranza | Certificazione |
|---|---|---|
| Taglia pronto-moda | ±20 mm | no |
| Logistica, uso interno | ±10 mm | no |
| Camicia su misura | ±3 mm su circonferenze | no |
| Logistica, fatturazione | ±5 mm L/W, ±2 mm H | OIML / NTEP / MID — **fuori perimetro** |

**Principio:** la tolleranza va definita in millimetri assoluti e per punto di misura, mai come percentuale globale. L'altezza di un collo e la circonferenza di un torace non hanno budget d'errore esprimibili nella stessa unità.

### 8.1 Sartoria — nota critica

Le tolleranze pubblicate dal settore sono **sul capo finito, non sulla misura del corpo**, e i due errori vanno in serie.

Riferimenti: produzione in serie ±0,5" (1,25 cm) fino a ±0,75"; capi tecnici o sartoria di precisione ±0,25". Proper Cloth pubblica ±0,25" sulla larghezza torace, che raddoppiata dà ±0,5" sulla circonferenza.

Regola metrologica standard: il sistema di misura non dovrebbe assorbire più del 10–20% della banda di tolleranza. Su ±12 mm di circonferenza torace significa **±2–3 mm sulla misura del corpo**.

**Limite fisico indipendente dalla tecnologia:** il corpo non è rigido. Respira, cambia postura, la tensione del metro varia. Anche due sarti umani non ripetono entro pochi millimetri. Per questo 3DLOOK non usa geometria pura ma un modello statistico costruito su un laboratorio di scansione interno con dati sintetici su conformazioni diverse.

Il video sul corpo ha un difetto controintuitivo: più dura la ripresa, più il soggetto si deforma. È il motivo per cui 3DLOOK lavora su due sole foto. Un video del corpo è inoltre un dato molto più sensibile sotto GDPR.

---

## 9. Input forniti dall'utente

Oltre alle immagini, l'app accetta dati inseriti dall'utente: automisurazioni col metro, taglie abitualmente indossate, numero di scarpa, altezza e peso. Sono **osservazioni con la propria incertezza, non verità di riferimento**, e vanno trattate di conseguenza.

### 9.1 Quanto vale un'automisurazione

Studio classico su 103 donne che si misuravano per l'acquisto per corrispondenza:

- Errore assoluto medio **4,10 cm** sulle proprie misure — peggiore dei 3,34 cm ottenuti misurando un'altra persona
- Circonferenza fianchi **sottostimata sistematicamente di 4,54 cm**
- Statura sovrastimata in media di 0,68 cm, errore assoluto 2,26 cm
- Il 97% riportava il valore arrotondato al quarto di pollice o peggio, pur avendo un metro con precisione 1,6 mm

Quattro centimetri su una circonferenza sono un ordine di grandezza sopra il target sartoriale di ±3 mm.

Conferma indiretta: un'app validata su 1200 partecipanti ha ottenuto errori pari a **meno della metà** di quelli delle automisurazioni, usando come riferimento tecnici addestrati.

**La guida cambia tutto.** Con un breve video istruttivo prima della misurazione, uno studio ha ottenuto ICC tra automisura e tecnico di 0,97 su vita e 0,96 sui fianchi, con oltre il 93% delle differenze entro i limiti di concordanza. Conseguenze operative: se si chiede l'automisurazione bisogna **insegnarla** (dove appoggiare il metro, quanta tensione, che postura) e **richiedere il valore al millimetro**, non arrotondato.

### 9.2 Fusione, non sostituzione

L'automisura entra nella stima con il suo peso, non al posto di quella dell'app. A ogni fonte va assegnata un'incertezza e le osservazioni vanno combinate: due osservazioni indipendenti mediocri battono una buona.

| Fonte | Incertezza indicativa | Ruolo |
|---|---|---|
| Automisura non guidata | ±40 mm | Osservazione debole, plausibilità |
| Automisura guidata (con video istruttivo) | ±10 mm | Osservazione da fondere |
| Misura dell'app, modalità stima | da calibrare | Osservazione primaria |
| Misura dell'app, modalità certificata | da calibrare | Osservazione primaria |
| Taglia dichiarata | molto larga | Priore debole, mai misura |
| Numero di scarpa | pochi mm sulla lunghezza piede | Ancoraggio di scala |
| Altezza / peso dichiarati | altezza sovrastimata | Priore per il modello parametrico |

*I valori indicativi vanno sostituiti dai risultati del protocollo di validazione (questione aperta 3).*

**Gestione del disaccordo.** Se app e utente divergono oltre soglia non si sa chi ha ragione, e la scelta silenziosa è la peggiore opzione. Mostrare entrambi i valori, dichiarare la discrepanza, chiedere di rimisurare quel singolo punto. Stessa logica del doppio riferimento (5.3).

**Chiedere poco e bene.** Come per la scelta della prossima foto, va richiesta la misura che riduce di più l'incertezza, non tutte: "misura solo il girovita e la stima migliora del 40%" è accettabile, "inserisci quindici misure" no.

### 9.3 Taglie e numero di scarpa: priori, non misure

**Taglia dichiarata.** Dato debole: vanity sizing e differenze tra brand fanno sì che "porto la M" corrisponda a una distribuzione larga di circonferenze. Utile per inizializzare il modello parametrico e come **controllo di plausibilità** — se l'app calcola un torace da 88 cm e l'utente dichiara XXL, conviene rifare lo scatto invece di consegnare il numero.

*Rischio di circolarità:* se la taglia dichiarata è un priore e l'output è una raccomandazione di taglia, si rischia di restituire all'utente ciò che ha dichiarato. Il priore deve restare debole e il sistema deve poterlo contraddire — "in base alle misure la tua taglia è L, non M" è il valore che si vende.

**Numero di scarpa.** Ancoraggio molto migliore, per ragione fisica: il piede è rigido e la taglia è quantizzata su un passo fisso (nel sistema francese due terzi di centimetro). Vincola la lunghezza del piede entro pochi millimetri ed è un controllo di scala quasi gratuito.

**Altezza e peso.** Miglior rapporto valore/attrito: quasi tutti li conoscono, si inseriscono in pochi secondi, sono priori forti per il fitting del modello parametrico. Cautela: l'altezza autodichiarata è tipicamente sovrastimata.

### 9.4 Due requisiti di sistema

**Provenienza su ogni valore.** Ogni misura in uscita porta la sua origine — misurata dall'app, dichiarata dall'utente, inferita dal modello. È il principio dell'incertezza che viaggia col dato (4.3) applicato alla fonte, e serve a chi deve decidere di quale numero fidarsi.

**Ciclo di apprendimento.** Taglia dichiarata + misura calcolata + esito dell'acquisto (tenuto o reso) è un dataset che si costruisce da solo. È ciò che nel tempo permette di passare dalla geometria pura al modello statistico — la strada percorsa da 3DLOOK con un laboratorio di scansione interno, percorribile qui con i dati d'uso.

---

## 10. Visualizzazione delle misure corporee

**Avatar / manichino 3D** con misure evidenziabili al tocco.

Il valore non è estetico ma tecnico: **elimina l'ambiguità del punto di misura**. Il torace si misura tipicamente un pollice sotto la cucitura dell'ascella, ma ogni brand definisce i propri punti diversamente. Una misura senza punto definito non è una specifica, è un'opinione. Mostrare *la linea* sul corpo comunica dove si è misurato, non solo quanto. Permettere di spostarla e ricalcolare è un differenziatore rispetto ai concorrenti a lista di numeri.

**Rischio:** l'avatar comunica implicitamente "questa è la forma del tuo corpo", ma gran parte della superficie è inferita, non misurata. Soluzione coerente col resto: **distinguere visivamente il misurato dall'interpolato**, con l'incertezza che compare insieme alla misura.

**Manichino stilizzato, non avatar realistico**, per tre ragioni convergenti:

- **Aspettativa** — un manichino neutro non promette fedeltà fotografica e non delude
- **Privacy** — una mesh realistica del corpo di un cliente cambia la valutazione d'impatto GDPR, i tempi di conservazione e la base giuridica. Un manichino parametrico definito da venti numeri è quasi banale da trattare. 3DLOOK dichiara esplicitamente che le foto servono solo a generare modello e misure, con cancellazione su richiesta: postura da adottare fin dall'inizio
- **Sensibilità** — mostrare una rappresentazione realistica del proprio corpo non è un atto neutro

Note pratiche:
- Interazione **bidirezionale**: tocco sul corpo → misura, e tocco sulla misura in lista → evidenziazione sul corpo (serve al sarto che compila una scheda)
- **Correzione manuale** fin da subito, marcata come inserita a mano. Le deviazioni forti tra correzione e stima sono dati di validazione gratuiti
- **Da verificare presto:** condizioni di licenza per uso commerciale dei modelli parametrici del corpo umano

---

## 11. Applicazioni in logistica (uso interno)

### 11.1 Anagrafica e magazzino
- **Creazione anagrafica articolo al ricevimento** — caso più solido: il dato passa da inesistente ad approssimativo, salto più grande che da approssimativo a preciso
- Slotting e capacità di stoccaggio
- Verifica in ingresso contro le dimensioni dichiarate dal fornitore
- Scelta dell'imballo e riduzione del riempitivo
- Controllo qualità in punti non presidiati (cross-dock, staging, corsie)

### 11.2 Trasporto e carico
- Cubatura e piano di carico — l'errore relativo si media favorevolmente su molti colli
- "Ci sta nel mezzo" — decisione binaria
- Merce fuori sagoma — soglia, non misura
- Pre-audit delle contestazioni — **confine con la fatturazione, da tenere distinto nel messaggio**
- Classificazione preliminare per la tariffazione, come stima

### 11.3 Fuori dal magazzino
- **Traslochi** — settore che già compra esattamente questo: virtual survey con giro video autoguidato e inventario generato dall'AI. Il disclaimer di categoria è già la norma ("stima rapida e utile, non una misura esatta"). Incumbent strutturati: Yembo, Voxme, Move4U, Virtual Estimate
- Self-storage — quale box serve
- Marketplace dell'usato — dimensioni nell'annuncio per calcolare la spedizione
- Accessi e ingombri — passa dalla porta, dall'ascensore
- Logistica di cantiere ed eventi
- Resi e logistica inversa — proof of condition al ritiro
- Perizie e sinistri

---

## 12. Altri campi di applicazione

Classificati per **tipo di decisione**, non per settore, perché è questo che determina se la tolleranza basta.

### 12.1 Classificazione discreta
Il caso più favorevole: non si misura, si sceglie tra opzioni distanziate.

**Calzature** è il verticale più maturo e più affollato. Findmeashoe fa scattare una foto con il piede su un foglio standard, con precisione dichiarata di 1 mm, e attribuisce alla mancata conoscenza di forma e misura del piede il 50% dei resi per vestibilità. Aetrex risolve con una foto sola. Snapfeet chiede 4–5 foto e usa ARKit. MS ShoeSizer dichiara di funzionare senza oggetto di riferimento.

Stessa logica: anelli, guanti, caschi, taglia bici, pettorine e trasportini per animali, cinturini.

### 12.2 Decisioni a soglia
Il divano passa dalla porta, il frigo entra nel vano, il macchinario sale in ascensore. Risposta binaria; l'errore conta solo vicino alla soglia, dove l'app può dire "sei al limite, verifica a mano".

Nota di prodotto: richiede di confrontare due misure prese in momenti e luoghi diversi (il mobile in negozio, il vano a casa). È funzione di prodotto, non di misura — ed è ciò che Metro copre male.

### 12.3 Stima di quantità
Vernice, piastrelle, parquet, carta da parati, terriccio, ghiaia, cemento. La matematica lavora doppiamente a favore: l'errore si media su superfici composte da più misure, e il materiale si acquista arrotondato per eccesso al confezionamento.

Adiacente: preventivi rapidi per tinteggiatura, posa, serramenti.

### 12.4 Documentazione e ispezione a distanza
Perizie assicurative, stato di consegna e riconsegna di noleggi e locazioni, verbali di danno, documentazione di cantiere. Il valore non è il numero ma **avere una misura tracciabile allegata a una foto datata**.

### 12.5 Campo scientifico e agricolo
In zootecnia: un'app di misura da immagine su Android è stata usata per rilevare le dimensioni corporee dei suini, mostrando che le misure morfometriche da immagine predicono il peso con buona accuratezza senza stressare l'animale — tecnica semplice, economica, utilizzabile con poco addestramento.

In agricoltura: calibro dei frutti, diametro dei tronchi, crescita delle piante, stima di resa. Esistono già studi con iPhone e Polycam su alberi da frutto.

Volumi bassi ma ottimi casi di validazione pubblicabili: la credibilità scientifica è un asset commerciale.

### 12.6 Principio di selezione

**La tecnologia è forte dove il risultato è una scelta e debole dove il risultato è un numero.** Taglia, sì o no, quanti secchi: risposte discrete che assorbono l'incertezza. Un valore da trascrivere in un contratto: no.

Tre criteri di priorità:
1. Preferire le decisioni a soglia alle misure
2. Preferire i casi dove l'alternativa attuale è *nessuna* misura
3. Diffidare di tutto ciò che finisce in una fattura, anche indirettamente

### 12.7 Avvertimento trasversale

La trappola della fatturazione si ripresenta travestita in altri domini: misura del pescato per i limiti di legge, distanze per la conformità antincendio, calibro commerciale dei prodotti agricoli, superficie catastale. Sono tutte **misure che producono conseguenze regolamentari**.

**Da scrivere una volta come principio di prodotto, non caso per caso.**

---

## 13. Privacy e architettura del trattamento

*Sezione da validare con un legale prima di scrivere codice: l'architettura dei consensi si ridisegna male a posteriori.*

### 13.1 Il criterio decisivo è dove viene elaborata l'immagine

"Le foto le usa l'utente, non noi" non è una tutela. Ciò che conta è chi determina finalità e mezzi del trattamento, e soprattutto se l'immagine lascia il dispositivo.

| | Elaborazione on-device | Elaborazione cloud |
|---|---|---|
| Esposizione | Bassa: non trattiamo quei dati | Siamo titolare o responsabile a pieno titolo |
| Obblighi | Trasparenza | Base giuridica, informativa, conservazione, cancellazione, sub-responsabili, eventuale DPIA |
| Costo | Maggiore in ingegneria | Minore in ingegneria, maggiore in infrastruttura |
| Posizionamento | Vendibile come caratteristica | Da giustificare |

**Canali di fuga da verificare esplicitamente:** telemetria e analytics, log di crash che allegano l'ultimo frame, cache di upload, backup automatici del dispositivo, e i **sub-responsabili** — se il modello gira su un servizio cloud di terzi, l'immagine è passata da lì.

**Le misure derivate restano dati personali** anche dopo la cancellazione delle immagini. Una circonferenza torace associata a una persona identificabile è un dato personale, e a differenza della foto non si può cancellare: è l'output del prodotto.

**Decisione da prendere:** elaborazione del verticale corpo interamente on-device. Costa di più in sviluppo e risolve gran parte del problema. È coerente con due scelte già fatte per altre ragioni — il manichino stilizzato al posto della mesh realistica (10) e la postura dichiarata sulle foto usate solo per generare le misure.

### 13.2 Categorie particolari: probabilmente fuori, ma il confine va presidiato

Il Considerando 51 del GDPR stabilisce che il trattamento di fotografie non va sistematicamente considerato trattamento di categorie particolari. Il dato biometrico è categoria particolare (art. 9) **solo quando è trattato allo scopo di identificare univocamente una persona**. La nostra finalità è determinare una taglia, non identificare: con ogni probabilità siamo fuori dall'articolo 9, quindi niente consenso esplicito rafforzato né doppio test di liceità.

Il confine però è meno solido di come suona: in assenza di guida chiara di un organismo sovraordinato l'interpretazione resta incerta, e la CNIL nel caso Clearview AI ha ritenuto che il trattamento di fotografie costituisse trattamento di dati biometrici.

**Due sviluppi ci riporterebbero dentro l'articolo 9:**

1. Aggiungere il riconoscimento dell'utente dalle immagini
2. Derivare indicatori di salute — peso, BMI, composizione corporea — che sono dati sanitari a pieno titolo

Entrambi vanno considerati decisioni con implicazione giuridica, non feature incrementali.

### 13.3 Basi giuridiche per finalità

**Il consenso non è la base giusta per il servizio.** Deve essere liberamente prestato: se l'utente apre l'app per farsi misurare, elaborare la foto non è un'opzione ma il servizio stesso, quindi quel consenso non è libero — e un consenso non libero è invalido. In più è revocabile in qualsiasi momento, e non si costruisce il funzionamento base di un prodotto su qualcosa che l'utente può ritirare.

| Finalità | Base | Note |
|---|---|---|
| Elaborare l'immagine per restituire la misura | Esecuzione del contratto (art. 6.1.b) | Nessuna schermata di consenso |
| Conservare le immagini oltre l'elaborazione | Consenso separato | Rifiutabile senza perdere il servizio |
| Addestrare i modelli | Consenso separato | Vedi nota sotto |
| Condividere misure con brand o partner | Consenso separato | |
| Analytics non essenziali | Consenso separato | |

**I consensi devono essere granulari.** Caselle distinte, rifiutabili una per una, e il rifiuto non deve impedire l'uso dell'app. Accorpare "elabora la mia foto" e "usa la mia foto per addestrare il modello" in un unico consenso li invalida entrambi.

**Nota sul training.** Se l'utente revoca il consenso dopo l'addestramento, la situazione è spinosa. Il ciclo di apprendimento descritto in 9.4 deve quindi lavorare su **dati derivati e anonimizzati** — taglia dichiarata, misura calcolata, esito dell'acquisto — non sulle immagini. Stesso valore statistico, frazione dell'esposizione.

### 13.4 Ruoli nello scenario B2B

Se è il sarto a fotografare il **cliente**, il soggetto dei dati non è il nostro utente. Il sarto è titolare, noi responsabile del trattamento: serve un accordo ex articolo 28. È lo stesso flusso tecnico ma una configurazione giuridica diversa.

Conseguenza di prodotto, da mettere in roadmap e non risolvere per contratto:

- Cattura del consenso del soggetto dentro il flusso di misurazione
- Informativa personalizzabile dal professionista
- Cancellazione su richiesta del cliente finale

### 13.5 Requisiti trasversali

- **Informativa contestuale prima della cattura**, non sepolta nei termini al primo avvio: una riga nel momento in cui l'utente sta per scattare, che dica dove va la foto e quanto ci resta
- **Tempi di conservazione dichiarati**
- **Cancellazione come funzione nell'app**, non come indirizzo email
- **Minori** — un genitore che fotografa un figlio per comprargli una giacca è un caso d'uso prevedibile. Va deciso consapevolmente, non scoperto dopo
- **Stati Uniti** — l'Illinois BIPA copre la scansione della geometria del volto o della mano e prevede azione privata risarcitoria: è la norma che ha generato le class action più costose del settore. Se le immagini corpo includono il volto, è il rischio economico più concreto dell'elenco. Da verificare prima della distribuzione negli USA, non dopo

---

## 14. Questioni aperte

| # | Questione | Priorità |
|---|---|---|
| 1 | Verifica legale sull'uso di immagini di banconote (EURion, CDS, regole BCE) | Alta se si conferma la banconota |
| 2 | Licenze commerciali dei modelli parametrici del corpo umano | Alta prima di sviluppare il verticale sartoria |
| 3 | Definizione del protocollo di validazione e del dataset ground truth | Alta — blocca la calibrazione dell'incertezza |
| 4 | Ripartizione elaborazione on-device / cloud e impatto sul modello di costo | Alta |
| 5 | Scelta del verticale di lancio | Alta |
| 6 | Profili di calibrazione della distorsione per modello di dispositivo | Media |
| 7 | **Decisione on-device / cloud per il verticale corpo** (13.1) — determina l'intero impianto privacy, il costo infrastrutturale e il posizionamento | Alta, bloccante per il verticale corpo |
| 8 | Taratura empirica delle incertezze da assegnare alle fonti utente (tabella 9.2) e regole di fusione | Media, dipende dalla questione 3 |
| 9 | Produzione del materiale istruttivo per l'automisurazione guidata | Media, diventa alta col verticale corpo |
| 10 | Validazione legale dell'impianto basi giuridiche / consensi (13.3) prima dello sviluppo | Alta col verticale corpo |
| 11 | Verifica BIPA e normative statali USA se le immagini includono il volto (13.5) | Alta prima della distribuzione USA |
| 12 | Flusso di consenso del soggetto terzo nello scenario B2B e accordo art. 28 (13.4) | Media, alta col primo cliente professionale |

---

## 15. Indicazione strategica

La riga più accessibile della tabella tolleranze è la **prima**, non l'ultima. La classificazione taglia — abbigliamento pronto-moda, calzature, accessori — è raggiungibile con la tecnologia descritta già oggi, con margine. Il su misura è l'evoluzione, non il punto di partenza.

Analogamente in logistica: il posizionamento "dare un'idea" allarga il mercato più di quanto lo restringa. Ci sta il pacco in furgone, stima volumetrica di un carico, preventivo di trasloco, annuncio su un marketplace, self-storage — contesti dove oggi si usa il metro a nastro o si tira a indovinare, e dove nessuno chiederà mai una certificazione OIML.
