# L'host — `tools/host.py`, `tools/font.py`

La milestone dichiarata in [`STRATEGY.md`](STRATEGY.md) era: *caricare una
mappa, eseguire uno script di evento reale e mostrare a schermo la sua finestra
di messaggio*. È raggiunta.

```
python tools/view.py extract/pac/field_16.ps3.pac \
    --event extract/.../Event/Devil/Devil.lua.eu --skip 14
```

Sullo schermo: la mappa dal `.pac`, le texture dal `TPKG`, il post-processing
YEBIS, e sopra il riquadro con `Ｌｅｅ：　ＴｈーＴｈａｔ　ｉｓ　ｔｈｅ
　Ｄａｒｋ　Ｋｉｎｇ　Ｏｎｙｘ！？` disegnato con il font del gioco, mentre
uno script Lua originale gira su una VM Lua vera e decide *quando* mostrarlo.

Nessun pezzo di quella frase è nostro: il testo è nel sorgente Lua, i glifi
nell'atlante `TPKG`, le larghezze nel descrittore `Font.lua.eu`, i tempi nelle
chiamate `Wait` dello script.

## Cosa gira davvero

```
python tools/host.py coverage extract/.../data/Event

377 script eseguiti su 378, 377 arrivati in fondo, 0 in errore
128 metodi distinti, 6.634 chiamate
43 implementati su 128 usati, che coprono 5.814 chiamate su 6.634 (87%)
```

Il registro delle entità — `SetNpcDirection`, `CreateNpc`, `Pause`… — sta in
[`entities.md`](entities.md), ed è quello che ha portato la copertura dal 63%
all'87%.

Gli script sono eseguiti **verbatim**: il file `.lua.eu` che sta sul disco,
dato a `lupa` (Lua 5.5). Non una traduzione, non un sottoinsieme.

Perché ci arrivino servono due cose che non sono ovvie.

**Le librerie condivise.** Gli script chiamano funzioni come `seafterboss()` o
`setnpccamerac()` che non sono metodi dell'host: sono Lua normale, definito in
`Event/eventfunction.lua.eu` e `Event/eventflag.lua.eu`. È il package manager
del gioco a caricarle prima. Senza, un evento su due muore alla prima riga.

**Gli stub devono essere chiamabili.** Una tabella permissiva che non risponde
a `__call` fa fallire ogni funzione che non conosciamo ancora. Con `__call` che
restituisce `nil`, l'evento prosegue e la mancanza viene registrata invece di
uccidere lo script.

## Lo scheduler

Il ritmo di uno script di evento è sempre lo stesso:

```lua
Event:Wait(0.9);
coroutine.yield();
```

Si chiede qualcosa all'host, si cede il controllo, l'host riprende quando la
richiesta è soddisfatta. Lo scheduler quindi **non interpreta niente**: gli
basta sapere quando riprendere, e per l'intero corpus degli eventi bastano tre
condizioni — un tempo scaduto (`Wait`), un input del giocatore
(`WaitContinue`), la fine di una sequenza (`WaitScene`).

Una nota di implementazione che costa mezz'ora a chi non la sa: il thread della
coroutine **non deve attraversare il confine** fra Lua e Python. Passato a
Python e restituito, torna indietro come funzione e `coroutine.resume` lo
rifiuta. Lo scheduler tiene quindi il thread in una variabile Lua e ci parla
attraverso due funzioni, `__start` e `__step`.

## I globali nativi

`EventClass` e `soundList` non li definisce **nessuno** script del disco: li
forniva il codice C++ della PS3. Qui `EventClass.Event` è l'oggetto host, e
tutto il resto diventa una tabella permissiva che si ricorda il proprio nome:

```
soundList.SoundID.SE_quake   ->   "soundList.SoundID.SE_quake"
```

Il valore numerico non lo conosciamo — sta nell'EBOOT, Fase 3 — ma il nome
basta per far girare lo script e per registrare *cosa* è stato chiesto. È la
differenza fra un host che si ferma e un host che misura.

Allo stesso modo, ogni metodo non implementato viene **contato invece che
fallire**. È il criterio della Fase 5: uno script che gira senza chiamare
metodi ignoti è un sottosistema finito.

## La lista della spesa

Misurata, non stimata: i metodi che gli eventi chiamano davvero, in ordine.

| chiamate | metodo | |
|---:|---|---|
| 875 | `Print` | ✅ |
| 472 | `WaitContinue` | ✅ |
| 417 | `CloseMessage` | ✅ |
| 385 | `GetEventFlag` | ✅ |
| 292 | `BackupCamera` | ✅ |
| 290 | `RestoreCamera` | ✅ |
| 258 | `Wait` | ✅ |
| 213 | `SetParamDepthofField` | ✅ |
| 201 | `BackupDof` | ✅ |
| 197 | `RestoreDof` | ✅ |
| 185 | `Pause` | |
| 184 | `Play` | |

**Stato: 22 metodi implementati su 128 usati (e 497 esistenti), che coprono il
63% di tutte le chiamate.** I primi dieci sono tutti fatti, 12 dei primi venti.
La coda è lunghissima e non urgente: 20 metodi fanno il 76% delle chiamate,
30 ne fanno l'85%.

Il gruppo dopo il dialogo non era quello che ci si aspetterebbe: **camera**
(oltre 700 chiamate) e **messa a fuoco** (altre 600). Per volume, un evento di
questo gioco è quasi tutto inquadrature — ed è il motivo per cui erano i due
sottosistemi da fare subito.

Il prossimo gruppo, ora, è **entità**: `Pause` / `Play` (369 chiamate insieme,
il congelamento del mondo durante una scena), `SetPlayerDirection` /
`SetNpcDirection` (330), `LockPlayer` / `UnlockPlayer` (266). Tutti chiedono la
stessa cosa che ancora manca: un mondo con dentro dei personaggi.

### Due misure sbagliate, e perché

Questo numero è stato misurato male due volte prima di venire giusto, e vale la
pena dirlo perché sono due errori che si ripetono facilmente.

**Un errore contava come successo.** Il primo `coverage` diceva "376 arrivati in
fondo". Ma un errore Lua terminava la coroutine, e la coroutine terminata era
proprio il criterio con cui contavo le conclusioni. Separando `done` da
`failed` il vero risultato era 89 su 378, con 288 script morti su una funzione
mancante — che è ciò che ha portato a scoprire le librerie condivise.

**Un metodo non implementato gonfia il proprio conteggio.** Nella stessa
misura, `Select` e `GetSelect` risultavano terzo e quarto con oltre mille
chiamate ciascuno, e sembravano la priorità successiva. Erano un artefatto: uno
script che ripete la scelta finché non ottiene una risposta valida gira a vuoto
per sempre se `Select` non risponde, e ogni giro conta. Implementati, i loro
numeri veri sono **56 e 54 chiamate, venticinquesimo e ventiseiesimo posto**.

La morale: la misura dell'uso di un'API è distorta proprio dai pezzi che non
hai ancora costruito. Va rifatta dopo ogni implementazione, non una volta sola.

## Il font — `tools/font.py`

`UserInterface/Font/Font.lua.eu` non è un file di dati travestito da Lua: è
Lua, e lo carica la stessa VM. Dichiara tutto — atlante, tabella dei caratteri,
corpo, spaziatura, e la tabella delle larghezze per carattere.

- **Atlante**: `Font_eng.ps3.tpk`, 512×2048, celle da 32×32.
- **`Font.bin`**: 688 code point UTF-16BE, uno per glifo, nell'ordine
  dell'atlante. Comincia con gli hiragana in ordine あいうえお, poi i katakana,
  poi 387 kanji e 87 latini full-width. Non ha intestazione: la dimensione
  diviso due dà il numero di glifi, ed è l'unica lettura che non lascia byte
  spaiati.
- **Larghezze**: il font è **proporzionale** pur avendo una griglia fissa —
  la cella è sempre 32, l'avanzamento no (`Ｉ` 10, `Ｍ` 18, `ｉ` 6).

Il testo di gioco è scritto a larghezza piena (`Ｓｎａｐｓｈｏｔ
　ｆａｉｌｅｄ．`), com'era già emerso in RECON §6.4. Dettaglio che si scopre
solo provando: nell'atlante **non c'è il trattino** `－`. Il gioco scrive i
trattini con `ー`, il segno di prolungamento dei katakana — si vede in
`ＴｈーＴｈａｔ`, che a prima vista sembra un errore di codifica e invece è
come l'hanno scritto loro.

## Le scelte, e i descrittori UI

`Event:Select()` **non prende argomenti** in nessuna delle 298 chiamate del
disco, e `GetSelect()` viene confrontato con 0 in 288 punti e con 1 in 9, mai
con altro: è un sì/no fisso. Le due etichette non stanno in nessuno script di
evento — erano stringhe native del C++ — ma sono dichiarate identiche nei
**16 descrittori UI** che hanno una scelta propria, e da lì le prendiamo.

Quei descrittori sono i "137 descrittori UI dichiarativi" trovati in Fase 1c, e
guardati da vicino sono una specifica di interfaccia completa:

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

Tre cose che ne discendono:

- le coordinate sono in uno **schermo virtuale 1280×720** (`X=640` è il centro):
  l'interfaccia è risoluzione-indipendente per costruzione, il che semplifica
  la vita a un port PC;
- `Cancel = {Enable, Index}` dice quale opzione sceglie il tasto di annullamento,
  quindi anche il comportamento dell'input è dichiarato, non nel codice;
- `Animation` dichiara quattro clip con inizio e durata — apertura, permanenza,
  chiusura, cursore — che sono intervalli dentro l'animazione del modello 3D
  nominato da `ScenePackageName`.

Perché la finestra di scelta **è un modello 3D**, non un disegno: `SelectA/B/C`
sono `.dsb` con le loro `.tpk`, e le texture contengono la cornice e la punta
del cursore come due disegni separati sulla stessa immagine. Il visualizzatore
usa la cornice vera, ritagliata alla prima colonna vuota.

## Camera e messa a fuoco, pilotate dallo script

Le firme non sono documentate da nessuna parte, ma i dati le rivelano con un
aiuto involontario degli autori. In `eventfunction.lua.eu` ci sono due helper
commentati `家NPCカメラ右から` ("camera NPC da destra") e `左から` ("da
sinistra"), e fra i due cambia **solo il segno del terzo argomento**:

```lua
Event:SetCameraAtBody(6.12, 19.61,  47.93, n);   -- da destra
Event:SetCameraAtBody(6.12, 19.61, -47.93, n);   -- da sinistra
Event:SetParamDepthofField(0.73, 0.60, 0.0);
```

Quindi il terzo è un **azimut in gradi**. Restano `6.12` e `19.61`: distanza e
elevazione — e le elevazioni di tutto il disco stanno fra 19 e 30 gradi, come
ci si aspetta da una camera che guarda dall'alto. La forma a tre argomenti di
`SetCamera` ha la stessa struttura `(distanza, elevazione, azimut)`.

Resta un'ipotesi da confermare in Fase 3: nella forma a sei argomenti il primo
vale `0.10` in 170 chiamate su 170 e ha la forma di un tempo di transizione,
mentre gli ultimi tre sono coordinate di mondo, cioè il punto inquadrato.

Il DOF va dritto nella catena di [`post.py`](render.md): è la specifica YEBIS
che si chiude: *i parametri arrivano dal Lua*. `BackupDof` / `RestoreDof` sono
una pila, e ogni evento la usa per lasciare la scena com'era.

L'unità del secondo argomento resta ignota, ma legarla alla **distanza di
fuoco** anziché al raggio della scena è l'interpretazione che regge in entrambi
i casi d'uso: su un primo piano a 6 metri, `0.60` dà una fascia nitida di 3,6
metri; su un panorama si allarga da sola, come fa un obiettivo vero.

## Codifiche miste nel corpus

Alla prima passata 13 script su 378 fallivano in decodifica. Non sono
corrotti: sono in **Shift-JIS**, mentre tutti gli altri sono UTF-8. Il
contenuto sono commenti degli sviluppatori — `--ボスを倒した場合`, "quando il
boss è sconfitto". Provare le due codifiche in ordine basta, perché UTF-8
fallisce in modo netto sui byte 0x80–0x9F.

## Cosa non fa

- *(Chiuso in sessione 7: il riquadro di dialogo ora è quello del gioco —
  `UserInterface/Message`, nelle due misure che il disco dichiara, con il testo
  dove lo mette il descrittore. Non era in `data/Balloon`, che è il cartello
  `CHECK`/`TALK`/`OPEN` sopra la testa: lo dicono le sue misure in unità di
  mondo e le 352 chiamate a `CreateBalloon(ActorType)`, che lo creano per un
  **attore**. Vedi [`ui.md`](ui.md).)*
- Le bandiere di evento e il denaro esistono ma vivono solo in memoria, senza
  salvataggio.
- Il registro nomina 99 personaggi e ne colloca **40**: gli altri stanno già
  sulla mappa, e la griglia logica che li dichiara non è ancora letta —
  vedi [`entities.md`](entities.md).
- I descrittori UI ora si **eseguono** — [`ui.md`](ui.md), `tools/ui.py`: 119
  schermate composte con la loro scena, le scritte dove il descrittore le
  mette e il cursore dove dice lui. Resta l'animazione, cioè il moto fra la
  posa chiusa e quella aperta.
- Il markup `/vn` `/vh` `/vl` è riconosciuto e memorizzato come "tono", ma non
  produce suono — resta l'ipotesi di RECON §6.4.
