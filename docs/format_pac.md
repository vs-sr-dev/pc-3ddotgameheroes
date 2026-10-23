# Formato `.pac` — le mappe

**Stato: risolto, composizione compresa.** I 167 file delle mappe si aprono per
intero e la geometria si estrae con lo stesso parser dei modelli: 4.837
sezioni, 54.110 oggetti, **51.738.164 vertici**. Zero errori di validazione.
Le sezioni sono **schermi da comporre**, e la composizione è verificata contro
un file esterno al 91,2% — vedi *Cosa contiene una sezione*, che corregge la
conclusione opposta sostenuta fino alla sessione 3.
Parser: [`tools/dsb.py`](../tools/dsb.py) (`blocks()`),
composizione: [`tools/view.py`](../tools/view.py) (`screens()`, `load()`).

## Dove sono

`PS3_GAME/USRDIR/DATA/MAP/PAC_DATA/` contiene 167 file `*_PS3_PAC.GZ` e 338
`.TPK`. I `.GZ` sono gzip normali, col nome originale nell'header — `D_1_2.ps3.pac`
— e pesano 441 MB compressi contro **1,95 GB** decompressi. I `.TPK` accanto
sono le texture della mappa, con nomi che ricalcano quelli dei `.pac`.

167 mappe: **127 sotterranei** (`d_*`) e **40 aree dell'overworld** (`field_*`).
Le `field_*` sono tutte griglie 8×8.

## Il container

Banale, una volta decompresso:

| Off | Campo |
|---|---|
| 0x00 | u32 `n0` — colonne |
| 0x04 | u32 `n1` — righe |
| 0x08 | u32[`n0*n1 + 1`] offset delle sezioni |

Ogni sezione è un blocco `DSBF` completo, nel formato descritto in
[`format_dsb.md`](format_dsb.md). L'ultimo offset è la dimensione del file.

Due trappole:

- **le sezioni sono allineate a 0x80**, quindi la fetta fra due offset è più
  lunga del blocco. Va ritagliata alla dimensione che il `DSBF` dichiara al
  proprio offset 0x0C, altrimenti la validazione fallisce sul padding — ed è
  un errore che si presenta come "il formato non torna", non come un padding;
- **esistono sezioni vuote**: `field_01` ne ha 32 su 64, con zero oggetti e un
  bounding box sentinella `(1e8, 1e8, 1e8)…(−1e8, −1e8, −1e8)`, cioè invertito.

Il conteggio `n0 * n1` regge su tutti i 167 file.

## La griglia

L'indice della sezione si scompone in cella: `c = i % n0`, `r = i // n0`.

Non è una deduzione: **i nomi delle mesh contengono la cella**. Una mesh della
sezione 8 di una griglia 7×8 (quindi `c=1, r=1`) si chiama
`md_kbe_L0_01_01-mesh`. La corrispondenza vale in **12.097 casi su 12.097** —
ogni singola mesh di ogni mappa del disco.

Lo stesso nome porta anche il **livello di LOD**: `_L0_` e `_L1_` compaiono in
numero esattamente uguale, a coppie sulla stessa cella. Una parte delle mesh
(gli oggetti sparsi, non il terreno) non ha suffisso di LOD.

## Cosa contiene una sezione

**Una sezione è uno schermo**, disegnato attorno alla propria origine, e la
mappa si ottiene mettendo la sezione `(c, r)` al suo posto nella griglia:

```
scostamento(c, r) = ( ((c + ½)·cw − w/2)·1,6 ,  0 ,  −((r + ½)·ch − h/2)·1,6 )
```

dove `w × h` è la griglia logica dichiarata dalla
[`MAP_ALIGNMENT`](format_mapdat.md) omonima, e `cw = w/n0`, `ch = h/n1` è la
taglia di uno schermo in celle. **Una cella vale 1,6**, che è anche l'altezza
di un personaggio (vedi [`entities.md`](entities.md)).

Il rapporto è un intero, mai un numero a caso: **16 × 12 celle** per schermo
nei sotterranei (43 mappe) e **16 × 16** nell'overworld (39), più le mappe a
schermo unico dove lo schermo è tutta la mappa. `d_1_1_1` ha 7 × 8 schermi e
una griglia logica 112 × 96.

### La prova, e l'errore che ha corretto

Fino alla sessione 4 questo documento sosteneva l'esatto contrario: che le
sezioni fossero *cullings* già nel sistema della mappa, da disegnare senza
comporre nulla. Vale la pena tenere qui come si era arrivati a crederlo e cosa
l'ha smentito, perché l'errore era ragionevole.

Le tre osservazioni che sembravano provarlo:

- i nomi delle mesh sono tutti distinti fra sezioni — vero, ma sono nomi, non
  geometria;
- il 79% delle posizioni di vertice di una sezione ricompare **identico** nella
  vicina, senza traslazione — vero, e sembrava decisivo. Ma un sotterraneo è
  fatto di **blocchi ripetuti**: due schermi dello stesso corridoio, ognuno
  disegnato attorno alla propria origine, hanno per forza gli stessi vertici
  alle stesse coordinate locali. L'osservazione era giusta, la conclusione no;
- il centro del bounding box si muove con la cella — vero, ma di ±12 unità in
  tutto, non dei 25,6 di uno schermo. È il **culling** che si sposta, cioè
  quanto sporge oltre il proprio schermo, non lo schermo.

E l'immagine confermava: una mappa disegnata accatastata *sembra* un
sotterraneo plausibile, con stanze e corridoi. È il caso peggiore — il
risultato quasi giusto.

Il test che decide è esterno al formato. La `MAP_ALIGNMENT` dichiara, cella per
cella, se lì c'è mappa o si è fuori (`0xFFFFFFFF`). È un altro file, scritto
per un altro scopo, nell'unico endianness diverso del disco. Se la
composizione è giusta la geometria deve cadere **dove quel file dice che c'è
mappa**:

```
python tools/view.py layout

167 mappe verificate (0 senza griglia dichiarata)
celle di mappa coperte dalla geometria: 436.043/480.731 = 90,7%
  delle sole celle solide (collisione):  374.430/375.867 = 99,6%
  il resto è acqua e vuoto:              104.864 celle
geometria fuori mappa:                    14.192/625.861 =  2,3%
```

> **Il 9% mancante non mancava** (sessione 5). Per due sessioni quel 90,7% è
> stato letto come "geometria che non troviamo", e le ipotesi in lista erano
> tre. Era la prima: la griglia logica marca come regione anche le celle di
> **acqua e vuoto** — il fossato, il mare, la gola fra due altipiani — dove il
> gioco stesso non mette niente. Sono 104.864 celle, il 22% di quelle
> dichiarate, e la mappa le distingue: portano un identificativo di regione
> tutto loro.
>
> A dirlo è stato un file che non era ancora stato aperto,
> [`MAPCOLLISION/*.DPK`](format_dpk.md): misurata contro ciò che il gioco
> considera solido, la composizione copre il **99,6%**. Il denominatore era
> sbagliato, non il numeratore.

Sulle 82 mappe a più schermi — le uniche in cui le due letture differiscono —
il confronto diretto:

| | celle di mappa coperte |
|---|---|
| **composte** | 379.600 / 420.335 = **90,3%** |
| accatastate | 16.291 / 420.335 = 3,9% |

Ventitré volte tanto. Il 3,9% non è "un po' peggio": è la firma di due cose
che non c'entrano niente l'una con l'altra.

Una trappola nell'implementazione: la testata del container è **big-endian**
come tutto il disco, la `MAP_ALIGNMENT` è **little-endian**. Sono le uniche
due righe del progetto in cui i due mondi si toccano, e leggerle con lo stesso
formato dà una griglia `117440512 × 134217728` — cioè `screens()` che
restituisce `None` e nessuna composizione, in silenzio.

Le mappe non contengono `light`, `camera` né `skin`: solo `node`, `mesh`,
`material`, `effect` e `texture`. Illuminazione e telecamera arrivano da
altrove.

## Geometria

| | |
|---|---|
| sezioni | 4.837 |
| oggetti | 54.110 |
| mesh | 12.097 |
| chunk | 14.666 |
| vertici | 51.738.164 |
| indici | 84.224.102 |

Due soli formati di vertice, entrambi compressi:

| Chunk | Stride | Dichiarazione |
|---:|---:|---|
| 12.203 | 34 | pos:half3 nrm:half3 col:color4 uv:half2 tan:half4 binorm:half3 |
| 2.463 | 30 | pos:half3 nrm:half3 uv:half2 tan:half4 binorm:half3 |

La somma delle dimensioni dichiarate coincide con lo stride in **14.666 chunk
su 14.666**.

Verifica geometrica su un campione di 121 sezioni (1,46 M vertici, 820 k
triangoli), con gli stessi oracoli usati sui modelli:

| Controllo | Risultato |
|---|---|
| bounding box della mesh riempito | 377 / 377 |
| scena composta contro bbox dell'header | 85 / 85 |
| normali versori | 100,00% |
| tangenti / binormali versori | 99,60% |
| facce allineate agli assi | **93,92%** |
| chunk → `material` | 466 / 466 |

Il 93,9% di facce allineate agli assi è più alto del corpus dei personaggi
(87,6%): il terreno delle mappe è geometria a voxel quasi pura.

Sul **disco intero** — modelli e mappe insieme, 627 file e 5.297 blocchi — la
verifica completa (nessun campionamento) dà **zero problemi**:

| | |
|---|---|
| mesh / chunk | 20.804 / 23.436 |
| vertici | **54.176.741** |
| triangoli | 30.909.102 |
| bounding box della mesh riempito | 20.804 / 20.804 |
| scena composta contro bbox dell'header | 3.462 / 3.466 |
| normali versori | **100,00%** su 54,2 milioni |
| tangenti / binormali versori | 99,65% |
| facce allineate agli assi | 94,65% |
| chunk → `material` | 23.436 / 23.436 |
| material → `effect` | 10.458 / 10.458 |

Un dato che vale la pena isolare: **2.342 chunk sono dichiarati `strip` pur
avendo un conteggio di indici divisibile per 3**. La vecchia euristica
"divisibile per 3 → lista" li avrebbe sbagliati tutti, in silenzio.

Ogni materiale delle mappe usa esattamente due stage, colore base e normal map.

## La griglia logica

Accanto alla griglia di streaming del `.pac` ce n'è una seconda, **logica**,
in `MAP_ALIGNMENT/*.DAT`: dove stanno eventi, nemici e passaggi. Ha dimensioni
proprie — `d_1_1_1` è 7 × 8 di streaming e 112 × 96 di logica — ed è risolta:
vedi [`format_mapdat.md`](format_mapdat.md), da cui esce anche il **grafo di
come si naviga il mondo** (146 mappe, 320 archi, 95% con il ritorno).

## Altro da chiarire

- La testata del `.DAT` dà `(16, 112, 96)` per `d_1_1_1`, e i due numeri stanno
  alla griglia del `.pac` come 112 = 7×16 e 96 = 8×12. Ma il fattore verso le
  unità di mondo non torna in modo pulito su tutte le mappe: l'estensione
  geometrica di `d_1_1_1` è 25,6 × 19,2, e 25,6/112 non è un numero tondo. Non
  serve per disegnare, serve per capire le unità.

## Uso

```
python tools/dsb.py survey extract/pac
python tools/dsb.py verify extract/pac --every 40
python tools/dsb.py info  extract/pac/d_1_1_1.ps3.pac --sec 9
python tools/dsb.py scene extract/pac/d_1_1_1.ps3.pac mappa.obj --sec 9
```

Senza `--sec` i comandi di esportazione scelgono la sezione con più oggetti,
che è la cella da cui si vede di più.

`blocks()` accetta `.dsb`, `.pac` e `.gz` indifferentemente: i `.GZ` si possono
dare al parser senza decomprimerli prima. Attenzione a non passare al `survey`
una cartella che contenga sia i `.GZ` sia i `.pac` già estratti, o si contano
due volte.
