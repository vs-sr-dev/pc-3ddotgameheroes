# I nemici, eseguiti dagli script del disco — `tools/actor.py`

*Sessione 11.* Il compagno di [`host.md`](host.md) per un secondo dominio: là
gli eventi, qui gli attori. La tesi è la stessa, e stavolta è più difficile da
credere prima di vederla — **il moto dei nemici di 3D Dot Game Heroes è scritto
in Lua, sul disco, e si può eseguire**.

## Quello che il TODO ha detto per tre sessioni

> Il pattugliamento non è dichiarato in chiaro da nessuna parte, e resta non
> implementato invece che inventato.

Era vero dei posti in cui era stato cercato — `MapParameter`, `GameParamData`,
l'API Lua, i dodici attori del minigioco Block Defence — e falso del disco. Il
moto sta in `all.lua.eu`, che **non è un file**: è la concatenazione di
**1.486 sorgenti**, con l'albero delle cartelle lasciato nei commenti.

> *Corretto in sessione 12: erano dati per 869, che è il conto dei soli
> `../lua/`. Sotto ci sono altri ventotto alberi — `Event/`, `MiniGame/`,
> `UserInterface/` — cioè quasi tutti i file di dati del disco, nello stesso
> flusso. Cercare il confine di un sorgente solo fra i `../lua/` fa
> inghiottire a sette di loro le 185 che li seguono; nessuno dei sette è un
> file di nemico, quindi le misure qui sotto non cambiano, ma il conto sì.*

```
-- Start ../lua/Object/06Bee.lua.eu
```

Sotto `../lua/Object/` ci sono 55 file di nemico, 266 di NPC, 21 di gimmick,
100 di oggetto. Quarantasei chiamano `setBookRegistInfo`, cioè si registrano
nel bestiario, ed è **esattamente il numero di voci dell'album**; 37 portano il
comportamento per esteso, e i 9 che restano sono gli otto boss più Guardian,
che in Lua hanno la sola inizializzazione.

*Perché non lo si era visto: la ricerca era stata fatta in tre posti e non nel
quarto, che è il file più grosso del disco — e fino alla sessione 9 quel file
tornava indietro stroppiato, perché è uno dei 21 con i commenti in Shift-JIS.*

## Com'è fatto un nemico

Due funzioni globali, una macchina a stati esplicita, la fase in un campo
dell'attore e i tempi in slot numerati:

```lua
function BeeUpdate(Object)
    if(Object:GetPhase()==0 and Object:IsTimeZero()) then
        Object:SetPhase(1);
        CommonRandomDirection(Object,WallDistance);
        if( Object:IsActorMoveArea( MoveArea ) ) then
            Object:SetDirectionToInit();
        end
    end
```

e `MoveArea` è un `local` del file, con il commento degli autori:

```lua
local MoveArea = 10.0;   -- 出現位置からの行動可能範囲
```

*il raggio d'azione dal punto di comparsa*. **Il pattugliamento è quello**:
vaga a caso, e quando esce dal raggio torna verso il punto in cui è nato. Non
c'era niente da inventare.

## Cosa fa il modulo

`Troupe` carica la VM una volta sola — 3,7 MB e 869 sorgenti in un decimo di
secondo — e dà a ogni nemico piazzato da `walk.populate_enemies` il proprio
`Actor`, che è l'oggetto che il Lua riceve come `Object`. Ogni fotogramma
chiama la sua `Update`.

```
53 metodi implementati su 161 chiesti,  che coprono 4.225/5.335 chiamate = 79,2%
```

*(Il conto è cresciuto in sessione 12 con la correzione del confine dei
sorgenti, e in sessione 13 con `AddAnimation` e `InitializeAnimation` — due
metodi soli, sette punti, perché sono i più chiesti del corpus.)*

Sono quelli di fase, tempo, moto e percezione, scritti contro la griglia e le
colonne che il progetto ha già: un nemico non ha una collisione propria nel
dato, quindi si ferma ai muri passando dallo stesso codice del giocatore.
Tutti gli altri **si contano invece di fallire**, che è il criterio di
`host.py` e il modo di misurare quanto manca senza inventare.

### Tre decisioni che valeva la pena prendere bene

**In Lua `0` è vero.** Solo `nil` e `false` sono falsi, quindi rispondere zero
a un predicato non implementato vorrebbe dire che ogni `if
Object:IsQualcosa()` prende il ramo affermativo: un nemico che crede sempre di
vedere il giocatore e di avere un muro davanti. Sarebbe un comportamento
inventato da noi. A dare la risposta giusta è la convenzione di nome del
**codice originale**, regolare su tutti e 55 i file: `Is…` è un predicato e
risponde «no», `Get…` risponde zero, il resto è un comando e restituisce un
oggetto a cui si possono chiedere altri metodi — perché gli script incatenano,
`local club = Object:SetChildObject(…); club:setVisible(false)`.

**`GetPosition` deve restituire un riferimento vivo.** Gli script assegnano
dentro il valore che torna:

```lua
Object:GetPosition().y = Object:GetFloor()*1.6 + 4.0*1.6;
```

e quel `1.6` è `entity.TILE`, il lato della casella — la scala del mondo
confermata da un altro file ancora.

**Le chiusure vanno memoizzate.** Un solo nemico chiede `GetPhase` una decina
di volte per fotogramma: crearne una nuova ogni volta significa consegnare al
Lua decine di migliaia di oggetti Python temporanei al secondo che nessuno
tiene vivi, e il sintomo — attori che cadono dopo un centinaio di fotogrammi,
mai da soli, mai nello stesso punto — non somigliava affatto alla causa.

## Le misure

Cinque mappe, cinque secondi di vita ciascuna, in [`walk.py`](../tools/walk.py):

```
312 attori su 312 nemici piazzati trovano il proprio comportamento
  0 script caduti
  0 nemici usciti dal calpestabile muovendosi
261 su 312 si muovono da soli
```

Il 12% che sta su una cella senza pavimento c'era **già alla partenza**: sono i
546 che la sessione 10 ha misurato sbordare di una cella dentro il muro. Chi
parte sul pavimento non lo lascia mai.

E i 51 che non si muovono non sono un difetto: sono in attesa per ragioni
proprie, e fra loro ci sono tutti i Togetoge, che la prima riga della loro
`Update` congela finché il giocatore non entra nella stanza —
`if( not Object:IsPlayerArea() ) then return; end`.

## La prova che chiude il cerchio

La sessione 11 aveva letto la classe delle celle 5080 come **asse di
movimento**, e lo aveva dedotto dal commento del file più la geometria del
piazzamento. Eseguendo gli script, la stessa cosa si misura dall'altro capo:

```
Togetoge classe 1 (orizzontale)   spostamento  X 2,3   Z 0,0
Togetoge classe 0 (verticale)     spostamento  X 0,0   Z 29,2
```

Una lettura statica del dato e una dinamica del codice che si confermano a
vicenda, e nessuna delle due sa dell'altra.

## E gli abitanti, che sono la stessa cosa

Nella stessa cartella ci sono **33 file di NPC**, `N01WiseMan1` … `N31Spelunker`,
e l'aggancio è di nuovo il nodo che caricano — con una piega che vale la pena
notare, perché mostra due mani sullo stesso disco: i modelli 02–08 scrivono
`NP_NPC05_01`, l'01 e tutti quelli da 09 in su `NP_NPC_09_01`. Il numero però
non sbaglia mai: **il numero nel nome del file e quello del nodo coincidono 33
volte su 33**, che è la terza conferma indipendente della tabella
archetipo→modello dedotta in sessione 4 dai nomi dei 237 script `npcevent_`.

> **Sessione 12.** La frase regge, e va letta stretta: coincide il numero del
> *file* con quello della *costante* `NP_NPC_NN`. Da costante a **modello** c'è
> un passo in più, e lo dichiara la tavola dei nodi — dove due voci sono
> scambiate, `NP_NPC_19` ↔ `NP_NPC_26`. Vedi [`objects.md`](objects.md).

`OldManUpdate` è il gironzolare dei villaggi, per intero:

```lua
Object:SetRandomDirection();
Object:SetSpeed(1.6);      -- una casella al secondo
Object:SetDistance(6.4);   -- quattro caselle, poi si ricomincia
```

```
la corte del castello: 33 abitanti, 32 con il proprio script, 22 gironzolano
0 errori   0 usciti dal pavimento
```

**Dieci file non hanno affatto una `Update`**, e non è una lacuna: sono
`N10King`, i sei saggi, `N28LegendHeroGhost`, `N29MedalKing`, `N30LegendHero`.
Il disco dichiara l'immobilità con un'assenza, e la categoria è esattamente
quella giusta — un re sul trono e un saggio in fondo a un tempio aspettano, non
passeggiano. Fra i 55 file di nemico non ne manca nemmeno una.

Fermi ma non immobili, però: `KingInitialize` carica le due pose del passo e
le alterna ogni mezzo secondo con `AddAnimation(0,0.5)`, `AddAnimation(1,0.5)`.
È il motivo per cui `AddAnimation` viene chiamata anche da chi non si muove.

**Una cosa che nessuno dichiara**, e va detto: la direzione iniziale. Non sta
negli script — nessuno dei dieci fermi chiama `SetDirection` o `setAngle` — e
non sta nella griglia, dove le celle che nominano un NPC non portano un solo
flag. Il `facing = 1` con cui li mettiamo giù resta **una nostra scelta**.

Ma non è una scelta cieca, e la differenza vale: **il piazzamento la implica**.
Chi non si muove sta sempre più in alto della porta da cui si entra —

```
personaggi immobili al chiuso: 11,  con la porta più vicina più in basso: 11
d_20_1  il Re a y=11, la porta a y=36, sei cortigiani schierati in mezzo
```

— quindi gli si cammina incontro, e guardare verso il basso della griglia vuol
dire guardare chi arriva. È la convenzione che chiunque abbia giocato a un
gioco di questo genere si aspetta (si entra nella sala del trono da sud e il re
guarda a sud), e qui non è ripresa dal genere: è misurata sul piazzamento, 11
casi su 11. Resta un'inferenza — il dato dice dove stanno, non dove guardano —
ma è un'inferenza con un oracolo, che è cosa diversa da un'abitudine.

L'unica eccezione del disco è un saggio in campagna aperta (`field_8`), dove
«la porta più vicina» non è l'ingresso di una sala e la domanda non si pone.

## Cosa manca

I 98 metodi non implementati sono il 27,3% delle chiamate, e sono quasi tutti
fuori dal moto: animazione (`AddAnimation`, `InitializeAnimation`), colore
(`AddColor` — vedi qui sotto: sono **i frammenti**, e senza distruzione non c'è
niente da implementare), suono
(`PlaySE`), effetti
(`CreateEffect`, `createWarpEffect`),
combattimento (`IsHitGuardPlayer`, `GetPlayerHP`, `Throw`) e la registrazione
nel bestiario. Il combattimento in particolare è un sottosistema che il
progetto non ha ancora, non un buco in questo.

Il moto non è coperto in due punti soli, e sono dichiarati qui perché non si
leggono: il flag di `Move(false)` — 17 chiamate, sempre `false`, significato
non dichiarato da nessuna parte — e la curva di `Fly`, dove gli script passano
una gravità che qui diventa un avvicinamento lineare alla quota di volo.

## Il ciclo di pose è dichiarato — `AddAnimation`

Era «il metodo più chiesto che manca»: **916 chiamate in 192 moduli**. Ora
gira, e con `InitializeAnimation` porta la copertura dal 71,8% al **79,2%**
delle chiamate — due metodi, sette punti, perché sono i più chiesti di tutti.

`AddAnimation(i, wait)` aggiunge al ciclo **il nodo `i`**, mostrato per `wait`
secondi. Che il primo argomento sia un indice nell'ordine di `AddNode` non è
una scelta di lettura, è l'unica che il corpus permette:

```
file in cui l'indice massimo di AddAnimation e' < numero di AddNode   314/314
```

Zero eccezioni. E il secondo argomento è un'attesa, come dice il nome che gli
script gli danno — `AnimationWait`, `DashAnimationWait`, `patapataSpeed`
(パタパタ, lo sbattere delle ali). Vale `0.5` in 702 chiamate su 916.

**Non sta nella `Initialize`**, e questo è il difetto in cui si cade: sta nella
`Update`, al cambio di stato. `06Bee` rifà il proprio `1, 2` ogni volta che
passa da fermo a volo, quindi il ciclo va riportato nell'entità dopo ogni
fotogramma. E siccome solo 63 moduli su 192 chiamano `InitializeAnimation`, la
lista si allungherebbe all'infinito: si tiene il **periodo**, che è
indistinguibile a vedersi e non cresce.

### Conferma quel che si deduceva, e corregge dieci nemici

Su 25 nemici che dichiarano un ciclo, **15 dicono esattamente `02_a`/`02_b`**,
cioè la regola dedotta in sessione 4 dalla sola geometria dei nodi. Gli altri
dieci no, e sono i casi che il progetto non poteva indovinare:

| modello | riposo | ciclo | passo |
|---|---|---|---|
| `c_enm_06` | `01` | `04_a`, `04_b` | 0,15 s |
| `c_enm_12`, `13` | `06` | `02_a`, `01`, `02_b`, `01` | 0,22 s |
| `c_enm_23`, `24` | `01` | `02`, `01` | 0,25 s |
| `c_enm_16` | `02_a` | `02_b`, `06` | 0,25 s |
| `c_enm_35` | `01` | `01`, `06` | 0,25 s |

I goblin camminano a **quattro tempi** — passo, fermo, passo opposto, fermo —
che dai suffissi non si legge in nessun modo. E `c_enm_23`/`24` sono fra gli
otto modelli che la sessione 8 aveva contato **senza nessuna coppia `_a`/`_b`**:
restavano fermi perché il ciclo lo cercavamo nei nomi, e invece è scritto.

Anche il passo smette di essere un numero nostro: era `0.25` (o `0.3` per i
dodici del minigioco), e adesso ogni nemico ha il proprio, da 0,12 a 0,25.

*I 12 che non dichiarano niente tengono il ripiego di prima, che è la regola
dedotta: dove il disco tace non si cambia idea.*

## `AddColor` sono i frammenti, e lo scrivono gli autori

La domanda stava nel TODO da due sessioni, con l'ipotesi giusta e nessuna
prova. La prova è un commento, in tre punti del corpus:

```lua
Object:SetAmount( 4 );                  -- 壊れた時の破片の量
Object:AddColor( 0.38, 0.26, 0.00 );    -- 破片の色
```

*La quantità di frammenti quando si rompe*, e *il colore dei frammenti*. Sono
in Shift-JIS dentro un file UTF-8, come le 21 note che fino alla sessione 9
rendevano illeggibile quasi tutto ciò che `all.lua.eu` conteneva — e infatti
qui erano restate mute.

**Il dato regge la lettura senza eccezioni**: `AddColor` è **sempre al più
`SetAmount`**, 71 file su 71. Non si dichiarano più colori che frammenti. E
`SetAmount` vale **4 in 52 file su 78**: una cosa che si rompe in quattro
pezzi.

Da cui si spiega, invece di restare una stranezza, la misura della sessione 12
— *«i 132 colori dichiarati sono già quelli dei vertici del proprio modello, a
mezzo grado di tinta»*. Certo che lo sono: **i frammenti di una cosa hanno il
colore della cosa.** Quella misura non diceva che `AddColor` è inutile, diceva
che i suoi colori vengono da lì.

E cade anche l'argomento con cui la sessione 12 aveva escluso l'ipotesi «uno
per nodo»: che `12GoblinRed` dichiari due volte lo stesso colore non esclude
niente, perché in una tavolozza di quattro frammenti un colore ripetuto è
semplicemente **un colore che pesa doppio**.

### I boss non si rompono, e i loro colori sono per parte

Gli otto boss non chiamano `SetAmount`, ed è la ragione per cui il TODO li
aveva isolati. `B01Snake` mostra cosa fanno invece:

```lua
Boss:AddColor     (0.62, 0.63, 0.43);   -- 頭      la testa
Boss:AddBodyColor (0.62, 0.63, 0.43);   -- 体      il corpo
Boss:AddTailColor (0.62, 0.63, 0.43);   -- 尻尾    la coda
```

Tre metodi paralleli per le tre parti di un serpente, tre colori ciascuno. E
che anche lì si tratti di frammenti lo dice `B02BeeChild`, che usa lo stesso
`Boss:AddColor` con il commento `-- 破片の色`: il boss si rompe **per parti**,
e ogni parte ha la sua tavolozza.
