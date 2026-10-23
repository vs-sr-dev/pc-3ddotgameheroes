# Camminare nel mondo

**Stato: il giro di gioco esiste.** Si sta su una mappa, si cammina di cella in
cella, si attraversa un passaggio e si arriva nell'altra mappa nel punto che il
disco dichiara, si parla con chi ci abita e risponde con il suo dialogo.
Modulo: [`tools/walk.py`](../tools/walk.py) — regole e verifiche, senza schermo.
Comando: `python tools/view.py play <mappa>`.

```
python tools/view.py play field_91          la corte del castello, 33 abitanti
python tools/view.py play d_1_1_1           il primo sotterraneo
python tools/view.py walkabout              la misura, su tutte le mappe
python tools/walk.py                        le verifiche interne (50 proprietà)
```

Frecce o WASD per camminare, spazio per parlare con chi si ha davanti, `K`
toglie e rimette il soffitto, il mouse orbita, `ESC` esce.

È la prima cosa del progetto che si **gioca** invece di guardarla, ed è anche
la prova d'integrazione più severa che ci sia: mette in fila la composizione
degli schermi, la griglia logica, il grafo dei passaggi, la rubrica degli NPC,
il registro delle entità e la VM Lua. Se un solo riferimento è storto non si
vede un'immagine storta — si cammina dentro un muro, o si esce nella mappa
sbagliata.

Quasi tutti i pezzi c'erano già; mancava l'anello. L'unico formato nuovo è la
collisione, [`MAPCOLLISION/*.DPK`](format_dpk.md), ed è arrivata dopo — quando
camminare ha reso evidente che approssimarla non bastava.

## La regola: una cella per volta

Una cella vale `1,6`, che è anche l'altezza di un personaggio. Il passo è
discreto e si muove nel tempo (`entity.Entity.move_to`), e girarsi **non è**
camminare: se si guarda da un'altra parte, il primo comando gira e basta. È il
comportamento dei giochi a griglia, ed è anche l'unico modo di parlare con chi
si ha di fianco senza salirgli addosso.

Il comando è relativo a chi guarda: "avanti" è dove punta la telecamera, non
una direzione fissa del mondo. Con la mappa girata, il contrario è
disorientante.

## Il muro

Le celle fuori mappa (`0xFFFFFFFF` nella griglia logica) sono un muro, ma
**grossolano**: quella griglia marca regioni rettangolari, non corridoi.

La parete vera la dice `MAPCOLLISION/*.DPK` — vedi
[`format_dpk.md`](format_dpk.md) — una mesh di triangoli per mappa, nello stesso
riferimento del `.pac`, che è proprio ciò con cui il gioco ferma il giocatore.
Dove manca (i palchi degli eventi, la scena d'apertura) si ripiega sulla
geometria disegnata, che è un'approssimazione e non lo nasconde.

Da mesh a risposte: ogni cella tiene una **colonna** di fette da un quarto di
casella, e per ogni fetta la quota più alta che vi si è trovata. I triangoli si
seminano di punti a passo di una fetta, perché in una mesh di collisione i
triangoli sono grandi — un pavimento di venti caselle è due triangoli — e i loro
soli vertici lascerebbero vuote tutte le celle in mezzo.

Da dove parte la colonna e quante fette ha **lo dichiara la mesh**, e non è un
dettaglio di allocazione: vedi [«Il fondo e il cielo»](#il-fondo-e-il-cielo).

Da qui le due sole domande che servono:

- **si passa?** la colonna è libera all'altezza del corpo, da +0,3 a +1,3 sopra
  i piedi;
- **dove si posa il piede?** la superficie più alta entro un gradino dai piedi —
  che è anche come si sale una scala senza sapere che è una scala, e come non si
  sale una rupe.

Un dislivello più alto di un gradino non si sale **e non si scende**: è ciò che
impedisce di camminare fuori dal bordo di un tetto.

### Il gradino vale una casella, e non è una taratura

Era l'unico numero inventato di tutto il sistema — avevo scritto 0,6, «un
ginocchio» — ed era sbagliato di quasi tre volte. Lo dicono due oracoli
indipendenti.

**Il primo: i dislivelli sono quantizzati.** Fra celle vicine calpestabili la
differenza di quota è un multiplo esatto di 1,6.

```
  0,00  (0 caselle)   85,3%
  1,60  (1 casella)    8,6%
  3,20  (2 caselle)    3,3%
  4,80  (3 caselle)    0,2%
```

In mezzo non c'è quasi niente. Il mondo è costruito a gradini alti quanto un
personaggio, come ogni altra cosa in questo gioco.

**Il secondo: gli abitanti si saturano.** Un abitante che la mappa dichiara è un
posto in cui il gioco *deve* far arrivare il giocatore, altrimenti non ci si
parla. Quanti se ne raggiungono, al variare della soglia:

```
gradino  0,6:  206/264        gradino  2,5:  256/264
gradino  0,9:  208/264        gradino  3,3:  256/264
gradino  1,7:  255/264        gradino  4,9:  256/264
```

Una casella compra 49 abitanti; tutto il resto ne compra uno. Non c'era un
parametro da tarare, c'era un quanto da riconoscere.

### Una cella ha fino a quattro pavimenti

Il ballatoio sopra la sala, il ponte sopra il fossato, il tetto sopra la casa.
Tenendo un solo piano per cella, un posto in cui si è già stati diventa un
dislivello invalicabile, e lo stato di chi cammina non è «la cella» ma **la
cella e il piano**: chi sta sul ballatoio e chi sta sotto sono nello stesso
posto e non si incontrano.

### L'errore che questa parte è costata

La prima versione contava tutti i vertici insieme, e la mappa si spezzava in
isole: da qualunque punto si raggiungeva quasi niente, e sembrava un problema
di soglie.

Non lo era. **Un blocco pieno ha vertici solo sulle sue facce.** Il pavimento
di un sotterraneo alto 1,6 ne offre quindi due — la faccia di sopra a 1,6 e
quella di sotto a 0,0 — e la più bassa, vista dai soli vertici, sembra un
pavimento perfettamente calpestabile con un metro e mezzo d'aria libera sopra.
Cioè si camminava dentro la roccia, in un piano che non esiste, scollegato da
tutto.

A dire quale delle due facce è un pavimento è la **normale**: si sta in piedi
su ciò che guarda in su. Quindi le quote si raccolgono in due tabelle — le
superfici rivolte verso l'alto per il pavimento, tutto quanto per l'ostacolo,
perché per sbatterci contro la normale non conta.

*Corollario da tenere: la geometria dichiara superfici, non volumi. Dedurre il
solido dai vertici funziona solo se si guarda da che parte sono girati.*

## Il fondo e il cielo

La colonna era ancorata a zero e alta 64 fette, cioè 25,6 unità, e tutte e due
le cose erano assunte invece che misurate. Tutte e due sbagliate:

- **lo zero non è il fondo del mondo.** 69 file di collisione su 171 scendono
  sotto, fino a −4,35. Peggio: il pavimento di un sotterraneo sta a
  `−0,000002` — lo scarto di un `float32` passato per una somma baricentrica —
  e una fetta ancorata allo zero se lo perde **per intero**. In `d_1_2` i 114
  punti che cadevano nella cella d'ingresso venivano buttati tutti e 114, e la
  cella d'arrivo del primo passaggio del gioco risultava non calpestabile.
- **25,6 unità non sono il cielo.** `FIELD_07` è una montagna e arriva a 51,2:
  la sua cima veniva troncata via.

Adesso base e altezza le dichiara la mesh (`walk.span()`), con una fetta di
margine da ogni lato.

### Il fondale

Rimessi i piani sotto lo zero, la misura è **peggiorata**: dal 63% al 41% delle
celle. Il motivo è che sotto ogni mappa di campagna c'è un unico quadrilatero
piatto steso da parte a parte — in `FIELD_22` sono letteralmente **due
triangoli** per 10.368 caselle, su una mappa che ne ha 16.384 — a −3,2 o giù di
lì. Guarda in su, quindi è un pavimento a tutti gli effetti; solo che sopra ha
metri di roccia. Ed essendo il piano più basso, è quello da cui la mappa
comincia: `field_30` scendeva a 84 celle percorse su 10.219.

A separare il fondale da un pavimento vero è un conto, non una soglia. Le celle
a due piani sono **163.878**, e in **758** soltanto quello di sotto non è la
quota minima della mappa. Cioè il ballatoio sopra la sala esiste — ed è lo
0,16% del mondo; tutto il resto della sovrapposizione è questo fondale.

`Columns.bury()` lo toglie dai pavimenti dove sopra c'è terra. Riconoscerlo
vuole tre cose insieme, perché in un sotterraneo la quota minima **è** il
pavimento e toglierlo svuoterebbe la mappa: è **piatto** (tutto entro una
fetta), è **esteso** (almeno un terzo delle celle che hanno un pavimento), e ha
**terra sopra** (in almeno un quarto delle celle che copre). È la terza a
separarlo dal pavimento di `d_1_2`, che pure copre il 69% della sua mappa ma
non ha niente sopra di sé.

### L'acqua, che cade da qui

Le celle in cui il fondale è l'**unico** piano non sono terra: sono il mare, il
fossato, la gola fra due altipiani. `Columns.water()` le dà, e sono **40.964**
su tutto il disco.

E qui il disco si conferma da solo, per una via che non c'entra niente: la
griglia logica assegna a quelle celle un identificativo di regione, e quello è
**119** — un valore unico su tutto il disco, non uno per gruppo di mappe come
si era ipotizzato.

```
88,4% delle celle d'acqua porta il tag 119
85,1% delle celle col tag 119 è acqua      (il tag è largo una cella in più)
```

Mappa per mappa, dove il tag c'è, ne porta il 98–100%. Quindi **l'acqua si sa
senza aprire il file di collisione**, che è ciò che serve al renderer per
sapere dove disegnarla.

Da non confondere con il **vuoto** — le celle senza nessuna collisione, 55.477
— che è un'altra cosa e che il tag non dichiara: quelle sono lo scarto fra la
regione rettangolare e la mappa vera.

## I passaggi, usati invece che contati

Che una cella di partenza dichiari mappa, varco e direzione, e che nella
destinazione ci sia la cella che quel varco lo dichiara come proprio, era già
stabilito — vedi [`format_mapdat.md`](format_mapdat.md), 508 partenze su 517.

```
Warp        D_1_2;-gfrom_d_1;-right      D_1_1_1, cella (55,11)
Exit        -gfrom_d_1                   D_1_2,   cella (12,17)
```

Quello che cambia è che quel numero smette di essere una statistica sul grafo e
diventa il modo in cui si cambia mappa. Attenzione alle **due forme** del
varco, perché la seconda è il grosso dei passaggi interni:

- **a nome** (`from_d_1`, `dungeon1`, `tf11_2`) — l'arrivo è una cella `Exit`
  con lo stesso `-g`;
- **a numero** (`-g11;-o101;`) — l'arrivo è la cella che porta quella coppia
  come *propria* identità. Sono le scale, e le due celle si nominano a vicenda:
  `A` dichiara di portare all'identità di `B`, e `B` a quella di `A`.

Leggendo solo la prima forma si risolve il **46%** invece del 98%. Il sintomo è
lo stesso che aveva già tradito il grafo una volta: un numero troppo basso per
un mondo che si attraversa.

Da non confondere: `arrivals` — ogni cella che dichiara un `-g` — contiene
centinaia di osservatori e gimmick, e non è un posto da cui partire. Il punto
d'ingresso di una mappa sono le celle di classe **`Exit`**, che sono i posti in
cui il gioco stesso fa comparire qualcuno. Partire dal primo `-g` qualsiasi
faceva cominciare la partita **in cima a un muro**, con due celle raggiungibili
in tutto.

## Gli abitanti

Le celle che portano come classe il solo identificativo (`a1_010`) sono i posti
degli NPC: 264 celle, 236 identificativi. Gli script di evento ne nominavano 37.

Gli altri li nomina il **loro** script. I 243 file
`npcevent_n<NN><archetipo><id>` sono uno per abitante e dichiarano nel nome del
file il modello (`n05` → `c_npc_05`) e l'archetipo, e nel corpo il dialogo; 151
di loro si nominano anche per esteso al proprio interno
(`setnpccamerac("OldMana1_300")`), che è da dove viene la scrittura esatta del
nome — `Blacksmith` o `BlackSmith` non lo si può indovinare.

Rimettere insieme le due metà popola una mappa da sola: **225 identificativi su
236 (95%)** con nome, faccia e battuta. E il nome è quello che gli script
userebbero, quindi un evento che più tardi nomini quell'NPC trova **questo**,
già al suo posto, invece di materializzarne un altro senza posizione.

Sei archetipi in più hanno guadagnato il loro modello dichiarato:
`WiseMan1` → `c_npc_01`, `WiseMan2`…`WiseMan6` → `c_npc_20`…`c_npc_24`.

## Gli oggetti di mappa sono attori, non pezzi di mappa

La griglia logica dichiara **1.518 celle in 112 classi** oltre ai passaggi e
agli abitanti (`Grid.objects`):

```
Exit             397    observer  163    destructionWall  46    WarpDoor  29
Warp             240    Observer  149    up               30    PitFall   21
SwitchObserver    80    EnemyObserver 65    BlackHole       7    Barricade  7
```

La domanda che conta per chi cammina è dove vivano: nel `.pac` che si disegna,
nel `.DPK` che ferma, o in nessuno dei due. Misurato cella per cella, con la
quota della geometria disegnata e con la colonna della collisione:

| classe | geometria sopra il pavimento | ferma il corpo |
|---|---:|---:|
| `destructionWall` (45) | 0% | 0% |
| `BlackHole` (7) | 0% | 0% |
| `WarpDoor` (29) | 3% | 0% |
| `PitFall` (21) | 19% | 14% |
| `observer` / `Observer` / `*Observer` (457) | 65–70% | 65–70% |

**Il muro rompibile non esiste in nessuno dei due file.** La sua cella è
pavimento liscio: né si disegna né ferma. Lo stesso per il buco nero e per la
porta. Il motore li istanzia da queste celle come attori — la tassonomia è
l'enum `ActorType` estratto dal Lua, che ha appunto `AT_DESTRUCTION_WALL`,
`AT_DOOR`, `AT_WOOD_DOOR`, `AT_GIMM_GROUND_SWITCH`, `AT_PUSH_OBJECT` fra i suoi
33 membri.

Due conseguenze, e vanno tenute tutte e due:

- **la misura attraversa i muri rompibili.** 45 muri e 7 barricate sono
  invisibili a chi cammina, quindi il `walkabout` è un limite superiore. È un
  limite stretto — 52 celle — ma va detto, perché la tentazione opposta
  (aprirli e vedere quanto mondo si guadagna) l'ho provata e dà **zero celle in
  più su tutte e 78 le mappe**: erano già aperti.
- **gli osservatori non sono grilletti da pavimento.** Due su tre stanno dentro
  il solido, e infatti solo il 31–41% delle loro celle è calpestabile. Sono
  marcatori di posizione per il codice, non piastrelle a pressione, e il loro
  `-g<numero>` è un identificativo che vive negli script, non nella mappa.

*Corollario: quando un oggetto dichiarato non si trova in nessuno dei file che
descrivono il mondo, non è un difetto di lettura — è la dichiarazione che quel
mondo si costruisce a runtime.*

## Chi vive in una cella: il campo che nessuno leggeva — `mapdat.actor()`

Il record di cella ha sei campi numerici prima delle due stringhe, e cinque
erano marcati `?` da cinque sessioni. Il quinto, a **+0x10**, è l'**attore**:
0 dove non c'è nessuno, e altrove un identificativo *globale al gioco*, non un
indice locale alla mappa.

Che sia globale lo dice la costanza: `4100` sono gli osservatori in tutte e 170
le griglie, e non per convenzione nostra ma perché il valore è **costante per
classe di cella in 175 casi su 195** (89,7%). Le venti eccezioni non sono
rumore: sono le celle la cui "classe" è in realtà il nome di una mappa di
destinazione (`D_7_1_2`, `Field_50`), che oggetti non sono.

La partizione della numerazione la dichiarano **tre file che non si
conoscono**:

| intervallo | chi | come si sa |
|---|---|---:|
| 4000–4999 | oggetti di mappa | costante per classe, 175/195 |
| 5002–5082 | nemici | l'album `EnemyView`, **45 su 46** |
| 5047+`NN` | NPC, con `c_npc_NN` | 226 celle su 240, **94,2%** |

I 4xxx più fitti si leggono direttamente, perché ognuno compare *solo* con le
sue classi: **4100** gli osservatori e i `Warp` (706 celle), **4101** le cose
solide — `Exit`, `destructionWall`, `WarpDoor`, `PitFall`, `BlackHole`,
`WoodDoor` (503) — e **4115** i grilletti di evento (168).

La regola degli NPC merita una riga a parte perché è un **oracolo in più su una
conclusione già presa**: che l'archetipo `n05` fosse `c_npc_05` la sessione 4
l'aveva dedotto dai nomi dei 237 script `npcevent_n<NN>...`, una fonte
completamente diversa. Qui venti valori consecutivi lo ripetono da soli —
5049→`c_npc_02`, 5050→`c_npc_03`, … 5072→`c_npc_25` — e le poche eccezioni
cadono **tutte** sui modelli alti (`c_npc_19`…`c_npc_26`), cioè esattamente
quelli che quella deduzione risolveva peggio. Il disaccordo indica il punto
debole della nostra rubrica, non del disco.

> **Sessione 12: il punto debole era `NP_NPC_19` ↔ `NP_NPC_26`, scambiati.** Lo
> dichiara `all.lua.eu`, e la frase qui sopra era giusta a indicare dove
> guardare. Vedi [`objects.md`](objects.md).

### Sessione 12: `4000 + NN` è il modello — `Grid.props`, `nodes.props()`

La banda 4xxx non è una numerazione opaca: **l'identificativo è 4000 più il
numero del modello `m_obj_NN`**, cioè il pezzo dentro
`map/map_model/map_object.ps3.dsb` che lo script del gimmick carica. Lo
confermano 51 celle su 51, su tre famiglie di script che non si conoscono —
i 34 `Signboard` (4041 / `m_obj_41`), i 12 `Stonemark` (4067 / `m_obj_67`), i
tre `Well` (4063 / `m_obj_63`) — e zero discordanti.

E la banda 3xxx è `3000 + NN` → `d_hmw_NN`, i «Dungeon配置物» del commento
degli autori: i 28 numeri che le celle usano sono esattamente i 28 che
`d_haichi.ps3.dsb` porta.

Da cui **7.695 celle-oggetto su 11.924 (64,5%) hanno un modello e si
disegnano**, e le altre non sono un buco: 3.843 delle 4.229 stanno in
`4100`…`4105`, che è il blocco della numerazione in cui i modelli non
esistono — cioè proprio i marcatori che il paragrafo precedente aveva misurato
assenti sia dalla geometria sia dalla collisione.

Restano non attribuiti gli 8.053 valori della banda 1xxx, che è l'equivalente
in campagna della 3xxx e non si chiude allo stesso modo perché là le famiglie
di modelli sono due (`f_hmw` e `f_ntr`) invece di una.

## I nemici stanno sul disco, cella per cella — `Grid.enemies`

Il TODO dava per acquisito che il disco dicesse solo *dove vivono* le specie —
l'album ha un campo `LivingId` — e che a metterle in mappa fosse il codice:
«resta al codice solo quanti ne mette per stanza e con che regola». Non è così.
La griglia piazza **10.196 nemici**, uno per cella, con la specie nel campo
+0x10.

E ogni cella nemico porta un **set di piazzamento**, `-sA` … `-sH`, che era una
stringa mai vista prima in nessun documento del progetto. Le lettere sono due
terne e non una sequenza — `A,B,C` e `F,G,H`, con `D` ed `E` che non esistono:

```
A 1807   B 1824   C 1804        F 1456   G 1654   H 1557        Z 94
```

**A, B, C sono tre disposizioni alternative della stessa popolazione.** Lo
dicono tre misure che sbagliano in modi diversi:

- le tre lettere portano **le stesse specie in 58 mappe su 59** (98,3%);
- sono equinumerose su tutto il disco (1807 / 1824 / 1804, scarto dell'1%), e
  nel Grass Temple lo sono specie per specie: 13 Soldier Bones, 10 Scorpion,
  15 Bat, 22 Red Slime, tre volte identiche;
- le loro celle coprono la **stessa area**: la scatola di una lettera è l'88%
  di quella delle tre, sopra l'80% in 51 mappe su 59, e sotto il 40% in
  nessuna. Quindi non sono squadre che presidiano zone diverse.

> **Una misura di troppo, tolta in sessione 10.** Qui c'era scritto anche «le
> loro celle non si sovrappongono mai», e sembrava la prova più forte delle
> tre. Non prova niente: `mapdat.cells` percorre `for i in range(w*h)`, cioè
> **una cella, un record**, e ogni record porta un attore e una lettera soli.
> Due lettere nella stessa cella non possono esistere *nel formato*. Era una
> tautologia travestita da misura. Le altre due reggono, e la lettura non
> cambia — ma il conto degli indizi sì.

**F, G, H sono le stesse tre per FROM Mode**, la difficoltà che si sblocca
finendo il gioco — e la lettera lo dice, `F` sta per FROM. Qui il parallelismo
si rompe, ed è giusto che si rompa: in `FIELD_16` sono 36/47/45 celle contro
19/19/19 e sette specie contro quattro, mentre nel Grass Temple sono meno
numerose ma più dure (Clay Golem e Ropus al posto di Red Slime e Bat).

### La conferma è venuta da fuori

Questa lettura è stata messa alla prova contro un [walkthrough di
GameFAQs](walkthrough/) — una fonte scritta per giocare, non per leggere byte,
che quindi sbaglia in un modo tutto suo. Quattro incontri, nessuno cercato:

- sui set alternativi: *«If the enemy positions are annoying, you can leave the
  room and come back and see if they respawn in a more favorable location.»*
  È `A`/`B`/`C` descritto dall'altra parte dello schermo.
- su FROM Mode: *«tough enemies appear all over the world map in hordes»*, e
  *«Enemy information does not apply to From mode, where all kinds of crazy
  enemies spawn all over the place — even enemies that are normally restricted
  to dungeons.»* Che è esattamente il profilo di `F`/`G`/`H`: più celle in
  campagna, e specie da sotterraneo dove non dovrebbero stare.
- su due nemici in particolare: *«Crystal Slimes and Blue Dragons spawn
  rarely... It may be that they can actually spawn anywhere.»* Nel nostro
  album **5075 Crystal Slime** e **5076 Blue Dragon** sono gli **unici due dei
  46 con `LivingId = -1`**, cioè senza habitat dichiarato. Il campo che li
  distingue nel dato è lo stesso che li distingue nel gioco.
- sui boss, uno per uno: Eelagon/Grass, Queen Bee/Forest, Giga Golem/Desert,
  Kraken/Aqua, Dragon/Flame, Dark Knight/Wind, Fuelle e Onyx nella torre. Il
  nostro album dà `DUNGEON_GRASS`, `DUNGEON_FOREST`, `DUNGEON_SANDS`,
  `DUNGEON_WATER`, `DUNGEON_FIRE`, `DUNGEON_EARO`, `DUNGEON_MAGIC` — **otto su
  otto**, e con essi cade l'ultimo dubbio su `EARO`, che è *aero*, il vento.

E il modo in cui i boss si distinguono nel dato, senza sapere che sono boss:
hanno **2 celle su 1 mappa e nessun `-s`**, contro le centinaia di celle su
decine di mappe dei nemici comuni. Un boss non ha bisogno di piazzamenti
alternativi perché sta in una stanza sola.

E la frase più specifica di quella fonte — *«even enemies that are normally
restricted to dungeons»* — si misura, perché l'album dà a ogni specie il suo
habitat e la griglia dice su che mappa sta:

```
A,B,C in campagna:  2.195 nemici,    12 di specie da sotterraneo =  0,5%   3 specie
F,G,H in campagna:  3.902 nemici, 1.356 di specie da sotterraneo = 34,8%  17 specie
```

Settanta volte tanto. Con uno stacco così non serve altro per dire cosa siano
le due terne, ed è la verifica che `walk.py` tiene ferma.

### E si aggiungono, non sostituiscono — misurato per assurdo

Era l'ultima cosa che il disco sembrava non dire, e la si dava per inferenza
aritmetica. Si misura, negando l'altra ipotesi:

```
mappe che dichiarano A,B,C e F,G,H     50
mappe che dichiarano i soli A,B,C       9      la più popolosa è d_5_1_2, 45 nemici
mappe che dichiarano i soli F,G,H       0
```

Se `F,G,H` **sostituissero** `A,B,C`, quelle nove mappe resterebbero senza un
solo nemico proprio nella difficoltà che il walkthrough descrive come *«tough
enemies appear all over the world map in hordes»*. Fra loro un piano di
sotterraneo con 45 nemici, che diventerebbe una passeggiata vuota.

Lo dice anche il verso opposto: `|F| < |A|` in 29 mappe su 59, e nel Grass
Temple si passerebbe da 60 nemici a 13. Sostituire renderebbe FROM Mode *più
vuoto*, che è il contrario di quello che è.

Quindi **si aggiungono**, e non è più un'inferenza.

### Metterli nel mondo — `Walk.populate_enemies()`, `view.py play --spawn`

Il disegnatore non ha avuto bisogno di una riga nuova: un'entità con modello
`c_enm_01` cerca il nodo `c_enm_01_01`, che è esattamente ciò che l'album
dichiara in `NodeStrings`. L'unica traduzione è togliere da quel nome la posa
— l'album nomina un **fotogramma**, nel mondo serve la radice — ed è la
conferma, da un terzo file, del «i figli di un nodo sono pose intere» di
sessione 4. I nove boss hanno un file per uno e vanno solo qualificati con la
cartella.

```
python tools/view.py play d_1_1_1 --cell 39,18             due Scorpion, un Soldier Bones
python tools/view.py play d_1_1_1 --cell 39,18 --spawn C   gli stessi, in altri posti
python tools/view.py play field_16 --spawn F               la campagna in FROM Mode
python tools/view.py play <mappa> --spawn -                nessun nemico
```

Il secondo comando è la prova visiva dei tre piazzamenti: stessa stanza, stesso
giocatore, stesse tre specie, posizioni completamente diverse.

Il nome dell'entità è costruito dalla cella (`@enemy_39_18`), perché il dato
dichiara la **specie** e non l'individuo: nessuno script nomina mai un nemico,
e dargli un nome finto che somigli a quelli veri inviterebbe a cercarlo negli
script.

E una validazione che è venuta gratis: **il 96% dei nemici ha pavimento
sotto**, e a dirlo è il `.DPK`, che è un altro file e non sa niente di questa
griglia. Il 4% che non ce l'ha si posa a quota zero invece di sparire, e il
perché resta ignoto — l'ipotesi ovvia, «sono i volanti», si è potuta misurare
ed è **falsa** (vedi sotto).

## Come si animano, e i dodici nemici scritti in Lua

Il gioco implementa i nemici in C++, ma il disco ne porta **dodici scritti per
esteso**: sono gli attori del minigioco Block Defence, che riusa i modelli del
gioco vero — e li riusa per numero, non per copia. `MGBee` carica
`EN_ENEMY_06_04_a`, che è esattamente il `NodeStrings` che l'album dà a
`Killer Bee`.

L'aggancio si fa sul numero di modello e si verifica sui **nomi**, che nessuno
dei due file prende dall'altro: `MGSkelton` cade su *Soldier Bones*, `MGWood`
su *Evil Tree*, `MGHagureSlime` su *Crystal Slime*, `MGGoblinRed` su *Goble*.
**Dodici su dodici.**

Da lì si leggono tre cose che altrimenti andavano inventate:

- **il periodo del fotogramma**, `local StepWait`, che vale `0.3` in tutti e
  dodici. Il nostro valeva 0,25 e non veniva da nessun dato: usciva da un
  `int(walk * 4) % 2` scritto per avere due passi al secondo;
- **le pose del ciclo, che non sono le stesse per tutti.** `02_a`/`02_b` è il
  caso comune ma non la regola: il coniglio alterna `01` e `03`, il fantasma
  `01` e `06`, l'ape `04_a` e `04_b`, l'ombra riposa su `06`. È un difetto
  nostro che questo file ha scoperto — **12 modelli `c_enm` su 37** non hanno
  affatto `02_a`, quattro camminano con `04` e otto non hanno nessun paio,
  quindi un terzo dei nemici restava fermo perché cercavamo una posa
  inesistente;
- **chi vola**: `Type` vale `0:陸` o `1:空`, e sono Ghost, Killer Bee e Shadow.

E una regola che vale su **tutti e 22** gli attori del minigioco, senza
eccezioni: *se il modello ha due pose appaiate `_a`/`_b`, il ciclo lo fa il
motore; altrimenti l'attore le alterna a mano con `SetNode`.* Che è la
controprova, da un file scritto per un minigioco, del «`_a` e `_b` sono i due
passi» dedotto in sessione 4 dalla sola geometria.

Le due fonti si completano bene: dove il minigioco tace, il ciclo lo dichiara
il modello stesso — e per *Cloudon*, che il minigioco non ha, dice `04_a`/`04_b`,
la stessa forma dell'ape.

Quello che **non** si legge è come si spostino nel mondo: nel minigioco
camminano verso la torre con un `BlockDefenceMove()` nativo, che di quel
minigioco è proprio la regola. Il pattugliamento resta non dichiarato, ed è
lasciato tale invece che inventato.

### L'ipotesi del volo, misurata e caduta

Avere `Type` per dodici specie permette di mettere alla prova la spiegazione
naturale delle celle senza pavimento. Non regge:

```
terrestri: 1.499 celle,  60 senza pavimento = 4,0%
volanti:     177 celle,   4 senza pavimento = 2,3%
```

Se mai il verso è l'opposto, e i due numeri sono troppo vicini per dire
qualcosa. Specie per specie è ancora più chiaro: *Killer Bee*, che vola, sta
sul pavimento nel **100%** dei casi, mentre a mancarlo di più sono *Clay
Golem* (17%) e *Black Knight* (10%), che camminano.

### Il posto giusto in cui dividere la domanda è la campagna

Cercata la causa nella specie, non c'era. È nel **posto**:

```
in campagna:    0 su 6.097 nemici senza pavimento =  0,0%
nei sotterranei:  546 su 4.099                   = 13,3%
```

Zero su seimila. In campagna il disco mette ogni singolo nemico su una cella
calpestabile, e non è un caso fortunato: è la prova che il piazzamento *sa*
dov'è il terreno. Il fenomeno è tutto e solo dei sotterranei — e la stessa cosa
fanno gli oggetti di mappa, che nei sotterranei stanno senza pavimento nel 32%
dei casi e in campagna nello 0,2%.

**E non è uno scarto di una cella fra la griglia e la collisione**, che era
l'ipotesi successiva e la più preoccupante, perché sarebbe stata colpa nostra.
Il segnale che la suggeriva è forte: il pavimento non sta **mai** a destra né
in basso, e quando il vicino con pavimento è uno solo sta in alto a sinistra
44 volte su 44. Ma spostare *tutti* i nemici di una cella non ripara niente:

```
dove il disco li mette      86,7% su celle calpestabili
spostati di (-1,-1)         87,6%          il migliore dei 24 spostamenti
spostati di (+1,+1)         69,5%
```

Nove decimi di punto è rumore; uno scarto vero porterebbe al 99%. E in campagna
non c'è margine per migliorare, perché si è già al 100%.

Quel che resta è una regola stretta: **nessuno sborda di più di una cella**.
Tutte e 546 le celle senza pavimento ne hanno da uno a tre vicini che ce l'hanno
— mai zero, mai più di tre — e in 497 casi su 546 quei vicini stanno tutti alla
stessa quota. Il piazzamento è disegnato sul rettangolo della stanza e trabocca
di una cella dentro il muro; in campagna non c'è muro in cui traboccare.

Da cui la conseguenza pratica, che prima era un `else 0.0`: un nemico senza
pavimento si posa alla quota di quello **accanto** (`Columns.ground_near`),
non a zero.

### Dove si è — `mapdat.locations()`, `Atlas.where()`

`MapParameter.lua.eu` non era mai stato aperto in otto sessioni, e ci si è
arrivati per una ragione che non c'entrava: il TODO diceva di cercarci il
pattugliamento prima di inventarlo. Il pattugliamento non c'è — e non c'è
nemmeno altrove, perché l'API Lua ha `PlayEnemy`, `PauseEnemy` e
`visibleEnemy`, cioè congelare e mostrare, mai muovere. Ma il file dichiara
**211 mappe** con il nome del posto in inglese e il brano:

```lua
Identifier=map_manager.MS_FIELD_1, Location="Mt. Sabre",
Bgm=soundList.SoundID.BGM_field05, Volume=1.0
```

L'identificativo si aggancia al nome del file senza artifici — `MS_DUNGEON_1_1_1`
è `d_1_1_1` — e copre **168 delle nostre 170 griglie**; le due che restano sono
`field_99` e `field_test`, cioè mappe di prova. Le località distinte sono 55 su
168 mappe, ed è proprio questo che rende il nome un'informazione: attraversare
`field_6` e `field_7` è restare a "Klovis".

Un nome che fa ridere e conferma che il gioco è pieno di scherzi:
`field_3` è **"Nialliv Valley"**, cioè *Villain* al contrario.

E arriva una conferma a costo zero su una cosa che ci è costata tre sessioni:
`d_1_1_1` si chiama **"Grass Temple"** e `d_6_1_3` **"Wind Temple"**. Che
`DUNGEON_EARO` fosse *aero*, il vento, era stato dedotto da `Item.lua.eu`,
confermato dal walkthrough via Dark Knight, e ora è scritto in inglese in un
quarto file.

### `LivingId` è la famiglia, non la casa

Avere insieme il nome del tempio e il piazzamento vero permette di mettere alla
prova una lettura che i documenti davano per buona — «quale nemico appartiene a
quale sotterraneo si sa». Il conto:

```
nemici piazzati nei templi: 1.988
il cui LivingId nomina il tempio in cui stanno: 936 = 47,1%
```

Con sette habitat il caso darebbe il 14%, quindi la correlazione è forte e
reale; ma il 47% non è una regola, e il Flame Temple è pieno di
`DUNGEON_WATER`. `LivingId` classifica il nemico, non lo colloca — e finché il
piazzamento non si sapeva leggere, era il miglior surrogato disponibile.

**La Dark Tower non ha un habitat proprio: li attraversa tutti**, e in un
ordine che non è casuale. L'habitat prevalente piano per piano fa

```
d_7_1_1 GRASS   d_7_1_2 GRASS   d_7_1_3 SANDS
d_7_1_4 WATER   d_7_1_5 WATER   d_7_1_6 EARO
```

cioè 1, 1, 3, 4, 4, 6 nell'ordine in cui il gioco fa visitare i templi: una
successione **non decrescente**. La torre finale ripercorre il viaggio.

### Due valori che l'album non dichiara

Delle 37 specie piazzate, **35 si disegnano**. Le due che no sono i due
identificativi che l'album non elenca, e sono diversi fra loro:

- **5024**, 168 celle, con i set `A`…`H` come un nemico qualunque — ma
  l'album salta esattamente quel numero (…5023, 5025…). E le sue celle stanno
  in **file continue**, `(51,65) (52,65) (53,65)…` con le lettere che ciclano,
  che non è come stanno gli altri;
- **5080**, 94 celle, l'unico con `-sZ`, e la sua classe è un **numero** (`0`,
  `1`, `4`). Le posizioni cadono su una griglia regolare.

Nessuna delle due è un nemico letto male: sono due cose diverse che condividono
l'intervallo, e vanno guardate a parte.

### 5024 è il masso che cade

L'album non lo dichiara ma **la sua stessa numerazione lo predice**. Nel tratto
5018–5026 lo scarto fra identificativo e numero di modello è costante:

```
5018 → c_enm_02   5021 → c_enm_05   5023 → c_enm_07   5025 → c_enm_09
5019 → c_enm_03   5022 → c_enm_06   [5024 manca]      5026 → c_enm_10
5020 → c_enm_04
```

Otto voci dichiarate, scarto 5016 in tutte e otto, e **5024 è l'unico buco del
tratto**. Il modello che ne segue, `c_enm_08`, esiste davvero fra i 39 `c_enm`
di `c_obj_all` — ed è una massa bitorzoluta color ocra, senza pose: un sasso.

Il piazzamento dice il resto, e sono tre cose che concordano:

- sta su **sei mappe sole, tutte d'altura** — Mt. Sabre, Sukaboko Highlands,
  Klovis (due schermate), Vatara Highlands (due). Nessun sotterraneo, nessuna
  pianura;
- sta **in righe** e in quota, da 5 a 28 caselle sopra lo zero;
- e il terreno davanti a lui **scende**, in una direzione sola:

```
verso il basso dello schermo:  scende 50%   piano 48%   sale  2%
verso l'alto:                  sale   22%   piano 76%   scende 2%
a sinistra e a destra:         scende 12%   piano ~82%
```

Alle spalle il terreno sale, davanti precipita. E il walkthrough, che di questo
non sa niente, descrive Sukaboko Highlands così: *«You will come to a screen
with Centauses and **falling rocks**.»*

Quindi 5024 è il masso che rotola giù dalla rupe: un attore nemico a tutti gli
effetti — ha i sei set di piazzamento, quindi ricompare come gli altri — che
l'album non elenca perché **non è un mostro da registrare**.

### 5080 è Togetoge, e la sua classe è il verso in cui si muove

La lettura precedente diceva «non è una creatura, è una figura, e la classe `4`
disegna i quattro vertici di una schermata». La geometria era giusta e la
conclusione no: 5080 **è** un attore, e per saperlo bastava aprire il file che
lo scrive. Sta in `all.lua.eu`, cartella `../lua/Object/`, e si chiama
`69Togetoge.lua` — トゲトゲ, *«spuntoni»*. Il commento di intestazione dichiara
la tabella che stavamo cercando:

```
0 : 縦移動                  verticale
1 : 横移動                  orizzontale
2 : 縦移動（突撃タイプ）      verticale, a carica
3 : 横移動（突撃タイプ）      orizzontale, a carica
```

e `Togetoge4Update` chiama `TogetogeDashUpdate(Object,2)`, cioè 縦横: sta fermo
finché il giocatore non gli si allinea, poi carica — su **tutti e due** gli
assi. Le classi che le griglie usano sono `0`, `1` e `4`.

**La geometria diventa la controprova**, e ha la forma giusta per esserlo,
perché è una regola che il piazzamento non può violare senza rompere il gioco:
due spuntoni che vanno su e giù non possono condividere una colonna, due che
vanno di lato non possono condividere una riga — al primo passo si
scontrerebbero. Chi invece resta fermo agli angoli le condivide per forza.

```
classe 0 (verticale)    tutte le colonne distinte    4 gruppi su  4
classe 1 (orizzontale)  tutte le righe distinte      5 gruppi su  5
classe 4 (a carica)     2 colonne e 2 righe         11 gruppi su 11
```

Undici gruppi di quattro, sempre a (1,1) (14,1) (1,10) (14,10) dentro lo
schermo 16×12: gli spuntoni a carica presidiano i vertici della stanza e la
attraversano quando ti ci metti in linea. Ecco perché le mappe dei boss ne
hanno **zero** e perché dentro ogni rettangolo c'è un osservatore e da 10 a 16
nemici: è una stanza-trappola, non una figura.

Il modello c'è, e chiude il conto: `Object:AddNode(package_manager.EN_ENEMY_39_01)`
è `c_enm_39_01`, cioè **l'ultimo** dei 39 `c_enm`. La regola dei nemici avrebbe
dato `c_enm_64` e quella degli NPC `c_npc_33`, e nessuno dei due esiste: era la
regola a non valere lì, non il modello a mancare.

E l'album ha ragione a non elencarlo. `69Togetoge` non chiama
`setBookRegistInfo`, cioè **non si registra nel bestiario** — e non lo fa
neanche `08RockFall.lua`, che carica `EN_ENEMY_08` ed è il masso di 5024. I 46
dell'album sono i 46 che si schedano; un masso e una trappola vivono nella
stessa numerazione perché sono `AT_ENEMY` a tutti gli effetti, ma non sono
mostri da registrare. Vedi `entity.LUA_ACTORS`.

*Il nome del file dà anche la conferma più economica che questo progetto abbia
avuto: la sessione 10 aveva dedotto che 5024 fosse il masso che cade dal buco
in un tratto a scarto costante e dal terreno che gli scende davanti. Il file si
chiama `08Rock**Fall**`.*

Il walkthrough, che di byte non sa niente, valida sia le stanze sia la regola
di ingaggio: gli *«spike puzzle»* che elenca cadono in Aqua Temple, Wind Temple,
Dark Tower e nella caverna a ovest della torre — e sono le sole mappe con
`5080` di classe 0 o 1. E dove spiega *«if you don't move at all upon entering a
room, you are not technically "in" it yet, and thus traps won't activate»*, il
codice dice la stessa cosa in una riga: `if( not Object:IsPlayerArea() ) then
return; end`.

## Camminare fa scattare gli eventi — `Grid.triggers`

64 celle non nominano un oggetto ma un **evento**, e il TODO le dava per
irrisolte: «solo 3 nomi su 25 trovano il file; gli altri 22 non hanno uno
script che si chiami così».

A sbagliare era la ricerca, non il dato. Non sono file, sono **funzioni** — e
stanno in un file per elemento, in una cartella che si chiama come quello che
contiene: `gimmick_grass4` vive dentro `Event/gimmickevent/gimmick_grass.lua.eu`
insieme agli altri sei `gimmick_grass`. Cercandole come funzioni globali si
risolvono **25 su 25**, e la verifica gira da sola in `walk.py`.

Il contenuto conferma che sono grilletti di posizione: si apre con una guardia
`if Event:GetEventFlag(167)==1 then return end`, cioè una volta sola, poi
`LockPlayer`, la fata che compare e spiega l'interruttore, `UnlockPlayer`.
Sono già eseguibili dall'host della Fase 4 senza aggiungere un metodo.

Fra i 25, cinque stanno nello **stesso** file e sono le quattro direzioni più
il centro: `mainevent_herodream` `n`, `s`, `e`, `w` e `2`.

## Cosa fanno gli oggetti: il file che li parametrizza

`GameParamData/gimmickParam.lua.eu` — 174 righe, in chiaro, con i commenti
degli autori in giapponese — dichiara il comportamento di quindici gimmick, e i
nomi combaciano con le classi di celle: `WarpDoor` e `BlackHole` alla lettera,
`Hole` per il `PitFall`, `stone_monument` per gli `Stonemark`.

```
ShotArrowWall  offset, shot_size 0.4, reload_time 1.0, speed 18.0
WallSwitch     offset_x 1.0, offset_y 1.4, offset_z 1.0
TargetSwitch   collision_size 0.6, clamp_value 0.4   -- quando la freccia si conficca
WarpDoor       castle_open_time 1.5, house_open_time 0.5, dark_open_time 1.5
Hole           detection_range 0.5, fall_time 1.0, gravity 18.0, pop_count 1
QuickSand      detection_range 1.3, speed 4.5
BlackHole      damage 4, vacuum_range 6.4, first_wait_time 1.0
poison         damage 8, e sei numeri di colore
stone_monument "Magic might help...", "Parallax revealed a hint!"
```

Il walkthrough valida anche questi, e uno **parola per parola**: la lastra di
`stone_monument` è quella su cui si lancia Parallax — *«it can only be used
where there is a surface such as the big slate... Using the spell will reveal
the writing on the slate»* — e i nostri dodici `Stonemark00`…`Stonemark11`
stanno uno o due per tempio, nelle stesse stanze in cui la guida dice di
lanciarlo. Così pure `ShotArrowWall` (*«two contraptions on the north wall...
traps that will shoot arrows at you»*), `WallSwitch` (*«hitting the wall switch
with your Boomerang»*), `QuickSand`, e il `destructionWall` (*«the cracked wall
to the west... can be bombed»*).

Quello che questo file **non** contiene è la logica, che resta nel codice. Ma
la sua forma la conosciamo, perché il disco ne porta 34 esemplari scritti in
Lua: gli attori del minigioco Block Defence (`data/MiniGame/*.lua.eu`) hanno
tutti e quattro i callback del contratto d'attore del motore —

```lua
function MGBombRockInitialize(Object)   Object:SetType(actor_manager.AT_DESTRUCTION_WALL) ...
function MGBombRockUpdate(Object)
function MGBombRockCheckMove(Object, Type)       -> MR_BLOCK | MR_NONE
function MGBombRockCheckCollision(Object, Type)  -> se AT_BOMB: CreateEffect, ResetMapGridData, Destroy
```

— cioè il muro che la bomba apre, scritto per esteso, solo che nel minigioco
invece che nel mondo. `MR_BLOCK` e `MR_NONE` non compaiono da nessun'altra
parte del disco: gli oggetti di mappa veri li implementa il C++, e questi sono
il calco che dice con quali funzioni.

## Cosa dichiarano davvero: la stanza — `Grid.rooms`, `room_of()`

Restava da capire *cosa dicono* quelle celle. La forma della stringa le divide
in due famiglie, e la divisione è netta:

| | celle | forma |
|---|---:|---|
| `SwitchObserver`, `EnemyObserver` | 80, 65 | `-gN;` da solo |
| `destructionWall`, `WarpDoor` | 46, 29 | `-gN;-oN;` con **i due numeri uguali** |
| `PitFall`, `BlackHole` | 21, 7 | `-gN;-oM;` con **i due numeri diversi** |

Dove i due numeri sono uguali, la coppia si ritrova su una cella di **un'altra
mappa**: `WarpDoor` 29 su 29, `destructionWall` 43 su 46. Quelli sono passaggi,
ed è il motivo per cui `walkabout` li attraversava già.

### L'ipotesi del TODO era sbagliata

«Il `PitFall` ha una coppia `-g`/`-o` come i passaggi, quindi cadere è
probabilmente *arrivare* da qualche parte». Provata, non regge: la coppia di un
`PitFall` si ritrova altrove **2 volte su 21**, e quella di un `BlackHole` 3 su
7. Nemmeno cercando il solo `-g` o il solo `-o`, che ricadono sì ma su venti
celle per volta — cioè non risolvono, collezionano.

### Il numero è `(piano)(stanza)`, e lo dicono altri due file

I sette buchi neri della torre oscura stanno uno per piano e portano
`-g12`, `-g212`, `-g37`, `-g410`, `-g514`, `-g63`, `-g712`: prima cifra 1, 2, 3,
4, 5, 6, 7 in ordine di piano. Sembrava che nominassero i sette templi — la
torre che si apre sui sei sotterranei sarebbe stata una bella lettura, ed è
falsa: nessuna di quelle coppie esiste nel sotterraneo che la cifra nomina, 0
su 7. La cifra è **il piano su cui la cella si trova**.

Il che si misura, e su due oracoli esterni:

```
2.484 varchi numerici su 2.490:  la prima cifra e' il piano che dice
                                 il **nome del file** (99,8%)
  404 stanze su 413:             le stanze cosi' ricavate sono quelle che
                                 i descrittori `dungeonMapNN_MM` disegnano
                                 come `room_on_NN` (21 piani su 21)
```

Quattordici piani su ventuno combaciano **esattamente**. E i due oracoli non si
conoscono: uno è una stringa nel nome di un file, l'altro è uno schermo di
interfaccia scritto per disegnare una minimappa.

Quindi il `-g` non è un indirizzo: è `(piano)(stanza)`, locale alla mappa, e le
celle degli oggetti dichiarano **a quale stanza appartengono** — non cosa fanno.
Il comportamento sta davvero nel codice; ma le stanze adesso sono una struttura
vera, ed è esattamente quella che la mappa del sotterraneo colora una casella
per volta (`view.py play <mappa> --map`, o `M` mentre si cammina).

### Dove una stanza cominci e finisca il disco non lo dice

Sapere *in quale* stanza si è renderebbe la mappa una minimappa vera, e non si
può: le celle marcate sono radi segnaposto, non regioni. Tre strade provate,
tre risultati:

- **la stanza è uno schermo**: la scatola delle celle marcate sta in 16×12 nel
  95,4% dei casi, ma solo 305 stanze su 416 cadono in un blocco allineato. Le
  stanze sono grandi *circa* uno schermo, e non sono lo schermo;
- **il tag di regione della cella è la stanza**: no. In `d_1_1_1` tutte e 23 le
  stanze portano lo stesso tag `2001` — il tag è il **sotterraneo**;
- **il marcatore più vicino**: le scatole delle stanze non si sovrappongono
  (1,3% di coppie), ma coprono il 12% della mappa, e sulle celle che stanno
  dentro una scatola sola il marcatore più vicino azzecca il **75,7%**. Per gli
  standard di questo progetto è rumore con una preferenza, non una regola.

Il che, messo insieme, dice una cosa coerente: gli osservatori sono i
**grilletti d'ingresso** che il motore usa per registrare in quale stanza sei —
ed è per questo che sono radi, e che due su tre stanno dentro il solido invece
che sul pavimento. La regione non serve a nessuno tranne a noi.

## Parlare

Premendo spazio si guarda chi c'è nella cella davanti e si fa partire il suo
`npcevent_*` sull'host Lua, verbatim. L'host è lo stesso di sempre; l'unica
cosa nuova è `Host.begin()`, che ricomincia una conversazione da capo senza
ricaricare il mondo — pagine, attese e coroutine ripartono pulite, altrimenti
la seconda battuta arriverebbe già finita.

Il mondo è **lo stesso oggetto** per l'host e per chi cammina: se il registro
fosse dell'uno o dell'altro, un evento sposterebbe un personaggio diverso da
quello che si vede. Mentre l'evento parla, la camera è sua (`SetCameraAtBody`);
appena finisce si torna all'inquadratura di gioco, non a quella dell'ultima
battuta.

## Il soffitto

I sotterranei di questo gioco hanno il soffitto: dall'alto sono una lastra, e
chi ci cammina dentro non lo vede nessuno. Il frammento scarta tutto quello che
sta sopra una quota, e quella quota segue il giocatore (`--roof`, di norma 2,4
unità sopra i piedi; `K` la toglie, `--no-roof` la spegne).

Non è un effetto: senza, `play` in un sotterraneo mostra un pavimento visto da
sotto.

## La misura

Un fotogramma con un personaggio in mezzo a una mappa è un aneddoto.
`view.py walkabout` è il numero: per ogni mappa carica la collisione, parte dal
punto d'ingresso che il dato dichiara e guarda dove si arriva a piedi.

```
167 mappe percorse in 58s
in tutto     167 mappe, ingresso calpestabile in 167
             celle raggiunte a piedi    242.818/363.009 = 67%   (acqua 40.964 a parte)
             abitanti raggiunti             256/264     = 97%
             passaggi raggiunti             369/512    , con l'arrivo in piedi 365
sotterranei  127 mappe   celle 68%   abitanti  95%   passaggi 179/301
campagna      40 mappe   celle 66%   abitanti  99%   passaggi 186/211
```

Una mappa si percorre **da tutte le sue porte**, non da una. Non è una
comodità: `field_14` ha sei celle `Exit`, e la prima dà su un ripiano di 16
celle sotto una rupe mentre le altre cinque danno sulle 3.213 che sono la
mappa. Prenderne una sola misura la porta invece della mappa.

Come si leggono:

- **l'ingresso è calpestabile in 167 mappe su 167.** Il punto in cui il gioco fa
  comparire il giocatore è, in tutte le mappe del disco, un posto in cui si sta
  in piedi. Non era ovvio: dipende dalla composizione degli schermi, dalla
  scala, dall'origine della griglia e dalla lettura delle superfici, tutte
  insieme.
- **365 passaggi su 369 portano in una cella in cui si sta in piedi**, ed è il
  99%. I quattro che restano non sono un arrivo sbagliato: sono passaggi la cui
  mappa di destinazione non esiste sul disco.
- **le celle al 67% non sono un fallimento del 33%.** Il denominatore conta ogni
  cella su cui *si starebbe* in piedi, tetti delle case e cime dei muri
  compresi, che infatti non si raggiungono e non si devono raggiungere. L'acqua
  invece è tolta e contata a parte, perché non è né terra né tetto.
- **gli abitanti al 97% sono la misura vera**, perché un abitante
  irraggiungibile è un pezzo di gioco che non si vede, mentre una cella
  irraggiungibile è spesso un tetto.

### Da dove viene questo numero

Vale la pena tenerne traccia, perché la strada per arrivarci ha corretto due
volte una conclusione già scritta:

| | celle | abitanti | passaggi | in piedi |
|---|---:|---:|---:|---:|
| geometria di rendering, gradino 0,6 | 18% | 65% | 194 | |
| collisione vera (`.DPK`), gradino 0,6 | 25% | 78% | 202 | |
| collisione vera, gradino **una casella** | 63% | 96% | 303 | 281 |
| colonna misurata, fondale sepolto, tutte le porte | **67%** | **97%** | **369** | **365** |

E il divario fra sotterranei e campagna — 26% contro 13% di celle, 76% contro
51% di abitanti — **è sparito**: ora sono 63% e 63%, e la campagna sta meglio
dei sotterranei sugli abitanti (99% contro 94%).

Questo smentisce quello che era scritto qui ieri, cioè che la campagna avesse
due cause distinte e che la prima fosse geometria mancante. La causa era una
sola, ed era la soglia inventata. La copertura al 90,7% di `view.py layout`
resta una questione aperta, ma **non** era questa.

## Cosa manca

- **Il comportamento degli oggetti di mappa.** Dove stanno e cosa sono si sa
  ora (vedi sopra); cosa *fanno* — la bomba che apre il muro, l'interruttore,
  la caduta nella trappola — è logica di gioco, e viene dopo.
- **I nemici.** `c_enm_NN` esiste e si disegna, ma nessuna cella li dichiara
  come dichiara gli NPC: li crea il codice, sui suoi `EnemyObserver`.
- **Disegnare l'acqua.** Dove sta ora si sa — il tag 119, e la maschera dalla
  collisione — ma la superficie la disegna il motore e non il `.pac`, quindi è
  lavoro di renderer. È la ragione per cui un fotogramma dell'overworld ha
  grandi zone nere.
- **Le mappe che restano poco percorribili.** `d_60_2` (3%), `d_60_14` (8%),
  `d_80_1` (11%): poche e circoscritte, e adesso che l'ingresso non è più
  sospetto vale la pena guardarle una per una.
- **La spada e lo scudo**, che nel modello sono nodi a parte.
