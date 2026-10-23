# Formato DSBF — scene e modelli

**Stato: container, geometria, grafo di scena e materiali risolti.**
Header, tabelle e testate dei record sono validati su tutti i 460 file `.dsb`
del disco — 25.443 oggetti, 39.348 stringhe, zero discrepanze. La geometria si
estrae da **460 file su 460**: 8.707 mesh, 8.770 chunk, **2.438.577 vertici** e
**1.611.418 triangoli**. Il grafo di scena si ricompone: genitore, trasformazione
e geometria collegata di ogni nodo. La catena `node → mesh → material → texture`
è chiusa, con le texture assegnate ai loro stage. Restano lo skinning e alcuni
parametri di materiale senza nome.
Parser: [`tools/dsb.py`](../tools/dsb.py).

Tutto big-endian.

## Il modello del file

Un header di 16 byte seguito da **un'immagine di memoria** che il motore carica
di blocco. La conseguenza pratica, e la cosa da sapere prima di ogni altra:

> **Tutti gli offset interni sono relativi al byte 0x10 del file, non a 0.**
> Il valore `0x520` indica il byte `0x530`.

Il file ha **due regioni**: le *strutture* dall'inizio fino al byte indicato dal
campo header `0x08`, e da lì in poi i *buffer* di vertici e indici. Gli offset
dei vertex buffer nei record mesh sono relativi all'inizio della seconda.

Due indizi confermano che l'exporter scriveva struct C++ con `memcpy`:
il riempimento **`0xCC`** (stack non inizializzato di MSVC) che compare sia in
campi fissi dell'header sia *dentro* le struct, e il padding coerente con
l'allineamento naturale del compilatore. Il layout su disco rispecchia quindi
il layout in memoria del motore originale — utile quando si arriverà all'EBOOT.

## Header

| Off | Tipo | Campo |
|---|---|---|
| 0x00 | char[4] | `'DSBF'` |
| 0x04 | u16 | versione exporter: `0x0195`, `0x019D`, `0x01A4`, `0x01A5` |
| 0x06 | u16 | `0x0027`, costante |
| 0x08 | u32 | dimensione della regione delle strutture = **offset dei buffer** |
| 0x0C | u32 | dimensione del file |
| 0x10 | u32 | `1`, costante |
| 0x14 | u32 | `3`, costante |
| 0x18 | u32 | dimensione della regione dei buffer; `0x08 + 0x18 == filesize` |
| 0x1C | u32 | offset della tabella degli offset di stringa |
| 0x20 | u32 | numero di stringhe |
| 0x24 | u32 | `112`, costante |
| 0x28 | u32 | numero di oggetti |
| 0x2C | u32 | `0xFFFFFFFF`, costante |
| 0x30 | u32[2] | zero |
| 0x38 | u32 | offset della lista di binding, vedi §binding |
| 0x3C | u32 | `0xCCCCCCCC` |
| 0x40 | float[4]×2 | **bounding box** della scena: min e max |
| 0x60 | float[4] | colore RGBA (ambiente) |
| 0x70 | float[4] | parametri di proiezione (near/far osservati: 1.0, 100.0, 0.001) |
| 0x80 | u32[] | **tabella degli offset degli oggetti**, `0x28` elementi |

Le versioni exporter sul disco: `0x01A5` (386 file), `0x01A4` (43),
`0x019D` (24), `0x0195` (7).

## Tabella stringhe

All'offset `0x1C` c'è un array di `0x20` u32, ciascuno l'offset di una stringa
NUL-terminated. Le stringhe seguono, consecutive.

Gli oggetti si referenziano fra loro in due modi diversi, e conviene non
confonderli: per **CRC32 del nome** (l'IEEE standard, esattamente `zlib.crc32`)
nelle liste di binding, e per **indice nella tabella degli oggetti** nel grafo
di scena.

Il suffisso del nome codifica la classe: `-node`, `-mesh`, `-fx`, `-skin`,
`-light`, `-camera`, oppure l'estensione `.dds` per le texture.

## Record oggetto — testata di 16 byte

| Off | Tipo | Campo |
|---|---|---|
| +0x00 | u32 | indice **1-based** del proprio nome nella tabella stringhe |
| +0x04 | u32 | CRC32 del proprio nome |
| +0x08 | u32 | indice 1-based del **nome base** (nome senza suffisso di classe), `0` se assente |
| +0x0C | u32 | **codice di tipo** |

Il campo +0x00 è stato verificato su **25.443 oggetti su 25.443**: coincide
sempre con l'indice del nome il cui CRC32 sta a +0x04. Nome e hash sono
ridondanti di proposito, per permettere il lookup in entrambi i sensi.

Il campo +0x08 punta al nome base: `'CHECK-fx'` → `'CHECK'`,
`'c_etc_03a_eng.dds'` → `'c_etc_03a_eng_dds'` (il punto diventa underscore).
Corrispondenza esatta nel 92,7% dei casi; il resto sono sanitizzazioni dello
stesso tipo (`'Camera01.Target-node'` → `'Camera01_Target'`).

### Codici di tipo

| Codice | Tipo | Oggetti | % |
|---:|---|---:|---:|
| 17 | node | 11.671 | 45,9% |
| 14 | mesh | 8.707 | 34,2% |
| 4 | effect (`-fx`) | 1.792 | 7,0% |
| 2 | material | 1.792 | 7,0% |
| 1 | texture | 992 | 3,9% |
| 9 | light | 400 | 1,6% |
| 16 | skin | 77 | 0,3% |
| 11 | camera | 12 | 0,0% |

`effect` e `material` compaiono in numero **identico**: ogni materiale ha
esattamente un effetto associato.

## Record `mesh` (tipo 14)

La testata comune è lunga **112 byte** — è il significato della costante `0x24`
nell'header. Da lì in poi comincia la parte specifica del tipo.

| Off | Campo |
|---|---|
| +0x20 | float[4] bounding box locale, min |
| +0x30 | float[4] bounding box locale, max |
| +0x44 | u32 **numero di chunk di geometria** |
| +0x50 | u32[] puntatori ai chunk |

> Una mesh **non è un solo blocco di geometria**: è una lista di chunk.

Sul disco 8.655 mesh ne hanno uno solo, 42 ne hanno due, 9 tre e una quattro,
per un totale di 8.770 chunk, concentrati in sei file (`c_obj_all`, `Bee`,
`Opening`, `map_object`, `c_bos_01_all`, `Castle`). Sono poche, ma sono fra le
più grandi del gioco. Fermarsi al primo chunk non dà errore: perde in silenzio
il resto della mesh.

Il pattern `{puntatore, conteggio}` seguito dall'array inline si ripete in tutti
i tipi di record: il puntatore sta a +0x40, il conteggio a +0x44, l'array a
+0x50. Riconoscerlo è la chiave per leggere anche i record `material`.

### Chunk di geometria

| Off | Campo |
|---|---|
| +0x00 | u32 **indice dell'oggetto `material`** |
| +0x10 | u32 numero di indici |
| +0x14 | u32 byte basso = **primitiva** (3 lista, 4 strip); bit `0x100` = indici a 32 bit |
| +0x18 | u32 puntatore alla **dichiarazione del vertice** |
| +0x20 | u32 numero di attributi |
| +0x24 | u32 numero di vertici |
| +0x28 | u32 **offset del vertex buffer**, relativo alla regione dei buffer |
| +0x2C | u32 dimensione del vertex buffer |

L'index buffer segue immediatamente il vertex buffer, allineato alla dimensione
dell'indice. Non serve nessuna euristica di impacchettamento: i buffer sono
indirizzati esplicitamente.

Il campo +0x00 è l'indice dell'oggetto `material`, valido in **8.770 chunk su
8.770**. È anche la spiegazione dei chunk multipli: *un chunk per materiale*.

Il flag `0x100` è alzato in esattamente 3 chunk su 8.770 — gli unici che
superano i 65.535 vertici (`c_bos_05_all`, `c_bos_08_all`, `Castle/kabe`, fino a
123.712 vertici). Letti a 32 bit, l'indice massimo risulta *esattamente*
`n_vertici − 1`.

### Dichiarazione del vertice

Il formato del vertice non va indovinato: ogni chunk lo **dichiara**, come array
di `n_attr` coppie u32 `(semantica, tipo)`. Gli attributi si susseguono nel
vertice nell'ordine dichiarato, senza padding.

| Semantica | | | Tipo | Byte |
|---:|---|---|---:|---:|
| 0 | posizione | | 0 | `float2` 8 |
| 1 | normale | | 1 | `float3` 12 |
| 2 | colore | | 2 | `float4` 16 |
| 3 | uv | | 3 | `half2` 4 |
| 6 | tangente | | 4 | `half3` 6 |
| 7 | binormale | | 5 | `half4` 8 |
| 8 | uv2 | | 6 | `ubyte4` 4 |
| 9 | (da chiarire) | | 7 | `ubyte4` normalizzato, RGBA 4 |

I codici 6 e 7 hanno la stessa dimensione ma sono distinti: il 7 è il colore
(l'ultimo byte vale `0xFF` nel 99% dei vertici, quindi l'ordine è RGBA), il 6
compare solo accanto alla semantica 9.

Formati osservati sul disco:

| Chunk | Vertici | Stride | Dichiarazione |
|---:|---:|---:|---|
| 6.122 | 39.924 | 32 | pos:float3 nrm:float3 uv:float2 |
| 1.507 | **1.518.514** | 34 | pos:half3 nrm:half3 col:color4 uv:half2 tan:half4 binorm:half3 |
| 630 | 699.159 | 76 | pos:float3 nrm:float3 col:float4 uv:float2 tan:float4 binorm:float3 |
| 194 | 16.739 | 40 | pos:float3 nrm:float3 col:float4 |
| 71 | 37.629 | 88 | …float4 uv:float2 **uv2:float2 attr9:ubyte4** tan:float4 binorm:float3 |
| 58 | 232 | 24 | pos:float3 nrm:float3 |
| 51 | 17.622 | 20 | pos:half3 nrm:half3 col:color4 uv:half2 |
| 47 | 19.960 | 16 | pos:half3 nrm:half3 col:color4 |
| 33 | 154 | 30 | pos:half3 nrm:half3 uv:half2 tan:half4 binorm:half3 |
| 32 | 73.698 | 48 | pos:float3 nrm:float3 col:float4 uv:float2 |
| 13 | 906 | 12 | pos:half3 nrm:half3 |
| 6 | 12.414 | 60 | pos:float3 nrm:float3 col:float4 uv:float2 uv2:float2 attr9:ubyte4 |
| 4 | 234 | 16 | pos:half3 nrm:half3 uv:half2 |
| 2 | 1.392 | 36 | pos:half4 nrm:half4 uv:half2 tan:half4 binorm:half4 |

Il formato a 34 byte da solo vale **1,5 milioni di vertici su 2,4**: è la
geometria compressa dei personaggi e del mondo. È lo stesso set di attributi di
quello a 76 byte, con posizioni e versori in half-float e il colore in un
ubyte4.

Da notare: lo stesso `n_attr` copre set di attributi diversi — a 3 attributi
esistono sia `pos/nrm/uv` (stride 32) sia `pos/nrm/col` (stride 40, mesh a
colore per vertice senza texture). È per questo che dedurre il layout dal
numero di attributi non poteva funzionare.

Le semantiche 8 e 9 compaiono insieme e solo in 77 chunk, tutti in un unico
file, `Opening.ps3.dsb`. La **semantica 9 è l'indice di osso**, cioè
l'`atBlendIndex` che gli shader dichiarano (vedi [`renderer.md`](renderer.md)):
i suoi valori stanno in `0 .. n_ossi-1` del record `skin` corrispondente, e i
77 chunk che la portano sono esattamente le 77 mesh skinnate del disco. La
semantica 8 è un secondo set di UV.

Resta vero, e va tenuto insieme al resto, che **nessun vertice porta pesi**:
c'è l'indice ma non `atBlendWeight`. Lo skinning è quindi **rigido**, un osso
per vertice. Cadono così due ipotesi vecchie in un colpo solo: quella che lo
stride 88 fosse 76 byte più indici *e* pesi, e quella successiva che le
semantiche 8 e 9 non avessero a che fare con lo skinning.

### Copertura

Su 460 file, **460 estraggono la geometria**. Tutti gli oracoli sono verdi:

| Controllo | Risultato |
|---|---|
| somma delle dimensioni dichiarate == stride | 8.707 / 8.707 mesh |
| ogni indice < numero di vertici | nessuna violazione |
| le posizioni **riempiono** il bbox del record | 8.707 / 8.707 |
| la scena composta riempie il bbox dell'header | 455 / 459 file |
| normali versori | 100,00% su 2.438.577 |
| tangenti / binormali versori | 99,62% / 99,63% su 2.256.848 |
| facce allineate agli assi | 87,59% su 1.611.418 triangoli |
| UV interamente in 0..1 | 78,6% dei chunk; 99,8% entro ±64 (tiling) |
| chunk → oggetto `material` | 8.770 / 8.770 |
| material → oggetto `effect` | 1.792 / 1.792 |
| slot texture → oggetto `texture` o −1 | 1.954 assegnazioni, 0 non valide |

I 4 file che non riempiono il bbox della scena (`Dragon`, `Golem`, `Water`,
`Opening`) sbagliano di frazioni di unità su un asse: sono scene animate, dove
il bounding box dichiarato copre il movimento e non la posa a riposo.

Lo stesso parser regge sulle mappe senza una modifica: contando anche i 167
`.pac` si arriva a 5.297 blocchi, 20.804 mesh e **54.176.741 vertici**, sempre
con zero problemi. Vedi [`format_pac.md`](format_pac.md).

## Record `node` (tipo 17) — il grafo di scena

| Off | Campo |
|---|---|
| +0x40 | float[4] posizione |
| +0x50 | float[4] **quaternione** di rotazione (x, y, z, w) |
| +0x60 | float[4] scala |
| +0x70 | u32 **indice dell'oggetto genitore**, `0xFFFFFFFF` = radice |
| +0x78 | u32 **indice dell'oggetto collegato**, `0xFFFFFFFF` = nessuno |

I due campi sono indici nella tabella degli oggetti, **non** CRC — ed è
esattamente l'errore che vale la pena non rifare: cercarli fra i CRC dà valori
"sconosciuti" piccoli e ordinati, che è il sintomo di un indice letto come hash.

La verifica su tutti gli 11.671 nodi del disco non lascia margini:

- il genitore è **sempre** un altro `node` (9.135) o assente (2.536); mai un
  oggetto di altro tipo, mai fuori range, **nessun ciclo**, profondità massima 8;
- il collegato è **sempre** `mesh` (8.633), `light` (400), `skin` (77) o
  `camera` (12), mai un `node`. I conteggi coincidono con il censimento dei tipi.

E la conferma semantica, che vale più dei numeri: in `c_bos_01.ps3.dsb` le
catene sono `neck_04 → neck_03 → neck_02 → neck_01 → c_bos_01` e
`tale_05 → tail_04 → … → tail_01 → c_bos_01`. È lo scheletro di un drago.

Composta la catena di trasformazioni fino alla radice, `demoplay` dà il
risultato esatto: bounding box locale (−256,0,−128)…(256,0,128), nodo in
(640,−360,0) ruotato di 90° attorno a X, e la scena finisce **precisamente** in
(384,−488,0)…(896,−232,0), che è il bounding box dichiarato nell'header.

## Record `material` (tipo 2) ed `effect` (tipo 4)

Entrambi sono **a dimensione fissa**: 368 byte il materiale, 32 l'effetto. Ed è
la prima cosa da sapere sull'effetto: i suoi 16 byte oltre la testata comune
sono `00000000 00000000 CCCCCCCC CCCCCCCC` in **tutti e 1.792** i record. Un
`effect` è solo una maniglia con un nome — non porta dati. Il conteggio 1:1 con
i materiali si spiega così, e non c'è niente da estrarne.

| Off | Campo |
|---|---|
| +0x20 | u32 **indice dell'oggetto `effect`** associato |
| +0x24 | u32 puntatore al blocco parametri (sempre a +0x30) |
| +0x28 | u32 **identificativo di shader / tecnica** — 43 valori distinti |
| +0x3C | float[4] **diffuse** RGBA |
| +0x58 | float[3] **ambient** |
| +0x64 | float[3] **emission** |
| +0x70 | float[3] **specular** |
| +0x7C | float esponente speculare — `5.0` su tutto il disco |
| +0xE4 | u32[4] **texture per stage**, `0xFFFFFFFF` = nessuna |

Il campo +0x20 cade su un oggetto `effect` in **1.792 casi su 1.792**.

### Le texture, per stage

I quattro slot a +0xE4 sono indici di oggetto, e cadono su un oggetto `texture`
o valgono −1: **zero riferimenti non validi** su 1.954 assegnazioni. La
posizione nello slot *è* lo stage, e coincide con l'assegnazione che
[`renderer.md`](renderer.md) aveva ricavato dagli shader:

| Slot | Stage | Materiali | Le texture che ci finiscono |
|---:|---|---:|---|
| +0xE4 | 0 — colore base | 1.519 | `dot_base.dds`, `loading.dds`, `background.dds` |
| +0xE8 | 1 — utility color | **0** | mai usato |
| +0xEC | 2 — normal map | 377 | `dot_nm`, `dot_512_nm`, `dot_256_nm`, `editchar_nml` |
| +0xF0 | 3 — environment map | 58 | `forref_dungeon`, `forref_sword`, `forref_coin`, `forref_field` |

Sono i **nomi** a chiudere la verifica, non i conteggi: nello slot 2 finiscono
solo file che terminano in `_nm` o `_nml` — cioè normal map — e nello slot 3
solo file che cominciano per `forref_`, cioè *for reflection*. Nessuno dei due
prefissi compare mai nello slot 0. Un'assegnazione sbagliata degli slot non
potrebbe produrre questa separazione.

Le quattro `forref_*` sono le texture di riflessione effettivamente referenziate
dai materiali; `ref_01.dds`, l'unica cubemap del gioco secondo `renderer.md`,
non compare qui — quindi lo stage 3 in pratica usa la variante *sphere map*
(`gSphereEnvironmentMap_stage3`).

### I parametri

`specular` vale `(0.8, 0.8, 0.8)` nel 99% dei materiali e l'esponente `5.0` in
tutti: il gioco ha una risposta speculare uniforme, coerente con l'estetica a
voxel. Diffuse e ambient variano; `emission` è nulla nell'86% dei casi.

La conferma semantica di `emission` vale più della statistica: dei 26 materiali
che hanno `light` nel nome, **22 hanno emissione non nulla**, contro il 14%
degli altri 1.766. E i valori si leggono da soli — `MR_c_bos_heart` (il cuore
del boss) ha diffuse `(1.00, 0.49, 0.00)` ed emissione `0.30`: arancione e
luminoso.

## Binding delle costanti

Il campo header `0x38` punta a una lista di risorse usate per il disegno, una
voce per oggetto: `{indice del nome, CRC del nome, 0x01CCCCCC, puntatore}`.
L'ultimo puntatore porta a una **tabella di binding** di voci da 12 byte
`{puntatore al valore, 0, tag}`, dove ogni valore è un `float4` in uno slot
allineato a 16 byte.

Su `demoplay` la tabella del nodo ha 11 voci: tre con tag `0x1E1800xx` che
puntano alle tre componenti della scala, quattro con `0x1F1800xx` per il
quaternione, tre con `0x201800xx` per la posizione, più una `0x22000000`. Cioè
**una componente per slot**, come vuole il file di costanti di RSX.

È il meccanismo che collegherà i float dei record `material` agli uniform degli
shader elencati in [`renderer.md`](renderer.md): non un layout fisso da
indovinare, ma una tabella con dentro gli identificatori.

## Record `skin` (tipo 16)

Un nodo non aggancia sempre una mesh: nei 77 casi del disco — tutti in
`Opening.ps3.dsb` — aggancia uno `skin`, che a sua volta nomina la mesh. Chi
segue solo `node → mesh` perde silenziosamente quelle 77 mesh, cioè 50.043
vertici.

```
  +0x20 u32   indice dell'oggetto mesh
  +0x30 u32   numero di ossi
  +0x60       poi n entry da 80 byte:
                +0x00 float[16]  matrice 4x4
                +0x40 u32        indice del nodo dell'osso
                +0x44 u8[12]     0xCC di riempimento
```

Che il layout sia questo lo dice il record stesso: `0x60 + n * 0x50` dà
**esattamente** la sua dimensione. La stessa prova che ha risolto
`MAP_ALIGNMENT`.

La matrice è **row-major con la traslazione nell'ultima riga**, convenzione
D3D, ed è la **bind pose inversa**. L'oracolo che decide la convenzione è
questo: `world(osso) @ Mᵀ` viene *identica per tutti gli ossi* di una stessa
skin — che è la proprietà che definisce la posa di binding — mentre le altre
tre combinazioni (`M @ world`, `world @ M`, `Mᵀ @ world`) danno matrici tutte
diverse fra loro.

Con l'indice di osso nella semantica 9 del vertice e nessun peso, la formula si
riduce a un solo termine:

```
v_mondo = world(osso[v]) @ Mᵀ[osso[v]] @ v
```

**Attenzione a una trappola.** Disegnando le parti con la trasformazione del
*nodo* invece che con quella dell'osso si ottiene un villaggio 3D dall'aria
plausibile, con qualche pezzo fuori posto — sembra un errore di dettaglio ed è
invece l'ipotesi sbagliata per intero. La composizione giusta è **piatta**: la
catena di nodi passa per `oka_s-node` (scala Y 0,04) e `Dummy_2D_pos-node`, e
schiaccia tutto su un piano verticale. La scena di apertura è un **fondale 2D
visto dall'alto** — villaggio, sentieri, staccionata, alberi — non un plastico
tridimensionale. Il risultato "quasi giusto" era il più ingannevole dei due.

## La catena completa

Tutti gli anelli sono ora espliciti, e ognuno è un indice di oggetto verificato
sull'intero corpus:

```
node --+0x78--> mesh --chunk +0x00--> material --+0xE4[stage]--> texture --nome--> TPKG
  |        \                              |
  |         +--> skin --+0x20--> mesh     +0x20 --> effect (maniglia vuota)
  +0x70 genitore        +0x60 --> ossi (indice di nodo + bind pose inversa)
```

Gli oggetti `texture` portano il nome del file `.dds`, che è la stessa chiave
usata dai pacchetti [`TPKG`](format_tpk.md): l'ultimo passo del join è per
nome, senza indici numerici.

## Cosa manca

- Dei record `skin` restano i campi minori: i puntatori a +0x24 / +0x2C, che
  puntano dentro il record stesso, e i contatori a +0x28 / +0x3C.
- Significato dei tag della tabella di binding, e dei 43 identificativi di
  shader del campo material +0x28.
- Campi del materiale ancora senza nome: un secondo colore a +0xC4, una coppia
  `(0.2, 0.8)` a +0xD4 che ha la forma di bias/scala di Fresnel, e i bitfield di
  stato a +0x164 / +0x168.

## Uso

```
python tools/dsb.py info   <file.dsb>
python tools/dsb.py survey <dir>                validazione del container
python tools/dsb.py verify <dir>                oracoli sulla geometria
python tools/dsb.py obj    <file.dsb> <out.obj> geometria in spazio locale
python tools/dsb.py scene  <file.dsb> <out.obj> scena composta in spazio mondo
python tools/dsb.py names  <dir> --out x.json   dizionario CRC32 -> nome
```

I comandi accettano indifferentemente `.dsb`, i `.pac` delle mappe e i `.gz`
non decompressi: il contenitore lo risolve `blocks()`, vedi
[`format_pac.md`](format_pac.md). Nei `.pac` la sezione si sceglie con
`--sec N`; `verify` accetta `--every N` per campionare i corpora grandi.

`obj` e `scene` scrivono anche un `.mtl` accanto all'`.obj`, con colori,
esponente speculare e i nomi `.dds` in `map_Kd` / `norm` / `refl`. Le mesh
portano `usemtl`, quindi il modello si apre già assegnato — le texture vanno
solo estratte dai `TPKG` con lo stesso nome.

Il comando `names` costruisce un dizionario CRC32→nome da **tutte** le tabelle
stringhe del corpus: un nome presente in un file risolve i riferimenti in tutti
gli altri. Sul disco le 39.348 stringhe si riducono a **15.206 nomi distinti**.
