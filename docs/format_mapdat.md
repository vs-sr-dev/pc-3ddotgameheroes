# `MAP_ALIGNMENT/*.DAT` — la griglia logica delle mappe

**Stato: layout risolto, semantica dei passaggi risolta.** Restano da nominare
cinque campi del record e i valori dei tag.
Parser: [`tools/mapdat.py`](../tools/mapdat.py).

170 file in `PS3_GAME/USRDIR/DATA/MAP/MAP_ALIGNMENT/`, 34 MB. Sono gli **unici
file little-endian del disco**: tutto il resto di 3D Dot Game Heroes è
big-endian, come vuole il PPC della PS3. Se qui un campo non ha senso, la prima
cosa da provare è l'altro endianness.

Descrivono la griglia *logica* di una mappa — dove stanno eventi, nemici e
passaggi. `D_1_1_1` ha una griglia logica 112 × 96 e una griglia di schermi
7 × 8 nel `.pac`.

Le due griglie non sono indipendenti: **il rapporto è sempre un intero**, ed è
la taglia di uno schermo in celle (16 × 12 nei sotterranei, 16 × 16
nell'overworld). Una cella vale **1,6 unità di mondo**, la stessa altezza di un
personaggio. Da qui si compone la mappa — vedi
[`format_pac.md`](format_pac.md) — e da qui si legge il sistema di riferimento
in cui parlano gli script: origine a un angolo, X positiva verso destra,
Z negativa verso il basso, `SetPlayerPosition(cx, cy, piano)`.

Questo file è anche l'**oracolo esterno** con cui la composizione si verifica:
il suo campo a +0x00 vale `0xFFFFFFFF` fuori mappa, quindi dice cella per cella
dove la geometria deve esserci. `python tools/view.py layout` fa il confronto
su tutte le mappe del disco.

## Formato

```
testata
  +0x00 u32       8, 16 o 32 — costante per gruppo di mappe (16 in 140 file)
  +0x04 u32       w, celle in orizzontale
  +0x08 u32       h, celle in verticale
  +0x0C u32       ?
  +0x10 u32       len
  +0x14 char[len] stringa di livello mappa

poi esattamente w*h record, uno per cella, in ordine di riga
  +0x00 u32       identificativo di regione, 0xFFFFFFFF fuori mappa
  +0x04 u32       ?   (0 nel 91%)
  +0x08 u32       ?   (0xFFFFFFFF nel 56%)
  +0x0C u32       ?
  +0x10 u32       ?   (0 nel 97%)
  +0x14 u32       ?
  +0x18 u32       len1
  +0x1C u32       len2
  poi len1+len2 byte di testo, senza terminatore né allineamento
```

### Perché è certo

Un formato a record variabili offre un oracolo durissimo, e conviene usarlo:
percorrendolo record per record — lunghezze delle stringhe incluse — si deve
finire **esattamente** sull'ultimo byte del file dopo `w*h` record. Succede in
**170 file su 170**.

Con una taglia di record sbagliata si esce dal file quasi subito. Prima ancora,
la taglia si era ristretta a 32 byte confrontando `len(file) − w·h·taglia`:

| Taglia | Resto medio |
|---:|---:|
| 16 | 50,3% |
| 24 | 25,4% |
| 28 | 13,0% |
| **32** | **0,5%** (max 1,9%) |

36 dà resto negativo ovunque. Solo 32 lascia un avanzo dell'ordine dell'1%, che
sono appunto le stringhe.

## Le stringhe

La prima è i **parametri**, nella stessa sintassi a flag dell'API Lua; la
seconda è di solito la **classe** dell'oggetto.

```
params = "D_1_2;-gfrom_d_1;-right"     cls = "Warp"
params = "-g11;-o02;-f0;-e1;-ex0;"     cls = ""
params = "-g112;-o112;"                cls = "destructionWall"
```

> **Ma "di solito" non basta.** Nel 14% dei casi (294 su 2.170) la seconda
> stringa contiene a sua volta un `;` ed è una *seconda specifica*, non un nome
> di classe:
>
> ```
> params = "-g110;-o102;"              cls = "D_7_1_2;-g212;-o102;"
> ```
>
> Leggere solo la prima stringa, o filtrare sulla classe `Warp`, perde metà
> del grafo: 192 archi invece di 320. Il sintomo che ha fatto scoprire la cosa
> è che la reciprocità era solo del 64% — troppo bassa per un mondo navigabile.

Su tutto il disco: 1.111.469 celle, il 56% vuote, **14.099 con un oggetto** e
615 classi distinte. Le più frequenti sono `Exit` (397), `Warp` (240),
`observer` / `Observer` (303 insieme), `SwitchObserver` (80), `EnemyObserver`
(65), `destructionWall` (46), `PitFall` (21). In 11.929 celle la classe è vuota
e ci sono solo parametri.

I flag più usati: `-s` (10.196), `-g` (3.357), `-o` (2.795), `-i` (1.161),
`-f`, `-e`, `-ex`, `-p`, più parole di direzione (`right`, `up`, `down`).

## I passaggi — come si naviga il mondo

È la parte che serve davvero, ed è risolta.

> Un `Warp` porta `<mappa destinazione>;-g<nome del punto di arrivo>;-<direzione>`.
> Nella mappa di destinazione c'è un oggetto — di solito un `Exit` — che
> **dichiara quel nome** con lo stesso flag `-g`.

Il nome del gate è quindi la chiave di aggancio fra le due mappe, non una
coordinata. Esempio completo:

```
D_7_1_1  cella (87,60)  Warp  "D_7_2_1;-gd_7_1o;-right"
D_7_2_1                 Exit  "-gd_7_1o"
```

Tre verifiche indipendenti, tutte sull'intero corpus:

| | |
|---|---|
| punto di arrivo presente nella destinazione | **508 su 511** |
| destinazioni che corrispondono a un `.pac` | **140 su 143** |
| archi che hanno anche il ritorno | **305 su 320 (95%)** |

La reciprocità al 95% è la prova più forte: un mondo si attraversa nei due
sensi, e un'estrazione sbagliata non produce quel numero per caso — la prima
versione, che leggeva solo la prima stringa, si fermava al 64%.

Le poche eccezioni si spiegano da sole e sono difetti dei dati pubblicati, non
del parser: `D_7_3` punta a `D_7_2` quando le mappe vere sono `D_7_2_1`…`D_7_2_9`;
un file scrive `d7_1_4` senza il trattino basso; c'è una destinazione chiamata
`test`; e `D_0_2` — una mappa che contiene un solo oggetto, quel warp — cerca
in `Field_11` un gate che lì non esiste, in compagnia dei vari `-gDebug` e
`CAPTURE0000` sparsi nel corpus.

Il grafo finale ha **146 mappe e 320 archi**, e si legge bene:
`d_1_1_1 → d_1_2 → d_1_3` è la catena di stanze del primo sotterraneo,
`d_1_1_1 ↔ field_16` è l'uscita verso l'esterno, e `field_16` da sola si
affaccia su otto mappe fra sotterranei e aree confinanti.

## Gli NPC di mappa

271 celle su tutto il disco hanno come classe **il solo identificativo di un
NPC** — `a1_010`, `b8_010`, `a11_120`: lettera, uno o due numeri di area,
trattino basso, tre cifre — senza parametri e senza altro. 236 identificativi
distinti.

Sono le posizioni dei personaggi che stanno sulla mappa prima che un evento
cominci. Gli script li nominano come *archetipo + identificativo*
(`OldWomana6_010`), quindi la coda del nome è la chiave di aggancio, come il
nome del gate lo è per i passaggi. Vedi [`entities.md`](entities.md).

```python
mapdat.npc_spots(dat_bytes)   # -> {'a1_010': (7, 11), ...}
```

## Cosa manca

- I cinque campi del record fra +0x04 e +0x14.
- Il significato preciso del campo a +0x00, che ha 215 valori distinti sul
  disco. **Non** è un identificativo di oggetto, ed è un errore facile da fare:
  in `D_1_2` il valore `0x7D1` copre 360 celle su 520 mentre gli oggetti sono
  10. È piuttosto un identificativo di **regione** — `0xFFFFFFFF` nel 56% delle
  celle del disco, cioè fuori mappa, e poi valori bassi (`0x1`, `0x15`, `0x25`)
  o della fascia `0x7D1`…`0x7DD` a seconda della mappa. Non è nemmeno la classe
  dell'oggetto: `Exit` compare con `0x1`, `0x15` e `0x25`.

  **Un valore però ha un nome** (sessione 6): il `119` è l'**acqua**.

  A dirlo è un oracolo esterno, come sempre in questo progetto. Il file di
  collisione dice quali celle hanno per unica superficie il fondale steso sotto
  la mappa — il mare, il fossato, la gola fra due altipiani — e sono 40.964 su
  tutto il disco (vedi [`walk.md`](walk.md)). Confrontate con il tag:

  ```
  88,4% delle celle d'acqua porta il tag 119
  85,1% delle celle col tag 119 è acqua      (il tag è largo una cella in più)
  ```

  Mappa per mappa, dove il `119` compare ne porta il **98–100%**. Ed è un valore
  **unico su tutto il disco**, non uno per gruppo di mappe come si era scritto
  in sessione 5: quell'ipotesi nasceva dal confondere due cose diverse.

  Perché sono due cose diverse: l'**acqua** (il fondale è l'unica superficie) e
  il **vuoto** (nessuna collisione affatto, 55.477 celle) non coincidono, e il
  tag dichiara solo la prima — fra le celle di vuoto il `119` è appena il 10%.
  Il vuoto è piuttosto lo scarto fra la regione rettangolare dichiarata e la
  mappa vera, e per quello un tag non serve.
- Il campo +0x0C della testata.
- L'aggancio con l'enum `map_manager` estratto dal Lua, che ha 216 membri del
  tipo `MS_FIELD_50`, `MS_DUNGEON_5_1_1`, `MT_FIELD`: sono gli stessi nomi di
  mappa, ma i valori numerici sono nativi e arrivano con la Fase 3.

## Uso

```
python tools/mapdat.py info  <file.DAT>
python tools/mapdat.py cells <file.DAT>                 istogramma dei tag
python tools/mapdat.py graph <dir> --pac <dir con .pac> grafo dei passaggi
```

`--pac` attiva le verifiche: quante destinazioni esistono davvero e quanti
archi hanno il ritorno.
