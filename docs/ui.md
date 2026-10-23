# Le schermate di sistema — `tools/ui.py`

**Stato: si navigano.** 136 schermate dichiarate sul disco, caricate con la VM
Lua ed eseguite: la scena al suo posto, le scritte dove il descrittore le mette,
il cursore dove dice lui — e i tasti che lo muovono, perché anche quelli sono
dichiarati.

```
python tools/ui.py list                   le schermate dichiarate
python tools/ui.py show ClearSave out.png una schermata composta
python tools/ui.py menus Pause            le voci, e cosa spiegano
python tools/ui.py keys EnemyAlbum        la barra: quali azioni, con che tasto
python tools/ui.py drive Pause giu,giu,croce out.png    navigata
python tools/ui.py floors 5               i piani di un sotterraneo
python tools/ui.py clips Option           la tabella delle clip, per indice
python tools/ui.py anim ClearSave a.png   i fotogrammi dell'apertura
python tools/ui.py map 1 1 out.png        la mappa di un sotterraneo
python tools/ui.py check                  le verifiche interne (29 proprietà)
```

L'interfaccia di questo gioco è **dato, non codice**: 109 file Lua sotto `data/`
dichiarano salvataggio, opzioni, pausa, game over, negozio, album dei nemici e
le venti mappe dei sotterranei. Si porta senza riscriverla, esattamente come gli
script di evento.

```lua
ClearSave = {
    TexturePackageName = "UserInterface/Select/SelectA",
    ScenePackageName   = "UserInterface/Select/SelectA",
    Animation = { In={Start=0.0,Size=0.4}, Main={...}, Out={...}, Cursor={...} },
    Message = { Size=1, {X=640.0, Y=500.0, String="Ｏｋａｙ　ｔｏ　ｓａｖｅ？",
                         Align="Center"} },
    Select  = { Size=2,
                {CursorX=927.0, CursorY=525.0, X=961.0, Y=518.0, String="ＹＥＳ"},
                {CursorX=927.0, CursorY=557.0, X=961.0, Y=550.0, String="ＮＯ"} },
    Cancel  = { Enable=0, Index=1 },
};
```

Si caricano con `lupa` e non con un parser nostro, per la stessa ragione per cui
si carica così il font: **sono Lua**, e la VM li legge meglio di qualunque cosa
scritta da noi.

## Lo schermo virtuale è uno solo

Che le coordinate dei descrittori fossero in uno schermo 1280×720 era già noto —
`X=640` è il centro. Quello che permette di comporre è che **anche le scene 3D
ci vivono dentro**: la larghezza mediana delle 115 è 1280,0 esatti, e la
dissolvenza a piena pagina `Fade/Fade.ps3.dsb` — che per definizione copre lo
schermo e basta — misura `x [0, 1280]`, `y [-720, 0]` al decimale.

Da lì le due conversioni, che sono una lettura e non una taratura:

```
schermo_x = modello_x
schermo_y = −modello_y      la Y del modello cresce verso l'alto
z                           non è profondità: è il piano di sovrapposizione
                            (−90 la dissolvenza, −50 il fondo, 0 il fronte)
```

## Rettangoli, non triangoli

Dei **16.494 triangoli** delle 115 scene, 16.492 sono piatti in Z e **16.494 su
16.494** hanno due lati sugli assi. Cioè l'interfaccia è fatta di rettangoli
allineati, e disegnarla vuol dire ritagliare un pezzo di texture e incollarlo:
esatto al pixel, senza una pipeline 3D.

## Perché non bastava leggerli

I descrittori erano letti da tre sessioni e mai eseguiti, e provando si capisce
perché: **a riposo le schermate sono chiuse**.

Il nodo di ogni pezzo di `SelectA` ha **scala 0** su un asse — `(0,1,1)`,
`(1,0,1)` — mentre la mesh sotto è intera: `Confirm_02b` misura 149×99. E le
schermate a scorrimento hanno i pezzi parcheggiati fuori campo: il menu degli
oggetti arriva a `x=2193`, quasi il doppio dello schermo.

Ad aprirle è l'animazione, ed è la quarta cosa che il descrittore dichiara —
`Animation = {In, Main, Out, Cursor}`, quattro clip con inizio e durata. Il
`.dsb` non contiene curve: fra i suoi otto tipi di oggetto (`texture`,
`material`, `effect`, `light`, `camera`, `mesh`, `skin`, `node`) l'animazione
non c'è. Quindi il moto lo mette il motore, e la posa finale è la scala a 1 —
che è quello che fa `view.load(unfold=True)`.

*Corollario: un dato che sembra vuoto può essere solo chiuso. La geometria era
tutta lì; a nasconderla era uno zero in una scala.*

## `Start` non è un tempo, è un indice

Le clip si leggevano come `{Start, Size}` = inizio e durata su una linea del
tempo. Il conto dice altro: sulle 42 schermate che dichiarano `In`, `Start`
vale **0 tutte e 42 le volte**; `Main` vale 1 tutte e 38; `Out` vale 2 tutte e
42. Un tempo che non cambia mai non è un tempo — è **la posizione in una
tabella di clip**, e il nome della clip la determina. `Size` invece varia
(0,4 / 0,5 / 1,0) ed è la durata in secondi.

*I numeri sono cresciuti in sessione 9, quando le 17 schermate che
`descriptors()` scartava sono rientrate: la proprietà non si è indebolita, ha
retto su un quinto di casi in più.*

Le schermate grosse lo rendono evidente, perché lì gli indici arrivano
lontano e restano **densi e consecutivi**: `Option` va da 0 a 38 senza un buco.
E come sono distribuiti dice cosa indicizzano:

```
python tools/ui.py clips Option

[ 0] Display.WindowIn      [ 3] Display.MessageIn  [10..19] Volume.0 .. Volume.9
[ 1] Display.Window        [ 3] Message.MessageIn  [20] Sound.WindowIn
[ 2] Display.WindowOut     [ 3] Sound.MessageIn    [23] Message.WindowIn
```

I tre pannelli **condividono** gli indici 3–9 e hanno separati solo i propri
0–2 / 20–22 / 23–25: la zona dei messaggi, la barra dei tasti e il cursore sono
gli *stessi oggetti* riusati, e a cambiare è solo la finestra. Quindi l'indice
non identifica un momento, identifica **la cosa che si muove**.

I dieci indici 10–19 sono le dieci tacche del volume, e sono dichiarati in un
punto che si perde facilmente: `Volume` è un **array** e non un dizionario
(`Volume={{Start=10,Size=1.0},...}`). Un percorritore che scende solo nei
dizionari li salta e lascia un buco di dieci — che è esattamente quanti nodi
`Volume00…Volume09` ha la scena. Il buco era nostro, non del disco.

## Il moto: uno ce l'ha, l'altro no

Le due animazioni delle schermate sono due problemi diversi, e conviene non
tenerli insieme come un'unica voce «manca l'animazione».

**L'apertura ha tutti e due gli estremi sul disco.** Il pezzo è esportato con
la scala a zero e la mesh sotto è intera: da 0 a 1 c'è tutto, e la durata la
dichiara `Size`. Non c'è niente da inventare, e infatti `unfold` non è più un
interruttore ma un **fattore**:

```
python tools/ui.py anim ClearSave frame.png --frames 6

t=0.000s  aperta   0.0%      t=0.240s  aperta  60.0%
t=0.080s  aperta  20.0%      t=0.320s  aperta  80.0%
t=0.160s  aperta  40.0%      t=0.400s  aperta 100.0%
```

La finestra si apre come un televisore che si accende, ed è la scena a dirlo:
`Confirm_01` è fatto di tre pezzi, `a` (505×4) e `c` (505×7) con **scala X = 0**
e il corpo `b` (505×99) con **scala Y = 0**. Prima una riga orizzontale, poi il
corpo in verticale. L'asse che si apre è dichiarato da quale scala è nulla.

L'unica cosa non letta è la **curva**: qui si interpola lineare, perché è la
sola scelta che non aggiunge un numero inventato.

**Lo scorrimento ha un estremo solo.** Le schermate a scorrimento non sono
chiuse da una scala: sono *spostate*, e il disco porta solo il parcheggio.

```
selectmenu_eng    Window01  x [ -600,  -18]  y [ 48, 294]
                  Window03  x [ 1300, 1619]  y [ 48, 294]
                  Message   x [ 1285, 2193]  y [555, 628]
```

Il conto su tutte le scene: **38 pezzi parcheggiati fuori campo, 33 fuori solo
in X**, cioè il moto è orizzontale — e la Y è già quella definitiva. Lo
conferma il descrittore, che colloca «EQUIPMENT» a y=53 dentro `Window01`
(48–294), «ITEMS» a y=308 dentro `Window02` (303–550) e i tasti a y=635 dentro
la barra (632–666).

Ma **dove arrivino in X non sta da nessuna parte**: non nella scena, che ha
solo il parcheggio, e non nel descrittore, che colloca il contenuto e non il
contenitore. Interpolare fra parcheggio e posto non si può fare perché il posto
manca. È questa — e solo questa — la parte che vale la pena chiedere
all'EBOOT, e riguarda **5 schermate e 15 pezzi**: `Item`, `Orb`, `Option`,
`NameEntry`, `GameOver`.

## Il riquadro di dialogo, e il file che non era quello

Il riquadro del dialogo era l'ultimo pezzo disegnato da noi, e il TODO lo dava
in `data/Balloon`. Non è lì. `balloon_eng.ps3.dsb` sono tre quadri di
**1,6 × 0,6 unità di mondo** — 1,6 è la casella, cioè l'altezza di un
personaggio — con tre materiali `CHECK`, `TALK`, `OPEN`, e le texture sono tre
fumetti con il tasto ✕ e la codina in giù. È il cartello che galleggia sopra la
testa, non la finestra del dialogo.

Il riquadro sta in **`UserInterface/Message`**, ed è fatto come tutte le
finestre di questo gioco: `Message_a/b/c` (505 × 138) e `MessageBig_a/b/c`
(686 × 154), `a` e `c` righe sottili con la scala X a zero, il corpo `b` con la
scala Y a zero. Con loro c'è `Advance_Cursor`, la freccia del «premi per
continuare».

Il descrittore mette tutto il resto e non lascia niente da inventare:

```lua
Line=3,  X=421.0, Y=485.0, Space=8.0,   -- riquadro piccolo
         LargeX=325.0, LargeY=465.0, LargeSpace=4.0,
Speed={0.25, 0.225, ... 0.025},          -- dieci velocità di battitura
Color={White={...}, Blue={...}},
```

E i numeri si incastrano, il che è la verifica: il font a scala 1 misura **32
px** per riga, quindi `485 + 3×32 + 2×8 = 597` e il corpo del riquadro finisce a
**598**. Un pixel di margine — da cui si legge anche che `Space` è l'interlinea
**fra** le righe e non su ognuna: sommandola pure all'ultima si sfora di sette
pixel. E che il font a scala 1 sia già la misura giusta conferma per una via in
più che lo schermo virtuale è uno solo.

`ui.widget()` ritaglia un singolo pezzo da una scena — serve perché la misura
grande *contiene* la piccola, quindi non si separano ritagliando un rettangolo:
si filtra per nome di nodo.

## La mappa del sotterraneo, e la tinta che il compositore ignorava

Le venti mappe dei sotterranei erano nell'elenco di «cosa manca» come
*schermate con contenuto dinamico, che hanno bisogno di dati di partita che
ancora non esistono*. I dati adesso ci sono: la griglia dichiara a quale
**stanza** appartiene ogni cella (vedi [`walk.md`](walk.md)), e la scena ha un
pezzo per stanza e per stato.

```
python tools/ui.py map 1 1 out.png --seen 1,2,3,4,5,6 --here 4
```

Il descrittore chiude il cerchio da solo, perché le sue porte **nominano i
campi** che nella griglia sono cifre mute:

```lua
-- 普通扉[Door_marker_01]：対応する部屋[room_on_02⇔room_on_06]
room1=GameDataMapFlags.DUNGEON1_1_2,  room2=GameDataMapFlags.DUNGEON1_1_6,
groupId=12,  objectId=201,
```

`groupId` e `objectId` sono il `-g` e il `-o` della cella, e `groupId=12` sta
per il piano 1, stanza 2 — cioè lo stesso `(piano)(stanza)` misurato sulla
griglia, detto per esteso da un terzo file.

### I tre stati sono un colore, non tre disegni

Comporre la mappa non cambiava niente: le stanze uscivano identiche in tutti e
tre gli stati. Non era il filtro — `room_on_02`, `room_off_02` e
`room_still_02` sono la **stessa mesh**, nella stessa posizione, con le
**stesse UV**, sulla stessa texture. A distinguerli è il `diffuse` del
materiale:

| stato | diffuse |
|---|---:|
| `room_on` | 1,0 |
| `room_off` | 0,5 |
| `room_still` | 0,0 |

Una scala, e la scala li ordina: il più scuro è la stanza che non si è ancora
vista, perché 0,0 su una mappa vuol dire una stanza che non si vede. I nomi non
lo dicono e questa corrispondenza resta nostra, ma non è un'ipotesi al buio.

*Il difetto però era generale, non della mappa: il compositore guardava la sola
texture e buttava via il colore del materiale, su **ogni** schermata. Ora lo
moltiplica — l'alfa no, perché a spegnere un pezzo qui è il colore.*

E il difetto era grosso, perché la tinta è il modo in cui questa interfaccia
dichiara gli stati:

```
115 scene di interfaccia, 49 con almeno un nodo tinto, 1.869 nodi in tutto
   891 a 0,0     spenti del tutto
   864 a 0,5     a metà
    70 a 0,13, 42 a 0,59, e un solo nodo colorato davvero (0,0 0,24 0,5)
```

Ottocentonovantuno pezzi che devono essere neri venivano disegnati a piena
luce. È la stessa forma della scoperta di sessione 6 — *un dato che sembra
vuoto può essere solo chiuso* — ma per l'altro verso: qui un pezzo che sembra
acceso può essere solo **spento**, e a spegnerlo non è la geometria né l'alfa,
è un numero nel materiale.

## L'input era dichiarato quasi tutto

Era in «cosa manca» come *«`Cancel = {Enable, Index}` dice quale voce sceglie
il tasto di annullamento, quindi anche il comportamento è dichiarato: manca chi
lo esegue»*. Cercando chi lo esegue si è visto che il descrittore dichiara
molto più di quella riga, e che l'unica cosa da scegliere è una.

### Una voce è una voce se il cursore ci può stare

Il blocco `Select` erano diciannove sì/no, e sembrava tutto. Il criterio giusto
non è il **nome** del blocco ma `CursorX`/`CursorY`: cercando così si trovano
**23 blocchi per 60 voci**, e i nomi sono tre.

```
python tools/ui.py menus Title

Title.ClearMenu: 6 voci, annullare non e ammesso
   1. NEW GAME      cursore (534,377)   Start a new adventure.
   2. NEW GAME+     cursore (534,407)   Begin from your cleared data.
   ...
Title.Menu: 5 voci
   1. NEW GAME      cursore (534,407)   Start a new adventure.
```

`Menu` è il menu del titolo e quello di pausa — *RESUME, SAVE, LOAD, OPTIONS,
SNAPSHOT, ALBUM, BESTIARY, LOADING ART, TITLE* — e `ClearMenu` è il titolo **a
gioco finito**, con `NEW GAME+` in più. Le due liste condividono le posizioni
da 407 in giù: la voce nuova non si aggiunge in fondo, il menu **cresce verso
l'alto**.

Ogni voce porta anche la propria frase di spiegazione, ed è l'unico pezzo di
interfaccia che cambia al muoversi del cursore.

### L'asse non è una scelta, e nemmeno il passo

Le voci sono incolonnate in **23 blocchi su 23**, zero in riga: si sale e si
scende. Il cursore sta 34 px a sinistra della scritta e 7 in su, sempre gli
stessi, e fra due voci il passo è **32 px** — che è la riga di font con cui in
sessione 7 il riquadro di dialogo tornava a 597 contro un corpo che finisce a
598. Lo stesso numero, da un terzo posto.

### Annullare non vuol dire uscire

`Cancel = {Enable, Index}`, e **l'indice si conta da zero**. Lo dice il
contenuto: tutte e 19 le schermate hanno le stesse due voci `YES`/`NO` e tutte
e 19 dichiarano `Index=1`. Contando da uno, annullare vorrebbe dire acconsentire
in tutte e 19; contando da zero è `NO` in tutte e 19. È la stessa base di
`Start`, che vale 0 per la clip `In`.

Quindi il tasto ○ non chiude la finestra: **sceglie una voce precisa**. E dove
`Enable=0` non fa niente — sono `ClearSave`, `DeleteSaveDataSelect`,
`GameOverSaveSelect` e `GameOverResurrectSelect`, cioè le quattro schermate in
cui il gioco pretende una risposta invece di lasciar uscire.

```
python tools/ui.py drive Continue cerchio out.png
  cerchio  voce 2/2 'NO'  -> scelto 'NO'  (annullando)

python tools/ui.py drive ClearSave cerchio out.png
  cerchio  voce 1/2 'YES'          il tasto non fa niente
```

Due finestre identiche a vedersi, che si comportano in modo diverso perché il
disco lo dichiara.

### La barra dei tasti dichiara quali azioni ci sono

In fondo a ogni schermata c'è una striscia continua che alterna piastre e
icone: nell'album dei nemici i sette rettangoli vanno da 673 a 1176 senza un
buco. Le scritte stanno nel descrittore, le icone nella scena sotto un nodo
`KeyAssign`, e si accoppiano perché ogni scritta comincia **7-8 px dopo** la
fine di un'icona.

```
python tools/ui.py keys EnemyAlbum

  pageStrings     PAGE     x=  681   senza icona
  moveStrings     MOVE     x=  812   tasto grigio
  detailsStrings  INFO     x=  937   tasto croce
  canselStrings   CANCEL   x= 1054   tasto cerchio
```

A nominare il tasto è **il colore**, che su questo hardware è il tasto: la ✕ è
disegnata blu e la ○ rossa, sulle texture del disco. Il grigio invece non
separa niente — croce direzionale e dorsali `L1`/`R1` sono senza tinta — e
resta un nome solo.

`PAGE` non ha icona perché è la prima della striscia: a sfogliare sono le due
frecce ai lati della pagina, `Left_Cursor` e `Right_Cursor`, che nella scena
sono nodi per conto loro.

Dove la schermata **scorre** l'accoppiamento non si può fare, e non è un
difetto: la striscia è parcheggiata fuori campo con il resto della scena mentre
le scritte sono già al proprio posto. Sono le stesse 5 schermate di sempre.

### Il cursore non era nostro, e il suo posto misura il testo

Era l'ultimo pezzo che ci mettevamo noi — un triangolo disegnato a mano — e non
ce n'era bisogno: le scene lo portano, in due modi diversi.

- **Parcheggiato all'origine**, come tutto ciò che il descrittore colloca: un
  `Cursor_01` di 16–17 px per lato a `(0, 0)`. Così fanno 7 blocchi su 8, e va
  messo dove dice `CursorX`/`CursorY`.
- **Uno per riga, già collocato**: il menu di pausa ha nove marcatori alti 31
  px, alle posizioni che il descrittore dichiara voce per voce — 530 contro
  529, 86 contro 84. Lì il cursore non si sposta: se ne accende uno, e gli
  altri otto vanno spenti. È la stessa forma della mappa del sotterraneo, dove
  la scena porta tutti gli stati e il dato dice quale.

Ed è il cursore a dare l'oracolo su **come si dispone il testo**, che erano due
numeri tarati a occhio. La cella del font è 32×32, e il descrittore mette il
cursore 7 px più in giù della scritta: alto 16 px dentro una riga di 32, cade
esattamente in mezzo. Quindi `Y` è il **bordo alto** della riga e non il suo
centro, e la scala è **1** e non 1,4.

```
il cursore cade in mezzo alla riga a meno di 6 px, su 30 voci
```

Combacia con l'altro conto, quello del riquadro di dialogo di sessione 7:
`485 + 3×32 + 2×8 = 597` contro un corpo che finisce a 598. La stessa altezza di
riga, presa per due strade che non si conoscono.

### Il seguito di una schermata è dichiarato due volte su 136

Cercando il legame fra una schermata e la successiva — che sembrava non
esistere — si trova, ma raro: due schermate lo scrivono, per tre legami, e
sempre nella stessa forma, un campo in fondo alla tabella con la chiave uguale
al valore.

```lua
Pause = { ... , PauseTitleSelect = "PauseTitleSelect" };
```

Sono `Pause` che apre `PauseTitleSelect`, e `GameOver` che apre
`GameOverSaveSelect` e `GameOverResurrectSelect`: tutte e tre la **finestra di
conferma** di una scelta che non si torna indietro. Dove il seguito è una
domanda il disco lo dice; dove è un'altra schermata no.

### Una sola cosa è nostra

Che dall'ultima voce si torni alla prima. Con nove voci in pausa serve, ma il
disco non lo dichiara, quindi è una scelta e si spegne: `Screen(..., wrap=False)`.

## La pagina è il piano, con il segno

`setting = {pageMin, pageMax}` sta sui sette `dungeonMapNN_01` e dichiara
l'intervallo di ciò che si sfoglia. Sulle mappe dei sotterranei quel numero è
il **piano**, e il segno dice se si è sopra o sotto: `B1` è −1, `1F` è 0, `2F`
è +1.

Due conti indipendenti la mettono alla prova:

```
pageMax - pageMin + 1  =  numero di descrittori di piano       7 sotterranei su 7
le etichette stampate (B2, 5F) cadono dentro il proprio intervallo   19 su 19
```

I due che restano fuori sono i sotterranei a **un piano solo**, che dichiarano
`0..0` e `1..1` pur essendo tutti e due `B1`: dove non c'è niente da sfogliare
il campo non è mantenuto.

E la successione dei file non è quella dei piani — il sotterraneo 5 li tiene
nell'ordine `1F`, `2F`, `B1` — quindi il piano di un descrittore va letto, non
contato. Il primo però **non dichiara il proprio**: elenca le etichette di
tutti i piani, perché disegna il selettore a lato. Il suo si ricava per
differenza, ed è quello che gli altri non hanno preso.

```
python tools/ui.py floors 5

  pagina  -1  B1   dungeonMap05_03
  pagina   0  1F   dungeonMap05_01
  pagina   1  2F   dungeonMap05_02
```

Tutti e 21 i piani dei sette sotterranei hanno così il proprio nome, e nel giro
di gioco `M` apre la mappa e le frecce **sfogliano i piani** invece di
camminare.

## Il testo c'era, e non si vedeva

Tre difetti nostri, uno dentro l'altro, e il terzo si è visto solo togliendo i
primi due.

**Le tabelle permissive servivano anche qui.** `descriptors()` non caricava
`host.BOOT`, quindi 11 file cadevano in silenzio su una costante nativa
(`GameDataMapFlags`, `map_manager`): **17 schermate** in meno, fra cui l'album
dei nemici, `Equip` e tutte e sette le mappe dei sotterranei. Sono **136**, non
119. La stessa soluzione era già scritta in `descriptor_file()` da una
sessione.

**I file sono UTF-8 nei dati e Shift-JIS nei commenti.** Gli autori hanno
lasciato le proprie note nella codifica di casa: 21 file su 618, e il byte
guasto sta sempre subito dopo un `--`. Il ripiego di prima — *«se UTF-8 non va,
rileggi tutto in Shift-JIS»* — buttava via l'intero file per colpa di una nota,
e fra quei 21 c'è `all.lua.eu`, che da solo dichiara quasi tutte le schermate.
Le scritte tornavano indietro stroppiate: **319 su 358**. Il commento Lua lo
ignora fino a fine riga, quindi sostituire il byte non costa niente.

**E allora si è visto quante scritte il disco colloca.** Sono **432**, e se ne
disegnavano **85**: si guardava dentro `Message` e `Select` e basta, mentre il
testo sta anche nella barra dei tasti, nei nomi di posto e di piano, nei
cartigli (`TitleText`, `Font`, `fontStrings`) e nelle voci dei menu. Una
scritta si riconosce dal fatto che ha un testo **e** un posto: i 61 blocchi
senza `X`/`Y` sono elenchi di dati (`ItemList`, `LivingList`), cioè nomi che
un'altra parte della schermata andrà a pescare.

Da cui la mappa del sotterraneo, che prima era muta, ora dice «Dark Tower» e
«3F» — che è esattamente quello che una mappa deve dire.

*Una schermata può dichiarare più scritte **nello stesso punto**: sono
alternative fra cui il motore sceglie — l'album ne ha tre a (594,64), il conto,
«completo?» e «completo!». Qui si mette la prima invece di sovrapporle.*

*E può dichiarare interi blocchi alternativi: il titolo ha `Menu` e `ClearMenu`,
che sono lo stesso menu prima e dopo aver finito il gioco, e si disegna quello
che comanda. Quello che resta scoperto è che una schermata ha anche **stati**
alternativi non dichiarati come tali — sul titolo «PRESS START BUTTON» convive
con le voci del menu, e a distinguerli non è la posizione ma il momento. Chi
sappia quale stato è attivo non lo abbiamo ancora trovato.*

## Cosa manca

- **Dove atterrano i 15 pezzi che scorrono**, in 5 schermate. Vedi sopra: è
  l'unico estremo che il disco non dichiara.
- **La curva** delle clip: qui è lineare per non inventare nulla.
- **Cosa fa una voce scelta**: `Screen` dice *quale* voce si è scelta, non cosa
  succede dopo. Il legame fra schermate è dichiarato due volte su 136 (vedi
  sopra), quindi per le altre 134 va cercato altrove prima di inventarlo — e
  l'unico posto rimasto è l'EBOOT.
- **L'avvolgimento** del cursore: l'unica cosa qui dentro che è una scelta.
- Le schermate con contenuto dinamico (`Item`, `Status`) hanno bisogno di dati
  di partita che ancora non esistono. *(I `dungeonMapXX` non sono più fra
  queste: la griglia dà le stanze e il descrittore i piani.)*
