# Gli oggetti di mappa, e la tavola dei simboli — `tools/nodes.py`

*Sessione 12.* Il TODO chiedeva l'**aggancio** dei ventun gimmick di
`Object/gimmick/`: un vaso non carica `EN_ENEMY_NN`, quindi la regola con cui
la sessione 11 aveva collegato i nemici al proprio modello non lo raggiunge, e
la domanda era da dove passasse.

La risposta è che non passa da nessuna regola, perché **c'è una tabella**, e sta
in chiaro in `all.lua.eu` — che è la quinta sessione di fila in cui conteneva
la cosa che cercavamo:

```lua
package_manager.gPackageManager:addNodeListElement(
    package_manager.TFI_EVENT_OBJECT,  package_manager.DFI_EVENT_OBJECT,
    package_manager.MPD_M_OBJ_127_a,   "m_obj_127_01" );
```

Quattro argomenti: il pacchetto delle texture, quello della scena, **la
costante nativa con cui il codice nomina il pezzo**, e **il nome del nodo**.
Le righe sono **1.279**, sotto `../lua/packageManager/`, e coprono tutto ciò
che il gioco carica — il giocatore, i nemici, i boss, gli NPC, gli oggetti, le
armi, il terreno.

Cioè la corrispondenza fra il nome che uno script pronuncia e il nodo dentro un
`.dsb` non è più una nostra deduzione: è un dato dichiarato.

```
python tools/nodes.py census                 la tavola, e cosa conferma
python tools/nodes.py props                  gli oggetti di mappa, per id
python tools/nodes.py enum MPD_M_OBJ_127_a   dove sta un simbolo
```

## Quanto regge

```
nodi dichiarati                              1.279
  che esistono davvero in un .dsb            1.267    99,1%
costanti passate ad AddNode dagli script       394
  dichiarate nella tavola                      387    98,2%
```

I dodici nodi dichiarati che non esistono sono avanzi (`m_obj_27`, `m_obj_30`,
`m_obj_32`, `m_obj_35`, `m_obj_42`, e tre pezzi del drago); le sette costanti
non dichiarate sono le simmetriche, fra cui `MPD_E_TORCH`, che `Object/Torch`
chiede e che nella tavola non c'è più — la torcia si carica ormai per numero.

E le **dieci righe commentate** nominano tutte cose che non si possono
disegnare: nove un nodo che in nessun `.dsb` esiste, la decima il nodo di
raggruppamento dell'erba, che di mesh non ne ha. Che siano proprio quelle è la
controprova che la tavola era mantenuta.

## Cosa conferma: tre sessioni di deduzioni, e dove sbagliavano

La tavola è un oracolo su una catena che il progetto aveva costruito da solo, e
la conferma quasi per intero:

```
EN_ENEMY_NN -> c_enm_NN      135 voci su 136
NP_NPC_NN   -> c_npc_NN      112 voci su 116
```

Le cinque eccezioni non sono sparse, e una si spiega da sé — nel file, sotto
alla riga che la sostituisce:

```lua
  addNodeListElement( ..., EN_ENEMY_24_08, "c_enm_11_08" );
--addNodeListElement( ..., EN_ENEMY_24_08, "c_enm_24_08" );
```

`c_enm_24_08` non esiste, e il proiettile dello Slime blu prende quello dello
Spider blu. Gli autori hanno lasciato l'originale commentato lì accanto.

Le altre quattro sono **due numeri scambiati** —
`NP_NPC_19` è `c_npc_26` e `NP_NPC_26` è `c_npc_19` — ed è esattamente la
coppia che la sessione 8 aveva indicato come punto debole della propria
rubrica: *«le eccezioni cadono **tutte** su `c_npc_19`…`c_npc_26`»*. Il disco
dice dov'era lo scarto e conferma tutto il resto.

### E la rubrica degli abitanti, per un'altra strada

I 263 file di `../lua/Object/npc/` sono uno per abitante, si chiamano
`n<NN><archetipo><identificativo>`, e ognuno carica il proprio nodo. Passandoli
per la tavola si **legge** la rubrica archetipo→modello che la sessione 4 aveva
dedotto dai nomi dei 237 script di dialogo:

```
archetipi confrontabili   22
  concordi                20
  corretti                 2
```

E le due che cambiano valgono più delle venti che tengono:

- **`princessbug` è `c_npc_26`**, non `c_npc_19` — è lo scambio di cui sopra.
  Vista, la differenza è di colore: `c_npc_19`, `c_npc_26` e `c_npc_27` sono
  **tre figure alate** rosse, blu e verdi, e infatti i file si chiamano
  `N19PrincessBug`, `N26PrincessBugB`, `N27PrincessBugC`.
- **`goblinred` è `c_enm_12`**, cioè un modello di **nemico**. Questo non è uno
  scarto di un numero, è un cambio di famiglia: i goblin rossi amichevoli del
  villaggio riusano il goblin rosso che si combatte, ed è per questo che sotto
  `Object/` non esiste nessun `N26GoblinRed` — non serviva. `view.py char
  c_enm_12` disegna una creatura rossa con la tunica blu e le zanne bianche.

Nessuna deduzione fatta *dentro* la sola famiglia `c_npc` poteva arrivarci: la
rubrica cercava un `c_npc_NN` e ne trovava uno. Sbagliava restando plausibile,
che è il modo in cui sbagliano le inferenze fatte bene.

*Da cui una nota di metodo: il numero nel nome di uno script di **dialogo** e
il numero del **modello** sono due numerazioni, non una. Combaciano venti volte
su ventidue, ed è per questo che sembravano la stessa cosa.*

## Gli oggetti di mappa: la cella dichiara il modello

Gli script di `Object/gimmick/` e `Object/MessageBoard/` caricano
`MPD_M_OBJ_*`, che la tavola manda su `m_obj_*` dentro
`map/map_model/map_object.ps3.dsb` — più `Torch.ps3.dsb` per il 99, che ha un
file suo come i boss. E la cella lo sa già:

> **l'identificativo di cella è `4000 + il numero del modello`**

Non è una lettura di una: la reggono tre famiglie di script che non si
conoscono, con tre numeri diversi, e **51 celle su 51** senza una discordante.

| classe di cella | id | modello | script |
|---|---:|---|---|
| `Signboard00`…`Signboard33` | 4041 | `m_obj_41` | 34 file |
| `Stonemark00`…`Stonemark11` | 4067 | `m_obj_67` | 12 file |
| `Well01`, `Well02`, `Well03` | 4063 | `m_obj_63` | 3 file |

Da lì si legge tutta la banda 4xxx, che fino a ieri era un numero e basta:

```
4127   272 celle   m_obj_127    Grass, l'erba che si taglia
4111     6 celle   m_obj_111    BossMarker, la lapide del boss
4116..21 1 cella   m_obj_116..121  i sei altari delle sfere
4062     2 celle   m_obj_62     SwordPedestal
4099   859 celle   m_obj_99     la torcia, dalla sua libreria
4060 1.022 celle   m_obj_60     il forziere
```

Su tutto il disco: **11.924 celle-oggetto, 7.695 con un modello (64,5%)**.

### La prova per struttura, che è più forte del conto

I sei altari e le sei lapidi non stanno dove capita:

```
D_1_2  Grass Temple    4111          D_1_3  Grass Temple    4116  (7,4)
D_2_2  Forest Temple   4111          D_2_3  Forest Temple   4117  (8,4)
D_3_2  Desert Temple   4111          D_3_3  Desert Temple   4118  (8,4)
D_4_2  Aqua Temple     4111          D_4_3  Aqua Temple     4119  (8,4)
D_5_2  Flame Temple    4111          D_5_3  Flame Temple    4120  (8,4)
D_6_2  Wind Temple     4111          D_6_3  Wind Temple     4121  (8,4)
```

Una lapide per sala del boss, un altare nella sala successiva, sempre alla
stessa cella. E l'ordine degli altari è quello dei templi, che si legge nelle
guardie degli script: `item_yelloworb`, `item_greenorb`, `item_grayorb`,
`item_blueorb`, `item_redorb`, `item_whiteorb`. **Sei su sei, nel tempio
giusto, nell'ordine giusto.**

*E in sessione 13 anche del colore giusto*, che è la prova che qui mancava —
il **materiale** della sfera, letto dall'indice a `+0x00` del suo chunk:

| altare | l'item dello script | materiale | colore | il walkthrough |
|---|---|---|---|---|
| 4116 | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

Sei su sei con i nomi del walkthrough. E i due nomi interni che non descrivono
un colore — `gray` e `white` — sono esattamente i due che il modello smentisce:
il nome che il gioco mostra al giocatore vince su quello che gli autori si sono
scritti.

Perché il materiale va **guardato** e non dedotto dal numero: `m_obj_118_b` usa
`orb_121` e `m_obj_121_b` usa `orb_118`, uno **scambio esatto** in mezzo a
quattro che combaciano. Ed è la seconda coppia scambiata che questo disco ci
fa trovare, dopo `NP_NPC_19` ↔ `NP_NPC_26`.

Le lapidi sono sette script per sei celle, e il settimo lo dichiara da sé: in
`BossMarker07` la guardia è commentata e al posto dell'evento c'è
`Print("ぼひょー")`. È un avanzo, e si firma.

`SwordPedestal` sta in due mappe, e una si chiama `//Sword Room`. Il
walkthrough: *«retrieve the Ancient Sword from the pedestal»*.

### E l'assenza si legge come la presenza

Gli identificativi **4100** (i `Warp` e gli osservatori) e **4101** (`Exit`,
`destructionWall`, `WarpDoor`) sono fra i pochi che *non* hanno un `m_obj`. Non
è un buco della tavola: è che non c'è niente da disegnare — la stessa cosa che
[`walk.md`](walk.md) aveva misurato dal lato della geometria, senza poterla
spiegare.

E si vede meglio di così. Delle 4.229 celle senza modello, **3.843 (il 91%)
stanno in `4100`…`4105`**, sei numeri di fila; e `m_obj_100`…`m_obj_107` è
**il buco più lungo di tutta la numerazione** della libreria, otto numeri,
dove tutti gli altri sono larghi da uno a cinque e sparsi. Il disco ha
riservato un blocco della numerazione degli oggetti a quelli che un oggetto
non ce l'hanno.

> *Corollario di* `walk.md`: «quando un oggetto dichiarato non si trova in
> nessuno dei file che descrivono il mondo, non è un difetto di lettura — è la
> dichiarazione che quel mondo si costruisce a runtime». Ora quella
> dichiarazione ha anche un indirizzo.

## Le altre due bande

```
3000 + NN  ->  d_hmw_NN     28 numeri su 28
1000 + NN  ->  ?            38 numeri, da 1 a 51
```

`d_hmw` sono i *«Dungeon配置物»*, e il commento degli autori li chiama proprio
così — **oggetti di piazzamento** del sotterraneo. I 28 numeri che le celle
usano sono esattamente i 28 che `d_haichi.ps3.dsb` porta, senza uno in più né
uno in meno; l'unico dichiarato che le celle non usano è `d_hmw_03`, che è
anche l'unico ad avere sotto-varianti.

La banda 1000 è l'equivalente in campagna — l'85% delle sue 8.053 celle sta in
una `field_*` — e **non si chiude allo stesso modo**. Il motivo si vede, ed è
la cosa utile da lasciare scritta: dove il sotterraneo ha **una** famiglia
(`d_hmw`), la campagna ne ha **due** (`f_hmw` e `f_ntr`, cioè i manufatti e la
natura), e un solo numero non può dire quale delle due. Il campo è stretto a
due liste dichiarate, di 21 e 14 numeri; quello che manca è la regola con cui
il disco le mette in fila.

*Provata e caduta: che il numero fosse l'ordinale nella lista del pacchetto.
Nel sotterraneo darebbe 1…28 e invece i numeri arrivano a 36 con dei buchi,
cioè sono nomi. Se là sono nomi, in campagna non possono essere ordinali.*

### Il conto del sotterraneo torna da tre file

E vale la pena metterlo per iscritto, perché è il metro con cui misurare la
campagna:

```
oggetti dichiarati da d_haichi.ps3.dsb            28
voci DFI_DUNGEON_OBJECT nella tavola dei simboli  28
numeri usati dalla banda 3xxx                     28
```

Anche l'ultimo dubbio si chiude: `d_hmw_03`, che stava scritto qui come *«il
solo dichiarato che le celle non usano»*, **non manca — sta in un altro file**.
La famiglia è divisa fra `d_haichi` (i 28) e `d_chikei`, che porta lui solo, ed
è anche l'unico con sotto-varianti. Non era un avanzo: era altrove.

Per la campagna gli stessi due conti tornano fra loro — `f_haichi` dichiara
**40** oggetti e `DFI_FIELD_OBJECT` ha **40** voci — ma il terzo no: le celle
usano 38 numeri che arrivano a **51**.

### E le famiglie non sono due: la tavola le nomina tutte

Il campo era stato descritto come stretto a `f_hmw` e `f_ntr`. Sono di più, e
la tavola dei simboli dà il nome esteso della sigla — la costante è in rōmaji
dove il nodo è in tre lettere:

| sigla | costante | voci | cos'è |
|---|---|---:|---|
| `d_kbe` | `MPD_D_KABE` | 145 | 壁, il muro |
| `d_dns` | `MPD_D_DANSA` | 28 | 段差, il dislivello |
| `d_yka` | `MPD_D_YUKA` | 14 | 床, il pavimento |
| `d_hsr` | `MPD_D_HASIRA` | 8 | 柱, la colonna |
| `d_skr` | `MPD_D_SIKIRI` | 7 | 仕切り, il divisorio |
| `f_gke` | `MPD_F_CLIF` | 62 | 崖, la rupe |
| `f_jmn` | `MPD_F_CHIKEI` | 46 | 地面/地形, il terreno |
| `d_hmw`, `f_hmw` | `MPD_D_HMW`, `MPD_F_HMW` | 33, 28 | non espansa |
| `f_ntr` | `MPD_F_NTR` | 17 | non espansa |

Sette sigle su nove si leggono, e le due che restano sono proprio quelle delle
bande aperte. *(`NTR` per «natura» e `HMW` per i manufatti sono la lettura che
questo documento usava già; l'una regge sull'inglese, l'altra resta una
congettura — le altre sette invece non sono più tali.)*

E `MPD_F_CLIF_N_M` → `f_gke_NN_MM` sta accanto a `MPD_F_CHIKEI_N_M` →
`f_jmn_NN_MM` con **lo stesso primo numero**, `{1, 3, 5, 6, 8}`: il primo
numero è il *tipo di terreno* e il secondo il pezzo. Rupe e suolo sono
dichiarati in coppia.

### La banda 1xxx: tre cose che non è

Misurate, così il prossimo non le ripete:

- **non è `1000 +` il numero di un nodo.** Provate tutte le famiglie del disco:
  la miglior copertura dei 38 numeri è il **71%** (`m_obj` e `c_enm`), e nessuna
  arriva a 51;
- **non è un indice locale alla mappa.** Gli stessi numeri ricorrono su mappe
  diverse — il 42 in cinque mappe `D_21`/`D_22`, il 21 in otto — e ogni mappa ne
  usa **pochissimi**, mediana 4, con decine di celle ciascuno. È un
  identificativo globale, come 4xxx;
- **non è il bordo di uno schermo.** Le celle 1xxx che cadono sul bordo del
  proprio schermo sono il **29%**, contro il 21% che darebbe il caso.

Quel che invece si vede, e che è il vero indizio: le celle di uno stesso numero
**disegnano figure**. In `D_24_3` il 21 fa la **cornice della mappa**, una cella
di spessore su tutti e quattro i lati; in `D_23_1` fa una colonna continua per
tutta l'altezza; in `field_16` i numeri 41, 42 e 43 stanno in **filari
regolari** a due o tre celle di passo. Un numero che marca un perimetro non è un
oggetto per cella: somiglia più a un **contorno**, e le famiglie che il disco
tiene per i contorni ora hanno un nome — 崖 la rupe, 段差 il dislivello, 壁 il
muro.

### E la banda si spacca in due, misurata contro il terreno

Se un numero è un contorno di dislivello deve stare **dove il terreno fa un
gradino**. Misurato sulla collisione — quota massima della cella contro quella
delle quattro vicine, salto oltre mezza cella:

```
numero   celle   con un gradino accanto
     1   1.154        86%
     4     195        85%
    43     293        80%
    44     152        80%
     6     668        72%
    21   1.016        52%
    41   1.655        46%
     5     691        41%
                            media delle celle di mappa   33%
    26     290        20%
    42   1.362        14%
```

Non è un risultato solo, sono due gruppi: c'è chi sta sul gradino **tre volte
più spesso del caso** e chi ci sta meno della metà. Un numero che vale 86% e uno
che vale 14% non possono essere la stessa specie di cosa, e il confine cade
dove ci si aspetta che cada — fra ciò che segue la forma del terreno (le rupi, i
dislivelli) e ciò che ci sta semplicemente sopra.

È il punto da cui ripartire, e adesso la domanda è più precisa di *«qual è la
regola»*: **sono due bande in una**, e conviene prima separarle e poi cercare
due regole.

## Come si disegnano — `walk.Walk.populate_props`, `view.Charlib`

Un oggetto di mappa entra nel registro delle entità come tutti gli altri, e il
disegnatore non ha avuto bisogno di una strada nuova: cambia solo la libreria
in cui cercare il nodo, e i nomi bastano a dire quale, perché sono unici sulle
quattro di `map/map_model/`.

Due scelte che vale la pena dichiarare:

- **quale nodo**, quando un modello ne ha più d'uno. Si prende **il primo
  `AddNode` dello script**, che è la posa in cui l'oggetto compare: `Grass`
  carica prima l'erba e poi il taglio, e chi entra nella stanza vede l'erba.
  A parità, il nome minore — `_a` prima di `_b`.
- **niente pose**. Un vaso non cammina: la posa che l'entità chiede si ignora.

```
python tools/view.py play d_60_3 --cell 11,13     il pozzo, col suo cartello
python tools/view.py play field_91 --cell 27,44   le colonne della corte
python tools/view.py play d_1_1_1 --cell 39,18 --skip 6   i vasi e la porta
python tools/view.py play <mappa> --no-props      senza, per confronto
python tools/view.py char m_obj_116_a,m_obj_116_b,m_obj_63,m_obj_60,m_obj_111
```

Il pozzo di `D_60_3` è la verifica di riconoscibilità: la cella dice `Well01`,
l'identificativo 4063 dice `m_obj_63`, e quello che compare è **un pozzo di
pietra con l'intelaiatura di legno**, con accanto il cartello che la cella
vicina dichiara. Nella corte del castello compaiono **colonne e bracieri
schierati in specchio** sui due lati, che è quello che *配置物* vuol dire. E
nella stanza del Grass Temple dove la sessione 8 aveva messo due Scorpion e uno
Soldier Bones ci sono adesso anche **due vasi e la porta rossa**.

Messi in fila con `view.py char`, i modelli si riconoscono uno per uno — e uno
chiude un cerchio da solo:

```
m_obj_116_a   un altare di pietra
m_obj_116_b   una sfera gialla
m_obj_63      un pozzo
m_obj_60      un vaso
m_obj_111     un monumento a gradini
m_obj_127_01  un ciuffo d'erba verde
```

**`m_obj_116_b` è una sfera gialla**, ed è il secondo nodo che `OrbAltar01`
carica — quello che `OrbAltar01InitializeActor` spegne con
`SetNodeVisible(1, false)` *«se hai già preso la sfera gialla»*
(`EventFlag.item_yelloworb`). Il codice dice cosa nascondere e il modello è
giallo: due file che non si conoscono, la stessa sfera.

`m_obj_60` è **un vaso**, ed è l'oggetto più numeroso del disco: **1.022
celle**, più di qualunque altro. Che sia il `Jar` dei tre colori si dimostra
poco più sotto, e la dimostrazione è la stessa che smonta l'ipotesi su
`AddColor`.

## `AddColor` non è una tinta da applicare — l'ipotesi caduta

Gli oggetti vengono **scuri**, e la spiegazione ovvia era che `GrassInitialize`
chiama `AddColor(0.25, 1.0, 0.25)` e noi non la eseguiamo. È falsa, e vale la
pena averla scritta perché era la prima voce del TODO seguente.

Il primo dubbio è nel codice: `12GoblinRed` chiama `AddColor` **quattro volte
di fila e le prime due sono identiche**, il che esclude sia «una per nodo» (ne
carica quattro, diversi) sia «una per colore del modello» (sarebbero distinte).

La prova è un confronto che non costa niente. Per ogni colore dichiarato si
cerca la tinta più vicina **fra quelle che i vertici del suo modello già
portano**, e si misura lo scarto d'**angolo** — cioè il colore a meno della
luminosità, che nei vertici è illuminazione precotta:

```
python tools/nodes.py colors

132 colori dichiarati da 42 file, contro la tavolozza del proprio modello
  scarto d angolo   mediana 0,5 gradi   sotto 5 gradi 94%
  luminosita del modello sul dichiarato   mediana 1,50
```

**Mezzo grado di mediana su 132 valori.** I colori che `AddColor` dichiara
*sono* quelli del modello, non una tinta da sovrapporgli: applicarli non
cambierebbe la tinta di niente, e il buio viene dalla nostra illuminazione, non
da una chiamata mancante.

A cosa servano davvero resta da vedere, ma l'ipotesi con l'indizio migliore è
che siano i **cubetti in cui la cosa si sfascia**: 44 dei 52 file che chiamano
`AddColor` chiamano anche `SetAmount(n)`, e **gli 8 che non lo fanno sono
esattamente gli otto boss** — che in cubetti non esplodono, hanno una scena di
morte propria.

### E chiude la domanda del vaso

Perché la stessa misura, applicata a `Jar.lua` contro `m_obj_60`, dà tre
colpi su tre in un modello che di tinte ne ha sette:

```
dichiarato 0,74 0,55 0,31  ->  0,593 0,442 0,245    0,3 gradi
dichiarato 0,63 0,44 0,28  ->  0,304 0,213 0,135    0,1 gradi
dichiarato 0,44 0,30 0,28  ->  0,373 0,254 0,238    0,1 gradi
```

**`m_obj_60` è il `Jar`**, e l'identificativo di cella 4060 è il vaso: 1.022
celle, l'oggetto più numeroso del disco. La domanda con cui il TODO si apriva —
*«un vaso non carica `EN_ENEMY_NN`»* — si chiude qui, e non per il modo in cui
è stata posta: il vaso non carica niente perché non ha uno script. Lo istanzia
il C++, e di suo il disco dichiara la cella (`4000 + 60`) e la tavolozza.

*Ed è coerente che `Jar` sia uno dei **due** gimmick su ventuno senza script —
l'altro è `lava_fountain`, undici parametri con i commenti degli autori («se ne
fai troppi il gioco si ferma»). Due file di soli dati, per le due cose che il
motore fabbrica da sé.*

## Cosa manca

Il buio, che adesso si sa dove cercare: non in `AddColor` ma nel **modello
d'illuminazione**, che [`renderer.md`](renderer.md) dichiara mancante da
sempre. I vertici portano una luce precotta ~1,5× più chiara del colore
dichiarato, e noi la moltiplichiamo per una nostra lambertiana che la spegne.

E resta aperta la banda 1xxx, che è l'unica delle quattro numerazioni di cella
ancora chiusa — vedi sopra.
