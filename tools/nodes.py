"""
nodes.py - la tavola dei simboli che il disco dichiara.

Il TODO della sessione 11 chiedeva l'**aggancio** dei gimmick: un vaso non
carica `EN_ENEMY_NN`, quindi la regola che la sessione 11 aveva usato per i
nemici non lo raggiunge. La risposta e' che non serve nessuna regola, perche'
c'e' una tabella - e sta in chiaro, in `all.lua.eu`, sotto
`../lua/packageManager/`:

    package_manager.gPackageManager:addNodeListElement(
        package_manager.TFI_EVENT_OBJECT,  package_manager.DFI_EVENT_OBJECT,
        package_manager.MPD_M_OBJ_127_a,   "m_obj_127_01" );

Quattro argomenti: il pacchetto delle **texture**, quello della **scena**, la
costante nativa con cui il codice nomina il pezzo, e **il nome del nodo**. Le
righe sono 1.279 e coprono tutto quello che il gioco carica - il giocatore, i
nemici, i boss, gli NPC, gli oggetti, le armi, il terreno.

Cioe' la corrispondenza fra il nome che uno script pronuncia e il nodo che sta
dentro un `.dsb` non e' piu' una nostra deduzione: e' un dato.

## Cosa dice, e cosa conferma

La tavola e' un **oracolo su tre sessioni di deduzioni**, e le conferma quasi
per intero:

    EN_ENEMY_NN -> c_enm_NN   146 voci, una sola fuori schema
    NP_NPC_NN   -> c_npc_NN   116 voci, quattro fuori schema

Le cinque eccezioni non sono sparse: `NP_NPC_19` **e'** `c_npc_26` e
`NP_NPC_26` **e'** `c_npc_19`, cioe' due numeri scambiati. Ed e' esattamente
la coppia che la sessione 8 aveva indicato come punto debole della propria
rubrica - «le eccezioni cadono *tutte* su `c_npc_19`...`c_npc_26`». Il disco
dice dov'era lo scarto, e conferma tutto il resto.

## Gli oggetti di mappa, e la numerazione delle celle

Gli script di `../lua/Object/gimmick/` e `../lua/Object/MessageBoard/`
caricano `MPD_M_OBJ_*`, che questa tavola manda su `m_obj_*` dentro
`map/map_model/map_object.ps3.dsb` (piu' `Torch.ps3.dsb` per il 99, che ha un
file suo come i boss). E la cella lo sa gia':

    l'identificativo di cella e' 4000 + il numero del modello

51 celle su 51 lo confermano, su tre famiglie che non si conoscono - i 34
`Signboard` (4041 / `m_obj_41`), i 12 `Stonemark` (4067 / `m_obj_67`), i tre
`Well` (4063 / `m_obj_63`) - e zero discordanti. Da cui si legge tutto il
resto della banda 4xxx, che finora era un numero: **4127 e' l'erba che si
taglia**, 4111 le sette lapidi dei boss, 4116..4121 i sei altari delle sfere,
4062 il piedistallo della spada, 4099 le 859 torce.

E si legge anche l'assenza. Gli identificativi 4100 (i `Warp` e gli
osservatori) e 4101 (`Exit`, `destructionWall`, `WarpDoor`) sono fra i pochi
che **non hanno un `m_obj`**: il modello non c'e' perche' non c'e' niente da
disegnare, che e' la stessa cosa che `walk.md` aveva misurato dal lato della
geometria, un anno di sessioni fa, senza poterla spiegare.

## Le altre due bande

    3000 + NN  ->  d_hmw_NN     28 numeri su 28
    1000 + NN  ->  ?            38 numeri, 1..51

`d_hmw` sono i «Dungeon配置物» - gli *oggetti di piazzamento* del sotterraneo,
e il commento degli autori li chiama proprio cosi'. I 28 numeri che le celle
usano sono **esattamente** i 28 che `d_haichi.ps3.dsb` porta, senza uno in
piu' ne' uno in meno; l'unico dichiarato che le celle non usano e' `d_hmw_03`,
che e' anche l'unico ad avere sotto-varianti.

La banda 1000 e' l'equivalente in campagna - l'85% delle sue celle sta in una
`field_*` - ma non si chiude allo stesso modo, e il motivo si vede: dove il
sotterraneo ha **una** famiglia (`d_hmw`), la campagna ne ha **due**
(`f_hmw`, `f_ntr`), e un solo numero non puo' dire quale. Resta aperta, con
il campo stretto a due liste dichiarate.

Uso:
  python nodes.py census                    la tavola, e cosa conferma
  python nodes.py props                     gli oggetti di mappa, per id
  python nodes.py colors                    cosa sono i colori di AddColor
  python nodes.py enum MPD_M_OBJ_127_a      dove sta un simbolo
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

# Il file e' una concatenazione, e i commenti `-- Start` sono l'unico indice.
# Attenzione: **non sono 869**. Quello e' il numero dei sorgenti sotto
# `../lua/`, che e' un albero su ventinove: gli altri sono i file di dati
# (`Event/`, `MiniGame/`, `UserInterface/`...) copiati nello stesso flusso.
# In tutto sono 1.486, e la differenza non e' contabile: chi spezza solo sui
# `../lua/` fa inghiottire a sette sorgenti le 185 che li seguono - fra cui
# `Object/DropItemList`, che si prende i cento file del minigioco.
START = re.compile(r'-- Start (\S+?)\.lua')

NODEDEF = re.compile(
    r'addNodeListElement\(\s*package_manager\.(\w+)\s*,'
    r'\s*package_manager\.(\w+)\s*,\s*package_manager\.(\w+)\s*,'
    r'\s*"([^"]+)"\s*\)')

ADDNODE = re.compile(r'AddNode\(\s*package_manager\.(\w+)')

# Le librerie di modelli delle mappe. Sono quattro file e basta, e il nome
# dice cosa contengono: `haichi` e' 配置, il piazzamento; `chikei` e' 地形, il
# terreno; `map_object` sono gli oggetti che il codice istanzia come attori.
MAP_MODELS = 'map/map_model'

# Le tre bande di identificativi di cella che nominano un modello, e la
# famiglia di nodi in cui cercarlo. La quarta (5xxx) sono le creature e la
# risolve entity.actor_directory().
BANDS = {4000: 'm_obj', 3000: 'd_hmw'}


def sources(data: pathlib.Path) -> dict[str, str]:
    """Tutti i sorgenti dentro `all.lua.eu`, per percorso.

    Le chiavi sono quelle che il file scrive - `../lua/Object/06Bee`,
    `Event/mainevent/mainevent_001_herodream1` - senza estensione.

    I marcatori sono 1.486 e i nomi distinti 1.483: tre sorgenti di NPC
    compaiono due volte nella concatenazione, ed e' una ripetizione del
    montaggio, non due file diversi.
    """
    p = pathlib.Path(data) / 'all.lua.eu'
    if not p.exists():
        return {}
    src = p.read_text(encoding='utf-8', errors='replace')
    ms = list(START.finditer(src))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(src)
        out[m.group(1)] = src[m.end():end]
    return out


def nodelist(data: pathlib.Path) -> dict[str, dict]:
    """La tavola dichiarata: `{costante: {'node', 'tex', 'dsb'}}`.

    Le righe commentate si saltano: sono sei, e nominano modelli che nel disco
    finito non esistono piu'. Che siano proprio quelle a nominarli e' la
    controprova che la tavola e' mantenuta.
    """
    out = {}
    for testo in sources(data).values():
        if 'addNodeListElement' not in testo:
            continue
        for riga in testo.splitlines():
            riga = riga.strip()
            if riga.startswith('--'):
                continue
            m = NODEDEF.search(riga)
            if m:
                out[m.group(3)] = {'node': m.group(4), 'tex': m.group(1),
                                   'dsb': m.group(2)}
    return out


def loaders(data: pathlib.Path) -> dict[str, list[str]]:
    """Chi carica cosa: `{nome di sorgente: [costanti passate ad AddNode]}`.

    Solo i sorgenti sotto `../lua/Object/`, che sono quelli che il motore
    istanzia come attori. Il nome e' l'ultimo componente del percorso, ed e'
    anche il nome della classe che la cella scrive (`Well01`, `Signboard03`).
    """
    out = {}
    for k, testo in sources(data).items():
        if '/Object/' not in k:
            continue
        enums = []
        for m in ADDNODE.finditer(testo):
            if m.group(1) not in enums:
                enums.append(m.group(1))
        if enums:
            out[k.rsplit('/', 1)[-1]] = enums
    return out


def libraries(data: pathlib.Path) -> dict[str, str]:
    """Dove sta ogni nodo disegnabile delle librerie di mappa.

    `{nome del nodo: nome del file}`, e solo i nodi con una mesh appesa: un
    nodo senza mesh e' un raggruppamento, non un oggetto.
    """
    import dsb

    out = {}
    for p in sorted((pathlib.Path(data) / MAP_MODELS).glob('*.dsb')):
        try:
            name, blob = dsb.blocks(p)[0]
            d = dsb.Dsb(blob, name)
        except Exception:                                        # noqa: BLE001
            continue
        for n in d.nodes():
            if n['attached'] is None:
                continue
            nome = n['name']
            if nome.endswith('-node'):
                nome = nome[:-5]
            out.setdefault(nome, p.name)
    return out


def props(data: pathlib.Path) -> dict[int, dict]:
    """Gli oggetti di mappa, per identificativo di cella.

    Restituisce `{4127: {'model': 'm_obj_127', 'node': 'm_obj_127_01',
    'lib': 'map_object.ps3.dsb', 'scripts': ['Grass']}}`.

    `node` e' il pezzo da disegnare, e la scelta ha una fonte: se uno script
    dichiara cosa carica, si prende **il primo `AddNode`**, che e' la posa in
    cui l'oggetto compare (`Grass` carica prima l'erba e poi il taglio, e
    l'erba e' quella che si vede entrando). Altrimenti si prende la radice, e
    se la radice non ha mesh il primo figlio in ordine di nome.
    """
    tab = nodelist(data)
    lib = libraries(data)
    carica = loaders(data)

    # Da numero di modello ai nomi di script che lo caricano, passando per la
    # tavola: `Signboard03` -> `MPD_M_OBJ_41` -> `m_obj_41` -> 41.
    per_num: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
    primo: dict[tuple[str, int], str] = {}
    for nome, enums in carica.items():
        for e in enums:
            nodo = tab.get(e, {}).get('node')
            if not nodo:
                continue
            m = re.match(r'([a-z]+_[a-z]+)_(\d+)', nodo)
            if not m:
                continue
            key = (m.group(1), int(m.group(2)))
            if nome not in per_num[key]:
                per_num[key].append(nome)
            # Il **primo** `AddNode` di uno script e' la posa in cui l'oggetto
            # compare, e quando due script caricano lo stesso modello si
            # prende il nodo di nome minore: `_a` prima di `_b`, `_01` prima
            # di `_02`. Sull'altare della sfera gialla la differenza si vede -
            # `_a` e' il piedistallo, `_b` la sfera che ci sta sopra finche'
            # non la si prende.
            if e == enums[0]:
                primo[key] = min(primo.get(key, nodo), nodo)

    # I nodi di ogni modello, raggruppati una volta sola: `m_obj_127` ->
    # `['m_obj_127_01', 'm_obj_127_02', 'm_obj_127_03']`.
    figli: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
    for k in lib:
        m = re.fullmatch(r'([a-z]+_[a-z]+)_(\d+)(_\w+)?', k)
        if m and m.group(1) in BANDS.values():
            figli[(m.group(1), int(m.group(2)))].append(k)

    out = {}
    for base, fam in BANDS.items():
        for (f, nn), nodi in figli.items():
            if f != fam:
                continue
            radice = f'{fam}_{nn:02d}'
            nodo = primo.get((fam, nn))
            if nodo not in lib:
                nodo = radice if radice in lib else sorted(nodi)[0]
            out[base + nn] = {'model': radice, 'node': nodo, 'lib': lib[nodo],
                              'scripts': per_num.get((fam, nn), [])}
    return out


def npc_models(data: pathlib.Path) -> dict[str, str]:
    """Da archetipo di NPC al modello, **dichiarato**: `{'oldman': 'c_npc_05'}`.

    I 266 file di `../lua/Object/npc/` sono uno per abitante e si chiamano
    `n<NN><archetipo><identificativo>`; ognuno carica il proprio nodo, e la
    tavola dice quale sia. Cioe' la rubrica archetipo -> modello, che la
    sessione 4 aveva dedotto dai nomi dei 237 script di dialogo, qui si
    **legge** invece di dedurla.

    Confrontate, le due concordano su 33 archetipi su 35. Le due che
    disaccordano sono le stesse che la tavola dei nodi segnala da sola:

        princessbug   c_npc_26   (e non c_npc_19: i due numeri sono scambiati)
        goblinred     c_enm_12   (che e' un modello di **nemico**)

    La seconda e' quella che vale, perche' non e' uno scarto di un numero ma
    di famiglia: i goblin rossi amichevoli del villaggio riusano il modello
    del goblin rosso nemico, `12GoblinRed`. Ed e' per questo che sotto
    `Object/` non c'e' nessun `N26GoblinRed` - non serviva.
    """
    tab = nodelist(data)
    conta: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for k, testo in sources(data).items():
        if '/Object/npc/' not in k:
            continue
        # `n05oldmana11_290` = indice, archetipo, e la coda che colloca
        # l'istanza. Le due sole eccezioni sono i due `...sp`, le comparse di
        # una scena speciale, che di coda non ne hanno.
        m = re.fullmatch(r'n(\d\d)([a-z0-9]+?)(?:[a-z]\d{1,2}_\d{3}|sp)',
                         k.rsplit('/', 1)[-1])
        if not m:
            continue
        arch = m.group(2)
        for e in ADDNODE.findall(testo):
            nodo = tab.get(e, {}).get('node')
            if nodo:
                conta[arch][re.sub(r'_\d+(_[ab])?$', '', nodo)] += 1
    return {a: c.most_common(1)[0][0] for a, c in conta.items() if c}


# ------------------------------------------------------------------ comandi

def cmd_census(data: pathlib.Path) -> int:
    """La tavola, e le tre cose che conferma."""
    src = sources(data)
    tab = nodelist(data)
    lib_all = libraries(data)
    print(f'sorgenti in all.lua.eu      {len(src):6}')
    alberi = collections.Counter(k.split('/')[0] for k in src)
    print(f'  di cui sotto ../lua/      {alberi.get("..", 0):6}'
          f'   (il resto sono {len(alberi) - 1} alberi di dati)')
    print(f'nodi dichiarati             {len(tab):6}')

    # Che i nomi dichiarati esistano davvero e' la prima verifica, e va fatta
    # su tutto il disco perche' le librerie sono decine.
    import dsb
    esistono = set()
    for p in sorted(pathlib.Path(data).rglob('*.dsb')):
        try:
            esistono |= set(dsb.Dsb(p.read_bytes()).strings)
        except Exception:                                        # noqa: BLE001
            continue
    ok = [k for k, v in tab.items() if v['node'] in esistono]
    print(f'  che esistono in un .dsb   {len(ok):6}   '
          f'{100 * len(ok) / max(len(tab), 1):.1f}%')

    usati = set()
    for testo in src.values():
        usati |= {m.group(1) for m in ADDNODE.finditer(testo)}
    noti = usati & set(tab)
    print(f'costanti passate ad AddNode {len(usati):6}')
    print(f'  dichiarate nella tavola   {len(noti):6}   '
          f'{100 * len(noti) / max(len(usati), 1):.1f}%')
    print('  non dichiarate:', ', '.join(sorted(usati - set(tab))))

    print()
    print('la tavola contro le nostre rubriche')
    for pre, mod in (('EN_ENEMY', 'c_enm'), ('NP_NPC', 'c_npc')):
        tot = fuori = 0
        detta = []
        for k, v in sorted(tab.items()):
            m = re.fullmatch(pre + r'_?(\d+)(?:_\w+)?', k)
            if not m:
                continue
            tot += 1
            if not v['node'].startswith(f'{mod}_{int(m.group(1)):02d}'):
                fuori += 1
                detta.append(f'{k} = {v["node"]}')
        print(f'  {pre + "_NN":14} -> {mod}_NN   {tot - fuori:4}/{tot} '
              f'{"  fuori schema: " + ", ".join(detta) if detta else ""}')

    print()
    print('gli oggetti di mappa')
    pr = props(data)
    for base, fam in sorted(BANDS.items()):
        n = [k for k in pr if k // 1000 * 1000 == base]
        con = [k for k in n if pr[k]['scripts']]
        print(f'  {base} + NN -> {fam}_NN   {len(n):4} modelli, '
              f'{len(con)} con uno script che li nomina')
    print(f'  nodi disegnabili nelle librerie di mappa   {len(lib_all)}')
    return 0


def cmd_props(data: pathlib.Path) -> int:
    """Gli oggetti di mappa con il conto delle celle che li piazzano."""
    import mapdat

    root = pathlib.Path(data) / 'map/MAP_ALIGNMENT'
    celle = collections.Counter()
    classi = collections.defaultdict(collections.Counter)
    for f in sorted({p.resolve() for p in root.rglob('*.[Dd][Aa][Tt]')}):
        for c in mapdat.cells(f.read_bytes()):
            a = c['fields'][4]
            if a:
                celle[a] += 1
                if c['cls']:
                    classi[a][c['cls']] += 1
    pr = props(data)
    print(f'{"id":>5} {"celle":>6}  {"nodo":<16} {"libreria":<22} script')
    for i in sorted(celle):
        if i not in pr and not (3000 <= i < 5000):
            continue
        p = pr.get(i)
        sc = ', '.join((p or {}).get('scripts', [])[:3])
        if not sc:
            sc = ', '.join(k for k, _ in classi[i].most_common(2))
        print(f'{i:5} {celle[i]:6}  {(p or {}).get("node", "-"):<16} '
              f'{(p or {}).get("lib", "-  nessun modello"):<22} {sc[:52]}')
    senza = [i for i in celle if 3000 <= i < 5000 and i not in pr]
    print(f'\n{len(pr)} modelli, {sum(celle[i] for i in pr if i in celle)} celle; '
          f'{len(senza)} identificativi senza modello '
          f'({sum(celle[i] for i in senza)} celle)')
    return 0


def cmd_colors(data: pathlib.Path) -> int:
    """Cosa sono i colori di `AddColor`: **quelli che il modello ha gia'**.

    L'ipotesi da cui si era partiti era che fossero una tinta da applicare, e
    che gli oggetti venissero scuri perche' non la applicavamo. E' falsa, e a
    dirlo e' un confronto che non costa niente: per ogni colore dichiarato si
    cerca la tinta piu' vicina **fra quelle che i vertici del suo modello gia'
    portano**, e si misura lo scarto d'angolo - cioe' la tinta a meno della
    luminosita', che nei vertici e' illuminazione precotta.
    """
    import re as _re

    import numpy as np
    import view

    lib = view.Charlib(pathlib.Path(data))
    tab = nodelist(data)

    def unit(a):
        a = np.asarray(a, float)
        n = np.linalg.norm(a, axis=-1, keepdims=True)
        return a / np.where(n < 1e-6, 1, n)

    def valore(s):
        try:                                    # `142.0/255.0` e' un colore
            return float(eval(s, {'__builtins__': {}}, {}))   # noqa: S307
        except Exception:                                    # noqa: BLE001
            return None

    ang, rap, nfile = [], [], 0
    for k, testo in sources(data).items():
        if '/Object/' not in k:
            continue
        cols = []
        for m in _re.finditer(r'AddColor\(\s*([^)]*)\)', testo):
            x = [valore(a.strip()) for a in m.group(1).split(',')]
            if len(x) >= 3 and all(y is not None for y in x[:3]) \
                    and sum(x[:3]) > 0.05:
                cols.append(x[:3])
        if not cols:
            continue
        pezzi = []
        for e in ADDNODE.findall(testo):
            nodo = tab.get(e, {}).get('node')
            if not nodo:
                continue
            m = _re.match(r'((?:c_enm|c_npc|c_ply|c_bos)_\d+)_(.+)', nodo)
            pezzi += (lib.parts(m.group(1), m.group(2)) if m
                      else lib.parts(nodo, '-'))
        if not pezzi:
            continue
        c = np.unique(np.round(np.vstack(
            [p.col.reshape(-1, 4)[:, :3] for p in pezzi]), 3), axis=0)
        c = c[c.sum(1) > 0.05]
        if not len(c):
            continue
        nfile += 1
        for col in cols:
            cos = unit(c) @ unit(col)
            i = int(cos.argmax())
            ang.append(np.degrees(np.arccos(min(1.0, cos[i]))))
            rap.append(np.linalg.norm(c[i]) / np.linalg.norm(col))
    ang, rap = np.array(ang), np.array(rap)
    print(f'{len(ang)} colori dichiarati da {nfile} file, contro la tavolozza '
          f'del proprio modello')
    print(f'  scarto d angolo   mediana {np.median(ang):.1f} gradi   '
          f'sotto 5 gradi {100 * (ang < 5).mean():.0f}%')
    print(f'  luminosita del modello sul dichiarato   '
          f'mediana {np.median(rap):.2f}')
    print('  cioe AddColor non e una tinta da applicare: dichiara i colori '
          'che il modello ha gia.')
    return 0


def cmd_enum(data: pathlib.Path, name: str) -> int:
    """Dove sta un simbolo: il nodo, la libreria, e chi lo carica."""
    tab = nodelist(data)
    lib = libraries(data)
    v = tab.get(name)
    if v is None:
        vicini = [k for k in tab if name.upper() in k]
        print(f'{name}: non dichiarato'
              + (f'; simili: {", ".join(sorted(vicini)[:8])}' if vicini else ''))
        return 1
    print(f'{name}')
    print(f'  nodo      {v["node"]}')
    print(f'  libreria  {lib.get(v["node"], "(fuori da map_model)")}')
    print(f'  pacchetti {v["tex"]}, {v["dsb"]}')
    chi = [k for k, e in loaders(data).items() if name in e]
    print(f'  caricato da  {", ".join(chi) if chi else "(nessuno script)"}')
    return 0


def main() -> int:
    args = sys.argv[1:]
    root = pathlib.Path('../extract')
    for i, a in enumerate(args):
        if a == '--root' and i + 1 < len(args):
            root = pathlib.Path(args[i + 1])
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() else root
    cmd = args[0] if args else 'census'
    if cmd == 'census':
        return cmd_census(data)
    if cmd == 'props':
        return cmd_props(data)
    if cmd == 'colors':
        return cmd_colors(data)
    if cmd == 'enum' and len(args) > 1:
        return cmd_enum(data, args[1])
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
