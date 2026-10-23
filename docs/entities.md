# Le entità — `tools/entity.py`

**Stato: risolto.** 72 nomi su 99 collocati, 66 su 99 con il modello che il
disco dichiara. Quello che resta sono comparse di eventi principali e oggetti
di scena, che non passano dal meccanismo degli NPC di mappa.

Il livello che mancava fra lo script e il disegno. Prima:
`SetCameraAtBody` sapeva inquadrare un NPC ma non c'era nessun NPC da
inquadrare; [`view.py`](../tools/view.py) sapeva disegnare un personaggio, ma
come file, non come qualcosa che *sta in un posto*.

Ventidue metodi dell'API chiedevano tutti la stessa cosa, e insieme fanno
**1.664 chiamate, il 25% del corpus**. Erano la voce più grossa che restava.

```
python tools/view.py event extract/.../Event/mapevent/mapevent_d08_02.lua.eu --skip 40

8 entita in scena:
  <player @player (0.0, 0.0, 0.0) dir 1 c_ply_01>
  <npc PriestSP (0.0, 0.0, -9.6) dir 0 c_npc_05>
  <npc YoungWomana4_010 (1.6, 0.0, -1.6) dir 0 c_npc_27>
  ...
```

## Le quattro direzioni

Gli script girano i personaggi con un intero fra 0 e 3 — `SetNpcDirection`
(242 chiamate), `SetPlayerDirection` (149). Quale intero sia quale direzione lo
hanno deciso **due oracoli indipendenti che concordano**:

| direzione | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| versore | +Z | −Z | −X | +X |

1. **Chi si gira e poi cammina, cammina avanti.** Su 81 coppie
   `SetXDirection(d)` … `MoveX(dx, dz, …)` prese dal corpus, la direzione 0 va
   verso +Z in 34 casi su 45. È la cella più popolata e la più netta.
2. **Chi parla a qualcuno lo guarda.** In `mapevent_f80` Pizzaro e Rosy sono
   creati alle stesse coordinate tranne la X (−1,6 e +1,6) e si parlano: lui
   passa a 3, lei a 2. Quindi 3 è verso +X e 2 verso −X — e i due assi rimasti
   per 0 e 1 sono proprio quelli che dice l'oracolo meccanico.

L'enumerazione è ad **assi accoppiati** (0/1 su Z, 2/3 su X), non una rotazione
in senso orario. Nessuno l'avrebbe indovinata: `2` e `3` sono opposti fra loro,
non consecutivi in un giro.

### L'ipotesi che non ha funzionato

"L'NPC appena creato guarda il giocatore" dà **il 55%**, cioè poco più del
caso, e come miglior candidato propone `dir0 = −X`, che è sbagliato. Non è una
regola: `CreateNpc` li mette già orientati, e `SetNpcDirection` serve a girarli
*per la scena*, non a puntarli verso di noi.

Vale la pena tenerlo a mente: un oracolo al 55% non è "quasi giusto", è
rumore con una preferenza. Quello meccanico — che non passa per nessuna
intenzione narrativa — arriva al 75% sulla cella più grossa e concorda con una
lettura fatta a mano su un dialogo. Due strade diverse, stessa risposta.

### Il davanti del modello

L'unica cosa che nessun dato poteva dire. Le direzioni le decidono gli script,
il davanti lo decide la mesh, e per saperlo bisogna guardarla:

```
python tools/view.py char c_npc_05 --azim 180   # la faccia
python tools/view.py char c_npc_05 --azim 0     # la nuca
```

I personaggi sono authorati **verso −Z**, cioè già girati nella direzione 1.
Da qui gli angoli `(180°, 0°, 90°, −90°)` di `ANGLES`.

## L'unità di misura del mondo

Una casella vale **1,6**. Lo dicono due misure che si incontrano venendo da
file che non si conoscono:

- gli argomenti di `CreateNpc` sono multipli di 0,8 e per lo più di 1,6
  (`1.6`, `3.2`, `4.8`, `-9.6`…);
- ogni personaggio di `Character/c_obj_all.ps3.dsb` è alto **esattamente 1,60**
  con l'origine ai piedi — mediana su 31 modelli NPC, min 0,70, max 1,61.

**Un personaggio è alto una casella.** È il fatto su cui poggia tutto il resto,
e si vede a occhio nel palco a scacchi di `view.py event`, dove un quadretto è
una casella.

## Le pose, e perché non c'è uno scheletro

I modelli non hanno rig. Sotto ogni personaggio ci sono da 2 a 6 nodi figli, e
ognuno è un **personaggio intero** alto 1,6, distanziato di 2,0 lungo X nella
scena di authoring — 162 distanze su 200 valgono esattamente 2,0. Non sono
pezzi: sono **fotogrammi**.

| suffisso | 01 | 02_a | 02_b | 03 | 06, 07, 08 |
|---|---|---|---|---|---|
| occorrenze | 102 | 58 | 58 | 44 | 44 |
| lettura | fermo | primo passo | secondo passo | posa speciale | extra |

Il gioco anima **scambiando la mesh**, come un gioco a sprite. È coerente con
tutto il resto della sua estetica, e spiega perché lo skinning — risolto in
sessione 3 — compaia in un file solo su tutto il disco, `Opening.ps3.dsb`.

Lo conferma l'API, che è la prova indipendente: `SetNpcNode(nome, 0..3)`
sceglie un figlio per **ordinale**. `SetNpcNode("SwordPedestal", 1)` è il
piedistallo con la spada, `0` quello vuoto. Un metodo che sceglie fra i figli
di un nodo ha senso solo se i figli sono alternative, non parti.

L'ordine conta ed è quello **alfabetico**, non quello del file: i nodi stanno
scritti come `_01`, `_02_b`, `_02_a`, `_03`, e solo ordinandoli per nome
`SetNpcNode(x, 1)` diventa una cosa sensata.

## Il movimento non blocca

`MoveNpc` avvia uno spostamento e lo script prosegue. Si vede provando a usare
l'attesa che segue come cronometro: a parità di velocità (3,2) e di attesa
(0,5 s) le distanze percorse sono 1,6 — 3,2 — 4,8. L'attesa non misura niente.

Quindi il registro integra il moto nel tempo, in `tick()`, e un personaggio può
essere ancora a metà strada quando l'evento si chiude.

### Le firme, dette dai nomi

```
MoveNpc(nome, dx, dz, velocità [, flag])       87 chiamate
MoveNpcAndY(nome, dx, dy, dz, velocità)         5 chiamate
MovePlayer(dx, dz, velocità)                   43 chiamate
```

Il nome del secondo **dichiara la differenza**: il primo non ha la Y. Lo
conferma la velocità, che resta l'ultimo argomento in entrambi e vale 3,2 in 76
chiamate su 87 — e ricompare come terzo e ultimo argomento di `MovePlayer`, con
la stessa famiglia di valori (2,4 — 3,2 — 4,8 — 6,4).

Che la velocità sia in unità al secondo resta **non confermato**: nel corpus
non c'è niente che la cronometri (vedi sopra). È l'ipotesi più semplice
compatibile con i dati, e 3,2 dà due caselle al secondo, che è un passo.

## I modelli

`Character/c_obj_all.ps3.dsb` è la libreria: 22 MB, 646 nodi, **184 radici**.

| famiglia | c_npc | c_enm | c_ply | i_evt | i_mwp | i_nml | i_swp | i_she | i_mgc |
|---|---|---|---|---|---|---|---|---|---|
| quanti | 31 | 39 | 7 | 30 | 24 | 26 | 9 | 6 | 6 |

Tutti su una texture sola, `dot_base.dds`: sono voxel, il colore sta nella
palette.

I 30 `i_evt` sono **foglie**, senza fotogrammi. Un altare non cammina.

### Quale modello a quale nome: lo dicono i nomi dei file

Il nome che lo script usa — `"YoungWomana4_150"` — è un **identificativo
logico**, e non compare in nessun dato binario del disco. Sembrava materiale da
EBOOT (Fase 3). Non lo era: la tabella è nei **nomi dei file di script**.

I 237 script sotto `Event/npcevent_*` si chiamano
`npcevent_n<NN><archetipo><id>.lua.eu` —

```
npcevent_n05oldmana7_010.lua.eu
npcevent_n11imperialguarda3_320.lua.eu
npcevent_n16chickena3_010.lua.eu
```

— e quel numero è **l'indice del modello `c_npc_NN`**.

Che sia una tabella e non una coincidenza lo dice la **biiezione**: su 237
script, zero indici con più di un archetipo e zero archetipi con più di un
indice.

| | | | | | |
|---|---|---|---|---|---|
| 02 merchant | 03 youngman | 04 youngwoman | 05 oldman | 06 oldwoman | 07 girl |
| 08 boy | 10 king | 11 imperialguard | 12 ladysmaid | 14 dog | 15 cat |
| 16 chicken | 19 princessbug | 25 blacksmith | 26 goblinred | 31 spelunker | |
| 01 wiseman1 | 20 wiseman2 | 21 wiseman3 | 22 wiseman4 | 23 wiseman5 | 24 wiseman6 |

> **Sessione 12: venti su ventidue, e due corrette.** Il disco dichiara la
> tabella — 1.279 righe `addNodeListElement` in `all.lua.eu`, vedi
> [`objects.md`](objects.md) — e conferma tutta questa griglia tranne due
> caselle:
>
> - **`princessbug` è `c_npc_26`**, non `c_npc_19`: la tavola scambia proprio
>   quei due numeri, che sono anche i due che la sessione 8 aveva indicato
>   come punto debole. Vista, la differenza è di colore — `c_npc_19`, `26` e
>   `27` sono tre figure alate rossa, blu e verde, e i file si chiamano
>   `N19PrincessBug`, `N26PrincessBugB`, `N27PrincessBugC`;
> - **`goblinred` è `c_enm_12`**, che è un modello di *nemico*. I goblin rossi
>   amichevoli del villaggio riusano il goblin rosso che si combatte, ed è per
>   questo che sotto `Object/` non esiste nessun `N26GoblinRed`.
>
> La seconda dice anche perché l'inferenza non poteva arrivarci: cercava un
> `c_npc_NN` e ne trovava uno. Il numero nel nome di uno script di **dialogo**
> e quello del **modello** sono due numerazioni, non una — combaciano venti
> volte su ventidue, ed è per questo che sembravano la stessa.

E si verifica a occhio, che qui è una prova e non un'impressione — un cane e
una gallina non si confondono con nient'altro:

```
python tools/view.py char c_npc_31,c_npc_12,c_npc_11,c_npc_10,c_npc_16,c_npc_14
```

dà, nell'ordine: la salopette blu e il berretto rosso di **Spelunker**, una
cameriera, una guardia con la lancia, una corona d'oro su manto d'ermellino,
una **gallina** bianca con la cresta rossa, un **cane** marrone. Sei su sei.

Il primo indizio era arrivato per caso, in sessione 4: `c_npc_05` disegnato
aveva l'aria di un vecchio, e `n05` è `oldman`.

**66 nomi su 99** hanno così un modello dichiarato. I 33 che restano sono le
comparse degli eventi principali (`Princess`, `Priest`, `Landlord`,
`LegendHeroGhost`) e gli oggetti di scena (`OrbAltar01`, `BossMarker01`):
nessuno ha un `npcevent`, perché il codice li creava senza passare dal
meccanismo degli NPC di mappa. Per loro resta lo slot stabile per nome, che è
un segnaposto dichiarato.

> **Sessione 5, sei archetipi in più.** I `WiseMan1`…`WiseMan6` stavano in
> quella lista di comparse, e non ci dovevano stare: hanno un `npcevent`
> ciascuno, e quindi un modello dichiarato — `c_npc_01` e `c_npc_20`…`c_npc_24`.
> Erano sfuggiti perché il primo censimento guardava i nomi che gli **script di
> evento** usano, e i sei saggi parlano quasi solo attraverso il proprio.
> La rubrica completa è ora `entity.npc_directory()`: legge i 243 file e
> restituisce, per ogni identificativo, indice, archetipo, nome esatto e
> percorso del dialogo. Vedi [`walk.md`](walk.md).

#### La coincidenza da cui guardarsi

Undici directory sotto `Event/` hanno un `<Nome>.ps3.dsb`, e una si chiama
`Priest` come un nome di `CreateNpc`. Sembrava una risoluzione riuscita — un
nome di script che cade su un file del disco. Ma
`Event/Priest/Priest.ps3.dsb` misura **0,96 × 0,64 × 0,96** e usa
`cliff_01.dds`: è la *scenografia* dell'evento del prete, non il prete. Un
personaggio di questo gioco è alto 1,60 e sta su `dot_base.dds`.

La coincidenza sarebbe passata per una prova se non si fossero guardati i
numeri. Le altre dieci (`Devil`, `Dragon`, `Golem`…) sono le scene dei boss.

## Il collocamento nel mondo

`CreateNpc(x, y, z, nome)` mette l'NPC **relativo al giocatore**: le coordinate
stanno fra −9,6 e +16,0 e sono multipli di 0,8, mentre `SetPlayerPosition` usa
interi fino a 89. Sono offset, non punti del mondo. La Y è 0 in 108 chiamate su
115, ed è proprio questo a dire che il secondo argomento è l'altezza: le cinque
chiamate che valgono 8,0 sono i due amanti sul balcone di `mapevent_f80`.

E il giocatore sta dove `SetPlayerPosition(cx, cy, piano)` dice: **celle della
griglia logica** dei file `MAP_ALIGNMENT`, con il terzo argomento che è il
piano (0 in 48 chiamate su 71). Una cella vale `TILE`, e l'origine sta a un
**angolo** — X positiva verso destra, Z **negativa** verso il basso:

```
mondo = (cx · 1,6,  y,  −cy · 1,6)
```

Che l'origine sia a un angolo lo dicono gli argomenti stessi delle camere
assolute degli script, che hanno X sempre positiva (8,33…130,53) e Z sempre
negativa (−206,36…−11,19) — un quadrante, non un intorno dello zero. E si
verifica: ogni punto così letto cade dentro `[0, w·1,6] × [−h·1,6, 0]` in
**17 casi su 17** fra gli eventi che le `MAP_ALIGNMENT` sanno attribuire a una
mappa col flag `-e`.

Restava un ostacolo, che era il vero nodo: le mappe caricate misuravano una
ventina di unità mentre le camere arrivavano a x = 158. Non era un problema di
riferimento ma di **composizione** — le sezioni di un `.pac` sono schermi da
mettere in griglia, e si disegnavano tutte accatastate. Sciolto quello
([`format_pac.md`](format_pac.md)), i due sistemi combaciano e la conversione
è una sottrazione:

```python
locale = mondo − (w·1,6/2,  0,  −h·1,6/2)      # host.to_local()
```

Senza mappa caricata — il palco vuoto — la cella si registra e basta: non ci
sono `w` e `h` con cui tradurla.

### Gli NPC che stanno già sulla mappa

Dei 99 nomi del corpus solo 40 passano da `CreateNpc`. Gli altri sono lì prima
dell'evento, e lo script li nomina e basta — e dove stessero sembrava non
dirlo nessun file.

Lo dice la `MAP_ALIGNMENT`. Fra le 14.099 celle con un oggetto ce ne sono
**271** la cui classe è **il solo identificativo**, senza parametri e senza
altro:

```
d_20_1   cella (7, 11)   cls = "a1_010"      -> Kinga1_010
d_20_9   cella (7, 16)   cls = "b8_010"      -> WiseMan2b8_010
d_4_1_1  cella (62, 16)  cls = "b4_010"      -> PrincessBugb4_010
```

Il nome che usa lo script è **archetipo più identificativo**, quindi la coda
del nome è la chiave: `OldWomana6_010` = `OldWoman` + `a6_010`. Su 50 nomi del
corpus che portano un identificativo, **37 trovano la loro cella** — e la cella
si converte in posizione con la stessa formula del giocatore.

Il conto finale: **72 nomi su 99 collocati**, 40 da `CreateNpc` e 37 dalla
mappa (con qualche sovrapposizione). I 27 che restano non si disegnano:
`visible_entities()` mostra solo chi ha una posizione che qualcuno ha davvero
dichiarato, e `unplaced()` elenca gli altri. Metterli ai piedi del giocatore
li renderebbe visibili e sbagliati, che è peggio di assenti.

Il parser è `mapdat.npc_spots()`; l'host lo carica con `Host.load_map()`, che
è anche ciò che gli dà `(w, h)`.

> **Sessione 5: i 199 posti che nessuno nominava.** I 37 nomi qui sopra sono
> quelli che un evento cita. Gli altri 199 posti li nomina il **loro** script
> `npcevent_*`, e rimettere insieme le due metà porta il conto a **225
> identificativi su 236 (95%)** con nome, modello e dialogo. Da lì una mappa si
> popola da sola, senza aspettare che un evento nomini qualcuno:
> `walk.Walk.populate()`. Vedi [`walk.md`](walk.md).
>
> Una cosa che i nomi dei file da soli non dicono: le **maiuscole**. Il file è
> tutto minuscolo, e fra `Blacksmith` e `BlackSmith` non c'è modo di scegliere.
> Lo dicono i 151 script che si nominano per esteso al proprio interno
> (`setnpccamerac("OldMana1_300")`) — un'altra dichiarazione dello stesso fatto,
> presa da un'altra parte del file.

## Il palco vuoto

```
python tools/view.py event <script.lua.eu> [--skip N] [--at x,y,z]
```

Un evento **senza mappa**, su un pavimento a scacchi di caselle. Serve perché
le due cose sono sottosistemi diversi e finora si ostacolavano: una mappa di
questo gioco è piena, ha anche il soffitto, e dove ci sia terreno libero non è
scritto da nessuna parte. Gli NPC finivano dentro un muro e non si vedeva se il
registro funzionasse.

Il pavimento è nostro, non un asset: dà al palco una scala leggibile, e un
quadretto è `TILE`.

## Come si disegna

La mappa ha le trasformazioni cotte nei vertici — è ciò che rende possibile
disegnarne 54 milioni. Le entità no: si spostano a ogni fotogramma. Da qui la
matrice `model` nello shader, identità per la mappa e posizione più rotazione
per un personaggio, letta dal registro **al momento del disegno**. Il movimento
non costa niente: nessun buffer da ricostruire.

La posa sbagliata e l'entità nascosta si spengono con una **matrice nulla**
invece che con un ramo: i triangoli collassano in un punto e il rasterizzatore
li butta. Costa meno che togliere e rimettere una lista di vertici dal batch a
ogni fotogramma.

La camera dell'evento comanda solo se il suo bersaglio esiste per noi:
`SetCameraAtBody` su un'entità collocata, oppure un punto assoluto che cada
**dentro** la scena caricata. Altrimenti si scarta l'inquadratura intera. Il
filtro era nato come rete contro i fotogrammi neri; ora che i riferimenti
combaciano è quasi sempre il punto assoluto a passare, ed è il caso giusto.

### La firma di `SetCamera` era sbagliata

La forma a sei argomenti veniva letta `(tempo, distanza, azimut, x, y, z)`, con
la distanza dichiarata "ipotesi da confermare". Non lo era: **il secondo
argomento scende a −17,72**, e una distanza negativa non esiste. Le
distribuzioni sulle 142 chiamate dicono altro —

| arg | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| intervallo | 0,10…10,22 | −17,72…64,83 | −180…338 | 8,33…130,53 | 1,26…22,77 | −206,36…−11,19 |
| lettura | tempo (0,10 in 140/142) | elevazione | azimut | x | y | z |

— cioè `(tempo, elevazione, azimut, x, y, z)`: la distanza **non c'è**. I segni
degli ultimi tre sono la stessa firma del riferimento all'angolo, ed è quello
che ha fatto sospettare il resto.

## I metodi implementati

Chiamate **misurate** eseguendo tutti i 377 script, non contate nel sorgente:
le due cose differiscono, e la prima è quella che conta.

| metodo | chiamate | cosa fa |
|---|---:|---|
| `Pause` / `Play` | 185 / 184 | congela tutto: è quasi sempre la prima riga di un evento |
| `SetPlayerDirection` | 183 | |
| `SetNpcDirection` | 147 | |
| `LockPlayer` / `UnlockPlayer` | 133 / 133 | ferma il giocatore, non il mondo |
| `PlayNpc` / `PauseNpc` | 82 / 80 | |
| `SetStatusVisible` | 79 | l'HUD |
| `CreateNpc` | 57 | |
| `SetNpcVisible` | 57 | |
| `PlayEnemy` / `PauseEnemy` | 52 / 51 | |
| `setPlayerAngle` | 52 | l'angolo fine, in gradi |
| `SetPlayerPosition` | 46 | registra la cella, vedi sopra |
| `SavePlayerAngle` / `RestorPlayerAngle` | 37 / 36 | |
| `MovePlayer` | 28 | |
| `MoveNpc` | 24 | |
| `SetNpcNode` | 16 | la posa |
| `SetPlayerVisible` | 2 | |
| `MoveNpcAndY` | 0 | |

Due letture che il conteggio statico non dà. `setPlayerAngle` compare quattro
volte nel sorgente degli eventi e ne fa **52**: sta dentro un helper condiviso
di `eventfunction.lua.eu`, e chi conta le righe non lo vede. `MoveNpcAndY` è il
contrario: cinque chiamate scritte, **zero** eseguite — stanno tutte su rami
che con le bandiere di partenza non si prendono.

Con questi la copertura dell'host passa da **22 metodi / 63% delle chiamate** a
**43 metodi / 87%**.

## I nemici — `entity.py bestiary()`, `enemy_models()`

Il TODO li dava come «li crea il codice, sui suoi `EnemyObserver`», e diceva di
guardare i parametri di quelle celle prima di concludere che serve l'EBOOT. Le
celle infatti non portano nemici: le 65 `EnemyObserver` hanno un `-gNNN` e
niente altro, cioè **un numero di stanza**, e i cinque campi numerici della
cella (`2001`, `0`, `257`, `2`, `4100`) sono gli stessi che porta un `observer`
qualsiasi — proprietà della cella, non del nemico.

*(Sessione 8: quel `4100` era la traccia giusta letta nel posto sbagliato. È il
campo **attore**, e vale 4100 perché quella cella ospita un osservatore. I
nemici stanno in **altre** celle, dove lo stesso campo porta il loro
identificativo d'album — 10.196 in tutto il disco. Vedi
[`walk.md`](walk.md) §attori.)*

Il censimento però esiste, ed è in chiaro: l'**album dei nemici**.
`UserInterface/EnemyView/EnemyView.lua.eu` è un descrittore come gli altri e
dichiara la tabella intera, 46 voci:

```lua
Num=5003,                              -- identificativo, da 5002 a 5082
NodeStrings="c_enm_01_01",             -- il modello
NameStrings="Ｋｉｌｌｅｒ　Ｒａｂｂｉｔ",
LivingId=LIVING.FIELD_GRASS,           -- dove vive
ItemId=item.Item.IL_RED_APPLE,         -- cosa lascia cadere
```

**I modelli si risolvono 46 su 46**, e come sono divisi dice una cosa sul
gioco: 37 sono **nodi** dentro `Character/c_obj_all.ps3.dsb` — la stessa forma
degli NPC, che sono nodi dentro una scena sola — e i 9 **boss** hanno un file
per uno (`c_bos_01_all.ps3.dsb`). Che il campo si chiami `NodeStrings` lo
diceva già: non è un nome di file. `view.py char c_enm_01` disegna il primo, ed
è un coniglio viola con le corna rosse: ツノウサギ nel commento giapponese,
`Killer Rabbit` nel descrittore.

**I quindici habitat** sono `FIELD_*` e `DUNGEON_*` per elemento, e i sette
sotterranei combaciano uno a uno con i sette templi che `Item.lua.eu` dichiara
in `WarpItem`:

| `LivingId` | tempio |
|---|---|
| `DUNGEON_GRASS` | 草原の神殿, `Dungeon1` |
| `DUNGEON_FOREST` | 森の神殿, `Dungeon2` |
| `DUNGEON_SANDS` | 砂漠の神殿, `Dungeon3` |
| `DUNGEON_WATER` | 水の神殿, `Dungeon4` |
| `DUNGEON_FIRE` | 炎の神殿, `Dungeon5` |
| `DUNGEON_EARO` | 風の神殿, `Dungeon6` — *earo* è *aero*, il vento |
| `DUNGEON_MAGIC` | 闇の塔, `Dungeon7` |

Quindi **quale nemico appartiene a quale sotterraneo si sa senza l'EBOOT**.

*(Precisato in sessione 8, e la precisazione conta: `LivingId` dice la
**famiglia** di un nemico, non dove il gioco lo mette. Ora che si sa dove lo
mette — la griglia lo dichiara cella per cella — le due cose si possono
confrontare, e il nome inglese del tempio combacia con l'habitat della specie
che vi è piazzata solo nel **47,1%** dei casi su 1.988 nemici. Con sette
habitat è ben sopra il caso, quindi la correlazione c'è ed è forte; ma non è
una regola, e il Flame Temple è pieno di nemici `DUNGEON_WATER`. Quando c'è il
dato vero, l'habitat torna a essere quello che è: una classificazione.)*

E la tabella si è poi validata contro una fonte esterna che non sa nulla di
questi file: un walkthrough attribuisce a Eelagon il tempio dell'erba, a Queen
Bee quello della foresta, a Giga Golem il deserto, a Kraken l'acqua, a Dragon
il fuoco, a Dark Knight il vento, e mette Fuelle e Onyx nella torre. **Otto su
otto** con gli habitat qui sopra, e con essi cade l'ultimo dubbio su `EARO`.

Quello che si diceva restasse al codice — *quanti* ne mette in ogni stanza e
con che regola — **non resta al codice**: lo dichiara la griglia logica, cella
per cella, nel campo che sta a +0x10 del record. Vedi [`walk.md`](walk.md)
§nemici; qui basti che due dei 46 si distinguono nel dato prima ancora che nel
gioco, **5075 Crystal Slime** e **5076 Blue Dragon**, gli unici con
`LivingId = -1`, cioè senza habitat — e sono esattamente i due che le guide
descrivono come capaci di comparire ovunque.

Una nota di metodo che è costata il primo tentativo: senza le **tabelle
permissive** questo descrittore non gira affatto, perché nomina costanti native
che nessuno script definisce (`LIVING`, `GameDataFlags`, `item`). Con
`lua.execute` nudo il file solleva e la tabella sembra non esserci. È lo stesso
ostacolo degli eventi, e la soluzione era già scritta in `host.BOOT`.

## Verifiche

`python tools/entity.py` mette alla prova 49 proprietà, e non sono test di
cortesia: ognuna è una cosa dedotta dai dati, e se smette di valere è la
deduzione a essere sbagliata. Le direzioni opposte a due a due, gli angoli che
portano il davanti del modello sul versore giusto, l'offset relativo al
giocatore, uno spostamento di 4,8 a velocità 3,2 che finisce in 1,5 s, il
congelamento che ferma il moto, la riduzione dei nomi ad archetipi.
