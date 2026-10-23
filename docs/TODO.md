# PC-3Ddot — prossimi passi

Aggiornato: 2026-08-20, fine della sessione 13.
Stato generale in [`STRATEGY.md`](STRATEGY.md), ricognizione in
[`RECON.md`](RECON.md).

## Da fare la prossima volta

**La banda 1xxx**, che è la sola delle quattro numerazioni di cella ancora
chiusa. 8.053 celle, 38 numeri da 1 a 51, l'85% in campagna. In sessione 13 il
campo si è ristretto, ma **per esclusione**: non è `1000 +` il numero di un
nodo (miglior copertura 71%, e nessuna famiglia arriva a 51), non è un indice
locale alla mappa (gli stessi numeri ricorrono su mappe diverse, e ogni mappa ne
usa in mediana 4), non è il bordo di uno schermo (29% contro il 21% del caso).

L'indizio da cui ripartire è **la forma**: le celle di uno stesso numero
disegnano figure, e non oggetti sparsi. In `D_24_3` il 21 fa la cornice della
mappa su tutti e quattro i lati, in `D_23_1` una colonna per tutta l'altezza,
in `field_16` il 41-42-43 stanno in filari a due o tre celle di passo. Somiglia
a un **contorno**, e le famiglie che il disco tiene per i contorni adesso hanno
un nome: 崖 la rupe (`f_gke`, 62 voci), 段差 il dislivello, 壁 il muro.

E la misura contro la collisione dice **che la banda è doppia**: quanto spesso
una cella sta a ridosso di un gradino va dall'**86%** (numero 1) al **14%**
(numero 42), con la media di mappa al 33%. Chi sta sul gradino tre volte più
del caso e chi ci sta meno della metà non sono la stessa specie di cosa.
Quindi la domanda non è più «qual è la regola» ma **separare le due bande e poi
cercarne due**. Tutto in [`objects.md`](objects.md).

**Cosa misura l'intervallo di `+0x08`** — da riprendere dal Lua.

**Le torce** — 859 celle di `m_obj_99`, e nei sotterranei l'illuminazione è
tutta d'ambiente. La voce resta, ma **le tre strade che il disco poteva offrire
sono state provate e sono chiuse**, quindi chi la apre sa già che dovrà
dichiarare qualcosa come proprio:

- il materiale della fiamma non ha emissione. `Torch.ps3.dsb` *è* `m_obj_99`,
  con `m_obj_99_a` il supporto (`wall_01`) e `m_obj_99_b` la fiamma
  (`fire_01`, texture `Fire_01.dds`): emissione `0, 0, 0`. Ce l'hanno le lame
  magiche e le sfere, non lei;
- `setPointLight` è degli eventi, non delle mappe: le sue due chiamate mettono
  una luce a `(77.5, 1.51, -102.5)` per la fatina di una scena, e
  `pointLightOff` la spegne;
- nel `.pac` di una mappa non c'è **nessun** record `light`.

Resta la posizione, che si sa (sono le celle), e restano i **record `effect`**
— tipo 4, 1.792 sul disco, mai decodificati: `Torch.ps3.dsb` ne ha due per due
materiali, e se un `-fx` dichiara il modo di fondere la fiamma, quello è il
posto. È l'unico caso finora in cui il dato tace e l'occhio dice il contrario.

Restano il combattimento (un sottosistema che non c'è) e, per la Fase 3, la
sola voce rimasta: il seguito di una schermata.

## In due righe

**Si gioca.** Si sta su una mappa con i suoi abitanti, si cammina di cella in
cella, si attraversa un passaggio e si arriva nell'altra mappa dove il disco
dice, si parla con chi si ha davanti — e un cartello sopra la testa dice dove
premere — e risponde con il suo dialogo, nel riquadro del gioco. Nei
sotterranei si apre la mappa del piano.

Dalla sessione 8 il mondo ha anche **i suoi nemici**, che il disco piazza cella
per cella: nel tempio dell'erba si incontrano due Scorpion e un Soldier Bones,
e cambiando set di piazzamento sono gli stessi, in altri posti. Dalla sessione
11 **si muovono da soli**, eseguendo lo script che il disco porta per ognuno:
gli scorpioni pattugliano, gli spuntoni scorrono avanti e indietro e caricano
quando ti allinei. E con loro gli abitanti, che gironzolano per la corte —
tranne il Re e i saggi, che il disco lascia fermi non scrivendo la `Update`.

Dalla sessione 9 **le schermate si navigano**: le voci, il cursore, il tasto
che sceglie e quello che annulla stanno sul disco, e adesso rispondono.

E dalla sessione 12 il mondo ha **le sue cose**: forzieri, cartelli, torce,
pozzi, l'erba che si taglia, le colonne delle corti, le lapidi dei boss e i sei
altari delle sfere — 7.695 celle su tutto il disco, ognuna col modello che il
disco le assegna.

E dalla sessione 13 **si vede**: la luce di una mappa non è più una nostra
lampada puntata da 42 gradi di azimut, è quella che i vertici della mappa già
portano — e dove non la portano, quella che il disco dichiara nelle proprie
chiamate. In campagna metà schermo stava sotto 0,15 di luminanza; ora è il 6%.
E le cose che brillano brillano: le ventun lame magiche, ognuna del colore che
il suo materiale dichiara, e le sfere degli altari.

Nella stessa sessione i nemici hanno preso **il passo che il disco gli dà**: il
ciclo di pose non è più dedotto dai suffissi `_a`/`_b` ma letto da
`AddAnimation`, e i goblin camminano a quattro tempi.

```
python tools/view.py play field_91        la corte del castello, 33 abitanti
python tools/view.py play d_6_1_3 --map   il tempio del vento, con la mappa
python tools/view.py play d_1_1_1 --cell 39,18          i nemici, disposizione A
python tools/view.py play d_1_1_1 --cell 39,18 --spawn C   gli stessi, altrove
python tools/view.py play field_16 --spawn F            la campagna in FROM Mode
python tools/view.py play d_1_1_1 --cell 39,18 --skip 6  la stanza dopo 6s di vita
python tools/view.py play field_91 --skip 8            la corte, con chi ci vive
python tools/view.py walkabout            la misura, su tutte le mappe
python tools/actor.py census extract      quanto dei nemici sappiamo eseguire

python tools/ui.py drive Pause giu,giu,giu,croce out.png   il menu di pausa
python tools/ui.py menus Title             le voci, e cosa spiegano
python tools/ui.py keys EnemyAlbum         quali azioni, con che tasto
python tools/ui.py floors 5                i piani, col loro nome

python tools/view.py play d_60_3 --cell 11,13   il pozzo, col suo cartello
python tools/nodes.py census               la tavola dei simboli del disco
python tools/nodes.py props                gli oggetti di mappa, per id
python tools/view.py light                 quanto cielo vede ogni mappa
```

## Dove siamo

Fase 1 e Fase 2 sono chiuse per tutto ciò che serve a giocare; la Fase 4 ha
passato tre milestone dichiarate su tre, e la terza era il giro di gioco.

Il confine si è spostato ancora, e stavolta in modo diverso. Non è più "cosa
manca al sistema" ma "quanto del mondo regge quando ci si cammina dentro": la
misura c'è (`walkabout`) e dice **97% degli abitanti raggiungibili** e 365
passaggi su 369 con l'arrivo in piedi, cioè il 99%. Da qui in avanti si allarga
la superficie, con gli script come suite di test (Fase 5).

La Fase 3 resta evitata, e in sessione 11 si è **allontanata**: delle due voci
che le puntavano contro ne resta una. Il pattugliamento dei nemici non era
assente dal disco, era assente dalle nostre ricerche — sta in `all.lua.eu`, che
è la concatenazione di **1.486** sorgenti (869 è il conto dei soli `../lua/`,
corretto in sessione 12), con 37 nemici su 46 scritti per esteso, moto
compreso. E adesso **gira**: 312 nemici su 312 eseguono il proprio script,
nessuno cade e nessuno attraversa un muro, e dalla sessione 13 col proprio
ciclo di pose — **53 metodi su 161, il 79,2% delle chiamate**. Resta il seguito
di una schermata (sessione 9), 2 legami dichiarati su 136.

Ed è la **sesta** sessione di fila in cui quello che serviva era sul disco, in
chiaro, in un file che non avevamo aperto — o, stavolta, in una riga che non
avevamo saputo decodificare: `AddColor` sono i frammenti, e lo dicono due
commenti in Shift-JIS dentro un file UTF-8.

E una cosa che questa sessione ha fatto tre volte, e vale come metodo: **una
conclusione già scritta e non applicata è un debito**. `render.md` diceva dalla
sessione 3 che «la luce dinamica non deve moltiplicare due volte quello che è
già cotto», e per dieci sessioni il visualizzatore ha continuato a
moltiplicare.

## Fatto in sessione 13

Quattro voci del TODO prese in ordine: l'illuminazione, la banda 1xxx,
`AddColor`, `AddAnimation`. Tre chiuse, e la banda 1xxx no — ma con tre strade
sbarrate e la domanda riformulata.

Il TODO chiedeva l'illuminazione, e diceva dove: in `renderer.md`, non
nell'host Lua. Aveva ragione sul posto e torto sulla diagnosi — «la luce
precotta è ~1,5× più chiara del colore dichiarato e noi la spegniamo» dà per
buono che la luce nostra e quella del dato siano la stessa cosa in due scale.
Non lo sono: la nostra aveva una **direzione che il dato non ha**. Tutto in
[`renderer.md`](renderer.md).

### La domanda giusta era: la luce, il disco la dichiara?

E la risposta è due volte no, il che è la parte utile:

```
record `light` nei 167 .pac delle mappe        0
record `light` in tutto il disco             400   una per file
  di nome `ambient-environment-light`        399
  cono 40 gradi, decadimento +inf          400/400
```

Quaranta gradi e decadimento infinito sono i valori di partenza
dell'esportatore. Il colore lo conferma per assurdo: 336 bianche e 62 dello
stesso beige, e i 62 sono un insieme senza senso di gioco — otto boss, sette
mappe d'interfaccia del sotterraneo, `NameEntry`, `Option`. È l'ambiente di
lavoro di chi ha esportato. E `MapParameter`, che dichiara il posto e il brano
di 211 mappe, sulla luce non dice niente.

### Ma è cotta nei vertici, e in un mondo di cubi le normali sono sei

Quindi si rilegge, raggruppando i colori di vertice per faccia. Su `field_16`:
in su 0,969, i quattro fianchi 0,695–0,709, in giù 0,494.

**I quattro fianchi concordano entro l'1%.** Non è una lambertiana — che
avrebbe un lato chiaro e uno scuro — ma una luce d'ambiente **verticale**, cioè
il cielo. Sulle 40 mappe di campagna lo scarto fra i fianchi ha mediana 2,8%.

**E il verso si inverte.** Al chiuso la stessa misura dà il contrario:

```
                su/fianchi   giù/fianchi   scarto fra i fianchi
campagna  40       1,415         0,661            2,8%
chiuso   126       0,822         1,000            0,1%
```

Dove c'è un soffitto la faccia in su è la **più scura**, e quella in giù torna
al livello dei fianchi perché sotto non c'è più un cielo da cui distinguersi.
Un numero che si comporta così è luce.

### E i posti si mettono in fila da soli — la validazione

Il rapporto su/fianchi letto per località, coi nomi che `MapParameter`
dichiara: in cima Dash Circuit (1,52), Lake Garland, Nuntra Desert, Gilgamesh
Beach, Brilord Plains; in fondo, **sotto i sette templi (0,814–0,822), le
grotte** — Sacred Cave 0,78, Fairy's Cave e Rat Hole 0,75, Mountain Path e
Fairy Spring 0,68.

Spiagge, pianure e deserto in cima, grotte in fondo, templi in mezzo. La misura
ordina i posti del gioco come li ordinerebbe chi ci cammina, e nessuno di quei
nomi è entrato nel conto. Le due sole `field_*` che si comportano da chiuso
sono `field_50` e `field_91`, che è **la corte del castello**.

### Chi la porta e chi no, deciso da due misure che non si conoscono

La regola non è «mappa sì, personaggi no». Il colore di vertice è luce dove
**varia dentro una stessa direzione di faccia** — cioè dove c'è occlusione
cotta vertice per vertice, che il cielo da solo non spiega:

```
campagna   scarto entro i fianchi  42%     241 livelli distinti
chiuso                              3%       8 livelli
```

I sotterranei ne portano **due** (`d_1_1_1`: un verde muschio e il nero), e due
livelli non sono una luce: lì la geometria torna fra quella da illuminare, o le
pareti diventano una massa sola. La soglia del 30% non è a occhio — la seconda
misura, *«la faccia in su è più chiara dei fianchi?»*, che non sa niente della
prima, taglia le mappe nello stesso posto: **165 su 167**, e le due che restano
stanno a ridosso del confine.

E c'è una categoria che non potrebbe portarla **per costruzione**: un vaso
istanziato 1.022 volte non ha nei propri vertici la luce di 1.022 posti.
Infatti `c_obj_all` ha le sei facce entro il **5%** l'una dall'altra — lì il
colore di vertice è la tinta, ed è la stessa cosa che `nodes.py colors` aveva
misurato da un altro capo in sessione 12.

### A chi resta si dà ambiente più sole, coi numeri del disco

- `Event:SetSunLightAngle(5.65,62.59); -- yaw, pitch` — **il commento è degli
  autori**. 16 chiamate, 8 valori distinti, e tutti i pitch stanno fra 57,75 e
  86 gradi: il sole di questo gioco è sempre alto. Mediana 73,5.
- `SetParallelLight(0.15,0.15,0.15, 0.08,0.08,0.08)` — due terne, la prima
  sempre più chiara: diffusa e ambiente. `amb/(amb+dif)` vale 0,29, 0,35 e
  0,43, mediana **0,35** — che è, per inciso, esattamente il coefficiente che
  la vecchia formula aveva indovinato.

L'ambiente non è piatto: segue il profilo verticale che *quella* mappa mostra
nei propri vertici, così chi cammina in una grotta prende la luce della grotta.
Resta nostra una cosa sola, ed è dichiarata: gli yaw, a differenza dei pitch,
sono sparsi da −180 a 31 — sono della scena, non del mondo — e se ne prende uno.

### Cosa si vede

Quel che è sparito è la direzione orizzontale che il dato non ha: la
lambertiana veniva da `(0,4 0,8 0,45)`, cioè 42 gradi di azimut, e spegneva a
0,35 i due fianchi che le davano le spalle — sopra un colore che era già la
luce del posto. Su `field_16`:

```
                   luminanza media   sotto 0,15   mediana
prima                    0,195          47,9%      0,160
dopo                     0,295           5,9%      0,281
```

Metà schermo stava sotto 0,15, e gli alberi rivolti a nord e a ovest erano
neri. Nei sotterranei, dove la luce ora la mette il renderer, il pavimento
torna più chiaro delle pareti e la pianta della stanza si legge.

```
python tools/view.py light
```

### E chi brilla di suo: `emission`, un campo che il renderer non usava

Cercando le torce si è trovato l'opposto — le torce **non** sono sorgenti
dichiarate, e qualcos'altro sì. `emission` è pieno: **277 materiali su 1.792**.

**Il caso limite dice come va letto.** I 166 della tavolozza del `CharEditor`
valgono `1, 1, 1`: un pannello d'interfaccia non riceve luce, si mostra a
colore pieno. Quindi l'emissione non è un addendo — che li saturerebbe a
bianco — ma un **pavimento**: `luce = max(illuminazione, emissione)`. Con
questa lettura il caso dell'interfaccia torna da solo e niente satura.

Gli altri sono esattamente le cose che in un gioco brillano: le **21 lame
magiche** (`MR_i_mwp_NN_light`, `_light` in 21 casi su 21) hanno diffuse
**bianco** e tutto il colore nell'emissione, una per una — la 06 rosso fuoco,
la 12 azzurra, la 15 verde, la 22 magenta. E poi i proiettili: `tamaa`, 玉,
emissione 0,30, e quello del boss 0,60.

### Le sei sfere, e la seconda coppia scambiata del disco

I cinque emissivi della libreria di mappa sono le sfere degli altari, e il loro
colore chiude un cerchio della sessione 12, che l'ordine l'aveva stabilito dai
nomi degli item senza poterlo vedere:

| altare | mappa | l'item dello script | materiale | colore | il walkthrough |
|---|---|---|---|---|---|
| 4116 | `D_1_3` | `item_yelloworb` | `orb_116` | (211, 198, 53) | Yellow Orb |
| 4117 | `D_2_3` | `item_greenorb` | `orb_117` | (89, 189, 44) | Green Orb |
| 4118 | `D_3_3` | `item_grayorb` | **`orb_121`** | (235, 111, 1) | **Orange** Orb |
| 4119 | `D_4_3` | `item_blueorb` | `orb_119` | (45, 70, 196) | Blue Orb |
| 4120 | `D_5_3` | `item_redorb` | `orb_120` | (226, 44, 44) | Red Orb |
| 4121 | `D_6_3` | `item_whiteorb` | **`orb_118`** | (118, 75, 189) | **Purple** Orb |

**Sei su sei** con i nomi che il walkthrough usa — ed è la terza volta che
quella fonte, scritta per giocare, valida una lettura fatta sui byte. I due
nomi interni che non descrivono un colore, `gray` e `white`, sono proprio i due
che il modello smentisce: la sfera è arancione e viola. *Il nome che il gioco
mostra vince su quello che gli autori si sono scritti.*

E il materiale va **guardato**, non dedotto dal numero: `m_obj_118_b` usa
`orb_121` e `m_obj_121_b` usa `orb_118`, uno scambio esatto in mezzo a quattro
che combaciano. Dedurlo dal numero avrebbe dato due colori sbagliati, e sarebbe
stato lo stesso errore di forma di `NP_NPC_19` ↔ `NP_NPC_26`. Da cui anche
l'ultima stranezza, che segue il materiale e non il posto: `orb_121` è **il solo
dei sei senza emissione**, quindi a non brillare è la sfera del terzo tempio.

### `AddAnimation`: il ciclo di pose non si deduce più, si legge

Era «il metodo più chiesto che manca», 916 chiamate in 192 moduli. Adesso gira,
e con `InitializeAnimation` porta la copertura dal 71,8% al **79,2%** — due
metodi, sette punti.

`AddAnimation(i, wait)` aggiunge al ciclo il **nodo `i`** per `wait` secondi, e
che il primo argomento indicizzi gli `AddNode` è l'unica lettura che il corpus
permette: **in 314 file su 314** l'indice massimo è minore del numero di nodi
aggiunti, senza una eccezione. Il difetto in cui si cade è che **non sta nella
`Initialize`** ma nella `Update`, al cambio di stato.

Su 25 nemici che dichiarano un ciclo, **15 dicono esattamente `02_a`/`02_b`** —
cioè la regola che la sessione 4 aveva dedotto dalla geometria — e dieci la
correggono: i goblin camminano a **quattro tempi** (`02_a, 01, 02_b, 01`), la
Killer Bee sbatte le ali con `04_a`/`04_b`, e `c_enm_23`/`24`, che sono fra gli
otto modelli senza nessuna coppia `_a`/`_b`, hanno il proprio `02, 01`. Anche il
passo smette di essere un numero nostro: da 0,12 a 0,25 secondi, dichiarato uno
per uno. In `d_1_1_1`, **59 nemici su 60** prendono il ciclo dal proprio file.
Tutto in [`actor.md`](actor.md).

### `AddColor` sono i frammenti, e lo scrivono gli autori

La voce stava nel TODO da due sessioni con l'ipotesi giusta e nessuna prova. La
prova è un commento, e non era mai stato letto perché è in Shift-JIS dentro un
file UTF-8:

```lua
Object:SetAmount( 4 );                  -- 壊れた時の破片の量
Object:AddColor( 0.38, 0.26, 0.00 );    -- 破片の色
```

*La quantità di frammenti quando si rompe*, e *il colore dei frammenti*. Il
dato regge la lettura senza eccezioni — `AddColor` è **sempre al più
`SetAmount`, 71 file su 71** — e `SetAmount` vale 4 in 52 file su 78.

Da cui si **spiega** la misura di sessione 12, invece di doverla lasciare come
stranezza: *«i 132 colori dichiarati sono già quelli dei vertici del proprio
modello, a mezzo grado di tinta»*. Certo che lo sono — i frammenti di una cosa
hanno il colore della cosa. E cade l'argomento con cui quella sessione aveva
escluso «uno per nodo»: che `12GoblinRed` dichiari due volte lo stesso colore
non esclude niente, perché in una tavolozza di quattro frammenti un colore
ripetuto **pesa doppio**.

Gli otto boss non chiamano `SetAmount` perché si rompono **per parti**:
`B01Snake` ha `AddColor` per la 頭 (testa), `AddBodyColor` per il 体 (corpo) e
`AddTailColor` per la 尻尾 (coda), tre colori ciascuno. Tutto in
[`actor.md`](actor.md).

*Non c'è niente da implementare finché non c'è la distruzione: questa voce si
chiude come lettura.*

### La banda 1xxx non si è chiusa, ma tre strade sono chiuse

È l'unica voce di questa sessione che resta aperta, e sta in cima al TODO con
quello che si è misurato: non è il numero di un nodo, non è un indice locale,
non è il bordo di uno schermo. Quel che si è guadagnato è **la forma** (le
celle disegnano cornici e filari) e la spaccatura in due gruppi contro la
collisione, dall'86% al 14% di celle a ridosso di un gradino.

E tre cose cadute lungo la strada, che valgono per conto proprio:

- **`d_hmw_03` non manca.** Stava scritto in [`objects.md`](objects.md) come
  «il solo dichiarato che le celle non usano»: sta in `d_chikei` invece che in
  `d_haichi`. La famiglia è divisa fra due file, e non era un avanzo.
- **Il conto del sotterraneo torna da tre file**: `d_haichi` dichiara 28
  oggetti, `DFI_DUNGEON_OBJECT` ha 28 voci, la banda 3xxx usa 28 numeri. Per la
  campagna i primi due tornano fra loro (40 e 40) e il terzo no — che è
  esattamente dove sta il problema.
- **Le sigle si leggono**, perché la tavola dei simboli le nomina in rōmaji
  dove il nodo sta in tre lettere: `d_kbe` è `MPD_D_KABE`, 壁 il muro (145
  voci, la famiglia più numerosa del disco); `d_dns` è 段差 il dislivello;
  `d_hsr` 柱 la colonna; `d_skr` 仕切り il divisorio; `d_yka` 床 il pavimento;
  `f_gke` è `MPD_F_CLIF`, 崖 la rupe; `f_jmn` il terreno. **Sette su nove** — e
  le due che restano sigle sono proprio quelle delle bande aperte.

## Fatto in sessione 12

Il TODO chiedeva **l'aggancio** dei ventun gimmick, perché un vaso non carica
`EN_ENEMY_NN`. Non passa da nessuna regola: c'è una tabella, ed è la quinta
sessione di fila in cui quello che serviva era sul disco, in chiaro, in un file
che non avevamo aperto. Tutto in [`objects.md`](objects.md), `tools/nodes.py`.

### Il disco dichiara i propri simboli, 1.279 righe

```lua
addNodeListElement( TFI_EVENT_OBJECT, DFI_EVENT_OBJECT,
                    MPD_M_OBJ_127_a,  "m_obj_127_01" );
```

Il pacchetto delle texture, quello della scena, **la costante nativa con cui il
codice nomina il pezzo**, e **il nome del nodo**. Cioè il ponte fra il nome che
uno script pronuncia e il nodo dentro un `.dsb` non è più una nostra deduzione.

```
nodi dichiarati                          1.279
  che esistono davvero in un .dsb        1.267    99,1%
costanti passate ad AddNode                394
  dichiarate nella tavola                  387    98,2%
```

E le **sei righe commentate** nominano tutte e sei modelli che nel disco finito
non esistono più: la tavola era mantenuta.

### E conferma tre sessioni di deduzioni — tranne due caselle, che erano le nostre

```
EN_ENEMY_NN -> c_enm_NN     135 su 136
NP_NPC_NN   -> c_npc_NN     112 su 116
```

Le quattro voci fuori schema sono **due numeri scambiati**, `NP_NPC_19` ↔
`NP_NPC_26`, ed è esattamente la coppia che la sessione 8 aveva indicato come
punto debole della propria rubrica: *«le eccezioni cadono tutte su
`c_npc_19`…`c_npc_26`»*. Aveva ragione a dire dove guardare.

Passando per i 263 file di `Object/npc/` si rilegge la rubrica archetipo→
modello che la sessione 4 aveva dedotto dai nomi dei 237 script di dialogo:
**20 archetipi su 22 concordi, 2 corretti**. E la seconda correzione è quella
che vale:

- **`princessbug` è `c_npc_26`**, ed è lo scambio di cui sopra. Vista, la
  differenza è di colore: `c_npc_19`, `26` e `27` sono tre figure alate rossa,
  blu e verde — `N19PrincessBug`, `N26PrincessBugB`, `N27PrincessBugC`.
- **`goblinred` è `c_enm_12`**, cioè un modello di **nemico**. I goblin rossi
  amichevoli del villaggio riusano il goblin rosso che si combatte, ed è per
  questo che sotto `Object/` non c'è nessun `N26GoblinRed`: non serviva.

La seconda non è uno scarto di un numero, è un cambio di famiglia: nessuna
deduzione fatta *dentro* la sola `c_npc` poteva arrivarci, perché cercava un
`c_npc_NN` e ne trovava uno. *Il numero nel nome di uno script di **dialogo** e
quello del **modello** sono due numerazioni, non una — combaciano venti volte
su ventidue, ed è per questo che sembravano la stessa.*

### La cella dichiara il modello: `4000 + NN`

Gli script dei gimmick caricano `MPD_M_OBJ_*`, la tavola li manda su `m_obj_*`,
e l'identificativo della cella è **4000 più quel numero**. Non è una lettura di
una: la reggono tre famiglie che non si conoscono, **51 celle su 51**, zero
discordanti — 34 `Signboard` (4041 / `m_obj_41`), 12 `Stonemark` (4067 /
`m_obj_67`), 3 `Well` (4063 / `m_obj_63`).

Da lì si legge tutta la banda, che finora era un numero: **4127 è l'erba che si
taglia** (272 celle), 4111 le lapidi dei boss, 4116–4121 i sei altari delle
sfere, 4062 il piedistallo della spada, 4099 le 859 torce, 4060 i 1.022
forzieri. E la banda 3xxx è `3000 + NN` → `d_hmw_NN`, i «Dungeon配置物» del
commento degli autori, **28 numeri su 28**.

**La prova per struttura, che è più forte del conto.** I sei altari e le sei
lapidi non stanno dove capita: una lapide per sala del boss, un altare nella
sala successiva, sempre alla stessa cella (7–8, 4), e l'ordine degli altari è
quello dei templi — `item_yelloworb`, `greenorb`, `grayorb`, `blueorb`,
`redorb`, `whiteorb`. Sei su sei, nel tempio giusto, nell'ordine giusto. Le
lapidi sono sette script per sei celle, e il settimo si firma da sé: in
`BossMarker07` la guardia è commentata e al posto dell'evento c'è
`Print("ぼひょー")`.

**E l'assenza si legge come la presenza.** Delle 4.229 celle senza modello,
**3.843 (il 91%) stanno in 4100…4105**, sei numeri di fila; e
`m_obj_100`…`m_obj_107` è **il buco più lungo di tutta la numerazione** della
libreria, mentre gli altri sono larghi da uno a cinque e sparsi. 4100 sono i
`Warp` e gli osservatori, 4101 `Exit`, `destructionWall`, `WarpDoor` — cioè
esattamente le classi che la sessione 8 aveva misurato assenti sia dalla
geometria sia dalla collisione. Il disco ha riservato un blocco della
numerazione a chi un oggetto non ce l'ha.

### E si vedono — `walk.populate_props`, `view.Charlib`

7.695 celle-oggetto su 11.924 (**64,5%**) hanno un modello e si disegnano. Il
disegnatore non ha avuto bisogno di una strada nuova: cambia solo la libreria
in cui cercare il nodo, e i nomi bastano a dire quale.

La verifica è di riconoscibilità, come per i nemici in sessione 8:

- in `d_60_3` la cella dice `Well01`, l'identificativo dice `m_obj_63`, e
  compare **un pozzo di pietra con l'intelaiatura di legno**, col cartello
  accanto che la cella vicina dichiara;
- nella corte del castello compaiono **colonne e bracieri schierati in
  specchio** sui due lati — che è quel che *配置物* vuol dire;
- nella stanza del Grass Temple dove la sessione 8 aveva messo due Scorpion e
  uno Soldier Bones ci sono adesso anche **due vasi e la porta rossa**.

E messi in fila con `view.py char`, uno chiude un cerchio da solo:
**`m_obj_116_b` è una sfera gialla**, ed è il nodo che `OrbAltar01` spegne con
`SetNodeVisible(1, false)` *«se hai già preso la sfera gialla»*. Il codice dice
cosa nascondere e il modello è giallo, da due file che non si conoscono.

### E il vaso, che era la domanda di partenza

Il vaso è **`m_obj_60`, identificativo 4060, 1.022 celle — l'oggetto più
numeroso del disco**. E che sia lui lo dice `Jar.lua`, che è una tabella di tre
colori e nient'altro: i tre cadono su tre delle **sette** tinte di `m_obj_60`
a **0,1–0,3 gradi** l'una. Il vaso non carica niente perché non ha uno script:
lo istanzia il C++, e di suo il disco dichiara la cella e la tavolozza.

*Ipotesi caduta lungo la strada, e va detta perché era la prima voce di questo
TODO.* Gli oggetti vengono scuri e sembrava che mancasse `AddColor`. È falsa. Il
primo dubbio è nel codice — `12GoblinRed` chiama `AddColor` quattro volte di
fila **e le prime due sono identiche**, il che esclude sia «una per nodo» sia
«una per colore del modello». La prova è la misura di cui sopra, estesa a tutto
il corpus: **132 colori dichiarati da 42 file, scarto di tinta mediano 0,5
gradi, 94% sotto i 5 gradi** contro la tavolozza del proprio modello. `AddColor`
*dichiara* i colori che il modello ha già; applicarli non cambierebbe la tinta
di niente. Il buio è la nostra illuminazione.

```
python tools/nodes.py colors
```

### Un conto corretto: `all.lua.eu` sono 1.486 sorgenti, non 869

869 è il conto dei soli `../lua/`, che è un albero su ventinove: gli altri
ventotto sono i file di dati (`Event/`, `MiniGame/`, `UserInterface/`) nello
stesso flusso. Cercare il confine di un sorgente solo fra i `../lua/` fa
inghiottire a sette di loro le 185 che li seguono — `Object/DropItemList` si
prendeva i cento file del minigioco. Nessuno dei sette è un file di nemico,
quindi le misure di sessione 11 non cambiano; il conto sì, e con esso l'idea di
quanto disco quel file contenga.

*Caduto lungo la strada, e vale perché era una fonte in più che nessuno aveva
letto:* `DropItemList` è un array di 38 righe, e il commento della riga `N`
nomina il nemico `NN` — **37 su 38**, con l'unico scarto che è un refuso degli
autori (`34Succubus2` dove il file è `35Succubus2`), non uno slittamento,
perché la 36 torna a `36HagureSlime`. È la quarta conferma indipendente della
tabella numero→nemico. `08Rock` è l'unica voce vuota: un masso non lascia
cadere niente. E dopo le 38 ci sono **due chiavi per nome**, `['Grass']` e
`['Guard']` — l'erba che si taglia lascia monete, ed è lo stesso `Grass` delle
272 celle qui sopra.

## Fatto in sessione 11

Le due code piccole rimaste, prese sul serio — e cercando la prima si è aperto
un file che rimette in discussione la voce in cima a questo TODO.

### 5080 è Togetoge, e la classe è il verso in cui si muove

La sessione 10 aveva letto bene la geometria e concluso male: *«non è una
creatura, è una figura»*. È un attore, e a dirlo è il file che lo scrive —
`../lua/Object/69Togetoge.lua`, トゲトゲ, «spuntoni». Il commento in testa **è
la tabella che cercavamo**:

```
0 : 縦移動                verticale
1 : 横移動                orizzontale
2 : 縦移動（突撃タイプ）    verticale, a carica
3 : 横移動（突撃タイプ）    orizzontale, a carica
```

e la classe `4` è `TogetogeDashUpdate(Object,2)`, cioè 縦横: fermo finché non
gli ti allinei, poi carica su tutti e due gli assi.

La geometria diventa allora una controprova, e della specie giusta — è una
regola che il piazzamento non può violare senza rompere il gioco, perché due
spuntoni sulla stessa corsia si scontrerebbero al primo passo:

```
classe 0 (verticale)    colonne tutte distinte    4 gruppi su  4
classe 1 (orizzontale)  righe tutte distinte      5 gruppi su  5
classe 4 (a carica)     2 colonne e 2 righe      11 gruppi su 11
```

Il modello c'è, ed è `EN_ENEMY_39_01` = `c_enm_39_01`, **l'ultimo** dei 39: era
la regola `5080 → c_enm_64` a non valere lì, non il modello a mancare. E
l'album ha ragione a non elencarlo, perché `69Togetoge` non chiama
`setBookRegistInfo`: i 46 dell'album sono i 46 che **si registrano nel
bestiario**. Non lo fa neanche `08RockFall.lua` — che carica `EN_ENEMY_08`, e
il cui nome conferma per la terza volta il masso che cade di 5024.

Il walkthrough valida due volte senza saperlo: gli *«spike puzzle»* che elenca
stanno in Aqua Temple, Wind Temple, Dark Tower e nella caverna a ovest della
torre, cioè **le sole mappe con 5080 di classe 0 o 1**; e dove avverte che
*«if you don't move at all upon entering a room… traps won't activate»*, il
codice dice `if( not Object:IsPlayerArea() ) then return; end`.

Un'ipotesi caduta lungo la strada, e vale perché era la più naturale: che le
quattro celle agli angoli fossero i **quattro interruttori** dei puzzle a
tempo. Il walkthrough ne conta a decine in ogni tempio, Grass compreso — che di
5080 non ha nessuno.

### `+0x08` non è un numero, è una coppia — e la vecchia lettura era un campione

`n·257` e `2ⁿ` tornavano perché i due byte coincidono nel **92,3%** dei casi.
Sul disco intero quella lettura salta 33.000 volte. Quel che non ammette
eccezioni è un'altra cosa:

```
byte alti a zero      482.180 su 482.180
b1 >= b0              482.180 su 482.180
+0x0C con due bit     mai
```

Quindi è un **intervallo**, e `+0x0C` ne porta il solo estremo basso. Cosa
misuri resta aperto, ma il campo è molto più stretto di ieri: i valori vanno da
0 a 31, per mappa sono 2-3 nei sotterranei e fino a 7 in campagna — il profilo
di una **quota** — e il pavimento misurato concorda con `b0` nell'84,1% dei
sotterranei e nel 68,2% della campagna. Forte, e sotto la soglia a cui qui si
chiama oracolo un test.

L'indizio migliore è l'eccezione: le **272** celle in cui `+0x0C` ha più di un
bit stanno tutte in `field_7`, hanno `b0 = b1 = 31` e maschera `0x7FFFFFFF`.
Trentuno è il massimo che una maschera a 32 bit porta, e field_7 è la mappa più
alta del disco — quella che in sessione 6 obbligò a misurare l'altezza della
colonna invece di assumerla. È una saturazione.

Il tetto per mappa che `map_param.lua` dichiara (`field07=20`) **non** limita
`b1`: regge in 8 mappe su 35. Quella strada è chiusa.

### E il file che ha aperto tutto: i nemici sono scritti in Lua

`all.lua.eu` non è un file: è la **concatenazione di 869 sorgenti**, con
l'albero delle cartelle lasciato nei commenti (`-- Start ../lua/Object/06Bee.lua`).
Dentro ci sono 128 file `Object/`, 266 `Object/npc/`, 21 `Object/gimmick/`.

```
nemici che chiamano setBookRegistInfo      46      quanti ne dichiara l'album
di cui con la Update completa              46
di cui con il moto (fasi, velocita', direzione, inseguimento)   37
i 9 restanti: gli 8 boss piu' Guardian, che in Lua hanno la sola Initialize
```

Cioè **la voce in cima a questo TODO è da riscrivere**. «Il pattugliamento non
è dichiarato in chiaro da nessuna parte» era vero dei dodici file del minigioco
e falso del gioco: `06Bee.lua` dichiara `MoveArea = 10.0` col commento
*出現位置からの行動可能範囲* — il raggio d'azione dal punto di comparsa — e lo
usa in `IsActorMoveArea`. Il moto dei nemici comuni si legge.

*Perché non l'avevamo visto: il pattugliamento era stato cercato in
`MapParameter`, in `GameParamData` e nell'API — mai qui. E `all.lua.eu` è uno
dei 21 file con i commenti in Shift-JIS che fino a sessione 9 rendevano
illeggibile quasi tutto ciò che conteneva.*

### E i nemici si muovono — [`actor.md`](actor.md), `tools/actor.py`

Non è rimasta una lettura: gira. `Troupe` carica la VM una volta (869 sorgenti
in un decimo di secondo), ogni nemico piazzato riceve l'oggetto che il Lua
chiama `Object`, e ogni fotogramma se ne esegue la `Update`.

```
36 metodi implementati su 134 chiesti = 72,7% delle chiamate
312 attori su 312 nemici piazzati trovano il proprio comportamento
  0 script caduti      0 usciti dal calpestabile muovendosi
261 su 312 si muovono da soli, in cinque secondi, su cinque mappe
```

Il 12% che sta su una cella senza pavimento **c'era già alla partenza** — sono
i 546 di sessione 10 — e chi parte sul pavimento non lo lascia mai. I 51 fermi
non sono un difetto: fra loro ci sono tutti i Togetoge, che la prima riga della
loro `Update` congela finché il giocatore non entra nella stanza.

**La prova che chiude il cerchio con la coda di stamattina.** La classe di 5080
era stata letta come asse di movimento, dal commento del file più la geometria
del piazzamento. Eseguendo gli script la stessa cosa si misura dall'altro capo:

```
Togetoge classe 1 (orizzontale)   spostamento  X 2,3   Z 0,0
Togetoge classe 0 (verticale)     spostamento  X 0,0   Z 29,2
```

Tre decisioni di metodo sono in [`actor.md`](actor.md) e vale la pena
ricordarne una qui: **in Lua `0` è vero**, quindi rispondere zero a un
predicato non implementato darebbe un nemico che crede sempre di vedere il
giocatore — un comportamento inventato da noi. A dare la risposta giusta è la
convenzione di nome del codice originale (`Is…` predicato, `Get…` numero, il
resto comando), che è regolare su tutti e 55 i file.

`python tools/view.py play d_1_1_1 --cell 39,18 --skip 6` fotografa la stanza
dopo sei secondi di vita: gli scorpioni si sono girati e spostati, lo scheletro
ha camminato. `--still` li lascia fermi.

### E gli abitanti gironzolano

Stessa cartella, stesso aggancio: **33 file di NPC**, e `OldManUpdate` è tutto
il gironzolare dei villaggi — direzione a caso, una casella al secondo, quattro
caselle di raggio, da capo.

```
la corte del castello: 33 abitanti, 32 con il proprio script, 22 gironzolano
0 errori   0 usciti dal pavimento
```

**Dieci file non hanno affatto una `Update`** — il Re, i sei saggi, l'eroe
leggendario, il suo fantasma, il Re delle medaglie — e fra i 55 nemici non
manca mai. Il disco dichiara l'immobilità con un'assenza, e la categoria è
quella giusta: chi aspetta in fondo a un tempio non passeggia. Ma fermi non
vuol dire immobili: `KingInitialize` alterna le due pose del passo ogni mezzo
secondo, ed è il motivo per cui `AddAnimation` la chiama anche chi non si muove.

Caduto lungo la strada un aggancio che vale: i modelli 02–08 scrivono
`NP_NPC05_01` e gli altri `NP_NPC_09_01`, due convenzioni sullo stesso disco,
ma **il numero del file e quello del nodo coincidono 33 volte su 33** — la
terza conferma indipendente della tabella archetipo→modello di sessione 4.

E una cosa che **nessuno dichiara**, da segnare come nostra: la direzione
iniziale di un abitante. Non è negli script (nessuno dei dieci fermi chiama
`SetDirection`) e non è nella griglia (le celle che nominano un NPC non portano
un solo flag). Il `facing = 1` è una scelta di `walk.populate`.

Ma il **piazzamento la implica**, e questo si misura: chi non si muove sta
sempre più in alto della porta da cui si entra — **11 casi su 11** al chiuso,
con il Re di Dotnia a y=11, la porta a y=36 e sei cortigiani schierati in
mezzo. Gli si cammina incontro, quindi guardare verso il basso della griglia
vuol dire guardare chi arriva. È la convenzione che ci si aspetta da un gioco
del genere, ma qui non è presa dal genere: è misurata. Resta un'inferenza — il
dato dice dove stanno, non dove guardano — solo che è un'inferenza con un
oracolo. *(L'unica eccezione è un saggio in campagna aperta, dove «la porta più
vicina» non è l'ingresso di una sala e la domanda non si pone.)*

## Fatto in sessione 10

Le tre code che la sessione 8 aveva isolato, chiuse tutte e tre — e una premessa
che le sorreggeva, tolta.

### «Non si sovrappongono mai» era una tautologia

Fra le tre misure che dicevano *«A, B, C sono tre disposizioni della stessa
popolazione»*, la più convincente era che le loro celle non si sovrappongono
mai. Non prova niente: `mapdat.cells` percorre `for i in range(w*h)`, cioè
**una cella, un record**, e ogni record porta un attore e una lettera soli. Due
lettere nella stessa cella **non possono esistere nel formato**.

La lettura non cambia — le altre due misure reggono — ma il conto degli indizi
sì, ed è la ragione per cui vale la pena verificare la premessa prima del
risultato.

### `F,G,H` si aggiungono, e si misura per assurdo

Era l'ultima cosa scritta come inferenza aritmetica. Basta contare le mappe:

```
con A,B,C e F,G,H     50
con i soli A,B,C       9      la più popolosa è d_5_1_2, 45 nemici
con i soli F,G,H       0
```

Se `F,G,H` sostituissero, quelle nove mappe resterebbero **senza un nemico**
nella difficoltà che il walkthrough chiama *«hordes»* — fra loro un piano di
sotterraneo con 45. E `|F| < |A|` in 29 mappe su 59: il Grass Temple passerebbe
da 60 nemici a 13, cioè FROM Mode sarebbe più *vuoto*. Si aggiungono.

### Il 4% senza pavimento: la domanda andava divisa per posto, non per specie

Dopo che l'ipotesi del volo era caduta sulla specie, la risposta stava nel
posto:

```
in campagna:        0 su 6.097  =  0,0%
nei sotterranei:  546 su 4.099  = 13,3%
```

**Zero su seimila.** In campagna il disco mette ogni singolo nemico su una
cella calpestabile, il che dice che il piazzamento sa dov'è il terreno. Il
fenomeno è tutto e solo dei sotterranei, e lo condividono gli oggetti di mappa
(32% contro 0,2%).

L'ipotesi successiva era la più scomoda — uno **scarto di una cella fra la
griglia e la collisione**, cioè colpa nostra — e il segnale che la suggeriva è
forte: il pavimento non sta mai a destra né in basso, e dove il vicino con
pavimento è uno solo sta in alto a sinistra **44 volte su 44**. È stata
misurata e non regge: spostare *tutti* i nemici di una cella porta i sotterranei
dall'86,7% all'87,6% di celle calpestabili, e uno scarto vero porterebbe al 99%.

Resta una regola stretta, che è la risposta: **nessuno sborda di più di una
cella**. Tutte e 546 hanno da uno a tre vicini con pavimento, mai zero e mai
più di tre, e in 497 casi su 546 quei vicini stanno alla stessa quota. Il
piazzamento è disegnato sul rettangolo della stanza e trabocca di una cella nel
muro; in campagna non c'è muro in cui traboccare. Da cui `Columns.ground_near`:
un nemico senza pavimento si posa su quello accanto, non a zero.

### 5024 è il masso che cade — e lo dice la numerazione dell'album

Nel tratto 5018–5026 lo scarto fra identificativo e numero di modello è
costante (5016) in **tutte e otto** le voci dichiarate, e 5024 è l'unico buco
del tratto: quindi `c_enm_08`, che fra i 39 modelli esiste davvero ed è una
massa bitorzoluta color ocra senza pose.

Il piazzamento concorda da tre parti: sei mappe sole e **tutte d'altura** (Mt.
Sabre, Sukaboko Highlands, Klovis, Vatara Highlands); celle in righe, da 5 a 28
caselle di quota; e il terreno che **scende in avanti nel 50% dei casi e in
nessun'altra direzione**, con la salita alle spalle. Il walkthrough, di
Sukaboko Highlands: *«a screen with Centauses and **falling rocks**»*.

Ha i sei set di piazzamento come ogni nemico — quindi ricompare — e l'album non
lo elenca perché un masso non è un mostro da registrare.

### 5080 non è una creatura: è una figura

Né `c_enm_64` né `c_npc_33` esistono, e l'ultimo campo del record vale **1**
dove i nemici hanno 0 e gli NPC 6. La sua classe non è un nome ma una cifra, e
la cifra sceglie una forma. La classe `4`:

```
11 figure, 4 vertici ciascuna, 44 celle
gli angoli sempre a (1,1) (14,1) (1,10) (14,10) dentro lo schermo 16×12
```

I quattro vertici di una schermata rientrati di una cella — uno per tempio più
cinque nella Dark Tower, nessuno nel Grass. Non sono stanze di boss, e lo dice
l'assurdo: le mappe dei boss ne hanno **zero**. Dentro ognuna c'è invece
**esattamente un osservatore**, 11 su 11, e da 10 a 16 nemici.

Le classi `0` e `1` disegnano altre figure — una diagonale di cinque celle, tre
volte — e restano aperte. Ma l'intervallo sopra 5000 non contiene solo
creature, e questo era il punto.

## Fatto in sessione 9

La voce ferma da tre sessioni, chiusa — e più larga di com'era scritta. Il TODO
diceva «`Cancel = {Enable, Index}` dice quale voce sceglie il tasto di
annullamento, quindi anche il comportamento è dichiarato: manca chi lo esegue».
Cercando chi lo esegue si è visto che di dichiarato c'è **quasi tutto**, e che
a mancare erano tre nostre letture.

### Una voce è una voce se il cursore ci può stare — [`ui.md`](ui.md), `ui.menus()`

Il criterio non è il **nome** del blocco ma `CursorX`/`CursorY`. Cercando così
si trovano **23 blocchi per 60 voci** e i nomi sono tre: `Select` sono i 19
sì/no già noti, ma `Menu` è il menu del titolo e quello di pausa — *RESUME,
SAVE, LOAD, OPTIONS, SNAPSHOT, ALBUM, BESTIARY, LOADING ART, TITLE* — e
`ClearMenu` è il titolo **a gioco finito**, con `NEW GAME+` in più.

Le due liste del titolo condividono le posizioni da 407 in giù: la voce nuova
non si aggiunge in fondo, il menu **cresce verso l'alto**. E ogni voce porta la
propria frase di spiegazione, che è l'unico pezzo di interfaccia che cambia al
muoversi del cursore.

L'asse non è una scelta: le voci sono incolonnate in **23 blocchi su 23**, zero
in riga. Il cursore sta 34 px a sinistra e 7 in su, sempre gli stessi, e il
passo fra due voci è **32 px** — la riga di font con cui in sessione 7 il
riquadro di dialogo tornava a 597 contro un corpo che finisce a 598. Lo stesso
numero da un terzo posto.

### Annullare non vuol dire uscire, e l'indice si conta da zero

Tutte e 19 le schermate con `Cancel` hanno le stesse due voci `YES`/`NO` e
tutte e 19 dichiarano `Index=1`. Contando da uno, annullare vorrebbe dire
acconsentire **in tutte e 19**; contando da zero è `NO` in tutte e 19. È la
stessa base di `Start`, che vale 0 per la clip `In`: due campi, la stessa
convenzione.

Quindi ○ non chiude la finestra, **sceglie una voce precisa**. E dove
`Enable=0` non fa niente — sono `ClearSave`, `DeleteSaveDataSelect`,
`GameOverSaveSelect`, `GameOverResurrectSelect`, cioè le quattro schermate in
cui il gioco pretende una risposta. Due finestre identiche a vedersi che si
comportano in modo diverso perché il disco lo dichiara:

```
python tools/ui.py drive Continue cerchio out.png
  cerchio  voce 2/2 'NO'  -> scelto 'NO'  (annullando)

python tools/ui.py drive ClearSave cerchio out.png
  cerchio  voce 1/2 'YES'          il tasto non fa niente
```

Di tutta questa parte resta **nostra una cosa sola**, e si spegne: che
dall'ultima voce si torni alla prima (`Screen(..., wrap=False)`).

### La barra dei tasti dichiara quali azioni ci sono — `ui.keybar()`

Le scritte stanno nel descrittore, le icone nella scena sotto un nodo
`KeyAssign`, e si accoppiano perché ogni scritta comincia **7-8 px dopo** la
fine di un'icona; la striscia è continua, nell'album i sette rettangoli vanno
da 673 a 1176 senza un buco. A nominare il tasto è **il colore**, che su questo
hardware *è* il tasto: la ✕ è disegnata blu e la ○ rossa. Il grigio invece non
separa niente — croce direzionale e dorsali sono senza tinta — e resta un nome
solo.

Due cose che il conto dice e che vale la pena tenere: `PAGE` non ha icona
perché a sfogliare sono le frecce ai lati della pagina, che nella scena sono
nodi per conto loro; e dove la schermata **scorre** l'accoppiamento non si può
fare, perché la striscia è parcheggiata fuori campo mentre le scritte sono già
al proprio posto. Sono le stesse 5 schermate di sempre.

### La pagina è il piano, con il segno — `ui.pages()`, `ui.dungeon_floors()`

`setting = {pageMin, pageMax}` era un campo mai guardato. Sulle mappe dei
sotterranei quel numero è il piano e il segno dice da che parte: `B1` è −1,
`1F` è 0. Due conti indipendenti:

```
pageMax - pageMin + 1  =  numero di descrittori di piano    7 sotterranei su 7
le etichette stampate (B2, 5F) cadono nel proprio intervallo      19 su 19
```

I due che restano fuori sono i sotterranei a **un piano solo**, che dichiarano
`0..0` e `1..1` pur essendo tutti e due `B1`: dove non c'è niente da sfogliare
il campo non è mantenuto.

La successione dei file non è quella dei piani — il sotterraneo 5 li tiene
nell'ordine `1F`, `2F`, `B1` — e il primo descrittore **non dichiara il
proprio** piano, perché elenca tutte le etichette per disegnare il selettore.
Il suo si ricava per differenza: è quello che gli altri non hanno preso, e
torna in tutti e cinque i sotterranei a più piani. Tutti e **21 i piani** hanno
ora il proprio nome, e in `play` la mappa si sfoglia con le frecce.

### Il testo c'era e non si vedeva: tre difetti, uno dentro l'altro

**Le tabelle permissive servivano anche in `descriptors()`.** 11 file cadevano
in silenzio su una costante nativa: **17 schermate** in meno, fra cui l'album
dei nemici e tutte e sette le mappe dei sotterranei. Sono 136, non 119. La
soluzione era già scritta in `descriptor_file()` da una sessione.

**I file sono UTF-8 nei dati e Shift-JIS nei commenti.** Gli autori hanno
lasciato le note nella codifica di casa — 21 file su 618, e il byte guasto sta
sempre subito dopo un `--`. Il ripiego «se UTF-8 non va, rileggi tutto in
Shift-JIS» buttava via l'intero file per colpa di una nota, e fra quei 21 c'è
`all.lua.eu`, che da solo dichiara quasi tutte le schermate: le scritte
tornavano indietro stroppiate, **319 su 358**.

**E allora si è visto quante scritte il disco colloca.** Sono **432**, e se ne
disegnavano **85**, perché si guardava dentro `Message` e `Select` e basta. Una
scritta si riconosce dal fatto che ha un testo **e** un posto: i 61 blocchi
senza `X`/`Y` sono elenchi di dati, cioè nomi che un'altra parte della
schermata andrà a pescare.

Da cui la mappa del sotterraneo, che era muta, ora dice «Dark Tower» e «3F».

*Il difetto ha la stessa forma delle due scoperte precedenti — in sessione 6 un
dato che sembrava vuoto era solo chiuso, in sessione 7 un pezzo che sembrava
acceso era solo spento — ma stavolta la causa era **tutta nostra**: il disco
diceva le cose, e noi leggevamo male il file.*

### Il cursore non era nostro, e il suo posto misura il testo

Era l'ultimo pezzo che ci disegnavamo a mano, e la scena lo porta in due modi:
**parcheggiato all'origine** in 7 blocchi su 8 (un `Cursor_01` di 16 px, da
mettere dove dice `CursorX`), e **uno per riga già collocato** nel menu di
pausa, nove marcatori alle posizioni che il descrittore dichiara voce per voce
— 530 contro 529, 86 contro 84. Nel secondo caso vanno spenti gli altri otto,
che è la stessa forma della mappa del sotterraneo.

E il cursore dà l'oracolo su **due numeri nostri tarati a occhio**: la cella
del font è 32×32, e il descrittore mette il cursore 7 px sotto la scritta —
alto 16 dentro una riga di 32, cade in mezzo. Quindi `Y` è il bordo **alto**
della riga e la scala del font è **1**, non 1,4. Il cursore cade in mezzo alla
riga a meno di 6 px su 30 voci, e combacia con il conto del riquadro di
dialogo di sessione 7 (`485 + 3×32 + 2×8 = 597` contro un corpo che finisce a
598): la stessa altezza di riga per due strade che non si conoscono.

### Il seguito di una schermata è dichiarato due volte su 136

Cercandolo prima di dichiararlo assente: `Pause` apre `PauseTitleSelect`, e
`GameOver` apre `GameOverSaveSelect` e `GameOverResurrectSelect` — un campo in
fondo alla tabella con la chiave uguale al valore. Tutte e tre sono la
**finestra di conferma** di una scelta che non si torna indietro. Dove il
seguito è una domanda il disco lo dice; dove è un'altra schermata, no.

## Fatto in sessione 8

La prima voce del TODO precedente, chiusa — e con essa tre censimenti che il
progetto teneva separati, perché si è scoperto che li tiene insieme **un solo
campo**. Poi, per la prima volta, una validazione contro una fonte esterna.

### Il campo +0x10 è l'attore — [`walk.md`](walk.md), `mapdat.actor()`

Il record di cella ha sei campi numerici e cinque erano marcati `?` da cinque
sessioni. Il quinto è **chi vive lì**, con una numerazione globale al gioco, e
a partirla sono tre file che non si conoscono: gli oggetti sotto 5000 (costante
per classe, **175 su 195**), i nemici che l'album `EnemyView` dichiara
(**45 su 46** si ritrovano piazzati), e gli NPC su **5047 + NN** con `NN`
l'indice di `c_npc_NN` (**226 celle su 240**, 94,2%).

L'ultima è la più bella perché è un oracolo *in più* su una conclusione già
presa: che `n05` fosse `c_npc_05` la sessione 4 l'aveva dedotto dai nomi dei
237 script `npcevent_`, e qui venti valori consecutivi lo ripetono da soli. Le
eccezioni cadono **tutte** su `c_npc_19`…`c_npc_26`, cioè proprio i modelli che
quella deduzione risolveva peggio: il disaccordo indica il punto debole della
nostra rubrica, non del disco.

Restano non attribuiti gli 8.781 valori sotto 4000.

Caduto lungo la strada anche un secondo campo: +0x08 e +0x0C sono lo **stesso
numero in due codifiche**, `257·n` e `2ⁿ`, senza una coppia fuori schema.

### I nemici sono sul disco, e le sei lettere sono due terne

«Resta al codice solo quanti ne mette per stanza e con che regola» era scritto
qui, ed era sbagliato: la griglia piazza **10.196 nemici**, uno per cella. E
ogni cella porta un **set**, `-sA`…`-sH`, che era una stringa mai vista in
nessun documento del progetto.

**A, B, C sono tre disposizioni alternative della stessa popolazione**, e lo
dicono tre misure che sbagliano in modi diversi: stesse specie in **58 mappe su
59**, equinumerose su tutto il disco (1807/1824/1804), e celle che non si
sovrappongono **mai** pur coprendo la stessa area (88%, sopra l'80% in 51 mappe
su 59, sotto il 40% in nessuna — quindi non sono squadre). Nel Grass Temple
l'identità è specie per specie: 13 Soldier Bones, 10 Scorpion, 15 Bat, 22 Red
Slime, tre volte.

**F, G, H sono le stesse tre per FROM Mode** — e la lettera lo dice, `F` sta per
FROM. Lì il parallelismo si rompe, ed è giusto: in `FIELD_16` 36/47/45 contro
19/19/19, sette specie contro quattro.

### E i nemici sono entrati nel gioco — `view.py play --spawn`

`Walk.populate_enemies()` li mette in mappa, e il disegnatore non ha avuto
bisogno di una riga: un'entità con modello `c_enm_01` cerca il nodo
`c_enm_01_01`, che è esattamente ciò che l'album dichiara in `NodeStrings`.
L'unica traduzione è togliere da quel nome la posa, perché l'album nomina un
**fotogramma** e nel mondo serve la radice — che è poi la conferma, da un terzo
file, del «i figli di un nodo sono pose intere» di sessione 4.

La verifica è di riconoscibilità, ed è passata tre volte:

- nel tempio dell'erba, alla cella (39,18), compaiono **due Scorpion e un
  Soldier Bones** — due scorpioni rossi e uno scheletro con la spada, che è
  esattamente ciò che le celle attorno dichiarano;
- **cambiando `--spawn` da A a C**, nello stesso punto, ci sono di nuovo due
  Scorpion e un Soldier Bones (più due Red Slime), **in posti del tutto
  diversi**. L'ipotesi dei tre piazzamenti si guarda invece di leggerla;
- in `field_16` con `--spawn F` la campagna verde si popola di Spidel e Goble.

E una misura che il render ha suggerito e che vale più del render, perché mette
alla prova la frase più specifica del walkthrough — *«even enemies that are
normally restricted to dungeons»*:

```
A,B,C in campagna:  2.195 nemici,    12 di specie da sotterraneo =  0,5%
F,G,H in campagna:  3.902 nemici, 1.356 di specie da sotterraneo = 34,8%
```

Settanta volte tanto, e 17 specie contro 3. Non è una preferenza statistica: è
la difficoltà che si dichiara nel dato.

### I dodici nemici scritti in Lua — `entity.enemy_motion()`

Il gioco implementa i nemici in C++, ma il disco ne porta dodici per esteso:
gli attori del minigioco Block Defence riusano i modelli veri **per numero**,
e `MGBee` carica `EN_ENEMY_06_04_a`, che è il `NodeStrings` di `Killer Bee`.
L'aggancio si verifica sui **nomi**, che nessuno dei due file prende dall'altro
— `MGSkelton`→*Soldier Bones*, `MGWood`→*Evil Tree*, `MGHagureSlime`→*Crystal
Slime*: **dodici su dodici**.

Tre numeri che erano da inventare e ora si leggono: il **periodo** del
fotogramma (`StepWait`, 0,3 in tutti e dodici — il nostro era 0,25 e non veniva
da nessun dato), **le pose del ciclo**, e **chi vola**.

Le pose hanno scoperto un difetto nostro: `Entity.pose()` restituiva sempre
`02_a`/`02_b`, ma **12 modelli `c_enm` su 37** non hanno affatto `02_a` —
quattro camminano con `04` e otto non hanno nessun paio. Un terzo dei nemici
restava fermo perché cercavamo una posa inesistente. Ora il ciclo lo dichiara
il minigioco dove c'è, e altrimenti il modello stesso.

E una regola valida su **tutti e 22** gli attori, zero eccezioni: *se il
modello ha due pose appaiate `_a`/`_b` il ciclo lo fa il motore, altrimenti
l'attore le alterna a mano.* È la controprova, da un file scritto per un
minigioco, del «`_a` e `_b` sono i due passi» dedotto in sessione 4 dalla sola
geometria.

**Un'ipotesi caduta, e vale perché era misurabile solo adesso.** Avere `Type`
(terra/aria) permetteva di spiegare il 4% di nemici piazzati senza pavimento
sotto. Non lo spiega: volanti 2,3%, terrestri 4,0% — se mai il verso è
l'opposto, e chi manca il pavimento più spesso è Clay Golem (17%), che cammina,
mentre Killer Bee sta a terra nel 100% dei casi. Resta aperto.

Il **pattugliamento** invece non si legge: nel minigioco i nemici camminano
verso la torre con un `BlockDefenceMove()` nativo, che di quel minigioco è la
regola. Lasciato non implementato invece che inventato.

### Il pattugliamento non c'è, e cercarlo ha dato i nomi dei posti

`MapParameter.lua.eu` era l'ultimo posto da guardare prima di inventare il moto
dei nemici, e non contiene niente sul moto — né lo contiene l'API, che ha
`PlayEnemy`, `PauseEnemy`, `visibleEnemy`: congelare e mostrare, mai muovere.
**Il pattugliamento non è dichiarato in chiaro da nessuna parte**, e resta non
implementato invece che inventato.

Ma quel file dichiara **211 mappe con il nome del posto e il brano**, e ne
aggancia **168 delle nostre 170** (le due che restano sono `field_99` e
`field_test`). 55 località per 168 mappe, cioè un posto occupa più schermate:
attraversare `field_6` e `field_7` è restare a "Klovis". Ora `play` dice dove
si è. E `field_3` si chiama **"Nialliv Valley"**, cioè *Villain* al contrario.

Conferma a costo zero: `d_1_1_1` è **"Grass Temple"** e `d_6_1_3` **"Wind
Temple"**, quindi `DUNGEON_EARO` = vento lo dice ora un **quarto** file, in
inglese.

### `LivingId` è la famiglia, non la casa — una nostra lettura corretta

Con il nome del tempio e il piazzamento vero insieme, si è potuta mettere alla
prova una frase che i documenti davano per buona: 1.988 nemici piazzati nei
templi, e il loro `LivingId` nomina il tempio in cui stanno **nel 47,1%**. Con
sette habitat il caso darebbe il 14%, quindi la correlazione è forte; ma non è
una regola, e il Flame Temple è pieno di `DUNGEON_WATER`. L'habitat classifica
il nemico, non lo colloca — era il miglior surrogato finché il piazzamento non
si sapeva leggere.

E una lettura che ne esce: **la Dark Tower non ha un habitat proprio, li
attraversa tutti** — piano per piano l'habitat prevalente fa GRASS, GRASS,
SANDS, WATER, WATER, EARO, cioè 1, 1, 3, 4, 4, 6 nell'ordine in cui il gioco fa
visitare i templi. Una successione non decrescente: la torre finale ripercorre
il viaggio.

### La validazione esterna, che è la novità di metodo

Un [walkthrough](walkthrough/) — scritto per giocare, non per leggere byte,
quindi con errori tutti suoi — ha confermato quattro cose che avevamo dedotto
dai soli byte, e nessuna era stata cercata:

- *«If the enemy positions are annoying, you can leave the room and come back
  and see if they respawn in a more favorable location»* → i set `A`/`B`/`C`;
- *«all kinds of crazy enemies spawn all over the place — even enemies that are
  normally restricted to dungeons»* → il profilo di `F`/`G`/`H`;
- *«Crystal Slimes and Blue Dragons spawn rarely… they can actually spawn
  anywhere»* → **5075** e **5076** sono gli **unici due dei 46** con
  `LivingId = -1`, cioè senza habitat. Il campo che li distingue nel dato è lo
  stesso che li distingue nel gioco;
- gli otto boss con il loro tempio, **otto su otto** contro gli habitat
  dell'album — e con essi cade l'ultimo dubbio su `EARO`, che è *aero*.

E una lettura che il dato dava già senza saperlo: i boss si riconoscono perché
hanno **2 celle su 1 mappa e nessun `-s`**. Un boss non ha piazzamenti
alternativi perché sta in una stanza sola.

### I 25 nomi di evento erano funzioni, non file — `Grid.triggers`

«Solo 3 nomi su 25 trovano il file» diceva il TODO. A sbagliare era la ricerca:
`gimmick_grass4` è una **funzione** dentro `gimmick_grass.lua.eu`, insieme agli
altri sei `gimmick_grass`. Cercate così si risolvono **25 su 25**.

Sono grilletti di posizione, e il corpo lo conferma: guardia
`if GetEventFlag(167)==1 then return end`, `LockPlayer`, la fata che spiega
l'interruttore, `UnlockPlayer`. Girano sull'host della Fase 4 senza aggiungere
un metodo. Cinque dei 25 stanno nello stesso file e sono le quattro direzioni
più il centro: `mainevent_herodream` `n`, `s`, `e`, `w`, `2`.

### Cosa fanno gli oggetti: parametrizzato in chiaro, implementato in C++

`GameParamData/gimmickParam.lua.eu` dichiara quindici gimmick con i parametri e
i commenti degli autori — `Hole` con `gravity 18.0` e `pop_count 1`,
`BlackHole` con `vacuum_range 6.4`, `TargetSwitch` con il valore di clamp «di
quando la freccia si conficca», `stone_monument` con i suoi due messaggi. Il
walkthrough valida anche questi, e uno parola per parola: la lastra di
`stone_monument` è quella di Parallax, e i nostri dodici `Stonemark` stanno
nelle stanze in cui la guida dice di lanciarlo.

La **logica** resta nel codice, ma la sua forma la conosciamo: il disco porta
34 attori scritti in Lua per il minigioco Block Defence, con tutti e quattro i
callback del contratto (`Initialize`, `Update`, `CheckMove`, `CheckCollision`),
e fra loro c'è `75MGBombRock` — il muro che la bomba apre, scritto per esteso.
`MR_BLOCK` e `MR_NONE` non compaiono altrove sul disco.

## Fatto in sessione 7

La voce in cima al TODO precedente, chiusa — ma non come era scritta. La
domanda era «o si ricostruisce il moto interpolando fra il parcheggio e il
posto, o è la prima cosa da chiedere all'EBOOT», e la risposta è che erano
**due animazioni diverse** messe in una voce sola: una ha tutti e due gli
estremi sul disco, l'altra ne ha uno.

### `Start` non è un tempo, è un indice — [`ui.md`](ui.md), `ui.py clips`

Le quattro clip si leggevano come inizio e durata su una linea del tempo. Il
conto dice altro: su 36 schermate che dichiarano `In`, `Start` vale **0 tutte e
36 le volte**; `Main` vale 1 tutte e 33; `Out` vale 2 tutte e 36. Un tempo che
non cambia mai non è un tempo — è la posizione in una tabella di clip, e a
determinarla è il nome. `Size` invece varia ed è la durata in secondi.

Le schermate grosse lo confermano, e dicono anche cosa indicizza: in `Option`
gli indici vanno da 0 a 38, densi, e i tre pannelli `Display`, `Sound`,
`Message` **condividono** il blocco 3–9 tenendo separati solo i propri 0–2,
20–22, 23–25. Cioè la zona dei messaggi, la barra dei tasti e il cursore sono
gli stessi oggetti riusati: l'indice non identifica un momento, identifica **la
cosa che si muove**.

I dieci indici 10–19 sembravano un buco ed erano un difetto di lettura nostro:
`Volume` è un **array** e non un dizionario, e chi scende solo nei dizionari lo
salta. Sono le dieci tacche del volume, e la scena ha esattamente dieci nodi
`Volume00…Volume09`.

### L'apertura si ricostruisce, perché il disco ha tutti e due gli estremi

Il pezzo è esportato con la scala a zero e la mesh sotto è intera, quindi da 0
a 1 c'è tutto; la durata la dichiara `Size`. `unfold` non è più un interruttore
ma un **fattore**, e `ui.py anim` fa i fotogrammi.

La finestra si apre come un televisore che si accende, e a dirlo è la scena:
`Confirm_01` è tre pezzi, `a` (505×4) e `c` (505×7) con **scala X = 0** e il
corpo `b` (505×99) con **scala Y = 0** — prima una riga orizzontale, poi il
corpo in verticale. Quale asse si apre lo dichiara quale scala è nulla. L'unica
cosa non letta è la curva, e qui è lineare per non aggiungere un numero
inventato.

### Lo scorrimento invece ha un estremo solo, e sono 15 pezzi

Le schermate a scorrimento non sono chiuse da una scala: sono **spostate**.
Sul disco c'è solo il parcheggio — `Window01` a `x=-600`, `Window03` a `x=1300`,
`Message` a `x=1285`.

Il moto è orizzontale, ed è misurato: **38 pezzi parcheggiati fuori campo, 33
fuori solo in X**. La Y è già quella definitiva, e lo conferma il descrittore
per un'altra strada — colloca «EQUIPMENT» a y=53 dentro `Window01` (48–294),
«ITEMS» a y=308 dentro `Window02` (303–550), i tasti a y=635 dentro la barra
(632–666).

Ma **dove atterrino in X non sta da nessuna parte**: non nella scena, che ha
solo il parcheggio, e non nel descrittore, che colloca il contenuto e non il
contenitore. Interpolare fra parcheggio e posto non si può, perché il posto
manca. È questa e solo questa la parte da chiedere all'EBOOT, e riguarda
**5 schermate e 15 pezzi**: `Item`, `Orb`, `Option`, `NameEntry`, `GameOver`.

### Il riquadro di dialogo, e il file che non era quello — [`ui.md`](ui.md)

Era l'ultimo pezzo disegnato da noi, e il TODO lo dava in `data/Balloon`. Non
è lì: `balloon_eng.ps3.dsb` sono tre quadri di **1,6 × 0,6 unità di mondo** —
1,6 è la casella — con materiali `CHECK`, `TALK`, `OPEN`, e le texture sono tre
fumetti con il tasto ✕ e la codina in giù. È il cartello che galleggia sopra la
testa. Stessa forma dell'errore di `Priest.ps3.dsb`: un nome che convince, e una
misura che lo smentisce.

Il riquadro sta in **`UserInterface/Message`**, con la stessa struttura a tre
pezzi di tutte le finestre — `Message_a/b/c` (505 × 138) e `MessageBig_a/b/c`
(686 × 154) — più `Advance_Cursor`, la freccia del «premi per continuare». Il
descrittore mette il resto: `Line=3`, l'origine del testo (`X`/`Y` e
`LargeX`/`LargeY`), l'interlinea, i colori e **dieci velocità di battitura**.

I numeri si incastrano, ed è la verifica: il font a scala 1 misura 32 px per
riga, quindi `485 + 3×32 + 2×8 = 597` e il corpo finisce a **598**. Da lì si
legge anche che `Space` è l'interlinea *fra* le righe e non su ognuna —
sommandola all'ultima si sfora di sette pixel. Ora `view.py` sceglie fra le due
misure quella in cui il testo ci sta, e la mette dove il disco dice.

### E i cartelli sono diventati il segnale «qui puoi parlare»

Trovato il file per sbaglio, l'oggetto si è rivelato quello che mancava al giro
di gioco: `play` non aveva modo di dire al giocatore dove premere. Ora il
cartello `TALK` sta sopra la testa di chi si ha davanti, e **solo se ha
qualcosa da dire** — è un invito a premere, non una decorazione.

Costa niente perché si aggancia a `EntityGroup`, che legge la matrice al
momento del disegno: una geometria sola nel batch, un'entità finta che ogni
fotogramma prende il posto di chi si ha davanti, e la matrice nulla a spegnerla.
L'angolo lo dà la camera, perché un cartello si legge sempre di fronte.

### Il corpo del riquadro piccolo è trasparente, ed è giusto così

Nel render il mondo si vede attraverso il riquadro di dialogo, e sembrava un
difetto di composizione. L'alfa dice il contrario: il corpo del riquadro
**piccolo** ha alfa media 19, cioè è vuoto, mentre quello **grande** sta a 214,
nero pieno. Il dialogo con un abitante sono due righe sottili e il testo sopra
il mondo; il pannello opaco è l'altra misura. *Prima di correggere una
trasparenza, misurarla: qui era il dato.*

### I nemici, e l'album che li dichiara tutti — [`entities.md`](entities.md)

Il TODO diceva di guardare i parametri delle celle `EnemyObserver` prima di
concludere che serve l'EBOOT. Quelle celle non portano nemici: 65 celle con un
`-gNNN` e basta, cioè **un numero di stanza**, e i cinque campi numerici sono
gli stessi di un `observer` qualsiasi.

Il censimento sta altrove ed è in chiaro. L'**album dei nemici**
(`UserInterface/EnemyView`) è un descrittore come gli altri e dichiara **46
nemici** con identificativo (5002–5082), modello, nome inglese, habitat e cosa
lasciano cadere. I modelli si risolvono **46 su 46**: 37 sono nodi dentro
`Character/c_obj_all.ps3.dsb` — la stessa forma degli NPC — e i 9 boss hanno un
file per uno. `view.py char c_enm_01` disegna un coniglio viola con le corna
rosse: ツノウサギ nel commento, `Killer Rabbit` nel descrittore.

I quindici habitat sono `FIELD_*` e `DUNGEON_*` per elemento, e i sette
sotterranei combaciano uno a uno con i sette templi di `Item.lua.eu`
(`DUNGEON_EARO` è *aero*, il vento). Quindi **quale nemico appartiene a quale
sotterraneo si sa senza l'EBOOT**; resta al codice solo quanti ne mette per
stanza e con che regola.

*(Corretto in sessione 8: non resta al codice. La griglia piazza i nemici cella
per cella, 10.196 in tutto, con la specie nel campo +0x10 e il set in `-sA`…
`-sH`. Vedi sopra.)*

Il primo tentativo è fallito e vale la pena dirlo: senza le **tabelle
permissive** il descrittore non gira, perché nomina costanti native (`LIVING`,
`GameDataFlags`, `item`) che nessuno script definisce — e la tabella sembra non
esserci. `ui.descriptor_file` ora carica `host.BOOT`, che quella soluzione la
aveva già.

### Gli oggetti di mappa dichiarano la stanza — [`walk.md`](walk.md), `Grid.rooms`

La forma della stringa divide le celle in due famiglie: `-gN;` da solo
(`SwitchObserver` 80, `EnemyObserver` 65) e `-gN;-oM;` in coppia. E dentro la
coppia, dove i due numeri sono **uguali** la cella si ritrova su un'altra mappa
— `WarpDoor` 29 su 29, `destructionWall` 43 su 46 — cioè quelli sono passaggi,
ed è perché `walkabout` li attraversava già.

**L'ipotesi scritta qui era sbagliata.** «Il `PitFall` ha una coppia come i
passaggi, quindi cadere è arrivare»: provata, la coppia si ritrova 2 volte su
21, e quella del `BlackHole` 3 su 7. Né il solo `-g` né il solo `-o` risolvono:
ricadono su venti celle per volta, cioè collezionano invece di indirizzare.

**Il numero è `(piano)(stanza)`**, e a dirlo sono due file che non si
conoscono: la prima cifra è il piano scritto nel **nome del file** (2.484
varchi su 2.490, 99,8%), e le stanze che ne escono sono quelle che i
descrittori `dungeonMapNN_MM` disegnano come `room_on_NN` — **404 su 413**, con
14 piani su 21 esatti.

Una bella lettura caduta lungo la strada: i sette buchi neri della torre oscura
stanno uno per piano e la prima cifra dei loro varchi va 1, 2, 3, 4, 5, 6, 7.
Sembravano i sette templi, e la torre che si apre sui sotterranei sarebbe stata
una spiegazione elegante. Nessuna di quelle coppie esiste nel sotterraneo che
la cifra nomina: **0 su 7**. La cifra era il piano su cui la cella sta.

### La mappa del sotterraneo si disegna — [`ui.md`](ui.md), `ui.py map`

Era in «cosa manca» come schermata con contenuto dinamico, che aspetta dati di
partita inesistenti. I dati sono arrivati dalla voce qui sopra: la griglia
dichiara la stanza di ogni cella, e la scena ha un pezzo per stanza e per
stato. `ui.py map 1 1 out.png --seen 1,2,3 --here 4` disegna il piano con le
stanze viste accese, quella corrente più chiara e le altre nere.

E il descrittore conferma la lettura delle stanze da un terzo file, nominando i
campi che nella griglia sono cifre mute: le porte dichiarano `groupId` e
`objectId`, che sono il `-g` e il `-o`, con `groupId=12` per il piano 1 stanza 2.

**I tre stati non sono tre disegni: sono un colore.** `room_on_02`,
`room_off_02` e `room_still_02` hanno la stessa mesh, la stessa posizione, le
stesse UV e la stessa texture, e a distinguerli è il `diffuse` del materiale —
1,0 / 0,5 / 0,0. Il difetto che questo ha scoperto è generale: il compositore
guardava la sola texture e buttava via il colore del materiale su **ogni**
schermata. Ora lo moltiplica — e il difetto era grosso, perché la tinta è il
modo in cui questa interfaccia dichiara gli stati: **49 scene su 115** hanno
nodi tinti, 1.869 in tutto, di cui **891 a 0,0** (spenti del tutto) e 864 a
0,5. Ottocentonovantuno pezzi che devono essere neri venivano disegnati a
piena luce.

### La mappa entra nel gioco, e tre strade che non portano da nessuna parte

`view.py play <mappa> --map`, o `M` mentre si cammina: la mappa del piano su cui
si sta, sopra la scena. Nel tempio del vento il selettore dei piani a sinistra
accende il terzo slot su cinque, che è il piano giusto — e lo fa da sé, perché
sta nella scena del descrittore.

Quello che **non** si può fare è dire in quale stanza si è, e non per pigrizia:

- «la stanza è uno schermo» — la scatola delle celle marcate sta in 16×12 nel
  95,4% dei casi, ma solo 305 stanze su 416 cadono in un blocco allineato;
- «il tag di regione è la stanza» — no: in `d_1_1_1` tutte e 23 le stanze
  portano lo stesso tag `2001`, che è il **sotterraneo**;
- «il marcatore più vicino» — le scatole non si sovrappongono (1,3%) ma coprono
  il 12% della mappa, e dove la risposta è certa il marcatore più vicino azzecca
  il **75,7%**: rumore con una preferenza.

Il quadro che ne esce è però coerente, ed è un risultato: gli osservatori sono
i **grilletti d'ingresso** con cui il motore registra in che stanza sei — per
questo sono radi e due su tre stanno dentro il solido invece che sul pavimento.
La regione non serve a nessuno tranne a noi, quindi non è dichiarata.

### Il formato `EDT`, il cuore identitario — [`format_edt.md`](format_edt.md)

`EDTFILE1.9`, i personaggi disegnati dot per dot. Risolto con lo stesso oracolo
di sempre: **90 file su 90 finiscono esattamente sull'ultimo byte**, per
260.860 voxel. Tutto big-endian e **senza allineamento** — un flusso di byte,
dove una stringa dispari sposta di uno tutto il resto.

Il voxel è 20 byte: posizione impacchettata più RGB più una finitura (0–6). E i
tre byte della posizione stanno **tutti fra 0 e 15**, cioè un cubo di
**16×16×16** — che è la griglia di `water_col.dds`, sedici dot per casella,
trovata in sessione 5 per tutt'altra ragione. Tre file che non si conoscono,
la stessa unità.

**Le sei parti sono sei pose.** I conti di `angel.edt` — 261, 256, 246, 240,
263, 267 — sono troppo vicini per essere sei pezzi di un corpo, e la misura
chiude: il **60,4%** dei voxel sta nella stessa posizione fra la prima parte e
le altre cinque. È il «i personaggi non hanno scheletro, i figli di un nodo
sono fotogrammi interi» di sessione 4, visto dall'altra parte.

La verifica è il provino a contatto: 90 personaggi riconoscibili — cavalieri,
maghi, Babbo Natale, un re con la corona, draghi, scheletri, un orso, una
zucca — e i preset tornano col proprio nome di file, `angel` con l'aureola e le
ali, `black_smith` con la barba bianca e il grembiule, `boxer` coi guantoni.

**E il primo provino usciva di spalle**, cosa che ha visto chi lo guardava
senza sapere cosa aspettarsi. Non era un difetto: prendendo la Z massima si
ottengono le nuche, prendendo la minima le facce — cioè i personaggi
dell'editor sono authorati **verso −Z**, la stessa convenzione che
`entities.md` aveva dedotto in un'altra sessione dalle mesh del gioco. Due file
scritti per scopi diversi, la stessa scelta. E si misura senza guardare: in
`black_smith.edt` il piano davanti porta 9 voxel e quello dietro 40, perché una
faccia è incavata e una nuca è piena.

Una sola cosa il primo percorso l'ha sbagliata, e si è corretta da sé: si
fermava 24 byte prima della fine. Ventiquattro è esattamente sei float — la
coda di parte, che c'è anche dopo l'ultima.

### Un'ipotesi caduta, che vale la pena tenere

I nodi `_PIVOT` sembravano dichiarare l'ancora della crescita, e il test
«per ogni pezzo a scala zero la mesh ha un bordo esattamente a 0 sull'asse
azzerato» dà l'**87,3%** — che sembra molto finché non si misura il controllo
sui pezzi a scala piena, che dà il **76%**. Non è un oracolo, è rumore con una
preferenza. E le eccezioni dicono perché: `NEW-node` di `EnemyAlbum` misura
`[-61,5, +61,5]`, cioè è **centrato** sull'origine e cresce dal centro.
L'ancora non è il bordo, è dove cade l'origine — che è solo come funziona una
scala, non una scoperta.

## Fatto in sessione 6

Le due voci in cima al TODO precedente, chiuse tutte e due — e la prima ha
aperto la seconda, che non era in programma per questa via.

### I 22 passaggi senza un arrivo calpestabile: erano zero letture sbagliate

Erano 19 arrivi non calpestabili più 3 passaggi la cui destinazione non esiste
sul disco. La domanda giusta si è rivelata la prima che si è posta: **c'è un
triangolo di collisione sopra quella cella?** Sì, in tutti e 19, e in diversi
casi che guardano pure in su. Quindi la collisione c'era e a mancarla era la
nostra lettura, in **tre** modi diversi — tutti e tre numeri assunti invece che
misurati:

- **la colonna era ancorata a zero.** 69 file di collisione su 171 scendono
  sotto, e il pavimento di `d_1_2` sta a `−0,000002`: uno zero appena negativo,
  lo scarto di un `float32` passato per una somma baricentrica. I 114 punti che
  cadevano nella cella d'ingresso del primo passaggio del gioco venivano
  buttati tutti e 114.
- **la colonna era alta 25,6 unità.** `FIELD_07` è una montagna e arriva a
  51,2: la cima veniva troncata.
- **la semina aveva un tetto di 96 suddivisioni**, che sembrava la scelta
  prudente. In `FIELD_07` 2.238 triangoli su 6.747 superano le 38,4 unità — il
  lato più lungo ne misura 190 — e per loro il passo diventava 2,0, cioè più
  largo di una casella: lasciava scoperte celle intere. Senza tetto costa il
  27% di punti in più su tutto il disco e non lascia buchi.

Ora base e altezza le dichiara la mesh, e i passaggi raggiunti con l'arrivo in
piedi sono **365 su 369**: i quattro che restano hanno la mappa di destinazione
assente dal disco.

### Il fondale, e il fatto che rimettere i piani giusti abbia peggiorato tutto

Rimessi i piani sotto lo zero, la misura è scesa dal 63% al 41%. Sotto ogni
mappa di campagna c'è un unico quadrilatero piatto steso da parte a parte — in
`FIELD_22` sono **due triangoli** per 10.368 caselle su 16.384 — a −3,2. Guarda
in su, quindi è un pavimento a tutti gli effetti; solo che sopra ha metri di
roccia, ed essendo il più basso è quello da cui la mappa comincia. `field_30`
scendeva a 84 celle percorse su 10.219.

A separarlo da un pavimento vero è un conto, non una soglia: le celle a due
piani sono **163.878**, e in **758** soltanto quello di sotto non è la quota
minima della mappa. Il ballatoio sopra la sala esiste ed è lo 0,16% del mondo;
tutto il resto della sovrapposizione è questo fondale.

Prima di arrivarci sono cadute due ipotesi plausibili, e vale la pena tenerle:
`LEVELS = 4` non c'entrava (quattro piani coprono il 100,00% delle celle), e il
criterio "sopra il fondale c'è dell'altro" va dal 30% all'83% senza uno stacco,
cioè è rumore con una preferenza.

### L'acqua, e il tag che la dichiara

Le celle in cui il fondale è l'**unico** piano non sono terra: sono il mare, il
fossato, la gola fra due altipiani. Sono **40.964**, e a quel punto la seconda
voce del TODO si risolve da sé, perché ora c'è con cosa mettere alla prova il
tag di regione:

```
88,4% delle celle d'acqua porta il tag 119
85,1% delle celle col tag 119 è acqua      (il tag è largo una cella in più)
```

Mappa per mappa, dove il `119` compare ne porta il 98–100%. Ed è un valore
**unico su tutto il disco**: l'ipotesi della sessione 5, che cambiasse per
gruppo di mappe, nasceva dal confondere l'**acqua** con il **vuoto** — le celle
senza nessuna collisione, 55.477, che sono lo scarto fra la regione
rettangolare dichiarata e la mappa vera, e che il tag infatti non dichiara (fra
loro il `119` è il 10%).

Quindi l'acqua si sa senza aprire il file di collisione, che è ciò che serviva
al renderer per sapere dove disegnarla.

### Una mappa si entra da tutte le sue porte

`field_14` ha sei celle `Exit`: la prima dà su un ripiano di 16 celle sotto una
rupe, le altre cinque sulle 3.213 che sono la mappa. La misura ne provava una e
scriveva 0%. Non è una taratura, è che prendere una porta sola misura la porta
invece della mappa.

E il quadro completo, che vale la pena tenere separato perché quattro cause
diverse si erano confuse in un numero solo:

| | celle | abitanti | passaggi | in piedi |
|---|---:|---:|---:|---:|
| geometria di rendering, gradino 0,6 | 18% | 65% | 194 | |
| collisione `.DPK`, gradino 0,6 | 25% | 78% | 202 | |
| collisione `.DPK`, gradino una casella | 63% | 96% | 303 | 281 |
| colonna misurata, fondale sepolto, tutte le porte | **67%** | **97%** | **369** | **365** |

### Si scende di una casella, e non è una scelta

La regola era simmetrica — un gradino in su, un gradino in giù — per non
camminare giù dai tetti, e la simmetria non era stata messa alla prova. Lo
stesso oracolo del gradino dice che va bene: lasciando scendere di più, gli
abitanti raggiunti restano **257 a qualunque discesa**, da una casella a nessun
limite. Scendere di più compra solo celle (+3,6%), cioè tetti e cornicioni.

Quindi le mappe che restano poco percorribili — `d_60_2`, `d_80_1`, `field_90`
— hanno isole vere, non una soglia sbagliata. Tre di loro, fra l'altro, **non
hanno nessun passaggio che punti a loro**: ci si entra per script
(`Event:SetMap("Field_90","-gtf3_1")`), e la porta che lo script nomina è
proprio quella da cui già si parte.

### Gli oggetti di mappa sono attori — [`walk.md`](walk.md), `Grid.objects`

La griglia dichiara **1.518 celle in 112 classi** oltre a passaggi e abitanti:
`observer` 163, `Observer` 149, `SwitchObserver` 80, `EnemyObserver` 65,
`destructionWall` 46, `up` 30, `WarpDoor` 29, `PitFall` 21, `BlackHole` 7,
`Barricade` 7.

La domanda utile era dove vivessero, e la risposta è **da nessuna parte**: il
muro rompibile è 0% disegnato e 0% solido, e così il buco nero e la porta. La
loro cella è pavimento liscio. Li istanzia il motore come attori — la
tassonomia è l'enum `ActorType` già estratto dal Lua, con
`AT_DESTRUCTION_WALL`, `AT_DOOR`, `AT_GIMM_GROUND_SWITCH` fra i 33 membri.

Da cui due cose che vanno tenute insieme: il giro di gioco **attraversa** i 45
muri rompibili (quindi il `walkabout` è un limite superiore, per quanto stretto
— e provare ad aprirli dà zero celle in più, perché erano già aperti), e gli
osservatori **non sono grilletti da pavimento**: due su tre stanno dentro il
solido, e solo il 31–41% delle loro celle è calpestabile.

Un filone piccolo di passaggio: 64 celle nominano uno script (`mainevent_*`,
`gimmick_*`), ma solo 3 nomi trovano il file — `mainevent_deserttemple1` sta in
`mainevent_201_deserttemple1.lua.eu`, cioè il numero non c'è nel nome della
cella. Gli altri 22 nomi non hanno uno script che si chiami così.

*(Corretto in sessione 8: si risolvono tutti e 25. Non sono file ma **funzioni**
dentro un file per elemento.)*

## Fatto in sessione 5

Le due voci in cima al TODO precedente, chiuse tutte e due. E poi due cose che
non erano in programma, che le ha chieste il camminare stesso: il formato della
collisione, e la scoperta che l'unico numero inventato del sistema era
sbagliato.

### Camminare nel mondo — [`walk.md`](walk.md), `tools/walk.py`

`view.py play <mappa>` — frecce per camminare, spazio per parlare, `K` per il
soffitto. Una cella per volta, e girarsi non è camminare.

- **Il muro.** Ogni cella tiene una colonna di 64 fette da un quarto di
  casella con la quota più alta trovata in ognuna, e fino a quattro **piani**
  distinti — il ballatoio sopra la sala è un posto, non un dislivello. Si passa
  se la colonna è libera fra +0,3 e +1,3 sopra i piedi; il piede si posa sulla
  superficie più alta entro un gradino, che è anche come si sale una scala
  senza sapere che è una scala.
- **Si sta in piedi solo su ciò che guarda in su.** È l'errore che questa parte
  è costata: un blocco pieno ha vertici *solo sulle sue facce*, quindi un
  pavimento alto 1,6 ne offre due, e la faccia di sotto sembra un pavimento con
  un metro e mezzo d'aria libera sopra. Si camminava dentro la roccia e la
  mappa si spezzava in isole. A separarle è la **normale** del vertice.
- **I passaggi, usati invece che contati.** Il varco ha due forme e servono
  tutte e due: a nome (`-gfrom_d_1`, aggancio su una cella `Exit`) e a numero
  (`-g11;-o101;`, aggancio sull'*identità* della cella d'arrivo, che è come
  sono fatte le scale). Con la sola prima forma si risolve il 46% invece del
  98%.
- **Il punto d'ingresso è una cella `Exit`**, non una cella qualsiasi con un
  `-g`: quelle sono centinaia — osservatori, gimmick — e partire dalla prima
  faceva cominciare la partita **in cima a un muro**.
- **Il soffitto si toglie sopra la testa del giocatore**, perché i sotterranei
  di questo gioco hanno il tetto e dall'alto sono una lastra.

E la misura, che è la cosa che resta:

```
python tools/view.py walkabout

167 mappe percorse in 62s, ingresso calpestabile in 167 su 167
celle raggiunte a piedi   221.227/352.278 = 63%
abitanti raggiunti            254/264     = 96%   (sotterranei 94%, campagna 99%)
passaggi raggiunti            303/512,  con l'arrivo in piedi 281
```

Il 63% delle celle non è un fallimento del 37%: il denominatore conta anche i
tetti e le cime dei muri, che infatti non si devono raggiungere. Il numero che
conta è quello degli abitanti.

### Le zone nere di un fotogramma sono acqua, e il disco lo dichiara

Guardando il fermo immagine dell'overworld: le grandi zone nere non erano un
difetto del render né geometria mancante — sono **acqua e vuoto**. Le celle
sotto quelle zone non hanno né geometria né collisione, e la `MAP_ALIGNMENT`
le distingue dandogli un identificativo di regione tutto loro (496 celle con
tag `119` in `Field_16`, e nessun'altra cella di quella mappa lo porta).

Da qui cade una voce aperta da due sessioni: **il 9% scoperto di `layout` era
il denominatore**. Contando solo le celle che il gioco considera solide, la
composizione delle mappe copre il **99,6%** invece del 90,7%; le altre 104.864
celle, il 22%, sono mare e fossati. `view.py layout` ora stampa tutti e due i
numeri.

*(Corretto in sessione 6: 99,3% e 96.062 celle, perché il denominatore delle
celle solide era a sua volta troncato sotto lo zero. E «mare e fossati» erano
due cose diverse messe insieme — vedi sopra.)*

L'acqua però resta da **disegnare**: il `.pac` non la contiene, e nessuna delle
sue 11 texture è acqua. La disegna il motore, e quello è lavoro di renderer.

### `MAPCOLLISION/*.DPK`, il muro vero — [`format_dpk.md`](format_dpk.md)

Non era in programma per questa sessione: l'ha chiesto il camminare, quando la
misura ha detto che approssimare la collisione con i vertici del disegno non
bastava. Risolto al primo tentativo, con lo stesso oracolo di `MAP_ALIGNMENT`:
una tabella di mesh, ognuna vertici e triangoli, e percorrendola si finisce
**esattamente** sull'ultimo byte in **171 file su 171** (301 mesh, 420.301
triangoli). Stesso sistema di riferimento del `.pac`, niente da convertire.

L'unico campo che non si indovina è il conto dei **float** invece dei vertici.
E c'è un refuso sul disco stampato: `DANGEON_8_2.DPK`.

### Il gradino vale una casella, e non era una taratura

L'unico numero inventato di tutto il sistema — «un ginocchio», 0,6 — sbagliato
di quasi tre volte. Due oracoli indipendenti dicono **1,6**:

- i dislivelli fra celle vicine calpestabili sono multipli esatti di 1,6
  (85,3% a zero, 8,6% a 1,60, 3,3% a 3,20, quasi niente in mezzo);
- gli **abitanti raggiunti** si saturano lì: 206/264 a 0,6, **255** a 1,7, 256 a
  2,5 e a 4,9. Una casella ne compra 49, tutto il resto uno.

Il guadagno complessivo, che vale la pena tenere separato perché due cause
diverse si erano confuse:

| | celle | abitanti | passaggi |
|---|---:|---:|---:|
| geometria di rendering, gradino 0,6 | 18% | 65% | 194 |
| collisione `.DPK`, gradino 0,6 | 25% | 78% | 202 |
| collisione `.DPK`, gradino una casella | **63%** | **96%** | **303** |

E il divario campagna/sotterranei **è sparito**: 63% e 63% di celle, con la
campagna al 99% di abitanti contro il 94% dei sotterranei. Quello che poche ore
prima era scritto come «due cause, la prima è geometria mancante» aveva una
causa sola, ed era la soglia inventata.

### I 199 posti di NPC senza un nome — [`walk.md`](walk.md), `entity.npc_directory()`

La mappa dichiara 236 identificativi e gli script di evento ne nominavano 37.
Gli altri li nomina il **loro** script: i 243 `npcevent_n<NN><archetipo><id>`
portano nel nome del file il modello e l'archetipo, e nel corpo il dialogo.

- **225 identificativi su 236 (95%)** hanno ora nome, faccia e battuta, e il
  nome è quello che gli script userebbero — quindi un evento che più tardi
  nomini quell'NPC trova *questo*, già al suo posto.
- Le **maiuscole** non le dice il nome del file (`Blacksmith` o `BlackSmith`?):
  le dicono i 151 script che si nominano per esteso al proprio interno.
- Sei archetipi in più con il modello dichiarato: `WiseMan1` → `c_npc_01`,
  `WiseMan2`…`WiseMan6` → `c_npc_20`…`c_npc_24`. Erano finiti fra le "comparse
  senza `npcevent`" perché il censimento guardava i nomi usati dagli **script di
  evento**, e i sei saggi parlano quasi solo attraverso il proprio.

## Fatto in sessione 4

Tre voci, tutte e tre in cima al TODO precedente, e **nessuna ha richiesto
l'EBOOT** come vi era scritto.

### Gli NPC di mappa e la tabella dei modelli — [`entities.md`](entities.md)
Le due voci in cima al TODO precedente, chiuse tutte e due, e **nessuna delle
due ha richiesto l'EBOOT** come era scritto.

- Le **posizioni**: fra le celle della griglia logica ce ne sono 271 la cui
  classe è il solo identificativo di un NPC (`a1_010`, `b8_010`), senza
  parametri. Il nome che usa lo script è archetipo più identificativo, quindi
  la coda del nome è la chiave — la stessa forma di aggancio del nome del gate
  per i passaggi. **72 nomi su 99 collocati**, erano 40.
- I **modelli**: i 237 script sotto `Event/npcevent_*` si chiamano
  `npcevent_n<NN><archetipo><id>`, e quel numero è l'indice di `c_npc_NN`.
  Biiezione perfetta — zero indici con due archetipi, zero archetipi con due
  indici — e verificata a occhio su sei modelli inequivocabili: Spelunker in
  salopette, la corona del re, la gallina, il cane. **66 nomi su 99 con il
  modello che il disco dichiara**, erano zero.

Il primo indizio era arrivato per caso: `c_npc_05` disegnato aveva l'aria di un
vecchio, e `n05` è `oldman`.

### La composizione delle mappe — [`format_pac.md`](format_pac.md)

`view.py screens()` + `layout`. Il nodo che teneva separati due pezzi
funzionanti, e insieme una **correzione**: fino a ieri le sezioni di un `.pac`
si credevano *cullings* già collocati, e si disegnavano tutte sovrapposte.

Sono **schermi da comporre**. La sezione `(c, r)` va messa al suo posto in una
griglia il cui passo è dichiarato dalla `MAP_ALIGNMENT` omonima: il rapporto
fra la griglia logica e quella del container è sempre un intero — 16 × 12 celle
per schermo nei sotterranei, 16 × 16 nell'overworld.

```
python tools/view.py layout

167 mappe verificate, celle di mappa coperte 436.043/480.731 = 90,7%
                      geometria fuori mappa   14.192/625.861 =  2,3%

sulle 82 mappe a più schermi:  composte 90,3%   accatastate 3,9%
```

L'oracolo è esterno al formato: la `MAP_ALIGNMENT` dice cella per cella dove
c'è mappa, ed è un altro file, con un altro scopo, nell'unico endianness
diverso del disco.

Da qui cade tutto il resto:

- **una cella logica vale 1,6**, cioè l'altezza di un personaggio: griglia
  logica, griglia degli schermi, modelli e argomenti degli script sono la
  stessa unità;
- gli script parlano in un riferimento con l'**origine a un angolo** (X
  positiva verso destra, Z negativa verso il basso), e `to_local()` lo porta su
  quello centrato del `.pac`;
- `SetPlayerPosition(cx, cy, piano)` colloca davvero il giocatore, e con lui
  gli NPC che nascono relativi a lui;
- la firma di `SetCamera` a sei argomenti **era sbagliata**: leggeva una
  distanza dove sta l'elevazione, e la distanza non c'è affatto. A dirlo è
  stato un segno — il secondo argomento scende a −17,72.

Ora `view.py <mappa> --event <script>` è la scena del gioco: la mappa intera,
i personaggi dove lo script li mette, l'inquadratura che lo script sceglie.
E ammettere un passo di schermo frazionario — `d_20_9` ha 3 schermi per 38
celle — porta la verifica da 163 mappe a **167 su 167**, 13.000 celle coperte
in più senza aumentare la geometria fuori mappa.

### Le entità — [`entities.md`](entities.md), `tools/entity.py`


**Le entità** — [`entities.md`](entities.md), `tools/entity.py`. La prima voce
del TODO precedente, chiusa. Il mondo ha dentro dei personaggi: posizione,
direzione, posa, movimento nel tempo. Ventidue metodi in più sull'host.

```
43 metodi implementati su 128 usati, che coprono 5.814 chiamate su 6.634 (87%)
                                              (erano 22 metodi e il 63%)
```

- Le **quattro direzioni** sono `0:+Z 1:−Z 2:−X 3:+X`, un'enumerazione ad assi
  accoppiati che nessuno avrebbe indovinato — 2 e 3 sono opposti fra loro, non
  consecutivi. L'hanno decisa due oracoli indipendenti che concordano: chi si
  gira e poi cammina cammina avanti (75% sulla cella più grossa), e Pizzaro e
  Rosy che si parlano da −1,6 e +1,6 in `mapevent_f80`.
- **Una casella vale 1,6, e un personaggio è alto una casella**: gli argomenti
  di `CreateNpc` sono multipli di 1,6, e i 31 modelli NPC misurano 1,60 esatti
  con l'origine ai piedi. Due file che non si conoscono, stessa scala.
- **I personaggi non hanno scheletro**: i figli di un nodo sono fotogrammi
  interi distanziati di 2,0 (162 su 200), non parti. Il gioco anima scambiando
  la mesh, come un gioco a sprite — e `SetNpcNode(nome, 0..3)`, che sceglie un
  figlio per ordinale, lo conferma per una via indipendente. Da qui anche il
  perché lo skinning stia in un file solo su tutto il disco.
- **`MoveNpc` non blocca**: a parità di velocità e di attesa le distanze
  percorse sono 1,6 — 3,2 — 4,8, cioè l'attesa che segue non cronometra niente.
- Due modalità nuove del visualizzatore: `view.py char <modello>` per guardare
  in faccia un personaggio con le sue pose in fila, e `view.py event <script>`
  per eseguire un evento **su un palco vuoto, senza mappa**. La seconda è nata
  da un ostacolo reale: le mappe di questo gioco sono piene e hanno il
  soffitto, gli NPC finivano dentro un muro e non si vedeva se il registro
  funzionasse.

Due cose che i dati hanno smentito lungo la strada, e che vale la pena
ricordare perché erano tutte e due plausibili:

- «l'NPC appena creato guarda il giocatore» dà **il 55%**, cioè rumore con una
  preferenza, e propone come miglior candidato una mappatura sbagliata;
- `Event/Priest/Priest.ps3.dsb` esiste e si chiama come un nome di `CreateNpc`,
  ma misura 0,96 × 0,64 e usa `cliff_01.dds`: è la *scenografia* dell'evento,
  non il prete. La coincidenza di nome sarebbe passata per una risoluzione
  riuscita se non si fossero guardati i numeri.

E una cosa che resta **dichiaratamente irrisolta**, invece che indovinata: dove
cada nel mondo una cella di `SetPlayerPosition`. La X sta a ~1,6 unità per
cella su 31 eventi, la Z cambia di un fattore dieci — perché ogni mappa ha la
propria origine. Quindi il registro annota la cella e non muove nessuno, e dei
99 nomi del corpus ne colloca 40 (quelli di `CreateNpc`, che sono offset dal
giocatore) e disegna solo quelli.

## Fatto in sessione 3

Le due voci in cima al TODO precedente, chiuse entrambe.

**Fase 1a, l'estrattore ufficiale** — [`extract.md`](extract.md),
`tools/iso.py`. `extract/` non è più stato locale: è una funzione del disco,
con manifesto e hash. 2.799 file indicizzati, 2.793 dichiarati per 3,1 GB,
`sha256` di tutti in 26 secondi, verifica completa in 30.

- Si legge via **UDF**, non ISO9660: i nomi ISO9660 sono troncati a 31 caratteri
  e in questo gioco i nomi *sono dati* (il materiale riferisce la texture per
  nome di file). La verifica l'ha dimostrato subito, segnalando come mancanti
  167 `.pac.gz` che in locale portavano il nome troncato di 7-Zip.
- Il lettore UDF è scritto a mano perché `pycdlib` rifiuta il disco: i Blu-ray
  PS3 usano UDF 2.50 con **partizione di metadati**, e gli inode stanno dentro
  un file che ricopre la partizione fisica. ~150 righe, nessuna dipendenza.
- Il **manifesto** (`tools/manifest.tsv`, `path · size · sha256`) è l'impronta
  del disco supportato: hash, non contenuto, quindi sta nel repository.
- Due ritrovamenti dell'inventario: `MakeLuaDump.exe` e
  `AdditionEditCharMessage.exe`, utility Windows degli sviluppatori rimaste sul
  disco stampato, e `Font.bin`.

**Il primo render** — [`render.md`](render.md), `tools/view.py`. Una mappa
caricata, composta e disegnata texturizzata in OpenGL 3.3. `d_1_1_1` esce al
primo tentativo; `field_16` è riconoscibilmente la campagna del gioco.

E la misura, non l'aneddoto: `view.py sweep` carica **tutto** il disegnabile del
disco — 627 file, 5.297 sezioni, **54.176.753 vertici**, 30,9 M triangoli in
**14 secondi** — e risolve 1.903 riferimenti a texture su 1.905. I due mancanti
sono residui di produzione (`SouthPeak_Logo.ifl` è un *Image File List* di
3ds Max: dice con che strumenti sono stati fatti gli asset).

Tre cose imparate guardando:

- il **colore per vertice è illuminazione precotta** — verde muschio con gli
  spigoli a nero — il che conferma per una via indipendente che l'ordine dei
  canali è RGBA, e avverte l'host di non moltiplicare due volte ciò che è già
  cotto;
- le mappe **includono il soffitto**: un sotterraneo dall'alto è una lastra;
- decodificare i vertici con numpy invece che con un dizionario per vertice fa
  la differenza fra 14 secondi e inservibile.

**Lo skinning, risolto.** Mancavano 50.043 vertici su 54 milioni — lo 0,09% —
e non era un errore di conteggio: erano le 77 mesh di `Opening.ps3.dsb` che
nessun nodo aggancia direttamente. Un nodo può agganciare uno **`skin`**, che
nomina la mesh a +0x20 e porta un array di ossi (indice di nodo + **bind pose
inversa**) a +0x60. Vedi [`format_dsb.md`](format_dsb.md) §skin.

Sono cadute insieme altre due voci del TODO precedente: la **semantica 9** del
vertice è l'**indice di osso**, e lo skinning è **rigido** — c'è l'indice ma
nessun peso. La convenzione delle matrici l'ha decisa un oracolo netto:
`world(osso) @ Mᵀ` viene identica per tutti gli ossi di una skin, cioè è la
posa di binding; le altre tre combinazioni no.

E una trappola da ricordare: con la trasformazione del *nodo* la scena di
apertura sembra un villaggio 3D con qualche pezzo fuori posto, cioè "quasi
giusta". Con le matrici degli ossi si **appiattisce**, e sembra un errore. Non
lo è: la catena passa per `oka_s-node` (scala Y 0,04) e `Dummy_2D_pos-node` —
l'apertura è un fondale **2D visto dall'alto**. Il risultato quasi giusto era
il più ingannevole dei due.

**Il post-processing YEBIS** — `tools/post.py`, documentato in
[`render.md`](render.md). I quattro effetti che il fornitore nomina sono
quattro passate: defocus per cerchio di confusione, glare additivo dal bright
pass, vignetting, color modification. I parametri vengono dalle **202 chiamate**
DOF contate negli script (`SetParamDepthofField`: primo argomento 0,37–3,02,
secondo 0,20–1,50, terzo sempre 0; `SetDofApaerture` sta a 0,70 in 14 casi su
20). Resta ignota l'unità di misura di quei numeri: non sono distanze di mondo,
e la risposta sta nell'EBOOT.

Scoperta di passaggio: `createFairyGlareEffect(38.27, 2.68, -23.2)` non prende
parametri di effetto, prende una **posizione nel mondo**.

Con la catena attiva `field_16` smette di sembrare un modello 3D e comincia a
sembrare un plastico.

**Il primo dialogo** — [`host.md`](host.md), `tools/host.py` + `tools/font.py`.
La milestone che valida la tesi del progetto: mappa dal `.pac`, script
`Devil.lua.eu` eseguito **verbatim** su VM Lua (`lupa`, Lua 5.5), scheduler a
coroutine, e la battuta a schermo col font del gioco.

```
377 script di evento su 378 girano, 377 arrivano in fondo, 0 errori
128 metodi distinti, 6.634 chiamate — 20 metodi fanno il 76% delle chiamate
```

Perché ci arrivino servono due cose non ovvie: **caricare le librerie
condivise** (`Event/eventfunction.lua.eu` definisce le funzioni Lua che gli
eventi chiamano, ed è il package manager a caricarle prima), e **stub
chiamabili**, perché una tabella permissiva che non risponde a `__call` uccide
lo script alla prima funzione sconosciuta.

**22 metodi implementati su 128 usati, che coprono il 63% delle chiamate** — i
primi dieci tutti, 12 dei primi venti. Oltre a dialogo e scelte ci sono ora
**camera** e **messa a fuoco**, che la misura indicava come il vero grosso di un
evento: `SetCameraAtBody(distanza, elevazione°, azimut°, bersaglio)` inquadra,
`SetParamDepthofField` e `SetDofApaerture` pilotano la catena YEBIS, e le due
pile `BackupCamera`/`RestoreCamera` e `BackupDof`/`RestoreDof` lasciano la
scena com'era.

Le firme le hanno rivelate gli autori senza volerlo: due helper in
`eventfunction.lua.eu` sono commentati "camera NPC da destra" e "da sinistra",
e fra i due cambia **solo il segno del terzo argomento**. Quindi il terzo è un
azimut, e i primi due distanza ed elevazione.

Tre condizioni di sospensione bastano all'intero corpus: `Wait`,
`WaitContinue`, `WaitScene`. I globali nativi (`EventClass`, `soundList`) non
li definisce nessuno script — li forniva il C++ — e qui diventano tabelle
permissive che ricordano il proprio nome: `soundList.SoundID.SE_quake` vale la
sua stringa, che è quanto basta per girare e per registrare cosa serve.

Due scoperte di passaggio: il corpus ha **codifiche miste** (13 script in
Shift-JIS fra 365 UTF-8), e nell'atlante del font **non esiste il trattino** —
il gioco scrive `ＴｈーＴｈａｔ` con il prolungamento dei katakana.

### L'acqua si disegna — [`render.md`](render.md), `view.py water_parts()`

La texture c'era, e stava dove aveva senso che stesse: **`data/shaders/water_col.dds`**,
uno dei due soli `.dds` sciolti del disco insieme a `Sun.dds`. Stare in
`shaders/` invece che in un pacchetto di mappa è la dichiarazione che non
appartiene a nessuna mappa: la disegna il motore.

È 128×128 non compressa, un reticolo blu notte di **16 quadretti per lato** —
cioè i sedici dot di una casella, quindi si posa una copia per cella e il
reticolo si allinea da solo.

La quota non è dichiarata da nessuna parte, ma il mondo la stringe da tutte e
due le parti: il fondale sta due caselle esatte sotto la riva (52,9%) e la riva
sta a 0,00 (50%), quindi in mezzo c'è **un solo multiplo di una casella**. Ogni
specchio prende la sua propagando il minimo dalle rive, così in `Field_16` il
lago di montagna resta a +11,2 mentre il mare sta a −2,0.

```
celle di mappa coperte dalla geometria: 436.043/480.731 = 90,7%
  di cui acqua, ora disegnata:           40.964 celle
  restano nere in un fotogramma:          8.503 celle = 1,8% della mappa
```

`Field_16` è un'isola nel mare e `Field_31` un arcipelago; prima erano isole
nel nulla. Il nero che resta è vuoto vero — celle senza geometria *e* senza
fondale — e non è più una zona ma dei buchi.

Trovata di passaggio nella stessa cartella: `graphics.ps3.tpk` contiene
`ref_01`, che è un **CUBEMAP**, cioè l'environment map che `renderer.md` dà per
mancante.

### Le schermate di sistema si compongono — [`ui.md`](ui.md), `tools/ui.py`

I 137 descrittori UI erano letti da tre sessioni e mai eseguiti. Ora **119
schermate** si compongono: la scena al suo posto, le scritte dove il descrittore
le mette, il cursore dove dice lui.

Due misure hanno reso possibile comporre invece di rasterizzare:

- **lo schermo virtuale è uno solo.** Che i descrittori parlassero in 1280×720
  era noto; che ci vivessero anche le **scene 3D** no. La dissolvenza a piena
  pagina misura `x [0, 1280]`, `y [-720, 0]` al decimale, e la Z non è
  profondità ma il piano di sovrapposizione (−90 la dissolvenza, 0 il fronte).
- **l'interfaccia è fatta di rettangoli**: dei 16.494 triangoli delle 115 scene,
  16.492 sono piatti in Z e **16.494 su 16.494** hanno due lati sugli assi.

E la ragione per cui in tre sessioni nessuno le aveva eseguite: **a riposo sono
chiuse**. Il nodo di ogni pezzo di `SelectA` ha scala **0** su un asse mentre la
mesh sotto è intera (149×99), e le schermate a scorrimento parcheggiano i pezzi
fuori campo — il menu degli oggetti arriva a `x=2193`. Ad aprirle è
l'`Animation` che il descrittore dichiara; il `.dsb` non ha curve, quindi il
moto lo mette il motore e la posa finale è la scala a 1 (`view.load(unfold=True)`).

## Da fare subito

### I gimmick, con la stessa domanda dei nemici
La voce sul pattugliamento è **chiusa in sessione 11** e non con una lettura:
gira, vedi sopra e [`actor.md`](actor.md). Ma la scoperta che l'ha aperta
travolge anche la seconda metà della voce di sessione 8, che dava i gimmick per
«parametrizzati in chiaro, implementati in C++». In `../lua/Object/gimmick/`
ce ne sono **21 scritti per esteso** — `Jar`, `Grass`, `SwordPedestal`,
`SpringFairy`, i sei `OrbAltar`, i sette `BossMarker`, i tre `Well`,
`lava_fountain` — e la griglia dichiara dove stanno. Stessa forma: un
`Initialize`, un `Update`, e l'infrastruttura ora c'è tutta (`actor.Troupe`).

L'aggancio però **non è più il modello**: un vaso non carica `EN_ENEMY_NN`, e
la cella lo nomina per classe (`Jar` sta fra le classi di `Grid.objects`).
Quindi la prima domanda è come si lega la classe di cella al file, e la
risposta più probabile è il nome stesso.

Nella stessa cartella restano da guardare i **100 file `Object/item/`** e i
**266 `Object/npc/`**, che non sono i 33 già usati (quelli stanno in
`Object/`): sono probabilmente le istanze per personaggio, non gli archetipi.

### L'animazione dichiarata, che adesso serve
`AddAnimation(i, secondi)` e `InitializeAnimation` sono 185 chiamate ed erano
fuori dal moto, quindi non urgenti. Ora lo sono: **è così che il Re fermo
respira**, e più in generale è il ciclo di pose dichiarato dal file invece che
dedotto dai suffissi `_a`/`_b`. Sostituirebbe con un dato ciò che
`entity.enemy_motion` ricava da dodici file di minigioco.

### Cosa resta scoperto dei nemici
Misurato, non congetturato: 98 metodi su 134, cioè il 27,3% delle chiamate,
quasi tutti fuori dal moto — animazione, colore, suono, effetti, e il
**combattimento** (`IsHitGuardPlayer`, `GetPlayerHP`, `Throw`), che è un
sottosistema che il progetto non ha ancora, non un buco in questo.

Due punti del moto sono dichiarati non letti, ed è bene restino visibili: il
flag di `Move(false)` (17 chiamate, sempre `false`, significato non scritto da
nessuna parte) e la curva di `Fly`, dove gli script passano una gravità che qui
diventa un avvicinamento lineare alla quota.

*(Le tre code di sessione 8 sono chiuse in sessione 10; le due di sessione 10
in sessione 11: 5080 è Togetoge e la classe è il verso del movimento, `+0x08` è
una coppia di byte con `b1 >= b0` sempre. Vedi sopra.)*

### Cosa misura l'intervallo di `+0x08`
La sola coda ancora aperta di quel filone, e adesso è una domanda precisa:
`(b1, b0)` con `b1 >= b0` in 482.180 celle su 482.180, valori da 0 a 31, e
`+0x0C = 1 << b0`. Concorda con la quota del pavimento all'84% nei sotterranei
e al 68% in campagna, satura a 31 nella mappa più alta del disco, e **non** è
limitato dal tetto per mappa di `map_param.lua`. Da riprendere dal Lua, ora che
sappiamo che 869 sorgenti sono in chiaro: se qualcuno legge quella griglia,
la legge lì.

### Cosa succede quando si sceglie una voce
`Screen` dice *quale* voce si è scelta, non cosa fa il gioco dopo. Il legame
fra una schermata e la successiva è dichiarato **due volte su 136** (sessione
9), e sempre e solo per aprire una finestra di conferma. Per le altre 134 non
c'è, e stavolta è stato cercato: nessun valore che nomini un'altra schermata, e
l'unica chiave che si chiami `Next` è uno scarto di 49 px fra due cifre.
**L'unico posto rimasto è l'EBOOT**, e questa è la seconda voce che ci finisce
contro dopo il pattugliamento.

## Da fare poi

- **`SAV`**: i tre salvataggi. Nessun magic, ma la stessa coppia
  `u32 len + UTF-8` degli `.edt`, e `test.SAV` porta dentro
  `edt/preset/pumpkin.edt` — quindi riferisce un preset per percorso invece di
  incorporarlo. (L'`EDT` è chiuso, vedi sessione 7.)
- **Le due utility sul disco**: `MakeLuaDump.exe` (9,5 kB) e
  `AdditionEditCharMessage.exe` (14,5 kB). PE x86 minuscoli; dal nome, il primo
  fa il lavoro di `tools/lua_tables.py` e può confermarne la semantica a costo
  quasi nullo.
- **Semantica 8**, il secondo set di UV che accompagna gli indici di osso.
- **Campi minori del record `skin`**: i puntatori a +0x24 / +0x2C, che puntano
  dentro il record stesso, e i contatori a +0x28 / +0x3C.
- **Campi di materiale ancora senza nome**: i 43 identificativi di shader
  (+0x28), un secondo colore a +0xC4, la coppia `(0.2, 0.8)` a +0xD4 che ha la
  forma di bias/scala di Fresnel, i bitfield di stato a +0x164/+0x168, e i tag
  della tabella di binding.
- **Fase 1d**: clustering dei 497 metodi per dominio. Nota: `host.py coverage`
  fornisce ora il dato che serviva davvero — non quanti metodi esistono, ma
  quanto sono chiamati. 106 dei 497 bastano a coprire tutti gli eventi.
- **I 41 script di evento non conversazionali**: 1 su 378 non arriva in fondo,
  vale la pena guardare perché.

## Quando servirà l'EBOOT (Fase 3)

Non è ancora stato toccato, e in sessione 11 una delle due voci che ci
puntavano contro **se n'è andata**: il pattugliamento dei nemici è in chiaro,
in `all.lua.eu`, e a mancare era la nostra ricerca. Ne resta una —

- **il seguito di una schermata** (sessione 9): 2 legami dichiarati su 136.

*E la morale è la solita, alla quarta volta: prima di dichiarare che una cosa
non c'è, contare in quanti posti la si è cercata. Qui erano tre, e il quarto
era il file più grosso del disco.*

e poi, come prima:

- semantica dei metodi di scripting ambigui (497 metodi, firme inferite ma non
  confermate);
- valori numerici degli **11 enum nativi** — servono per leggere salvataggi
  originali, non per far girare il gioco;
- conferma dell'ipotesi **OROCHI di Silicon Studio** come motore di base — il
  post-processing è invece già identificato come **YEBIS**, vedi RECON §6.7;
- uso effettivo delle SPU.

`EBOOT.BIN` è un SELF con `key_revision 0x0001` (2010, chiavi retail
pubbliche), decrittabile offline verso un ELF PPC64 big-endian; ora è estratto
(`iso.py extract boot`). Nota utile: i file `DSBF` sono immagini di memoria
scritte con `memcpy` di struct C++, quindi **le stesse struct saranno
riconoscibili in Ghidra** e daranno i nomi dei campi finora dedotti.

## Metodo che ha funzionato

Vale la pena ripeterlo, perché ha risolto cinque formati di fila: **usare come
test i vincoli che il formato stesso fornisce**, invece di congetturare.

- `TPKG`: DXT3 contro DXT5 deciso guardando il canale alfa decodificato nei due
  modi — l'interpretazione sbagliata produce bande orizzontali regolari.
- `DSBF` vertice: la somma delle dimensioni dichiarate deve dare *esattamente*
  lo stride, che il chunk dichiara per un'altra strada (`vb_size / n_vert`).
  Due campi indipendenti che devono coincidere: 8.707 su 8.707.
- `DSBF` posizioni: devono **riempire** il bounding box del record, non solo
  starci dentro. E la scena composta deve riempire quello dell'header — che
  mette alla prova gerarchia, quaternioni e scale in un colpo solo.
- `MAP_ALIGNMENT`: in un formato a **record di lunghezza variabile**, percorrere
  il file fino in fondo è l'oracolo migliore che esista — se il layout è giusto
  si finisce *esattamente* sull'ultimo byte dopo il numero di record atteso.
  170 file su 170.
- **UDF**: la catena dei descrittori dice sempre dove sta la cosa successiva.
  Non c'era niente da indovinare, solo da seguire — e chi indovina si ferma sul
  File Set Descriptor, come fa `pycdlib`.

Corollari, pagati sul campo:

- Quando un test dà **0% in tutte le interpretazioni**, di solito non significa
  "ipotesi sbagliata" ma "stai leggendo i dati nel posto sbagliato".
- Quando un riferimento non si risolve e i valori "sconosciuti" sono **piccoli
  e ordinati**, non è un hash: è un indice. Vale per la gerarchia dei nodi e
  vale per l'indice di mesh dentro il record `skin`.
- Quando il dato ha una **proprietà attesa a priori** — un grafo di mappe si
  percorre nei due sensi — quella proprietà misura la qualità dell'estrazione.
- **Un residuo dello 0,09% è un'informazione, non rumore.** I 50.043 vertici che
  mancavano all'appello non erano un errore di conteggio: erano l'intero
  sottosistema di skinning, che si è aperto solo perché il totale non tornava.
  Far quadrare i conti *esattamente* è ciò che rende visibile il resto.
- **Prima di rimandare all'EBOOT, guardare i nomi dei file.** La tabella
  archetipo → modello era in cima al TODO come "la prima cosa da chiedere a
  Ghidra". Stava nei nomi dei 237 script `npcevent_n<NN><archetipo><id>`, cioè
  in chiaro, in una directory già estratta. Vale come corollario di una regola
  che il progetto ha già: *cercare il campo che dichiara il layout*. Anche un
  nome di file è un campo.
- **Quando una conclusione è già scritta nei documenti, il test va rifatto lo
  stesso.** Che le sezioni di un `.pac` fossero già collocate era documentato,
  argomentato con tre osservazioni e confermato dall'immagine. Era falso, e per
  23 volte. Le tre osservazioni erano tutte *vere*: a essere sbagliata era
  l'inferenza dal fatto alla causa — il 79% di vertici identici fra sezioni
  vicine è ciò che si ottiene quando un sotterraneo è fatto di blocchi
  ripetuti e ogni schermo è disegnato attorno alla propria origine.
- **Il test buono viene da un file che non c'entra.** La composizione delle
  mappe non si poteva verificare dentro il `.pac`: qualunque lettura è
  autoconsistente. L'ha decisa la `MAP_ALIGNMENT`, che è un altro file, con un
  altro scopo, scritto nell'unico endianness diverso del disco, e che dichiara
  per altre ragioni dove c'è mappa e dove no.
- **Un segno è un oracolo.** La firma di `SetCamera` a sei argomenti è caduta
  su un dettaglio: il secondo argomento vale −17,72 in una chiamata, e una
  distanza negativa non esiste. Non serviva altro per sapere che quella
  lettura era sbagliata, e che al suo posto stava un'elevazione.
- **Due oracoli deboli che concordano valgono più di uno forte.** Le quattro
  direzioni le ha decise l'incontro fra una statistica meccanica (chi si gira e
  poi cammina) e una lettura a mano di un dialogo. Presi da soli, il primo dava
  75% su una cella e nulla sulle altre, il secondo era un aneddoto. Insieme non
  lasciano scampo, perché sbagliano in modi diversi.
- **Un oracolo al 55% non è "quasi giusto", è rumore con una preferenza.**
  "L'NPC guarda il giocatore" sembrava una premessa ovvia e proponeva con
  sicurezza una mappatura sbagliata. La soglia non è "meglio del caso": è
  "abbastanza netto da non poter essere altro".
- **Una coincidenza di nome non è una risoluzione.** `Event/Priest/Priest.ps3.dsb`
  esiste, si chiama come un NPC, e non è quell'NPC. A dirlo non è stato il
  nome ma la misura: 0,64 di altezza dove un personaggio ne fa 1,60.
- **Il risultato "quasi giusto" è il più pericoloso.** Le mesh skinnate disegnate
  con la trasformazione del nodo davano un villaggio 3D plausibile con qualche
  pezzo fuori posto — un errore che si sarebbe archiviato come dettaglio. La
  lettura corretta appiattisce la scena, e *sembra* sbagliata. A decidere non è
  stato l'occhio ma il determinante della matrice, che rimandava a due nodi
  della catena chiamati `oka_s` (scala Y 0,04) e `Dummy_2D_pos`. Quando
  un'immagine convince e i numeri no, hanno ragione i numeri.

- **Un avanzo che è un multiplo esatto di una struttura nota dice dove sta
  l'errore.** Il primo percorso dell'`EDT` si fermava 24 byte prima della fine,
  e 24 è esattamente sei float, cioè una coda di parte. Non serviva cercare:
  bastava riconoscere il numero. *Quando il conto non torna, guardare di quanto
  non torna prima di guardare dove.*
- **Quello che serve solo a noi non è dichiarato.** Dove una stanza cominci e
  finisca non sta sul disco, e tre strade indipendenti lo confermano (lo
  schermo al 95% ma non allineato, il tag che è il sotterraneo, il marcatore
  più vicino al 75,7%). Non è un dato mancante: al motore la regione non serve,
  perché a registrare l'ingresso in una stanza gli basta un **grilletto** — ed
  è per questo che gli osservatori sono radi e due su tre stanno dentro il
  solido invece che sul pavimento. *Prima di cercare a lungo un dato, chiedersi
  se il gioco ne avesse bisogno.*
- **Quando due cose che dovrebbero differire escono identiche, il campo che le
  distingue è uno che non stai leggendo.** Le tre stanze `room_on_02`,
  `room_off_02` e `room_still_02` uscivano pixel per pixel uguali, e sembrava
  un filtro rotto. Il filtro funzionava: le tre hanno la stessa mesh, la stessa
  posizione, le stesse UV e la stessa texture, e a distinguerle è il `diffuse`
  del materiale — 1,0 / 0,5 / 0,0. *Una differenza di zero esatto non è un bug
  del confronto: è la dichiarazione che stai guardando nel posto sbagliato.*
  È il gemello del corollario di sessione 6 — un dato che sembra vuoto può
  essere solo chiuso — preso per l'altro verso: un pezzo che sembra acceso può
  essere solo spento.
- **Un disegno bello va verificato più di uno brutto.** I sette buchi neri
  della torre oscura, uno per piano, con la prima cifra del varco che fa
  1-2-3-4-5-6-7: sembrava evidente che nominassero i sette templi, ed è la cosa
  che *un progettista avrebbe fatto*. Zero su sette. Era il numero del piano
  su cui la cella sta — la spiegazione noiosa, che poi si è misurata al 99,8%
  su 2.490 celle. *Quando una lettura è elegante e racconta bene il gioco, è
  proprio lì che conviene chiedere il conto.*
- **Un risultato riconoscibile può essere riconoscibile e sbagliato.** Il primo
  provino degli `EDT` mostrava novanta personaggi tutti identificabili, e la
  verifica sembrava passata: erano tutti **di spalle**. A vederlo è stato chi
  guardava senza sapere cosa aspettarsi, e il difetto era una scelta mai fatta
  — quale delle due Z sia il davanti. *Che una cosa sia riconoscibile dice che
  la catena regge, non che ogni convenzione dentro sia quella giusta; e le
  convenzioni non scelte non danno errore, danno un risultato specchiato.*
  La correzione ha poi fruttato una proprietà misurabile (9 voxel davanti
  contro 40 dietro) e una terza conferma del «authorati verso −Z».
- **Chi non sa cosa dovrebbe vedere è un oracolo indipendente.** Il modello
  `c_enm_01_01` è stato mostrato a chi non conosceva né il nome né lo stato
  della catena che lo disegna, e la prima parola è stata «coniglio». Il
  descrittore lo chiama `Killer Rabbit` e il commento giapponese ツノウサギ,
  coniglio cornuto. Vale perché **sbaglia in un modo diverso** dalle verifiche
  numeriche: quelle dicono che i byte tornano, questa dice che la cosa
  *significa* quello che dovrebbe. E vale perché era cieca — guardando la
  stessa immagine sapendo già la risposta si vede un coniglio in qualunque
  cosa, che è esattamente come il render «quasi giusto» dello skinning era
  passato per buono. *Quando una catena lunga produce qualcosa di
  riconoscibile, farlo riconoscere a chi non sa cosa aspettarsi.*
- **Una coincidenza di nome non è una risoluzione, anche quando è la nostra.**
  `data/Balloon` stava nel TODO come «l'originale del riquadro di dialogo», ed
  è il cartello `CHECK`/`TALK`/`OPEN` che galleggia sopra la testa: 1,6 × 0,6
  **unità di mondo**, non pixel. È lo stesso errore di `Priest.ps3.dsb`, ma
  commesso da noi e poi scritto nei documenti — dove ha aspettato tre sessioni.
  A smentirlo è bastato guardare l'unità di misura. *Le voci del TODO non sono
  risultati verificati: vanno messe alla prova come tutto il resto.*
- **Un campo che non varia mai non è il campo che il suo nome dice.** `Start`
  si leggeva come l'inizio della clip sulla linea del tempo, e vale 0 in tutte
  e 36 le `In`, 1 in tutte e 33 le `Main`, 2 in tutte e 36 le `Out`. Un tempo
  determinato dal nome non è un tempo: è un indice. *La prima cosa da chiedere
  a un campo numerico è quanto vari; se è costante per classe, il nome sta
  mentendo.*
- **Due estremi mancanti non sono lo stesso problema di uno.** «Manca
  l'animazione» era una voce sola e conteneva due cose: l'apertura, di cui il
  disco ha la posa chiusa (scala 0), quella aperta (la mesh intera) e la durata
  — quindi si ricostruisce senza inventare nulla; e lo scorrimento, di cui ha
  solo il parcheggio. Interpolare richiede due estremi, e separarli riduce la
  domanda per l'EBOOT da «l'animazione delle schermate» a «dove atterrano 15
  pezzi in 5 schermate».
- **Un buco nei dati può essere un buco nel percorritore.** Gli indici di
  `Option` saltavano da 9 a 20, e sembrava che il disco non dichiarasse dieci
  clip. Le dichiarava: `Volume` è un **array** invece che un dizionario, e chi
  scende solo nei dizionari lo salta. Che il buco fosse largo esattamente
  quanto i dieci nodi `Volume00…Volume09` della scena era l'indizio, ed era
  visibile prima di trovare la causa. *Un buco di dimensione sospettosamente
  significativa va cercato prima nel proprio lettore che nel dato.*
- **Un controllo va misurato insieme all'oracolo, non dopo.** «Il pivot mette
  il bordo di crescita sull'origine» dava l'87,3%, che sembra un risultato. Il
  76% dello stesso test sui pezzi a scala piena dice che non lo è. Senza il
  controllo sarebbe entrato nei documenti come una lettura del formato, e non
  era altro che il modo in cui funziona una scala.
- **Un dato che sembra vuoto può essere solo chiuso.** Le schermate di sistema
  si componevano nere, e sembrava un difetto di lettura delle texture o delle
  UV. La geometria era tutta lì: a nasconderla era uno **zero in una scala**, e
  la posa a riposo di un'interfaccia è la posa chiusa. Prima di cercare cosa
  manca, guardare se quel che c'è è a volume zero.
- **Dove un file *non* sta è un'informazione quanto il suo contenuto.** La
  texture dell'acqua non è in nessun pacchetto di mappa e in nessuno di
  personaggio: è sciolta in `data/shaders/`, insieme al sole. Quella cartella
  dice «questo lo disegna il motore», ed è la stessa cosa che dicevano il
  `destructionWall` assente dal `.pac` e il fondale assente dal disegno. Vale
  la pena guardare *dove* stanno le cose prima di chiedersi cosa contengano.
- **Se una cosa dichiarata non sta in nessuno dei file che descrivono il mondo,
  non è un difetto di lettura.** Il `destructionWall` non è nel `.pac` e non è
  nel `.DPK`: 0% e 0%. Cercarlo meglio sarebbe stato sprecato, perché
  l'assenza *era* l'informazione — quel muro lo costruisce il motore a runtime,
  e infatti il Lua ha `AT_DESTRUCTION_WALL` fra i 33 tipi di attore. La stessa
  forma di ragionamento che aveva già dato lo skinning, ma al contrario: là un
  residuo dello 0,09% era un sottosistema, qui uno zero pulito è una
  dichiarazione di architettura.
- **Un esperimento che dà zero va raccontato lo stesso.** Aprire tutti i muri
  rompibili non guadagna **una cella** su 78 mappe, e sapere che il mondo dietro
  di loro era già raggiungibile vale quanto un guadagno: dice che quel 33% non
  raggiunto sta altrove.
- **Una regola simmetrica per prudenza va provata come le altre.** Salire e
  scendere di una casella era una sola scelta, fatta per non camminare giù dai
  tetti. Provata a parte, la discesa satura subito: 257 abitanti da una casella
  a nessun limite. La prudenza era giusta, ma adesso è un risultato.
- **Un limite prudente è un numero inventato come gli altri.** Il tetto di 96
  suddivisioni della semina era stato messo per non far esplodere la memoria, e
  sembrava la scelta cauta. Su un terzo dei triangoli di `FIELD_07` rendeva il
  passo più largo di una casella, cioè faceva esattamente il danno che la semina
  serviva a evitare. Toglierlo costa il 27%. *Un tetto messo per prudenza va
  misurato contro la cosa che deve garantire, non contro la paura che lo ha
  suggerito.*
- **Aggiustare una lettura sbagliata può peggiorare la misura, e non vuol dire
  che l'aggiustamento fosse sbagliato.** Rimettere i piani sotto lo zero ha
  portato le celle raggiunte dal 63% al 41%. Il primo istinto — tornare
  indietro — avrebbe rimesso a posto il numero e lasciato il difetto. Quello che
  era successo è che il piano recuperato era il **fondale**, e scoprirlo ha poi
  dato in regalo la maschera dell'acqua. *Una correzione giusta può scoprire un
  secondo difetto che la prima nascondeva; la misura scende perché adesso
  guarda una cosa vera in più.*
- **Prima di scegliere fra due spiegazioni, contarle.** «Il fondale ha terra
  sopra» sembrava il criterio ovvio per riconoscerlo: va dal 30% all'83% senza
  uno stacco, cioè non è un criterio. Il conto che invece decide è un altro e
  banale — le celle a due piani sono 163.878 e in 758 soltanto quello di sotto
  non è la quota minima — e dice pure una cosa sul mondo: il ballatoio sopra la
  sala esiste, ed è lo 0,16% del gioco.
- **Un ingresso solo misura l'ingresso, non la mappa.** `field_14` ha sei porte
  e la prima dà su un ripiano di 16 celle sotto una rupe. Quando un dato
  dichiara più punti d'accesso, provarne uno e riportare la percentuale è un
  errore di misura travestito da risultato — e si riconosce perché la
  distribuzione ha una coda di mappe allo 0-3% invece di degradare piano.
- **Due nomi vicini per due cose diverse fanno concludere il falso.** «Acqua e
  vuoto» era una sola voce, e da lì veniva l'idea che il tag di regione
  cambiasse per gruppo di mappe. Separate — l'acqua è dove il fondale è l'unica
  superficie, il vuoto è dove non c'è collisione affatto — l'acqua ha un tag
  unico su tutto il disco (`119`, 88%) e il vuoto non ne ha nessuno, perché non
  è una cosa che qualcuno dichiari.
- **Un numero inventato sopravvive finché nessuno lo mette alla prova.** Di
  tutto il sistema del camminare, un solo valore non veniva dai dati: il
  gradino, «un ginocchio», 0,6. Ed era l'unico sbagliato — di quasi tre volte.
  Ha prodotto un sintomo che sembrava tutt'altro (mappe spezzate in isole, e la
  campagna molto peggio dei sotterranei) e una diagnosi plausibile e falsa
  («manca la geometria»). Quando una misura è bassa, il primo sospettato è il
  parametro che non ha una fonte.
- **Il quanto prima della taratura.** Il gradino non andava tarato ma
  riconosciuto: i dislivelli sono multipli esatti di una casella, e fra 1,7 e
  2,5 non cambia un solo numero. Se una soglia ha un intervallo piatto largo
  quanto il passo della quantizzazione, quella soglia non è una scelta.
- **Un secondo oracolo che satura vale più di una distribuzione.** Che i
  dislivelli siano multipli di 1,6 dice come è fatto il mondo, non cosa il
  giocatore può salire. A deciderlo è stato un oracolo di natura diversa: gli
  **abitanti** che la mappa dichiara sono posti in cui il gioco deve poter
  arrivare, e il loro conto si satura esattamente a una casella.
- **La geometria dichiara superfici, non volumi.** Dedurre il solido dai
  vertici funziona solo guardando da che parte sono girati: un blocco pieno ha
  vertici solo sulle sue facce, e la faccia di sotto di un pavimento sembra un
  pavimento con l'aria libera sopra. Contandole tutte e due si cammina dentro
  la roccia, e il sintomo — mappe spezzate in isole — sembra un problema di
  soglie. Non lo era: era una normale.
- **Un elenco "di quelli che non ce l'hanno" invecchia con il censimento che
  l'ha prodotto.** I sei `WiseMan` erano nella lista delle comparse senza
  modello dichiarato perché quel censimento partiva dai nomi usati dagli script
  di *evento*, e i saggi parlano quasi solo attraverso il proprio. Quando
  cambia la fonte, la lista dei mancanti va rifatta, non ereditata.
- **Prima di scegliere un punto di partenza, guardare di che classe è.**
  `arrivals` conteneva ogni cella con un `-g` — centinaia di osservatori e
  gimmick — e partire dalla prima faceva cominciare la partita in cima a un
  muro, con due celle raggiungibili. Il punto d'ingresso ha un nome nel dato:
  `Exit`.
- **Un host che misura vale più di un host che si ferma.** Ogni metodo non
  implementato viene contato invece che sollevare un errore, e ogni globale
  nativo mancante diventa una tabella che ricorda il proprio nome. Così
  l'ordine di implementazione non va indovinato: si legge.
- **Ma la misura va rifatta dopo ogni implementazione.** È stata sbagliata due
  volte di fila, in due modi diversi. Primo: un errore Lua terminava la
  coroutine, e la coroutine terminata era il criterio con cui contavo le
  conclusioni — gli errori contavano come successi, e "376 su 378" era in
  realtà 89. Secondo: `Select` risultava terzo con mille chiamate, perché uno
  script che ripete la scelta finché non ottiene risposta gira a vuoto se
  `Select` non risponde, e ogni giro conta; implementato, ne fa 56 ed è
  venticinquesimo. **La misura dell'uso di un'API è distorta proprio dai pezzi
  che non hai ancora costruito.**

- **Cercare una cosa e non trovarla è un risultato, se si è cercato in tutti i
  posti.** Il pattugliamento dei nemici non è in `MapParameter`, non è in
  `GameParamData`, e l'API Lua per i nemici ha solo `PlayEnemy`, `PauseEnemy`,
  `visibleEnemy` — congelare e mostrare, mai muovere. Detto così, «non c'è»
  smette di essere una rinuncia e diventa la ragione per cui la prossima mossa
  è una **decisione** (inventarlo dichiarandolo) invece che una ricerca.
- **Il file aperto per la ragione sbagliata paga lo stesso.** `MapParameter`
  è stato aperto per cercarci il moto dei nemici, che non c'è, e dichiara i
  nomi di 211 mappe — un dato che il giro di gioco aspettava da otto sessioni
  senza che nessuno lo cercasse, perché nessuno sapeva di volerlo.
- **Un surrogato va rimisurato quando arriva il dato vero.** `LivingId` era
  «dove vive un nemico» finché il piazzamento non si sapeva leggere. Ora si
  legge, e il confronto dà il 47%: l'habitat è una classificazione, non una
  collocazione. *Il surrogato non diventa falso quando arriva il dato: si
  scopre che non era la stessa cosa, e va riscritto ciò che si era dedotto da
  lui.*
- **Un modo secondario di un gioco può essere l'unico posto in cui il modo
  principale è scritto in chiaro.** I nemici del mondo sono C++, ma dodici di
  loro esistono anche come attori Lua del minigioco, con le pose, il periodo e
  il tipo di moto. Non è una copia: riusano i modelli **per numero**, e i nomi
  lo confermano dodici volte su dodici. *Quando il pezzo principale è compilato,
  guardare se un pezzo secondario lo riusa — la modalità di contorno, l'editor,
  il minigioco, il tutorial.*
- **Una costante nostra sopravvive finché un file non la nomina.** Il periodo
  del ciclo di camminata valeva 0,25 perché usciva da un `int(walk * 4) % 2`
  scritto per avere due passi al secondo: nessuno l'aveva scelto, e nessuno
  l'aveva messo in dubbio. Il disco lo dichiara dodici volte e vale 0,3. È il
  gemello del gradino di sessione 5, ma più insidioso, perché 0,25 non
  produceva **nessun** sintomo.
- **Una generalizzazione dal caso comune si smaschera contando i casi.**
  `02_a`/`02_b` era il ciclo di camminata "di tutti", perché tutti i 31 NPC ce
  l'hanno. Fra i 37 nemici **dodici no** — quattro usano `04`, otto non hanno
  paia — e per quel terzo il codice chiedeva una posa inesistente, senza
  errore: cadeva sul primo fotogramma e il nemico restava fermo. *Prima di
  scrivere una costante presa dal caso che si ha davanti, contare su quale
  popolazione l'hai vista.*
- **Un'ipotesi diventa smentibile solo quando arriva il dato che la misura, e
  allora va misurata subito.** «I nemici senza pavimento sono i volanti» era
  stata scritta come motivazione di una scelta di implementazione, e sembrava
  ovvia. Il minigioco ha portato il campo `Type`, e il conto dice 2,3% contro
  4,0%, cioè semmai il contrario. *Una motivazione plausibile scritta in un
  commento è un'ipotesi non verificata che si traveste da spiegazione.*
- **Una fonte esterna sbaglia in un modo tutto suo, ed è per questo che vale.**
  Un walkthrough è scritto per giocare, non per leggere byte: non sa niente dei
  nostri campi e non può confermarci per compiacenza. Quattro letture dedotte
  dai soli byte vi si sono ritrovate senza essere cercate — i set di
  piazzamento, il profilo di FROM Mode, i due nemici senza habitat, gli otto
  boss con il loro tempio. È la stessa forma di prova del «coniglio» di
  sessione 7 — chi non sa cosa dovrebbe vedere è un oracolo indipendente —
  ma su una scala che un'immagine sola non raggiunge. *Quando una lettura
  riguarda ciò che il giocatore vive, esiste già una letteratura che la
  descrive dall'altra parte dello schermo.*
- **Un campo "ignoto" può essere il campo che tiene insieme tutto il resto.**
  Il +0x10 della cella era marcato `?` da cinque sessioni mentre tre censimenti
  — oggetti di mappa, nemici, NPC — venivano tenuti separati perché sembravano
  tre problemi. Erano una numerazione sola. *Prima di aprire un fronte nuovo,
  contare quanti campi già letti sono ancora senza nome: un `?` in una struttura
  che si percorre tutta non è un buco, è lavoro non fatto.*
- **Un nome che non trova il suo file può essere una funzione.** «22 nomi su 25
  non hanno uno script che si chiami così» stava nel TODO come un risultato
  negativo, e la ricerca cercava file. `gimmick_grass4` è una funzione dentro
  `gimmick_grass.lua.eu`, e cercate come funzioni si risolvono 25 su 25. È il
  gemello del corollario «anche un nome di file è un campo»: *anche un nome di
  funzione lo è, e il livello a cui un dato nomina qualcosa va scelto invece
  che assunto.*
- **Due sottoinsiemi equinumerosi che non si toccano mai sono lo stesso
  insieme.** `A`, `B`, `C` hanno le stesse specie, quasi gli stessi conteggi, e
  zero celle in comune su tutto il disco. Preso da solo ognuno di quei fatti si
  spiega in molti modi; insieme ne lasciano uno. E la misura che li chiude è
  quella *geometrica*: se fossero squadre le loro scatole sarebbero piccole e
  separate, e invece sono l'88% della stessa.
- **Il caso irregolare va tenuto, non normalizzato.** `F`, `G`, `H` rompono il
  parallelismo di `A`, `B`, `C` — più celle, più specie, conteggi diversi — e
  la tentazione era leggerli come una seconda terna uguale. È la rottura a
  identificarli: quella asimmetria *è* la descrizione di FROM Mode.

E la morale più generale: prima di dedurre un layout, **cercare il campo che lo
dichiara**. Vale anche per gli script: `Font.lua.eu` dichiara il font intero, e
la VM lo legge meglio di qualsiasi parser scritto da noi.

## Ambiente

- `extract/` si ricostruisce con `python tools/iso.py extract` e si verifica con
  `verify --deep`. Estratti: tutti i set tranne `audio` (326 WAV, 638 MB) e
  `movie` (5 Bink, 1,2 GB), che non servono ancora — `iso.py extract audio movie`
  quando serviranno. Escluso da git per la politica BYOA; il manifesto no.
- Residuo da ripulire: in `data/map/pac_data` ci sono ancora i 167 `*_PAC.GZ`
  con i nomi troncati della vecchia estrazione 7-Zip, 441 MB inutili. I `.pac.gz`
  corretti sono accanto.
- 7-Zip esce con **codice 2** e `Headers Error` su questa ISO: è benigno, è la
  region table in coda. Ma estrae con i nomi ISO9660: usare `iso.py`.
- Disponibili: Python 3.14 con Pillow, numpy, **pyglet** (OpenGL 3.3) e
  **lupa** (VM Lua 5.5, installata in sessione 3 — è la dipendenza della Fase
  4), più 7-Zip, ffmpeg, ImageMagick.
- Strumenti: `iso.py` estrazione, `tpk.py` texture, `dsb.py` scene, `mapdat.py`
  grafo del mondo, `dpk.py` collisione, `view.py` + `post.py` render,
  `font.py` font, `edt.py` personaggi voxel, `host.py` VM Lua e scheduler,
  `entity.py` registro delle
  entità, `walk.py` il giro di gioco.
- `docs/walkthrough/` è una guida di GameFAQs salvata in locale (7 pagine,
  325 kB di testo estratto in `walkthrough.txt`). Serve come **oracolo
  esterno**: descrive dall'altra parte dello schermo le stesse cose che noi
  deduciamo dai byte. Non sta in git — è materiale di terzi.
- Le verifiche che si eseguono da sole: `python tools/entity.py` (49 proprietà,
  col bestiario e gli identificativi di attore),
  `python tools/walk.py` (31 proprietà, su tutte le 170 griglie, coi nemici
  piazzati e i grilletti di evento),
  `python tools/view.py sweep ../extract` (54.176.753 vertici, 1.903 texture su
  1.905), `python tools/view.py layout` (99,3% delle celle solide, 1,8% ancora nero),
  `python tools/view.py walkabout` (167 mappe percorse a piedi, 97% degli
  abitanti raggiunti, 365 passaggi su 369 con l'arrivo in piedi),
  `python tools/dpk.py check` (171 file su 171),
  `python tools/edt.py check` (6 proprietà, 90 file, 260.860 voxel),
  `python tools/ui.py check` (14 proprietà, 119 schermate),
  `python tools/host.py coverage ../extract/PS3_GAME/USRDIR/data/Event` (87%).
- `docs/lua_signatures.*` e `docs/lua_tables.*` sono in `.gitignore`: contengono
  dialoghi e tabelle del gioco. Si rigenerano dai tool in pochi secondi.
