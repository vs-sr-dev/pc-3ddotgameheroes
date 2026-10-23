# `MAPCOLLISION/*.DPK` — la collisione delle mappe

**Stato: risolto.** Layout, sistema di riferimento e uso.
Parser: [`tools/dpk.py`](../tools/dpk.py).

171 file in `PS3_GAME/USRDIR/DATA/MAPCOLLISION/`, **5,4 MB in tutto**: una mesh
di triangoli per mappa, 256.985 vertici e 420.301 triangoli. È un centesimo dei
poligoni con cui le stesse mappe si disegnano (30,9 milioni), ed è il muro che
il gioco usa davvero.

```
python tools/dpk.py check              171 su 171, fino all'ultimo byte
python tools/dpk.py info <file.DPK>
```

## Formato

```
+0x00 u32                   numero di mesh
poi n coppie (u32, u32)     offset e dimensione di ogni mesh

ogni mesh, al proprio offset:
  +0x00 u32                 numero di FLOAT, cioè 3 × i vertici
  poi n float32 big-endian  (x, y, z)
  +0x00 u32                 numero di indici
  poi n u16 big-endian      tre per triangolo
```

Il numero di mesh va da 1 a 5; 301 mesh in tutto sui 171 file.

### Perché è certo

Lo stesso oracolo che ha risolto `MAP_ALIGNMENT`: percorrendo ogni mesh dal suo
offset si deve finire **esattamente** sulla dimensione dichiarata, e l'ultima
sull'ultimo byte del file. Succede in **171 file su 171**, per tutte e 301 le
mesh. Con un campo letto male si esce dal file al primo blocco.

L'unico campo che non si indovina è il conto dei **float** invece dei vertici.
In `PLANE.DPK` — il file più piccolo, 80 byte — vale 12 per quattro vertici;
letto come numero di vertici manda l'offset degli indici 96 byte oltre la fine.

`PLANE.DPK` è anche il posto giusto da cui cominciare a leggere questo formato:
un quadrato di 102,4 unità (64 caselle) fatto di 4 vertici e 2 triangoli, cioè
il caso minimo in cui ogni campo è visibile a occhio nudo.

## Il sistema di riferimento

Lo **stesso** del `.pac`: origine al centro della mappa, X verso destra, Z verso
l'alto della griglia. Non c'è niente da convertire.

Si verifica a confronto, mappa per mappa:

```
DUNGEON_21_1   dpk  x [-20.0, 18.4]   z [-18.4, 20.0]
               pac  x [-20.0, 18.4]   z [-18.4, 20.0]      griglia 24 × 24
```

Le due estensioni coincidono, e coincidono con `w × 1,6`. Dove differiscono —
`DUNGEON_1_2` ha il `.pac` più largo di 3,3 unità — è la geometria decorativa
che sporge oltre la collisione, non un disallineamento.

## I nomi

Non concordano con quelli delle mappe: la collisione di `D_1_1_1` si chiama
`DUNGEON_1_1_1.DPK`, quella di `FIELD_9` si chiama `FIELD_09.DPK`, e in un file
lo sviluppatore ha scritto **`DANGEON_8_2.DPK`**. Il refuso è sul disco
stampato, quindi il parser lo gestisce insieme alla forma corretta.

`PLANE.DPK` è l'unico senza una mappa corrispondente: è il pavimento di prova
degli sviluppatori. **170 mappe su 170** hanno la loro collisione.

## Quanto è alto il mondo

Va misurato, non assunto, ed è costato caro assumerlo (vedi [`walk.md`](walk.md)):

```
y globale su 171 file:  [-4,35 ; 51,20]
scendono sotto zero:    69 file su 171
superano 25,6:          2 file        (FIELD_07 è una montagna e arriva a 51,2)
```

E lo zero non è un fondo pulito nemmeno dove sembra: il pavimento di `d_1_2` sta
a `−0,000002`, cioè lo scarto di un `float32` passato per una somma
baricentrica. Chi tronca a zero non perde un margine, perde il pavimento.

## Da mesh a colonne

Chi cammina non ha bisogno di triangoli ma di due risposte per cella — dove si
posa il piede, e cosa c'è all'altezza del corpo. `dpk.seed()` semina i
triangoli di punti a passo di un quarto di casella, che è la risoluzione delle
colonne di [`walk.md`](walk.md), e restituisce con ogni punto la **normale del
suo triangolo**.

La normale non è un di più: distingue un pavimento da un muro, e presa dal
triangolo invece che dal vertice è esatta invece che interpolata.

Seminare invece di prendere i vertici è necessario perché in una mesh di
collisione i triangoli **sono grandi**: un pavimento di venti caselle è due
triangoli, e i suoi soli vertici lascerebbero vuote tutte le celle in mezzo.

**Quanto grandi**: in `FIELD_07` il lato più lungo misura 190,3 unità, cioè 119
caselle, e 2.238 triangoli su 6.747 superano le 38,4 unità. Un tetto di 96
suddivisioni — che sembrava la scelta prudente — rendeva il passo di semina di
quei triangoli 2,0 unità, **più largo di una casella**, e lasciava quindi
scoperte celle intere: fra queste quattordici punti d'ingresso di mappa, che
risultavano non calpestabili. Senza tetto costa il 27% di punti in più su tutto
il disco (139 milioni contro 109) e non lascia buchi; la semina va a gruppi
perché una mappa sola arriva a 22 milioni di punti.

## Il fondale

Sotto ogni mappa di campagna c'è un unico quadrilatero piatto steso da parte a
parte, a −3,2 o giù di lì. In `FIELD_22` sono **due triangoli** per 10.368
caselle su una mappa che ne ha 16.384; in `FIELD_30` sono 32 triangoli per
13.628 caselle.

Guarda in su, quindi la lettura delle normali lo prende per un pavimento — solo
che sopra ha metri di roccia. Come si riconosce, e cosa se ne ricava (la
maschera dell'acqua), sta in [`walk.md`](walk.md).

## Cosa cambia averlo

`view.py walkabout` percorre a piedi tutte le mappe. Con le colonne ricavate
dalla geometria di rendering, e con le colonne ricavate dal `.DPK`:

| | geometria | `.DPK` |
|---|---:|---:|
| celle raggiunte a piedi | 18% | **63%** |
| abitanti raggiunti | 65% | **96%** |
| passaggi raggiunti | 194 | **303** |

E soprattutto: il divario fra sotterranei e campagna — 26% contro 13% di celle,
76% contro 51% di abitanti — **è sparito**. Con la collisione vera le due
famiglie stanno entrambe al 63% di celle, e la campagna arriva al 99% di
abitanti raggiunti.

Attenzione però a non attribuire tutto a questo file: metà del guadagno viene
dall'aver riconosciuto che il gradino vale **una casella**, che è una scoperta
indipendente (vedi [`walk.md`](walk.md)). Il `.DPK` da solo portava gli abitanti
dal 65% al 78%.

## Cosa manca

- **Le mesh multiple.** Un file su cinque ne ha più di una (fino a 5) e non è
  chiaro cosa le separi: aree, materiali di collisione, o solo il limite di
  65.536 vertici degli indici a 16 bit. Le mappe con più mesh sono anche le più
  grandi, il che fa pensare alla terza.
- **I materiali di collisione.** Non c'è nessun campo per triangolo: né tipo di
  terreno, né suono di passo, né "acqua". Se esistono stanno altrove — e per
  l'acqua stanno davvero altrove, nel tag di regione della griglia logica.
- **Il verso dei triangoli.** Qui si usa la normale geometrica e basta; se il
  formato dichiarasse un verso, si potrebbe distinguere il solido dal
  bidimensionale.
