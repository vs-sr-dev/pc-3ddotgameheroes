# Il primo render — `tools/view.py`

Il primo test di integrazione del progetto. Carica una mappa (o un modello),
compone la scena e la disegna texturizzata in OpenGL 3.3.

```
python tools/view.py <file.pac|.dsb|.gz> [opzioni]
python tools/view.py sweep <dir extract>      passata di verifica, senza schermo
```

Opzioni: `--sec N` una sola sezione, `--only <sottostringa>` filtra per nome,
`--shot out.png` disegna un fotogramma e esce (non serve una finestra visibile),
`--size`, `--azim/--elev/--dist`, `--flat` spegne la luce (resta il colore che
il dato porta), `--list` elenca le sezioni. Alla tastiera: WASD/RV per
muoversi, mouse per guardarsi intorno, F inquadra, T texture, L luce, C
culling.

```
python tools/view.py light                    quanto cielo vede ogni mappa
```

## Cosa mette alla prova

Quattro formati e le catene di riferimenti che li legano, tutti insieme:

    .pac  -> griglia di sezioni          format_pac.md
    DSBF  -> nodi, mesh, chunk, vertici  format_dsb.md
    chunk -> materiale -> texture        l'indice a +0x00 e i quattro stage
    TPKG  -> pixel DXT                   format_tpk.md

È un oracolo severo proprio perché è visivo: un errore non produce un disegno
un po' storto, produce geometria strappata o texture giuste su facce sbagliate.
Il primo sotterraneo (`d_1_1_1`, sezione 9) esce al primo tentativo con
pavimento a piastrelle, muri, casse e acqua al posto giusto; `field_16` è
riconoscibilmente la campagna del gioco, con l'erba a voxel, i sentieri di
terra e la strada lastricata.

## La passata di verifica

Un render bello è un aneddoto. `sweep` è la misura: carica **tutto** ciò che si
potrebbe disegnare e verifica ogni riferimento a texture.

```
627 file su 627, 5.297 sezioni, 23.439 chunk
54.176.753 vertici, 30.909.108 triangoli, in 14s
chunk senza UV: 312, senza texture: 312, mesh raggiunte via skin: 77
riferimenti a texture: 1.905, non risolti: 2
```

(Il tempo dipende dalla cache del disco: ~14 s a caldo, ~40 s a freddo.)

I 54.176.753 vertici sono **tutta** la geometria che il disco dichiara: il
censimento statico di `dsb.py verify` ne conta 54.176.741, e i 12 di
differenza sono una mesh che due nodi istanziano due volte. Non si perde niente
per strada.

I due riferimenti non risolti sono residui di produzione, non buchi:
`FireballColGrnColorFile` non è un nome di file, e `SouthPeak_Logo.ifl` è un
*Image File List* di 3ds Max — il formato con cui Max elenca i fotogrammi di
una texture animata. Rivelano con che strumenti sono stati fatti gli asset.

## Tre cose imparate guardando

**Il colore per vertice è illuminazione precotta.** Nel primo sotterraneo è un
verde muschio (119, 143, 83) con gli spigoli interni portati a nero: ambient
occlusion e tinta d'ambiente cotte nella geometria. Questo spiega perché le
texture sono grigie e la scena no. È anche una **conferma indipendente
dell'ordine dei canali**: se fosse ARGB l'alfa varierebbe e il blu sarebbe
sempre 255, mentre si osserva l'opposto — l'ultimo byte è costante a 255. È
RGBA.

Ne segue una conseguenza per l'host: la luce dinamica non deve moltiplicare due
volte quello che è già cotto.

*Scritto qui in sessione 3 e applicato in sessione 13, che è il ritardo di cui
vale la pena tenere conto: la conseguenza era giusta, e intanto il
visualizzatore continuava a moltiplicare.* Quando la si è misurata invece che
dedotta, il precotto si è diviso in due — in campagna è **occlusione per
vertice** (42% di variazione entro una stessa faccia, 241 livelli), nei
sotterranei sono **due livelli** e basta, cioè non è una luce. Da cui la
regola che il renderer ora applica: illuminare chi non ce l'ha, e con la luce
che il disco dichiara. Tutto in [`renderer.md`](renderer.md), il comando è
`python tools/view.py light`.

**Le mappe hanno un coperchio.** Un sotterraneo visto dall'alto è una lastra
piatta: la geometria include il soffitto. In gioco è il taglio della telecamera
a nasconderlo, non l'assenza del dato.

**Il collo di bottiglia non è la lettura.** Decodificare i vertici con numpy
direttamente dal vertex buffer — la stessa dichiarazione di `dsb.py`, tradotta
in `dtype` invece che in formati `struct` — porta l'intero disco a 14 secondi.
La versione che costruisce un dizionario per vertice è comoda per ispezionare,
inservibile per caricare.

## Lo skinning, risolto per caso

Contando i vertici disegnabili ne mancavano 50.043 su 54 milioni: lo 0,09%.
Cercarne la ragione ha aperto il record `skin`, che era in coda alle cose da
fare.

Le 77 mesh irraggiungibili sono **tutte** in `Opening.ps3.dsb`, e sono
esattamente quante sono le `skin` di quel file. Un nodo può agganciare uno
`skin` invece di una mesh, e lo `skin` nomina la mesh a +0x20. Il resto del
record — array di ossi, bind pose inversa, convenzione delle matrici — è
documentato in [`format_dsb.md`](format_dsb.md) §skin.

Due cose sono cadute insieme:

- la **semantica 9**, l'`ubyte4` misterioso che compariva solo in questo file,
  è l'**indice di osso**: i suoi valori stanno in `0 .. n_ossi-1`. Era in coda
  alle cose da fare per conto suo, e si è risolta da sola una volta aperto il
  record `skin`;
- lo skinning è **rigido**: c'è l'indice ma non il peso, un osso per vertice.

E c'è una trappola che vale la pena raccontare, perché è il genere di errore
che passa inosservato. Disegnando le parti con la trasformazione del *nodo* si
ottiene un villaggio 3D di aspetto plausibile, con qualche pezzo fuori posto:
sembra un dettaglio da sistemare. Con le matrici degli ossi, invece, la scena
si **appiattisce** — e la reazione istintiva è pensare di aver sbagliato. Il
determinante diceva altro: la catena dei nodi passa per `oka_s-node` (scala Y
0,04) e per un nodo che si chiama `Dummy_2D_pos-node`. La schermata di apertura
è un **fondale 2D visto dall'alto**, e guardandolo lungo l'asse giusto ecco il
villaggio con i suoi sentieri, la staccionata e gli alberi.

Il risultato "quasi giusto" era il più ingannevole dei due.

## Il post-processing — `tools/post.py`

La descrizione che Silicon Studio dà del proprio middleware in questo gioco
(RECON §6.7) nomina quattro effetti, e sono quattro passate:

> *"Applied for **vignetting** and **color modification** to give a toy camera
> feel, and realistic **defocusing** effects that create the feeling of a
> miniature world. Also contributes to sparkling **glare** effects for light
> sources or water."*

    scena  -> FBO colore + profondità
    prep   -> mezza risoluzione; in alfa il bright pass
    blur   -> gaussiana separabile, due giri: stretto per il defocus,
              largo per il glare
    comp   -> defocus per cerchio di confusione, glare additivo,
              vignetting, color modification

I parametri non sono di fantasia: li pilota il Lua e si possono contare. Su
**202 chiamate** presenti sul disco:

| chiamata | intervallo osservato |
|---|---|
| `SetParamDepthofField(a, b, c)` | `a` 0,37–3,02 (mediana 0,79); `b` 0,20–1,50 (mediana 0,70); `c` sempre 0 |
| `SetDofApaerture(x, 0)` | 0,70 in 14 casi su 20, poi 1,2 / 1,3 / 1,5 |
| `createFairyGlareEffect(38.27, 2.68, -23.2)` | **è una posizione nel mondo**, non parametri: il glare si piazza in un punto |

`BackupDof()` e `RestoreDof()` compaiono 526 e 612 volte: ogni evento salva il
DOF corrente, ne impone uno suo e alla fine lo rimette. Il fuoco è per-scena.

Quello che non sappiamo è **l'unità di misura**: 0,79 non può essere una
distanza di mondo, visto che una mappa è larga centinaia di unità. Sono valori
normalizzati o moltiplicatori di una base che sta nell'EBOOT — una domanda per
la Fase 3. Qui il fuoco insegue il bersaglio della telecamera (che è poi il
`switchDofPointGaze()` del Lua) e l'ampiezza nitida è una frazione del raggio
della scena, così il tilt-shift resta coerente da una mappa all'altra.

Una taratura ottenuta guardando: con la soglia del bright pass a 0,72 brillava
il pavimento di un sotterraneo, cioè tutto. Il fornitore però dice *"for light
sources or water"* — il glare è raro, non è un velo. A 0,88 torna a essere
quello che descrive.

Il risultato è che `field_16` smette di sembrare un modello 3D e comincia a
sembrare un plastico. Che è esattamente ciò che il *defocus* deve fare qui.

## L'acqua, che il `.pac` non contiene

Un fotogramma dell'overworld aveva grandi zone nere, e sembravano geometria
mancante. Erano il mare. La mappa non lo contiene — nessuna delle 11 texture di
`Field_16` è acqua — perché lo disegna il motore, e la sua texture sta fuori da
ogni pacchetto di mappa: **`data/shaders/water_col.dds`**, insieme a `Sun.dds`.
Sono i due `.dds` sciolti del disco, e stare in `shaders/` è la dichiarazione
che non appartengono a nessuna mappa e a nessun personaggio.

`water_col.dds` è 128×128, **non compressa** (32 bit, maschere `ARGB` in una
parola little-endian, cioè `BGRA` byte per byte), e disegna un reticolo blu
notte di **16 quadretti per lato**. Sedici quadretti sono i sedici dot di una
casella, quindi la texture si posa **una copia per cella** e il reticolo si
allinea da solo su tutto lo specchio, senza bisogno di ripetizione.

Le altre due cose che servono le dicono la griglia logica e la collisione, e
stanno in [`walk.md`](walk.md):

- **dove**: le celle in cui l'unica superficie è il fondale steso sotto la
  mappa (`Columns.water()`), 40.964 su tutto il disco — e la griglia le
  conferma per un'altra strada, col tag di regione `119`;
- **a che quota**: non è dichiarata da nessuna parte, ma il mondo la stringe da
  tutte e due le parti. Il fondale sta **due caselle esatte** sotto la riva nel
  52,9% dei casi e la riva sta a 0,00 nel 50%, quindi in mezzo c'è un solo
  multiplo di una casella. Ogni specchio prende la sua: si parte dalle rive e
  si propaga il **minimo** dentro l'acqua, così il lago di montagna di
  `Field_16` resta a +11,2 mentre il mare sta a −2,0.

```
python tools/view.py <mappa>.pac.gz            l'acqua si disegna da sola
python tools/view.py <mappa>.pac.gz --no-water com'era prima
```

E la misura di cosa resta, che `view.py layout` ora stampa:

```
celle di mappa coperte dalla geometria: 436.043/480.731 = 90,7%
  di cui acqua, ora disegnata:           40.964 celle
  restano nere in un fotogramma:          8.503 celle = 1,8% della mappa
```

Il nero residuo è l'altra metà della vecchia voce «acqua e vuoto»: celle dentro
la mappa senza geometria **e** senza fondale, cioè vuoto vero. Sono l'1,8%, e
non sono più una zona ma dei buchi.

## Cosa non fa

È un renderer di verifica, non il renderer del gioco. Manca il resto di
[`renderer.md`](renderer.md): normal map, environment map, rim light, ombre.
L'illuminazione non è più un aiuto a leggere le forme (sessione 13), ma restano
fuori le **luci puntiformi**: il disco ha `setPointLight` e `pointLightOff`, e
i sotterranei — le mappe che la propria luce non ce l'hanno — sono pieni di
torce, 859 celle.

Nota di passaggio raccolta cercando l'acqua: `data/shaders/graphics.ps3.tpk`
contiene `ice_03`, `snow_01`, `sun_01` e **`ref_01`, che è un CUBEMAP** — cioè
proprio l'environment map che questo elenco dà per mancante.
