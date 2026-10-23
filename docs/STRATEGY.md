# PC-3Ddot — Strategia

*Allineato alla fine della sessione 12 (2026-08-19). Lo stato di dettaglio e le
priorità stanno in [`TODO.md`](TODO.md); qui c'è solo l'impianto.*

Decisione presa in Sessione 1 (2026-08-09): **reimplementazione nativa guidata
dal Lua**. Costruiamo un motore PC che espone la stessa API di scripting e
riusa gli script Lua originali *verbatim*. L'EBOOT PS3 serve come oracolo di
riferimento, non come codice da tradurre.

Modello: Ship of Harkinian / OpenGOAL / devilutionX. Distribuzione BYOA.

**Perché non la ricompilazione statica PPC64.** Su Xbox 360 funziona bene
(XenonRecomp) perché la GPU è vicina a D3D9. Su PS3 l'RSX richiederebbe un
livello HLE sostanziale, e il risultato sarebbe un binario opaco e non
moddabile. Qui abbiamo un vantaggio che quella strada butterebbe via: il 100%
della logica di gioco è già in sorgente leggibile.

---

## Fase 1 — Fondamenta (nessun codice motore)

Tutto analisi statica, tutto automatizzabile, nessuna dipendenza dall'EBOOT.

- **1a. Estrattore ufficiale.** ✅ **fatto** — `tools/iso.py`, lettore UDF
  proprio (i Blu-ray PS3 usano la partizione di metadati di UDF 2.50, che
  `pycdlib` non gestisce), set dichiarati, manifesto con `sha256` e verifica.
  `extract/` e' ora una funzione del disco. Vedi [`extract.md`](extract.md).
- **1b. Inferenza delle firme.** ✅ **fatto** — `tools/lua_signatures.py`.
  497 metodi su 8 classi host, 29.626 call site; arità, tipo per posizione,
  uso del ritorno. Output: `docs/lua_signatures.md` + `generated/script_api.h`.
- **1c. Estrazione delle tabelle costanti.** ✅ **fatto** — `tools/lua_tables.py`.
  12 enum / 2.216 membri (`generated/script_enums.h`), più la scoperta dei
  descrittori UI dichiarativi — **136 caricati ed eseguiti** dalla sessione 9,
  vedi [`ui.md`](ui.md). Solo `EventFlag` ha i valori: gli altri 11 enum sono
  nativi, i valori arrivano con la Fase 3.
- **1d. Clustering per dominio.** Raggruppare i 497 metodi in sottosistemi
  (dialogo, camera, audio, entità, animazione, flag, mappa, UI) per stabilire
  l'ordine di implementazione e stimare il lavoro. — *da fare*. Nota: `host.py
  coverage` dà ormai il dato che serviva davvero — non quanti metodi esistono,
  ma quanto sono chiamati.
- **1e. Decoder del markup di dialogo.** ✅ **fatto** — censimento completo:
  9 codici, nessun escape, linguaggio chiuso (RECON §6.4). Semantica certa per
  `/r` `/b` `/co` `/cl`; la famiglia `/v*` resta un'ipotesi da confermare.

## Fase 2 — Formati asset

Priorità dettata da cosa serve per il primo frame a schermo.

| Formato | N | Priorità | Note |
|---|---|---|---|
| `TPKG` texture | 763 | ✅ **risolto** | [`format_tpk.md`](format_tpk.md) — 4.033 texture, 0 errori |
| `DPK` collisione | 171 | ✅ **risolto** | [`format_dpk.md`](format_dpk.md) — 171 file su 171 finiscono sull'ultimo byte, 301 mesh e 420.301 triangoli, stesso sistema di riferimento del `.pac` |
| `DSBF` scene | 460 | ✅ **risolto** | [`format_dsb.md`](format_dsb.md) — 1,61 M triangoli da 460 file su 460, materiali e texture agganciati, skin e bind pose inclusi |
| `.pac` mappe | 167 | ✅ **risolto** | [`format_pac.md`](format_pac.md) — 4.837 sezioni, 51,7 M vertici, stesso parser; **composizione** verificata contro la griglia logica, **99,3% delle celle solide** (il 90,7% di prima aveva nel denominatore mare e vuoto) |
| `EDT` voxel | 90 | ✅ **risolto** | [`format_edt.md`](format_edt.md) — 90 file su 90 finiscono sull'ultimo byte, 260.860 voxel in un cubo 16×16×16; le sei parti sono sei pose |
| `SAV` salvataggi | 3 | media | nessun magic, ma la stessa coppia `u32 len + UTF-8` degli `.edt`; riferisce i preset **per percorso** invece di incorporarli |
| `MAP_ALIGNMENT` | 170 | ✅ **risolto** | [`format_mapdat.md`](format_mapdat.md) — griglia logica e grafo del mondo; il campo +0x10 è **l'attore**, che tiene insieme oggetti, nemici e NPC |
| `spkg`/`CGB` shader | 4 | bassa | meglio riscrivere in GLSL/HLSL che tradurre Cg RSX |
| Bink, WAV, DDS | 333 | risolti | ffmpeg / diretti |

## Fase 3 — EBOOT come oracolo

Decrittare il SELF (`key_revision 0x0001`, chiavi retail pubbliche) verso ELF
PPC64 big-endian e aprirlo in Ghidra. Serve per: semantica dei metodi ambigui,
costanti del motore, uso effettivo delle SPU, e conferma dell'ipotesi OROCHI.
Non blocca la Fase 1 né la Fase 2.

**Non è ancora stata toccata in nove sessioni.** Fino alla settima non c'era
mai stata una vera ragione per aprirla: ogni volta che qualcosa sembrava
richiederla, era sul disco in chiaro. Adesso ce ne sono **due**, tutte e due
cercate in tutti i posti in chiaro e non trovate:

- il **pattugliamento dei nemici** (sessione 8) — pose e periodo si leggono dai
  dodici attori Lua del minigioco, il moto no;
- il **seguito di una schermata** (sessione 9) — quale schermata segue una
  scelta è dichiarato 2 volte su 136.

Nota utile per quando si aprirà: i file `DSBF` sono immagini di memoria scritte
con `memcpy` di struct C++, quindi **le stesse struct saranno riconoscibili in
Ghidra** e daranno i nomi dei campi finora dedotti.

**Nota di metodo, pagata più volte.** Diverse cose sono state rimandate a questa
fase e poi trovate sul disco in chiaro: i valori delle direzioni (li dicono gli
script confrontando chi si gira con chi cammina), la tabella archetipo →
modello (la dicono i nomi dei 237 file `npcevent_n<NN><archetipo><id>`), il
piazzamento dei nemici (lo dichiara la griglia, cella per cella) e l'input
delle schermate (lo dichiarano i descrittori, tranne l'avvolgimento del
cursore). Prima di rimandare qui, conviene chiedersi se il dato non sia già
scritto da qualche parte — anche in un nome di file.

## Fase 4 — Host

- VM Lua — ✅ **fatto**, `lupa` (Lua 5.5): **377 script di evento su 378
  girano, 377 arrivano in fondo, 0 errori**, e l'host copre l'**87% delle
  6.634 chiamate** del corpus con 43 metodi. Vedi [`host.md`](host.md)
- **Registro delle entità** — ✅ **fatto**, `tools/entity.py`: posizione,
  direzione, posa, movimento nel tempo; 72 nomi su 99 collocati e 66 su 99 con
  il modello che il disco dichiara. Vedi [`entities.md`](entities.md)
- **Giro di gioco** — ✅ **fatto**, `tools/walk.py`: camminare di cella in
  cella, i passaggi fra mappe con il loro punto d'arrivo, gli abitanti che una
  mappa dichiara (225 su 236 con nome, modello e dialogo). Vedi
  [`walk.md`](walk.md)
- **I nemici in mappa** — ✅ **fatto** (sessione 8): la griglia ne piazza
  **10.196**, uno per cella, con la specie nel campo +0x10 e il set di
  piazzamento in `-sA`…`-sH`. `A`,`B`,`C` sono tre disposizioni alternative
  della stessa popolazione; `F`,`G`,`H` le stesse per FROM Mode, e lì i nemici
  da sotterraneo in campagna passano dallo 0,5% al 34,8%. Vedi
  [`entities.md`](entities.md)
- **Le schermate di sistema** — ✅ **fatto** (sessioni 7 e 9), `tools/ui.py`:
  136 descrittori caricati ed eseguiti, composti dalla propria scena, e
  **navigabili** — 23 blocchi per 60 voci, il tasto che sceglie e quello che
  annulla, le pagine dei piani. Vedi [`ui.md`](ui.md)
- **Scheduler a coroutine** — ✅ **fatto**: ogni evento è una coroutine ripresa
  per frame, `Event:Wait()` / `:WaitContinue()` / `:WaitScene()` sono i tre
  punti di sospensione che bastano all'intero corpus
- Font di interfaccia — ✅ **fatto**, `tools/font.py`
- **Package manager** (`gPackageManager:addNodeListElement`) — ✅ **fatto**
  (sessione 12), `tools/nodes.py`: **1.279 righe** che mandano ogni costante
  nativa sul nome del proprio nodo, cioè la tavola dei simboli del disco.
  99,1% dei nodi dichiarati esiste in un `.dsb`, 98,2% delle costanti che gli
  script passano ad `AddNode` è dichiarata. Conferma le rubriche di sessione 4
  e 8 e ne corregge due caselle. Da lì gli **oggetti di mappa**: la cella li
  nomina con `4000 + m_obj_NN` e adesso si disegnano — 7.695 celle su tutto il
  disco. Vedi [`objects.md`](objects.md)
- Renderer — il ponte fra i formati e lo schermo esiste gia' come strumento di
  verifica: `tools/view.py` + `tools/post.py`, vedi [`render.md`](render.md).
  Disegna il 100% della geometria del disco (54,1 M vertici) texturizzata, con
  la catena di post-processing YEBIS ricostruita dalla descrizione del
  fornitore e parametrizzata dalle 202 chiamate DOF del Lua. Manca il modello
  d'illuminazione vero e il resto di [`renderer.md`](renderer.md).

**Milestone "primo dialogo"** — ✅ **raggiunta** (sessione 3). Mappa `field_16`
dal `.pac`, `Event/Devil/Devil.lua.eu` eseguito verbatim su VM Lua, e la sua
battuta a schermo col font del gioco:

```
python tools/view.py extract/pac/field_16.ps3.pac \
    --event extract/.../Event/Devil/Devil.lua.eu --skip 14
```

La tesi del progetto — riusare gli script originali invece di tradurli — è
verificata, non più solo argomentata.

Il dialogo è completo di scelte: `Select` / `GetSelect` funzionano e il
riquadro usa la cornice vera del gioco.

**Milestone "la scena"** — ✅ **raggiunta** (sessione 4). Un evento gira sulla
**sua** mappa, composta per intero, con i **suoi** personaggi al posto e nel
modello che il disco dichiara, nell'inquadratura che lo script sceglie:

```
python tools/view.py extract/.../map/pac_data/D_8_2.ps3.pac.gz \
    --event extract/.../Event/mapevent/mapevent_d08_02.lua.eu --skip 40
```

Quello che l'ha resa possibile non era un metodo dell'API ma un **sistema di
riferimento**: la cella logica vale 1,6 come l'altezza di un personaggio, le
sezioni di un `.pac` sono schermi da comporre, e gli script parlano con
l'origine a un angolo. Vedi [`entities.md`](entities.md) e
[`format_pac.md`](format_pac.md).

**Milestone "il giro di gioco"** — ✅ **raggiunta** (sessione 5). Si sta su una
mappa con i suoi abitanti, si cammina di cella in cella, si attraversa un
passaggio e si arriva nell'altra mappa nel punto che il disco dichiara, si
parla con chi si ha davanti:

```
python tools/view.py play field_91
```

È la prima cosa del progetto che si **gioca** invece di guardarla: il punto
d'arrivo viene dalla cella `Exit` dell'altra mappa, il dialogo dallo script
`npcevent_*` dell'abitante, il muro da `MAPCOLLISION/*.DPK`. E ha portato con sé
la misura che mancava — `view.py walkabout` percorre a piedi tutte le 170 mappe.

Camminare ha anche chiuso la Fase 2 su un formato rimasto in sospeso e
corretto un numero inventato: il `.DPK` si è risolto al primo tentativo, e il
gradino che un personaggio sale non è «un ginocchio» ma **una casella**, come
tutto il resto di questo gioco.

Il valore corrente della misura, dopo le correzioni di sessione 6 (colonna
misurata invece che assunta, fondale sepolto, tutte le porte d'ingresso):

```
python tools/view.py walkabout

celle raggiunte a piedi         67%
abitanti raggiunti              97%      (il numero che conta)
passaggi con l'arrivo in piedi  365/369  = 99%
```

Il 67% delle celle non è un fallimento del 33%: il denominatore conta anche i
tetti e le cime dei muri, che infatti non si devono raggiungere.

## Fase 5 — Bring-up per aree

**È dove siamo.** Sottosistema per sottosistema, usando gli script come suite
di test: uno script che gira senza chiamare metodi non implementati è un
sottosistema completo.

Il confine non è più «cosa manca al sistema» ma «quanto del mondo regge quando
ci si cammina dentro», e la misura che lo giudica è `walkabout`. Le priorità
correnti stanno in [`TODO.md`](TODO.md), che è il documento da leggere per
primo a inizio sessione.
