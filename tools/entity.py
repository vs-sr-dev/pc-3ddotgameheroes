"""
entity.py - il registro delle entita': chi c'e' nel mondo, dove sta, da che
parte guarda.

E' il livello che mancava fra lo script e il disegno. `host.py` sapeva gia'
inquadrare un NPC con `SetCameraAtBody`, ma non c'era nessun NPC da inquadrare;
`view.py` sapeva gia' disegnare un personaggio, ma solo come file, non come
qualcosa che sta in un posto. Qui in mezzo c'e' un registro: nomi, posizioni,
direzioni, pose, e il tempo che le fa muovere.

Non disegna e non esegue Lua: e' solo stato. Questo lo rende verificabile da
solo (`python entity.py`) e utilizzabile dai due lati senza dipendenze
circolari.

## Le quattro direzioni

Gli script girano i personaggi con un intero fra 0 e 3 - `SetNpcDirection`
(242 chiamate), `SetPlayerDirection` (149). Quale intero sia quale direzione
lo hanno deciso **due oracoli indipendenti che concordano**:

1. *Chi si gira e poi cammina, cammina avanti.* Su 81 coppie
   `SetXDirection(d)` ... `MoveX(dx, dz, ...)` prese dal corpus, la direzione
   0 va verso +Z in 34 casi su 45. E' la cella piu' popolata e la piu' netta.
2. *Chi parla a qualcuno lo guarda.* In `mapevent_f80` Pizzaro e Rosy sono
   creati alle stesse coordinate tranne la X (-1,6 e +1,6) e si parlano: lui
   passa a 3, lei a 2. Quindi 3 e' verso +X e 2 verso -X - e i due assi
   rimasti per 0 e 1 sono proprio quelli che dice l'oracolo meccanico.

Il risultato e' un'enumerazione ad assi accoppiati, `0/1` sull'asse Z e `2/3`
sull'asse X, non una rotazione in senso orario.

Da notare cosa **non** ha funzionato: l'ipotesi "l'NPC appena creato guarda il
giocatore" da' appena il 55%, cioe' poco piu' del caso. Non e' una regola:
`CreateNpc` li mette gia' orientati e `SetNpcDirection` serve a girarli per la
scena, non a puntarli verso di noi.

## L'unita' di misura del mondo

Una casella vale **1,6**. Lo dicono due misure che si incontrano:

- gli argomenti di `CreateNpc` sono multipli di 0,8 e per lo piu' di 1,6
  (`1.6`, `3.2`, `4.8`, `-9.6`...);
- ogni personaggio di `c_obj_all.ps3.dsb` e' alto **esattamente 1,60** con
  l'origine ai piedi (mediana su 31 modelli NPC).

Un personaggio e' alto una casella. E' la stessa scala, presa da due file che
non si conoscono.

## Le pose

I modelli non hanno scheletro: sotto ogni personaggio ci sono da 2 a 6 nodi
figli, ognuno un **personaggio intero** alto 1,6, distanziati di 2,0 lungo X
nella scena di authoring (162 distanze su 200 valgono esattamente 2,0). Sono
fotogrammi, non pezzi: il gioco anima scambiando la mesh, come un gioco a
sprite. Da qui il vocabolario dei suffissi: `01` fermo, `02_a` e `02_b` i due
passi del ciclo di camminata, `03` e oltre le pose speciali.

Lo conferma l'API: `SetNpcNode(nome, 0..3)` sceglie un figlio per ordinale -
`SetNpcNode("SwordPedestal", 1)` e' il piedistallo con la spada, `0` quello
vuoto.

## Il movimento non blocca

`MoveNpc` avvia uno spostamento e lo script prosegue. Si vede provando a usare
l'attesa che segue come cronometro: a parita' di velocita' (3,2) e di attesa
(0,5 s) le distanze percorse sono 1,6 - 3,2 - 4,8, cioe' l'attesa non misura
niente. Quindi il registro deve integrare il moto nel tempo, e lo fa in
`tick()`.

Uso:
  python entity.py            esegue le verifiche interne
"""
from __future__ import annotations

import math
import re

# Una casella. Vale sia per la griglia su cui gli script spostano le cose, sia
# per l'altezza di un personaggio: in questo gioco sono la stessa cosa.
TILE = 1.6

# Quanto dura un fotogramma del ciclo di camminata, in secondi. Era 0,25 e non
# veniva da nessun dato: usciva da un `int(walk * 4) % 2` scritto per avere due
# passi al secondo. Il disco lo dichiara, ed e' **0,3**: gli attori del
# minigioco portano un `local StepWait` e vale 0,3 in tutti e dodici, che e'
# tutta la popolazione che lo scrive. Vedi enemy_motion().
STEP_WAIT = 0.3

# direzione dichiarata -> versore di mondo (vedi il docstring: 0/1 su Z,
# 2/3 su X)
DIRS = ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0))

# Il davanti del modello. Non e' +Z come verrebbe da assumere: guardando
# `c_npc_05` da -Z (`view.py char c_npc_05 --azim 180`) si vede la faccia,
# baffi e tutto, e da +Z la nuca. I personaggi sono authorati **verso -Z**,
# cioe' gia' girati nella direzione 1.
#
# E' l'unica cosa di questo modulo che nessun dato poteva dire: le direzioni
# le decidono gli script, il davanti lo decide la mesh, e per saperlo bisogna
# guardarla.
FRONT = (0.0, 0.0, -1.0)
ANGLES = (180.0, 0.0, 90.0, -90.0)


def facing_angle(d: int) -> float:
    """Gradi di rotazione attorno a Y per la direzione `d`."""
    return ANGLES[d % 4]


# --------------------------------------------------------------- i modelli

# Il nome che lo script usa (`"PrincessBugSP"`, `"YoungWomana4_150"`) e' un
# **identificativo logico**, non un nome di file: non compare in nessun dato
# del disco fuori dagli script. La tabella che lo lega a un modello la teneva
# il C++, quindi sta nell'EBOOT (Fase 3).
#
# Quello che il disco dichiara da solo e' l'inventario dall'altro capo:
# `Character/c_obj_all.ps3.dsb` contiene **31** personaggi `c_npc_NN`, 39
# nemici `c_enm_NN`, 7 giocatori `c_ply_NN` e 30 oggetti di evento `i_evt_NN`.
# E gli archetipi che gli script nominano, una volta tolti i suffissi di
# istanza, sono una trentina. I due conti si somigliano, ma somigliarsi non e'
# una prova: finche' l'EBOOT non parla, l'assegnazione qui sotto e'
# **provvisoria**.
#
# La tabella vera, e non e' venuta dall'EBOOT: **la dichiarano i nomi dei file
# di script**. I 237 script sotto `Event/npcevent_*` si chiamano
# `npcevent_n<NN><archetipo><id>.lua.eu` - `npcevent_n05oldmana7_010`,
# `npcevent_n11imperialguarda3_320` - e quel numero e' l'indice del modello.
#
# Che sia una tabella e non una coincidenza lo dice la **biiezione**: su 237
# script, zero indici con piu' di un archetipo e zero archetipi con piu' di un
# indice. E si vede: `view.py char c_npc_10,c_npc_16,c_npc_14` mostra una
# corona con manto d'ermellino, una gallina bianca con la cresta rossa e un
# cane marrone, dove la tabella dice `king`, `chicken`, `dog`.
#
# Il primo indizio era arrivato per caso: `c_npc_05` disegnato aveva l'aria di
# un vecchio, e `n05` e' `oldman`.
NPC_MODELS = {
    'WiseMan1': 1, 'Merchant': 2, 'YoungMan': 3, 'YoungWoman': 4, 'OldMan': 5,
    'OldWoman': 6, 'Girl': 7, 'Boy': 8, 'King': 10, 'ImperialGuard': 11,
    'LadysMaid': 12, 'Dog': 14, 'Cat': 15, 'Chicken': 16, 'PrincessBug': 19,
    'WiseMan2': 20, 'WiseMan3': 21, 'WiseMan4': 22, 'WiseMan5': 23,
    'WiseMan6': 24, 'BlackSmith': 25, 'GoblinRed': 26, 'Spelunker': 31,
}

# *Sessione 12.* La tabella qui sopra non e' piu' provvisoria: il disco la
# **dichiara**, in `all.lua.eu`, con 1.279 righe `addNodeListElement` che
# mandano ogni costante nativa sul nome del proprio nodo (vedi nodes.py). E
# la conferma su 20 archetipi su 22 - gli altri due, che sono qui sotto,
# sbagliavano perche' il numero nel nome dello script di *dialogo* e quello
# del *modello* non sono sempre la stessa numerazione:
#
#   princessbug  il disco dice `c_npc_26`, e `NP_NPC_19` e `NP_NPC_26` sono
#                proprio i due nodi che la tavola scambia. La sessione 8
#                aveva gia' indicato `c_npc_19`..`c_npc_26` come il punto
#                debole della rubrica: era questo.
#   goblinred    il disco dice `c_enm_12`, che e' un modello di **nemico**.
#                I goblin rossi amichevoli del villaggio riusano il goblin
#                rosso che si combatte, ed e' il motivo per cui sotto
#                `Object/` non esiste nessun `N26GoblinRed`: non serviva.
#                Non e' uno scarto di un numero, e' un cambio di famiglia -
#                nessuna deduzione fatta dentro la sola `c_npc` poteva
#                arrivarci.
#
# Si ricalcola con `nodes.npc_models(data)`; qui e' trascritta perche' questo
# modulo non legge Lua (vedi il docstring in testa).
NPC_DECLARED = {'princessbug': 'c_npc_26', 'goblinred': 'c_enm_12'}

# Come si chiama uno script di NPC di mappa: `npcevent_n05oldmana1_300`, cioe'
# indice del modello, archetipo, identificativo. I dieci file che non hanno
# l'indice - `npcevent_graundc1_030`, `npcevent_signboardc1_180` - non sono
# personaggi: sono il terreno e un cartello.
NPC_SCRIPT = re.compile(
    r'npcevent_n(\d\d)([a-z0-9]+?)([a-z]\d{1,2}_\d{3})\.lua', re.I)

# Il nome esatto, con le maiuscole giuste, sta **dentro** lo script: 151 dei
# 243 si nominano da soli (`setnpccamerac("OldMana1_300")`). Per gli altri si
# ricompone dalla tabella, che e' la stessa scrittura che usano gli script.
QUOTED = re.compile(r'"([A-Za-z]\w*)"')


def npc_directory(root) -> dict:
    """La rubrica degli NPC di mappa: identificativo -> chi e', cosa mostra,
    cosa dice.

    Le celle della griglia logica dichiarano 236 posti ma portano solo un
    identificativo (`a1_300`): non dicono ne' chi ci sta ne' che aspetto ha.
    Lo dicono i 243 script `npcevent_*`, uno per abitante, che portano nel
    **nome del file** il modello e l'archetipo e nel corpo il dialogo.

    Rimettere insieme le due meta' popola le mappe di abitanti con nome,
    faccia e battuta - 225 posti su 236 - senza aspettare che un evento li
    nomini.
    """
    import pathlib

    root = pathlib.Path(root)
    canon = {v: k for k, v in NPC_MODELS.items()}
    out: dict[str, dict] = {}
    for p in sorted((root / 'Event').glob('npcevent_*/*.lua*')):
        m = NPC_SCRIPT.match(p.name)
        if not m:
            continue
        idx, arch, ident = int(m.group(1)), m.group(2), m.group(3).lower()
        name = (canon.get(idx) or arch.title()) + ident
        try:
            text = p.read_bytes().decode('utf-8', 'replace')
        except OSError:                                          # noqa: BLE001
            text = ''
        for q in QUOTED.findall(text):
            if q.lower() == name.lower():
                name = q
                break
        out[ident] = {'index': idx, 'archetype': arch, 'name': name,
                      'model': NPC_DECLARED.get(arch.lower(),
                                                f'c_npc_{idx:02d}'),
                      'script': p}
    return out

# Gli archetipi che gli script nominano ma nessun `npcevent` battezza -
# `Princess`, `Priest`, `WiseMan1`..`WiseMan6`, `Landlord` - restano senza
# indice dichiarato e prendono uno slot **stabile per nome**: non e'
# l'assegnazione del gioco, e' un segnaposto che non mente su cosa sia. Sono
# comparse di eventi principali, che il codice creava senza passare dal
# meccanismo degli NPC di mappa.
#
# La tentazione da cui guardarsi: undici directory sotto `Event/` hanno un
# `<Nome>.ps3.dsb`, e una si chiama `Priest` come un nome di `CreateNpc`. Ma
# `Event/Priest/Priest.ps3.dsb` misura 0,96 x 0,64 x 0,96 e usa `cliff_01.dds`:
# e' la **scenografia** dell'evento del prete, non il prete. Un personaggio di
# questo gioco e' alto 1,60 e sta su `dot_base.dds`. La coincidenza di nome
# sarebbe passata per una risoluzione riuscita se non si fossero guardati i
# numeri.
PROPS = ('OrbAltar', 'SwordPedestal', 'BossMarker', 'Altar', 'Pedestal')


# La coda di un nome di NPC: l'identificativo con cui la mappa lo colloca.
ID_TAIL = re.compile(r'([a-z]\d{1,2}_\d{3})$', re.I)


def bestiary(root) -> list[dict]:
    """I nemici che il disco dichiara: 46, con nome, modello e habitat.

    Il TODO li dava come «li crea il codice», e diceva di guardare i parametri
    delle celle `EnemyObserver` prima di concludere che serve l'EBOOT. Quelle
    celle non portano nemici - portano un `-gNNN`, cioe' un numero di stanza -
    ma il censimento sta altrove ed e' in chiaro: l'**album dei nemici**,
    `UserInterface/EnemyView/EnemyView.lua.eu`, e' un descrittore come gli
    altri e dichiara la tabella intera.

        Num=5003                    identificativo, da 5002 a 5082
        NodeStrings="c_enm_01_01"   il modello, che e' un nodo e non un file
        NameStrings="Killer Rabbit" il nome, gia' in inglese
        LivingId=LIVING.FIELD_GRASS dove vive
        ItemId=item.Item.IL_RED_APPLE  cosa lascia cadere

    Serve pero' leggerlo con le tabelle permissive, perche' `LIVING` e
    `GameDataFlags` sono costanti native che nessuno script definisce: senza,
    il file non gira affatto e la tabella sembra non esserci.
    """
    import pathlib

    import ui

    root = pathlib.Path(root)
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    d = ui.descriptor_file(data / 'UserInterface/EnemyView/EnemyView.lua.eu')
    blk = (d.get('EnemyView') or {}).get('EntryEnemyArray') or {}
    if isinstance(blk, list):
        rows = blk
    else:
        rows = [v for _, v in sorted((k, v) for k, v in blk.items()
                                     if isinstance(k, int))]
    return [{'num': int(r.get('Num', 0)),
             'node': str(r.get('NodeStrings', '')),
             'name': str(r.get('NameStrings', '')),
             'living': str(r.get('LivingId', '')),
             'item': str(r.get('ItemId', ''))}
            for r in rows if isinstance(r, dict) and 'NodeStrings' in r]


def enemy_models(root) -> dict:
    """Dove sta il modello di ogni nemico del bestiario.

    Due posti, e la divisione ha un senso: i nemici comuni sono **nodi** dentro
    `Character/c_obj_all.ps3.dsb` - la stessa forma degli NPC, che sono nodi
    dentro una scena sola - mentre i **boss** hanno un file per uno
    (`c_bos_01_all.ps3.dsb`). Che il campo si chiami `NodeStrings` lo diceva
    gia': non e' un nome di file.
    """
    import pathlib

    import dsb

    root = pathlib.Path(root)
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    p = data / 'Character/c_obj_all.ps3.dsb'
    names = set()
    if p.exists():
        f = dsb.Dsb(p.read_bytes(), str(p))
        names = {f.object(i)['name'] for i in range(f.n_objects)}
    out = {}
    for e in bestiary(root):
        nd = e['node']
        if nd in names or f'{nd}-node' in names:
            out[nd] = 'c_obj_all'
        elif (data / f'Character/{nd}.ps3.dsb').exists():
            out[nd] = f'{nd}.ps3.dsb'
    return out


def actor_directory(root) -> dict:
    """Chi e' ogni identificativo di attore, cioe' il campo +0x10 della griglia.

    La griglia logica mette in ogni cella un numero che finora era fra i "campi
    ignoti", e che invece e' l'**attore** che ci vive. La numerazione e' unica
    per tutto il gioco, e a partirla sono tre file che non si conoscono:

    - i **nemici** li dichiara l'album (`UserInterface/EnemyView`), 5002-5082,
      e 45 dei suoi 46 si ritrovano in mappa. Il solo mai piazzato e' 5073;
    - gli **NPC** cadono su `5047 + NN`, con `NN` l'indice del modello
      `c_npc_NN`: venti valori consecutivi lo rispettano esattamente, e sulle
      celle la regola misura il 94,2% (226 su 240). E' un oracolo in piu'
      sulla tabella archetipo->modello, che la sessione 4 aveva dedotto per
      un'altra strada - i nomi dei 237 script `npcevent_n<NN>...` - e le sue
      poche eccezioni cadono tutte sui modelli alti (`c_npc_19`..`c_npc_26`),
      cioe' proprio quelli che quella deduzione aveva risolto peggio;
    - gli **oggetti di mappa** stanno sotto 5000, e li' il valore e' costante
      per classe di cella in 175 casi su 195 (89,7%). Le eccezioni non sono
      rumore: sono le celle la cui "classe" e' in realta' il nome di una mappa
      di destinazione (`D_7_1_2`, `Field_50`), che oggetti non sono.

    Restituisce `{id: {'kind', 'name', 'model'}}`.
    """
    import pathlib

    root = pathlib.Path(root)
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    out = {}
    known = enemy_models(data)
    for e in bestiary(data):
        out[e['num']] = {'kind': 'nemico', 'name': e['name'],
                         'model': e['node'], 'living': e['living'],
                         'draw': _enemy_draw(e['node'], known)}
    # Gli NPC dopo, ma senza sovrascrivere: dove i due intervalli si toccano
    # (5060 e' `Fuelle`, ed e' anche 5047+13) l'album e' la fonte piu' forte,
    # perche' dichiara invece di essere dedotto.
    for nn in range(1, 32):
        out.setdefault(5047 + nn, {'kind': 'npc', 'name': f'c_npc_{nn:02d}',
                                   'model': f'c_npc_{nn:02d}', 'living': ''})
    for i, nome in OBJECT_ACTORS.items():
        out.setdefault(i, {'kind': 'oggetto', 'name': nome, 'model': '',
                           'living': ''})
    # E i due che l'album non elenca perche' non si registrano nel bestiario.
    # Vanno dopo, e con `setdefault`, per la stessa ragione degli NPC: dove una
    # fonte dichiara, non la si scavalca con una lettura.
    for i, a in LUA_ACTORS.items():
        out.setdefault(i, {'kind': 'nemico', 'name': a['name'],
                           'model': a['model'], 'living': '',
                           'draw': _enemy_draw(a['model'], known)})
    return out


def enemy_motion(root) -> dict:
    """Come si anima un nemico, secondo i file del minigioco.

    ATTENZIONE - la premessa di questa funzione e' **caduta in sessione 11**, e
    va detto qui perche' e' scritta qui sotto: non e' vero che «il gioco
    implementa i nemici in C++». Li implementa in Lua, per esteso, e sono tutti
    e 46 quelli dell'album: stanno in `all.lua.eu`, che e' la concatenazione di
    **869 sorgenti** con l'albero delle cartelle nei commenti (`-- Start
    ../lua/Object/06Bee.lua`). Trentasette dei 46 portano il moto completo -
    fasi, velocita', direzione, inseguimento; i nove restanti sono gli otto
    boss piu' Guardian, che in Lua hanno la sola inizializzazione.

    Questa funzione resta valida per cio' che misura (pose e periodo dal
    minigioco, verificati sui nomi), ma non e' piu' «l'unica fonte»: la fonte
    migliore e' il file del nemico stesso. Vedi docs/TODO.md, sessione 11.

    ----

    Il disco porta **dodici** nemici scritti in Lua anche altrove:
    sono gli attori del minigioco Block Defence
    (`data/MiniGame/NNMG<nome>.lua.eu`), che riusa i modelli del gioco vero. E
    li riusa per numero, non per copia: `MGBee` carica `EN_ENEMY_06_04_a`, che
    e' esattamente il `NodeStrings` che l'album da' a `Killer Bee`.

    L'aggancio si fa sul numero di modello e si verifica sui **nomi**, che
    nessuno dei due file prende dall'altro: `MGSkelton` cade su `Soldier
    Bones`, `MGWood` su `Evil Tree`, `MGHagureSlime` su `Crystal Slime`.
    Dodici su dodici.

    Da li' si leggono due cose che altrimenti andrebbero inventate:

    - **le pose del ciclo**, che non sono le stesse per tutti. `02_a`/`02_b` e'
      il caso comune ma non la regola: il coniglio alterna `01` e `03`, il
      fantasma `01` e `06`, l'ape `04_a` e `04_b`, l'ombra parte da `06`;
    - **il periodo**, `StepWait`, che i file dichiarano in secondi.

    Quello che nel **minigioco** non si legge e' come si spostano nel mondo:
    li' camminano verso la torre con un `BlockDefenceMove()` nativo, che di quel
    minigioco e' proprio la regola. Da qui la conclusione di sessione 8 - «il
    pattugliamento non e' dichiarato» - che valeva per questi dodici file e che
    sessione 11 ha ribaltato guardando i nemici veri: `06Bee.lua` dichiara
    `MoveArea = 10.0` con il commento 出現位置からの行動可能範囲, *il raggio
    d'azione dal punto di comparsa*, e lo usa in `IsActorMoveArea`.

    Restituisce `{id d'album: {'poses': [...], 'wait': float, 'flies': bool}}`.
    """
    import pathlib

    root = pathlib.Path(root)
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    mg = data / 'MiniGame'
    if not mg.exists():
        return {}
    flies = {}
    p = mg / 'BlockDefenceEnemyData.lua.eu'
    if p.exists():
        text = p.read_text('utf-8', 'replace')
        for m in re.finditer(r'Name\s*=\s*"(\w+)".*?Type\s*=\s*(\d+)',
                             text, re.S):
            flies[m.group(1)] = m.group(2) == '1'
    by_model = {}
    for e in bestiary(data):
        m = re.match(r'(c_enm_\d+)', e['node'])
        if m:
            by_model.setdefault(m.group(1), []).append(e['num'])
    out = {}
    for f in sorted(mg.glob('*.lua.eu')):
        name = re.sub(r'^\d+', '', f.stem.replace('.lua', ''))
        if name not in flies:
            continue
        text = f.read_text('utf-8', 'replace')
        nodes = re.findall(r'AddNode\(package_manager\.EN_ENEMY_(\w+)\)', text)
        if not nodes:
            continue
        wait = re.search(r'StepWait\s*=\s*([\d.]+)', text)
        idx = re.match(r'(\d+)_', nodes[0])
        poses = [n.split('_', 1)[1] for n in nodes if '_' in n]
        for num in by_model.get(f'c_enm_{idx.group(1)}', []) if idx else []:
            out[num] = {'poses': poses,
                        'wait': float(wait.group(1)) if wait else None,
                        'flies': flies[name]}
    return out


def _enemy_draw(node: str, known: dict) -> str:
    """Da `NodeStrings` al modello che il disegnatore sa aprire.

    L'album non nomina il personaggio ma **una sua posa**: `c_enm_01_01` e
    `c_enm_06_04_a` sono nodi figli, cioe' fotogrammi, ed e' coerente con la
    lettura di sessione 4 - i personaggi non hanno scheletro, i figli sono
    pose intere. Per metterne uno nel mondo serve la radice, e la posa la
    sceglie chi lo anima, come per gli NPC.

    I nove boss sono l'eccezione e hanno un file per uno; li' il nome e' gia'
    la radice, e va solo qualificato con la cartella.
    """
    m = re.match(r'(c_enm_\d+)_', node)
    if m:
        return m.group(1)
    f = known.get(node)
    return f'Character/{f}' if f and f.endswith('.dsb') else node


# Gli identificativi di attore sotto 5000 che una classe di cella nomina, e
# quindi si leggono senza congetture. Sono quelli su cui la costanza per classe
# e' totale: ognuno di questi valori compare **solo** con queste classi.
OBJECT_ACTORS = {
    4100: 'osservatore',       # `observer`, `Observer`, `SwitchObserver`,
                               # `EnemyObserver`, `Warp` - 706 celle
    4101: 'solido',            # `Exit`, `destructionWall`, `WarpDoor`,
                               # `PitFall`, `BlackHole`, `WoodDoor` - 503 celle
    4115: 'grilletto',         # `mazeforest`, `springfairy`, e le celle che
                               # nominano una funzione di evento - 168 celle
}


# I due attori sopra 5000 che l'album **non** elenca, e che a dichiarare e' il
# codice di gioco in Lua (`all.lua.eu`, cartella `../lua/Object/`).
#
# Che manchino dall'album non e' una lacuna del nostro percorso: nessuno dei
# due chiama `setBookRegistInfo`, cioe' **non si registrano nel bestiario** -
# un masso e una trappola non sono mostri da schedare. L'album dichiara i 46
# che si registrano, ed e' esatto; questi due vivono accanto a loro nella
# stessa numerazione perche' sono `AT_ENEMY` a tutti gli effetti.
#
#   5024 -> `08RockFall.lua`, che carica `EN_ENEMY_08` = `c_enm_08`
#   5080 -> `69Togetoge.lua`, che carica `EN_ENEMY_39_01` = `c_enm_39_01`
#
# Il primo conferma da un terzo file la deduzione della sessione 10 - il buco
# di un tratto a scarto costante - e il nome del file dice pure cosa fa:
# *Rock**Fall***, il masso che cade. Vedi walk.py e docs/walk.md.
LUA_ACTORS = {
    5024: {'name': 'Falling Rock', 'model': 'c_enm_08', 'lua': '08RockFall'},
    5080: {'name': 'Togetoge', 'model': 'c_enm_39_01', 'lua': '69Togetoge'},
}


def archetype(name: str) -> str:
    """Toglie dal nome i suffissi di istanza e lascia il personaggio.

    Gli script distinguono le copie con tre suffissi diversi, tutti visibili
    nel corpus: `a4_150` (mappa piu' numero progressivo), `SP`/`SP1`..`SP7`
    (le comparse di una scena speciale), e una lettera finale (`PrincessBugB`).
    Sotto restano una trentina di archetipi.
    """
    n = re.sub(r'[a-z]\d*_\d+$', '', name)     # YoungWomana4_150 -> YoungWoman
    n = re.sub(r'SP\d*$', '', n)               # PrincessBugSP3   -> PrincessBug
    n = re.sub(r'(?<=[a-z])[A-Z]\d*$', '', n)  # PrincessBugB1    -> PrincessBug
    n = re.sub(r'(?<=[a-z])e\d*$', '', n)      # Merchante1       -> Merchant
    return n or name


def model_for(name: str) -> str:
    """Il modello da disegnare per un nome di script.

    Restituisce o un percorso relativo di file, o la radice di un personaggio
    dentro `c_obj_all.ps3.dsb`. Vedi sopra perche' la seconda strada e'
    provvisoria.
    """
    a = archetype(name)
    if a.lower() in NPC_DECLARED:
        return NPC_DECLARED[a.lower()]
    if a in NPC_MODELS:
        return f'c_npc_{NPC_MODELS[a]:02d}'
    family, count = ('i_evt', 34) if any(p in a for p in PROPS) else ('c_npc', 31)
    # Somma dei caratteri: stabile, indipendente dalla versione di Python
    # (`hash()` di una stringa non lo e'), e sufficiente a non far collassare
    # due archetipi diversi sullo stesso modello nel corpus reale.
    slot = sum(ord(c) * (i + 1) for i, c in enumerate(a)) % count + 1
    return f'{family}_{slot:02d}'


# --------------------------------------------------------------- le entita'

class Entity:
    """Qualcosa che sta nel mondo: il giocatore, un NPC, un oggetto di evento.

    `pos` e' in unita' di mondo, con Y verso l'alto e l'origine ai piedi -
    la stessa convenzione dei modelli, cosi' mettere un personaggio a terra
    vuol dire `y = 0` e basta.
    """
    __slots__ = ('name', 'kind', 'pos', 'facing', 'visible', 'node',
                 'model', 'goal', 'speed', 'walk', 'created', 'script',
                 'frames', 'step')

    def __init__(self, name: str, pos=(0.0, 0.0, 0.0), facing: int = 0,
                 kind: str = 'npc', model: str | None = None):
        self.name = name
        self.kind = kind
        self.pos = [float(v) for v in pos]
        self.facing = int(facing) % 4
        self.visible = True
        self.node = None          # posa esplicita, se SetNpcNode l'ha scelta
        self.model = model if model is not None else model_for(name)
        self.goal = None          # destinazione dello spostamento in corso
        self.speed = 0.0
        self.walk = 0.0           # fase del ciclo di camminata, in secondi
        self.created = False      # nato da CreateNpc, non gia' sulla mappa
        self.script = None        # il suo `npcevent_*`, se la mappa lo ospita
        # I due fotogrammi del ciclo, quando non sono quelli soliti. I 31
        # modelli NPC hanno tutti `02_a`/`02_b`, ma **dodici nemici su 37 no**:
        # quattro camminano con `04_a`/`04_b` e otto non hanno nessun paio.
        # Vedi enemy_motion() per chi lo dichiara.
        self.frames = None
        self.step = STEP_WAIT     # quanto dura un fotogramma, in secondi

    # -- moto

    @property
    def moving(self) -> bool:
        return self.goal is not None

    def move_to(self, goal, speed: float) -> None:
        """Avvia uno spostamento. Non blocca: vedi il docstring del modulo."""
        self.goal = [float(v) for v in goal]
        self.speed = abs(float(speed))

    def move_by(self, delta, speed: float) -> None:
        self.move_to([p + d for p, d in zip(self.pos, delta)], speed)

    def stop(self) -> None:
        self.goal, self.speed = None, 0.0

    def tick(self, dt: float) -> None:
        if self.goal is None:
            return
        self.walk += dt
        d = [g - p for g, p in zip(self.goal, self.pos)]
        dist = math.sqrt(sum(v * v for v in d))
        step = self.speed * dt
        if dist <= step or dist == 0.0 or self.speed == 0.0:
            # velocita' nulla vuol dire "mettilo li'": nel corpus `MovePlayer`
            # ha 6 chiamate con velocita' 0, e sono cambi di posizione secchi.
            self.pos = list(self.goal)
            self.stop()
            return
        self.pos = [p + v / dist * step for p, v in zip(self.pos, d)]

    # -- come si disegna

    @property
    def angle(self) -> float:
        return facing_angle(self.facing)

    def pose(self) -> str:
        """Quale posa mostrare, come suffisso del nodo figlio.

        La posa esplicita di `SetNpcNode` vince su tutto - e' una scelta dello
        script. Altrimenti: fermo la posa `01`, in movimento i due passi che
        si alternano.
        """
        if self.node is not None:
            return f'#{self.node}'
        if self.frames:
            rest, cycle = self.frames[0], self.frames[1:]
            if not self.moving or not cycle:
                return rest
            return cycle[int(self.walk / max(self.step, 1e-3)) % len(cycle)]
        if self.moving:
            return '02_a' if int(self.walk / STEP_WAIT) % 2 == 0 else '02_b'
        return '01'

    def __repr__(self) -> str:
        p = ', '.join(f'{v:.1f}' for v in self.pos)
        return (f'<{self.kind} {self.name} ({p}) dir {self.facing} '
                f'{self.model}{"" if self.visible else " nascosto"}>')


class World:
    """Il registro. Un giocatore, gli NPC per nome, e i tre interruttori di
    congelamento che gli script usano piu' di ogni altra cosa.

    `Pause`/`Play` (369 chiamate misurate), `PauseNpc`/`PlayNpc` (162),
    `PauseEnemy`/`PlayEnemy` (103) sono tutti senza argomenti: fermano una
    **classe** di entita', non una in particolare. E' il modo in cui un evento
    si prende la scena.
    """

    def __init__(self):
        self.player = Entity('@player', kind='player', model='c_ply_01')
        self.npcs: dict[str, Entity] = {}
        self.order: list[str] = []          # ordine di creazione, per il disegno
        self.frozen = {'npc': False, 'enemy': False, 'player': False}
        self.player_locked = False
        self.status_visible = True
        self.time = 0.0
        self.angle_stack: list[float] = []
        self.player_angle: float | None = None
        # Dove la mappa dice che stanno i suoi NPC, per identificativo, gia'
        # in coordinate locali. Lo riempie chi carica la mappa.
        self.spots: dict[str, tuple] = {}

    # -- popolazione

    def create(self, name: str, offset=(0.0, 0.0, 0.0)) -> Entity:
        """`CreateNpc(x, y, z, nome)`.

        Le coordinate sono **relative al giocatore**: nel corpus stanno fra
        -9,6 e +16,0 e sono multipli di 0,8, mentre le posizioni assolute
        (`SetPlayerPosition`) sono interi di casella fino a 89. Sono offset,
        non punti del mondo.

        La Y quasi sempre e' 0 (108 chiamate su 115), ed e' proprio questo a
        dire che il secondo argomento e' l'altezza: le 5 chiamate che valgono
        8,0 sono i due amanti sul balcone di `mapevent_f80`.
        """
        e = Entity(name, [p + o for p, o in zip(self.player.pos, offset)])
        e.created = True
        if name not in self.npcs:
            self.order.append(name)
        self.npcs[name] = e
        return e

    def get(self, name) -> Entity | None:
        """Un'entita' per nome. `None` se non c'e'.

        Gli script nominano anche NPC che stanno gia' sulla mappa e che
        `CreateNpc` non ha creato: sono 98 nomi distinti contro 40 creati. Chi
        chiama deve saper reggere il `None`, che e' un dato - dice quali NPC
        vengono dalla mappa e non dallo script.
        """
        if name is None:
            return None
        if name == '@player':
            return self.player
        return self.npcs.get(str(name))

    def require(self, name: str) -> Entity:
        """Come `get`, ma se il nome non c'e' lo materializza.

        Serve perche' un evento puo' girare un NPC che nessuno script ha
        creato: sta gia' sulla mappa. Se la mappa ne dichiara il posto - vedi
        `spots`, che arriva da `mapdat.npc_spots` - lo si mette li' e conta
        come collocato; altrimenti resta senza posizione e non si disegna.
        Meglio una chiamata contata che una persa, ma non a costo di
        inventarsi dove sta.
        """
        e = self.get(name)
        if e is not None:
            return e
        e = self.create(str(name))
        e.created = False
        m = ID_TAIL.search(str(name))
        spot = self.spots.get(m.group(1).lower()) if m else None
        if spot is not None:
            e.pos = list(spot)
            e.created = True
        return e

    def visible_entities(self) -> list[Entity]:
        """Chi si puo' disegnare: solo chi ha una posizione che qualcuno ha
        davvero dichiarato.

        Un NPC nato da `CreateNpc` sta a un offset dal giocatore, e
        quell'offset e' un dato del disco. Uno arrivato da `require` no: lo
        script lo nomina perche' sta gia' sulla mappa, e dove stia non lo dice
        nessun file che sappiamo leggere. Metterlo ai piedi del giocatore lo
        renderebbe **visibile e sbagliato**, che e' peggio di assente: l'unica
        cosa che un'immagine cosi' insegna e' una posizione inventata.
        """
        out = [self.player] if self.player.visible else []
        out += [self.npcs[n] for n in self.order
                if n in self.npcs and self.npcs[n].visible
                and self.npcs[n].created]
        return out

    def unplaced(self) -> list[Entity]:
        """Nominati dagli script ma senza posizione: la lista della spesa di
        chi vorra' risolvere il collocamento degli NPC di mappa."""
        return [self.npcs[n] for n in self.order
                if n in self.npcs and not self.npcs[n].created]

    # -- il tempo

    def frozen_for(self, e: Entity) -> bool:
        if e.kind == 'player':
            return self.frozen['player'] or self.player_locked
        return self.frozen[e.kind if e.kind in self.frozen else 'npc']

    def tick(self, dt: float) -> None:
        """Un fotogramma di mondo.

        Il congelamento ferma il **moto**, non lo script: `Pause()` in questo
        gioco significa "smetti di far vivere il mondo mentre parlo", ed e'
        infatti quasi sempre la prima riga di un evento.
        """
        self.time += dt
        for e in [self.player] + list(self.npcs.values()):
            if not self.frozen_for(e):
                e.tick(dt)

    def __repr__(self) -> str:
        return f'<World {len(self.npcs)} npc, t={self.time:.1f}s>'


# ------------------------------------------------------------- verifiche

def _check() -> int:
    """Le proprieta' che il registro deve rispettare, messe alla prova.

    Non sono unit test di cortesia: ognuna e' una cosa dedotta dai dati, e se
    smette di valere e' la deduzione a essere sbagliata.
    """
    bad = 0

    def ok(cond, what):
        nonlocal bad
        print(f'  {"ok  " if cond else "NO  "}{what}')
        bad += not cond

    # le direzioni sono accoppiate a due a due su assi opposti
    for a, b in ((0, 1), (2, 3)):
        v, w = DIRS[a], DIRS[b]
        ok(all(abs(x + y) < 1e-9 for x, y in zip(v, w)),
           f'direzione {a} e {b} sono opposte')
    ok(abs(sum(x * y for x, y in zip(DIRS[0], DIRS[2]))) < 1e-9,
       'gli assi 0/1 e 2/3 sono perpendicolari')
    # l'angolo deve portare il davanti del modello sul versore della direzione
    for d, v in enumerate(DIRS):
        a = math.radians(facing_angle(d))
        c, s = math.cos(a), math.sin(a)
        got = (c * FRONT[0] + s * FRONT[2], 0.0, -s * FRONT[0] + c * FRONT[2])
        ok(all(abs(x - y) < 1e-6 for x, y in zip(got, v)),
           f'l angolo della direzione {d} porta il davanti su {v}')

    w = World()
    e = w.create('PrincessBugSP', (1.6, 0.0, 0.0))
    ok(e.pos == [1.6, 0.0, 0.0], 'CreateNpc mette l NPC a fianco del giocatore')
    w.player.pos = [16.0, 0.0, 8.0]
    e2 = w.create('Princess', (0.0, 0.0, 1.6))
    ok(e2.pos == [16.0, 0.0, 9.6], 'l offset e relativo al giocatore, non assoluto')

    # il moto arriva a destinazione, e ci arriva quando deve
    e.move_by((4.8, 0.0, 0.0), 3.2)
    for _ in range(90):                       # 1,5 s a 60 fotogrammi
        w.tick(1 / 60)
    ok(not e.moving and abs(e.pos[0] - 6.4) < 1e-4,
       'uno spostamento di 4,8 a velocita 3,2 finisce in 1,5 s')

    # congelato vuol dire fermo
    e.move_by((3.2, 0.0, 0.0), 3.2)
    w.frozen['npc'] = True
    before = list(e.pos)
    for _ in range(60):
        w.tick(1 / 60)
    ok(e.pos == before, 'PauseNpc ferma il moto degli NPC')
    w.frozen['npc'] = False
    for _ in range(120):
        w.tick(1 / 60)
    ok(not e.moving, 'PlayNpc lo fa ripartire e arrivare')

    # velocita' nulla: e' un salto, non un moto infinito
    e.move_by((9.6, 0.0, 0.0), 0.0)
    w.tick(1 / 60)
    ok(not e.moving, 'velocita 0 e uno spostamento secco')

    # gli archetipi si riducono come previsto
    for name, want in (('YoungWomana4_150', 'YoungWoman'),
                       ('PrincessBugSP3', 'PrincessBug'),
                       ('PrincessBugB1', 'PrincessBug'),
                       ('Merchante1', 'Merchant'),
                       ('ImperialGuarda1_231', 'ImperialGuard'),
                       ('Priest', 'Priest')):
        ok(archetype(name) == want, f'{name} -> {want}')
    ok(model_for('Priest').startswith('c_npc'),
       'Priest e una persona, non la scenografia del suo evento')
    # la tabella dichiarata dai nomi degli script, verificata a occhio
    for name, want in (('OldMana7_010', 2 + 3), ('Kinga1_010', 10),
                       ('ImperialGuarda3_320', 11), ('Doga2_010', 14),
                       ('Chickena3_010', 16), ('Spelunker', 31)):
        ok(model_for(name) == f'c_npc_{want:02d}',
           f'{name} usa c_npc_{want:02d}')
    ok(len(set(NPC_MODELS.values())) == len(NPC_MODELS),
       'nessun indice di modello serve due archetipi')
    # un posto dichiarato dalla mappa colloca chi lo porta in coda
    w2 = World()
    w2.spots = {'a6_010': (3.2, 0.0, -4.8)}
    e3 = w2.require('OldWomana6_010')
    ok(e3.pos == [3.2, 0.0, -4.8] and e3.created,
       'un NPC di mappa va dove la MAP_ALIGNMENT dice')
    ok(not w2.require('PrincessBugSP9').created,
       'chi non ha ne posto ne CreateNpc resta senza posizione')
    ok(model_for('OrbAltar01').startswith('i_evt'),
       'un altare e un oggetto di evento, non una persona')
    ok(model_for('PrincessBugSP') == model_for('PrincessBugSP4'),
       'due istanze dello stesso archetipo hanno lo stesso modello')

    # la rubrica degli NPC di mappa, se il disco e' estratto
    import pathlib
    import sys
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                        else '../extract/PS3_GAME/USRDIR/data')
    if (root / 'Event').is_dir():
        d = npc_directory(root)
        print(f'  ({len(d)} identificativi dalla rubrica di {root})')
        ok(len(d) > 200, 'la rubrica ha piu di 200 abitanti')
        ok(d['a1_300']['name'] == 'OldMana1_300' and
           d['a1_300']['model'] == 'c_npc_05',
           'a1_300 e OldMana1_300 e usa c_npc_05')
        # la biiezione fra indice e archetipo: e' cio' che rende la tabella
        # una tabella e non una coincidenza
        pairs = {(v['index'], v['archetype']) for v in d.values()}
        idx = [i for i, _ in pairs]
        ok(len(idx) == len(set(idx)),
           f'{len(set(idx))} indici, nessuno con due archetipi')
        # il nome ricomposto e' quello che gli script userebbero
        ok(all(v['name'].lower().endswith(k) for k, v in d.items()),
           'ogni nome finisce con il proprio identificativo')
        ok(all(archetype(v['name']).lower() == v['archetype']
               for v in d.values()),
           'e ogni nome si riduce all archetipo dichiarato dal file')

    # le pose
    e.stop()
    e.node = None
    ok(e.pose() == '01', 'fermo sta nella posa 01')
    e.move_by((3.2, 0, 0), 3.2)
    e.walk = 0.0
    a = e.pose()
    e.walk = 0.3
    ok({a, e.pose()} == {'02_a', '02_b'}, 'camminando i due passi si alternano')
    e.node = 2
    ok(e.pose() == '#2', 'SetNpcNode ha la precedenza')

    # il bestiario: dichiarato sul disco, e disegnabile
    import collections as _c
    import pathlib as _p

    root = _p.Path('../extract')
    if (root / 'PS3_GAME').exists():
        best = bestiary(root)
        models = enemy_models(root)
        liv = _c.Counter(e['living'] for e in best)
        print(f'\nbestiario: {len(best)} nemici, identificativi '
              f'{min(e["num"] for e in best)}-{max(e["num"] for e in best)}, '
              f'{len(liv)} habitat')
        print(f'  modelli risolti {len(models)}/{len(best)}: '
              f'{sum(1 for v in models.values() if v == "c_obj_all")} nodi in '
              f'c_obj_all, {sum(1 for v in models.values() if v != "c_obj_all")}'
              ' file di boss')
        ok(len(best) == 46, 'il disco dichiara i 46 nemici dell album')
        ok(len(models) == len(best),
           'ogni nemico ha il suo modello sul disco')
        ok(all(e['name'] for e in best), 'ognuno ha un nome')
        ok(len(liv) >= 12, f'{len(liv)} habitat distinti, campagna e sotterranei')

        # L'identificativo di attore: l'album e la griglia sono due file
        # scritti per scopi diversi, e si devono incontrare.
        import mapdat as _md

        d = root / 'PS3_GAME/USRDIR/data/map/MAP_ALIGNMENT'
        seen, npc_ok, npc_no = set(), 0, 0
        dirn = npc_directory(root / 'PS3_GAME/USRDIR/data')
        for p in sorted(d.glob('*.DAT')):
            for c in _md.cells(p.read_bytes()):
                v = c['actor']
                if not v or not 5000 <= v < 6000:
                    continue
                seen.add(v)
                for s in (c['cls'], c['params']):
                    for m in _md.NPC_ID.finditer(s or ''):
                        info = dirn.get(m.group(1)) or {}
                        mm = re.match(r'c_npc_(\d+)', info.get('model') or '')
                        if not mm:
                            continue
                        if v == 5047 + int(mm.group(1)):
                            npc_ok += 1
                        else:
                            npc_no += 1
        # Il minigioco e' l'unico posto in cui i nemici di questo gioco sono
        # scritti per esteso, e ci si aggancia per numero di modello. A dire
        # che l'aggancio e' giusto sono i **nomi**, che nessuno dei due file
        # prende dall'altro.
        mot = enemy_motion(root)
        pairs = {'MGRabbit': 'Rabbit', 'MGGhost': 'Ghost', 'MGZombie': 'Zombie',
                 'MGShadow': 'Shadow', 'MGBlackKnight': 'Black Knight'}
        names = {e['num']: e['name'] for e in best}
        agree = 0
        for mg, want in pairs.items():
            hit = [k for k, v in names.items()
                   if want.replace(' ', '') in
                   v.translate({0xFF01 + i: 0x21 + i for i in range(94)})
                   .replace('　', '').replace(' ', '')]
            agree += any(k in mot for k in hit)
        print(f'\nanimazione dichiarata dal minigioco: {len(mot)} specie; '
              f'nomi che si incontrano: {agree}/{len(pairs)}')
        ok(len(mot) == 12, 'dodici nemici del gioco sono scritti in Lua')
        ok(agree == len(pairs),
           'il nome del minigioco e quello dell album sono lo stesso nemico')
        ok({m['wait'] for m in mot.values()} == {STEP_WAIT},
           f'il fotogramma dura {STEP_WAIT}s, e lo dicono tutti e dodici')
        odd = [k for k, m in mot.items()
               if not any(p.endswith('_a') for p in m['poses'])]
        print(f'  specie il cui ciclo non e\' una coppia `_a`/`_b`: {len(odd)}')
        ok(odd, 'il ciclo di camminata non e\' lo stesso per tutti')

        nums = {e['num'] for e in best}
        hit = len(nums & seen)
        print(f'\nidentificativi di attore: {len(seen)} valori 5xxx sulle '
              f'griglie, {hit}/{len(nums)} sono nemici dell album')
        ok(hit >= len(nums) - 1,
           'i nemici che l album dichiara sono quelli che le mappe piazzano')
        tot = npc_ok + npc_no
        print(f'  celle NPC con modello noto: {tot}; con id = 5047 + NN: '
              f'{npc_ok} ({100 * npc_ok / max(tot, 1):.1f}%)')
        ok(tot and npc_ok >= tot * 0.9,
           'l identificativo di un NPC e 5047 piu l indice del suo modello')

    print(f'\n{"tutto a posto" if not bad else str(bad) + " verifiche fallite"}')
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(_check())
