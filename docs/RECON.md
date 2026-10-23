# 3D Dot Game Heroes — Ricognizione disco (Sessione 1)

Data: 2026-08-09/10
Sorgente: `3D Dot Game Heroes (Europe).iso` — 3.584.425.984 B
Disco masterizzato: **2010-03-25**, UDF 2.50, trophy ID `NPWR01180_00`

## 1. Struttura del supporto

Region table a offset 0x0: 2 regioni in chiaro, 1 "cifrata".

| Regione | Settori | Contenuto |
|---|---|---|
| 0 (plain) | 0x0 – 0x115F | metadati ISO9660/UDF |
| 1 ("enc") | 0x1160 – 0x18B49F | dati di gioco |
| 2 (plain) | 0x18B4A0 – 0x1AB4BF | `PS3_UPDATE/PS3UPDAT.PUP` (268 MB, firmware — irrilevante) |

**La regione 1 non è effettivamente cifrata** (entropia 0,09 bit/byte all'inizio,
sarebbe ~8,0 sotto AES): la ISO è in formato 3k3y/decrittata, region table
conservata ma payload in chiaro. Il layer di decrittazione SELF/disc-key resta
un modulo didattico opzionale, fuori dal percorso critico.

## 2. Lettura del filesystem

L'albero **ISO9660 tronca i nomi a 31 caratteri** (`..._lua.` → `.LU`, `.L`, `.E`).
I nomi reali stanno **solo nell'albero UDF**. Estrarre sempre via UDF:

```
7z x "…\3D Dot Game Heroes (Europe).iso" -o<dst> -y -r "*.lua.eu"
```

7-Zip segnala `Headers Error` / `Tail Size = 65536` (la region table in coda) ed
esce con codice 2: è **benigno**, l'estrazione è corretta. Ignorare l'exit code.

`tools/iso.ps1` implementa un lettore ISO9660 nativo — utile per sondaggi a
livello di LBA/settore, **non** per estrazione (nomi troncati).

## 3. Inventario

2.792 file, 3,07 GB sotto `PS3_GAME/USRDIR/`. Un solo eseguibile.

| Ext | N | MB | Formato | Difficoltà |
|---|---|---|---|---|
| `.bik` | 5 | 1193,2 | **Bink 1** (`BIKi`) | risolto (ffmpeg) |
| `.wav` | 326 | 638,3 | **RIFF PCM** 44,1 kHz 16-bit mono | risolto |
| `.tpk` | 763 | 623,3 | `TPKG`+`ps3` — texture package | **risolto** ([doc](format_tpk.md)) |
| `.gz` | 167 | 441,5 | **gzip** → `<nome>.ps3.pac` — mappe | **risolto** ([doc](format_pac.md)) |
| `.dsb` | 460 | 176,7 | `DSBF` — scene/model | **risolto** ([doc](format_dsb.md)) |
| `.dat` | 170 | 34,0 | `MAP_ALIGNMENT` — griglia logica, **little-endian** | mezzo risolto ([doc](format_pac.md)) |
| `.bin` | 2 | 21,6 | `EBOOT.BIN` + tabella font UTF-16BE | vedi §4 |
| `.dpk` | 171 | 5,4 | `MAPCOLLISION` — mesh di collisione | **risolto** ([doc](format_dpk.md)) |
| `.edt` | 90 | 5,0 | `EDTFILE1.9` — dati editor voxel | da RE |
| `.lua.eu` / `.lua` | 618 | 5,6 | **sorgente Lua in chiaro** | risolto |
| `.pkg` | 2 | 1,1 | `spkg`+`ps3` — shader package | da RE |
| `.spk` | 2 | 0,1 | `CGB` — **Cg binary** (RSX) | da RE |
| `.dds` | 2 | 0,3 | **DirectDraw Surface** standard | risolto |
| `.sav` | 3 | 0,6 | save editor, big-endian | da RE |

Formati standard o banali: **~2,3 GB su 3,07 GB (75%)**.

### Impronte di una toolchain Windows
- `data/MakeLuaDump.exe`, `data/EDT/Addition/AdditionEditCharMessage.exe` —
  utility di build x86, MSVC 2008 (VC90 CRT). Piccole, non parti del gioco.
- `data/ICONDATA/Thumbs.db` — cache thumbnail di Explorer finita sul master.
- `.dds` e Cg: pipeline asset di derivazione PC.

## 4. EBOOT.BIN

`SCE\0`, 22.601.208 B. SELF firmato, `key_revision = 0x0001` (gioco 2010 →
chiavi retail pubbliche), ELF interno 0x0158D478. Decrittabile offline verso un
ELF PPC64 big-endian. **Unico eseguibile del gioco**: nessun modulo PRX
aggiuntivo, nessun archivio SPU separato visibile a livello di filesystem.

## 5. Contenuto di un `.pac` (mappa)  ⟵ risolto, vedi [`format_pac.md`](format_pac.md)

`D_1_3.ps3.pac` → 963.072 B (gzip 5,0x). Wrapper attorno a uno o piu' blocchi
`DSBF` con **tabella stringhe leggibile**: scene graph con nomi.

```
D_1_3_00_00.ps3
dot_512_nm.dds / wall.dds / dot_floor_nm.dds / yka.dds     ← texture
d_kbe_01-fx / d_yka_01-fx                                  ← materiali
OPACITY                                                    ← parametro materiale
md_kbe_L0_00_00-mesh / md_hsr_L1_00_00-mesh                ← mesh (con LOD L0/L1)
md_kbe_L0_00_00-node / md_yka_00_00-node                   ← nodi gerarchia
```

Le texture sono referenziate per **nome `.dds`**, il che dà una chiave di join
diretta verso i pacchetti `TPKG`.

Il sospetto che i suffissi `_00_00` e `L0`/`L1` fossero cella e livello di
dettaglio si è poi rivelato esatto, e verificabile: il nome codifica la cella
in 12.097 mesh su 12.097.

## 6. Superficie API dello scripting  ⟵ risultato principale

618 file Lua, 5,57 MB di **sorgente in chiaro** (commenti giapponesi inclusi),
tutti contenuti in `all.lua.eu` (vedi §6.1). Misurato sul solo bundle, per non
contare due volte gli stessi call site: **497 metodi nativi**, **29.626 call
site**, su **8 classi host**.

> Una misura precedente riportava 501 metodi / 43.253 call site. Era gonfiata:
> analizzava bundle *e* file sciolti insieme, e usava regex invece di un lexer.
> L'insieme dei metodi è però risultato quasi identico (497 vs 501), il che dà
> fiducia sulla stabilità del risultato.

| Classe host | Metodi | Chiamate | Ruolo |
|---|---|---|---|
| `Object` | 297 | 14.999 | entità di gioco: nodi, animazioni, fase/stato, moto, collisione |
| `Event` | 176 | 13.136 | regia cutscene: dialoghi, camera, DOF, lock del player, audio |
| `PackageManager` | 3 | 1.351 | caricamento risorse (`addNodeListElement`) |
| `MapManager` | 1 | 72 | transizioni di mappa |
| `Boss` | 11 | 51 | logica boss |
| `observer`, `club`, `gimmick` | 9 | 17 | probabili alias di `Object` |

Metodi più frequenti: `:Print` (2.805), `:WaitContinue` (1.156), `:GetEventFlag`
(1.093), `:SetPhase` (1.291), `:AddNode` (1.281), `:AddAnimation` (916).

Firme complete inferite: [`lua_signatures.md`](lua_signatures.md) /
[`.json`](lua_signatures.json), header C++ generato in
[`generated/script_api.h`](../generated/script_api.h).

**Implicazione strategica.** Trama, dialoghi, eventi, NPC, logica dei boss e
progressione sono già disponibili come sorgente e sono *portabili verbatim*.
Non vanno reimplementati: va reimplementato l'host che espone quei 501 metodi.
Questo elenco è di fatto una specifica funzionale generata dalla macchina.

### 6.1 `all.lua.eu` è il bundle autoritativo

`data/all.lua.eu` (3.754.095 B, 190.695 righe) non è un dump di debug ma la
**concatenazione di 1.486 moduli** in ordine di caricamento, delimitati da
marcatori `-- Start <percorso>`. Contiene più moduli dei 618 file sciolti: i
file sciolti sono un sottoinsieme, probabilmente residui della build. Il bundle
è quindi sia il payload reale sia il **manifest dell'ordine di inizializzazione**.
Generato con ogni probabilità da `MakeLuaDump.exe`.

### 6.2 Il contratto del runtime è molto stretto

Tre proprietà misurate sull'intero corpus, tutte a favore della reimplementazione:

- **Zero libreria standard.** Nessuna occorrenza di `table.*`, `string.*`,
  `math.*`, `#`, varargs, `require`, `os.*`. Gli script sono una DSL
  completamente sandboxata: l'unico modulo stdlib usato è `coroutine`.
  → la versione esatta della VM Lua è quasi irrilevante; qualunque 5.x va bene.
- **Nessuna metatabella.** Zero `setmetatable`, `__index`, `loadstring`,
  `dofile` nel bundle. `Event:Metodo()` non è OO Lua: sono tabelle popolate
  direttamente con funzioni native dall'host. Dispatch banale da implementare.
- **Scripting a coroutine.** `coroutine.yield` è usato pervasivamente negli
  script di evento e di boss. `Event:Wait()` / `:WaitContinue()` sono punti di
  sospensione: l'host esegue ogni evento come coroutine e la riprende per frame.

Forma tipica di uno script (`Event/Guard/GuardAfter.lua.eu`):

```lua
function GuardAfterEvent()
    local Event = EventClass.Event;
    if (Event:GetEventFlag(EventFlag.scene_guardtomb) == 0) then
        Event:SetEventFlag(EventFlag.scene_guardtomb, 1);
        Event:StopBgm();
        Event:PlayBgm(soundList.SoundID.BGM_field02);
        return;
    end
end
```

Gli enum (`EventFlag.*`, `soundList.SoundID.*`) sono tabelle Lua definite dentro
il bundle: arrivano gratis, non vanno ricostruiti.

### 6.3 Encoding MISTO — insidia da tenere presente

Il corpus mescola UTF-8 e Shift-JIS **anche all'interno dello stesso file**:
in `all.lua.eu` ~11.837 righe UTF-8 e ~1.525 Shift-JIS pure; fra i file sciolti
514 UTF-8 e 20 Shift-JIS. Sono moduli scritti su macchine e in anni diversi.

Decodificare tutto come UTF-8 corrompe silenziosamente le stringhe giapponesi.
`tools/lua_lex.py::decode_lua()` decodifica **riga per riga** con fallback
UTF-8 → CP932. Lo split su `\n` è sicuro: in Shift-JIS il secondo byte di una
coppia non vale mai 0x0A.

### 6.4 I dialoghi sono stringhe letterali nel Lua

`Event:Print()` — il metodo più chiamato — riceve 2.639 stringhe letterali su
2.805 chiamate. **Il testo di gioco è nel sorgente Lua**, non in un archivio.

Due particolarità:
- Il testo inglese è memorizzato in **Latin fullwidth** (`ｔｈａｔ’ｓ ｎｏｔ
  ｅｎｏｕｇｈ ｍｏｎｅｙ．`), perché il font è una bitmap giapponese a
  larghezza fissa. Un port PC dovrà decidere se normalizzare a ASCII.
- 2.747 stringhe su 2.805 usano il fullwidth; **134 contengono ancora
  kana/kanji** nella build europea (stringhe non tradotte, probabilmente di
  debug — es. `/paてきをしゅつげんさせたよ`).

**Markup inline — censimento completo.** 9 codici, nessun carattere di
controllo, nessuna sequenza di escape. Il linguaggio è chiuso:

| Codice | Occorrenze | Interpretazione | Evidenza |
|---|---|---|---|
| `/r` | 2.770 | a capo dentro il riquadro | separa sempre 2-3 righe di testo |
| `/b` | 2.383 | fine blocco, attendi input | sempre in coda, seguito da `/co` o `/pl` |
| `/co` | 1.435 | chiudi il riquadro | terminatore dominante, sempre dopo `/b` |
| `/cl` | 1.422 | pulisci e continua sulla stessa finestra | in mezzo a messaggi lunghi |
| `/vn` | 857 | *voce* normale (ipotesi) | in testa, prima del nome del parlante |
| `/vh` | 387 | *voce* acuta (ipotesi) | idem |
| `/vl` | 25 | *voce* grave (ipotesi) | `/vlＢｌｕｓｅｙ：…` |
| `/pl` | 33 | terminatore alternativo a `/co` | sempre dopo `/b` |
| `/pa` | 2 | ignoto | solo su 2 stringhe giapponesi |

La famiglia `/vn` `/vh` `/vl` compare in testa alla battuta, subito prima del
nome del personaggio: quasi certamente il **tono del bip di testo** (il gioco
non ha doppiaggio, ma bip alla Zelda). Da confermare in Fase 3.

### 6.5 Tabelle costanti

Estratte da [`tools/lua_tables.py`](../tools/lua_tables.py) →
[`lua_tables.md`](lua_tables.md), header in
[`generated/script_enums.h`](../generated/script_enums.h). 12 enum, 2.216 membri.

| Enum | Membri | Rif. | Origine |
|---|---|---|---|
| `PackageId` (`package_manager.*`) | 1.354 | 5.447 | nativo |
| `MapId` (`map_manager.*`) | 216 | 409 | nativo |
| `GameDataMapFlag` | 195 | 228 | nativo |
| `SoundID` (`soundList.SoundID.*`) | 144 | 781 | nativo |
| `ItemId` (`item.Item.IL_*`) | 100 | 179 | nativo |
| `EventFlag` | 67 def. / 61 usati | 535 | **Lua, valori noti** (0..98) |
| `GameDataFlag` | 46 | 140 | nativo |
| `ActorType` (`actor_manager.AT_*`) | 33 | 6.674 | nativo |
| `SwordId` (`swordData.SwordData.SL_*`) | 24 | 104 | nativo |
| `LivingId` (`LIVING.*`) | 16 | 60 | nativo |
| `ObjectClassId` | 6 | 64 | nativo |

Solo `EventFlag` è definita in Lua e ha quindi i valori. Le altre tabelle
vivono nell'EBOOT: abbiamo i **nomi completi** dai siti d'uso, non i valori.
Non è bloccante — i valori sono liberi purché coerenti fra host e Lua — ma
vanno riconciliati con l'EBOOT prima di poter leggere salvataggi originali.

Convenzione utile scoperta: ogni costante enum ha **prefisso maiuscolo +
underscore** (`AT_`, `IT_`, `IL_`, `SL_`, `MS_`, `BGM_`, `SE_`, `ATTACK_`).
I campi dati non la seguono mai. È il discriminante che separa gli enum dagli
accessi a campo come `Boss.m_info.armHp`.

### 6.6 Anche la UI è dichiarativa in Lua

413 tabelle definite in Lua, 15.596 costanti foglia, così ripartite:
**137 descrittori di schermate UI**, 20 enum interi, 256 tabelle dati.

Ogni schermata (`EnemyAlbum`, `FieldMap`, i 20 `dungeonMapXX`, `Item`,
`Status`, …) è una tabella Lua con `TexturePackageName`, `ScenePackageName` e
il layout dei widget — fino a 421 chiavi per schermata. **L'intero layer di
interfaccia è dato, non codice**, e referenzia i pacchetti `TPK`/scena per
nome. Si porta senza riscriverlo, esattamente come gli script di evento.

Bonus: `Boss.m_info` espone 180 **parametri di bilanciamento dei boss**
(`armHp`, `armAttackDistance`, `armCutDownSpeed`, `accel`, …). Non è un enum
ma una struct popolata dal motore: elenco utile per il tuning del combattimento.

## 7. Ignoto / da chiarire

- Quanto uso viene fatto delle SPU (audio? culling? skinning?) — richiede l'ELF.
- Corpi dei record `DSBF`: mesh (vertici/indici), node (matrici, gerarchia),
  material, skin. Container e tabelle risolti, vedi [`format_dsb.md`](format_dsb.md).
  ~~`TPKG`~~ risolto, vedi [`format_tpk.md`](format_tpk.md).
- Formato voxel dell'editor (`.edt` / `.sav`) — cuore identitario del gioco.
- Semantica esatta dei 497 metodi: i nomi, le firme inferite e i siti di
  chiamata suggeriscono molto, ma i casi ambigui richiedono l'EBOOT.
- Valori numerici degli 11 enum nativi (§6.5).
- Semantica del markup di dialogo `/cl` `/b` `/co` `/pl` (§6.4), e se ne
  esistano altri codici oltre a quelli osservati.
- Ipotesi da verificare: il motore di base è l'**OROCHI di Silicon Studio**.
  Resta aperta: sapere che c'è YEBIS (§6.7) non la decide, perché YEBIS è solo
  la libreria di post-processing e può stare dentro un motore qualsiasi.

## 6.7 Il post-processing è YEBIS

Silicon Studio è prima di tutto un'azienda di **middleware**, non uno studio di
giochi: vende motori e librerie a terzi. Questo spiega la disciplina di
formato che abbiamo trovato — tabelle stringhe con oggetti nominati, lookup per
CRC32 tipici di un resource manager generico, UI dichiarativa, e un exporter
con numeri di versione presenti in ogni file.

Spiega anche il campo `'ps3\0'` nell'header `TPKG` e il suffisso `.ps3` nel
nome di ogni file del disco: la pipeline era **multipiattaforma** e marcava la
variante di target nel formato stesso.

**YEBIS**, il loro middleware di post-processing, è usato da 3D Dot Game Heroes
(fonte esterna, confermata dalla superficie API). I metodi esposti al Lua:

| Metodo | Note |
|---|---|
| `Event:BackupDof()` / `RestoreDof()` | 524 / 612 chiamate — fra i più usati dell'intera API |
| `SetDofApaerture(float, int)` | apertura del diaframma. **Il refuso è nell'originale** e va replicato: gli script lo chiamano così |
| `SetParamDepthofField(float, float, float)` | |
| `SetCaptureDOF()` | |
| `switchDofPointGaze()` / `resetDofPointGaze()` | fuoco che insegue un bersaglio |
| `createFairyGlareEffect(float, float, float)` | *glare* è una feature YEBIS |

### La descrizione del fornitore

La pagina di showcase YEBIS sul sito Silicon Studio (recuperata via Wayback
Machine) elenca 3D Dot Game Heroes e ne descrive così l'uso:

> *"Applied for vignetting and color modification to give a toy camera feel,
> and realistic defocusing effects that create the feeling of a miniature
> world. Also contributes to sparkling glare effects for light sources or
> water."*

È una specifica scritta dal fornitore, e le risorse sul disco corrispondono:

| Elemento della descrizione | Riscontro sul disco |
|---|---|
| defocusing / *miniature world* | l'intera famiglia DOF nell'API, fra i metodi più chiamati del gioco |
| glare su *light sources* | `shaders/Sun.dds`, `useSunStoneParameter()`, `createFairyGlareEffect()` |
| glare su *water* | `shaders/water_col.dds` e `ref_01.dds` — **l'unica cubemap del gioco**, la environment map dei riflessi |
| vignetting, *color modification* | nessuna texture o LUT dedicata: sta nel codice degli shader (`shaders.ps3.pkg`, `SasShader.ps3.spk` in Cg binario) |

**Conseguenza pratica, e non è secondaria.** Il *defocus* qui non è rifinitura
opzionale: è **identità visiva**. È l'effetto tilt-shift che fa leggere un
mondo di voxel come un diorama in miniatura — il motivo per cui il gioco
sembra quello che sembra. Toglierlo non significa avere una grafica meno
raffinata, significa avere un gioco che non somiglia più a 3D Dot Game Heroes.

Nella pianificazione dell'host, quindi, la catena di post-processing **non va
rimandata alla fase di rifinitura**: va messa vicino al primo render.

YEBIS è proprietario e non riutilizzabile, ma non serve riutilizzarlo:
sappiamo *quali* effetti servono e *con quale parametrizzazione*, perché è il
Lua stesso a pilotarli chiamata per chiamata. È una specifica del
post-processing ottenuta senza aprire l'EBOOT.

Nota a margine, **ipotesi smentita**: si era congetturato che "SAS" in
`SasShader.ps3.spk` stesse per *Standard Annotations and Semantics*, la
convenzione Microsoft per gli effetti `.fx`. Non è così: nei pacchetti shader
non compare **nessuna** stringa `Sas.`, e la convenzione dei nomi è tutta
interna (`at*` per gli attributi di vertice, `g*` per gli uniform). Cosa
significhi la sigla resta ignoto.

Il controllo però ha reso l'intera interfaccia del renderer — 1.200 programmi
Cg, 107 identificatori — documentata in [`renderer.md`](renderer.md).
