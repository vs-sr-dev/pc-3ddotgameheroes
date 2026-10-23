"""
mapdat.py - parser di MAP_ALIGNMENT/*.DAT, la griglia logica delle mappe.

Sono 170 file e sono gli **unici little-endian del disco**: tutto il resto di
3D Dot Game Heroes e' big-endian, come vuole il PPC della PS3. Se un campo non
ha senso, la prima cosa da provare qui e' l'altro endianness.

Il file descrive la griglia *logica* di una mappa - dove stanno eventi, nemici
e passaggi - ed e' cosa diversa dalla griglia di streaming del `.pac`
corrispondente, che ha dimensioni proprie (vedi docs/format_pac.md).

Formato

  testata
    +0x00 u32   costante per gruppo di mappe: 8, 16 o 32
    +0x04 u32   w, celle in orizzontale
    +0x08 u32   h, celle in verticale
    +0x0C u32   ?
    +0x10 u32   len, lunghezza della stringa che segue
    +0x14 char[len]  stringa di livello mappa

  poi esattamente w*h record, uno per cella, in ordine di riga:

    +0x00 u32   identificativo di regione: 0xFFFFFFFF nel 56% delle celle del
                disco, cioe' fuori mappa. NON e' un id di oggetto: in D_1_2 il
                valore 0x7D1 copre 360 celle su 520 e gli oggetti sono 10
    +0x04 u32   ?   (0 nel 91%)
    +0x08 u32   **due byte**, non un numero solo: `(b1 << 8) | b0`, con i due
                byte alti sempre a zero (482.180 celle su 482.180). 0xFFFFFFFF
                nel 56%, cioe' fuori mappa.

                Che siano due valori e non uno lo dice la sola misura che qui
                non ammette eccezioni: **b1 >= b0 in tutte e 482.180 le celle**.
                Sono uguali nel 92,3% - ed e' per questo che la lettura
                precedente, `n*257` (cioe' 0x0101*n), tornava su un campione e
                falliva su 33.000 celle. E' un intervallo, non un numero.

    +0x0C u32   1 << b0 nel 74,4% delle celle, 0 nel resto. **Mai due bit
                accesi**: 358.947 celle con un bit, 122.961 con nessuno, zero
                celle con due. Quindi non e' la maschera dell'intervallo, ma il
                solo estremo basso.

                L'unica eccezione e' istruttiva: 272 celle con 0x7FFFFFFF,
                cioe' **tutti** i bit, e stanno tutte in `field_7` con
                b0 = b1 = 31. Trentuno e' il massimo che una maschera a 32 bit
                puo' portare, e field_7 e' la mappa piu' alta del disco -
                quella che in sessione 6 costringeva a misurare l'altezza della
                colonna invece di assumerla. E' una saturazione, ed e' l'indizio
                migliore a favore della quota.

                Cosa siano b0 e b1 resta aperto. Vanno da 0 a 31; per mappa i
                valori distinti sono 2-3 nei sotterranei e fino a 7 in
                campagna, che e' il profilo di una **quota**, e infatti il
                pavimento misurato concorda con b0 nell'84,1% dei sotterranei e
                nel 68,2% della campagna - forte, ma sotto la soglia a cui
                questo progetto chiama oracolo un test. Il tetto d'altezza che
                `map_param.lua` dichiara per mappa **non** limita b1 (8 mappe su
                35), quindi quella non e' la strada
    +0x10 u32   **l'attore** che vive in questa cella, 0 se nessuno. E' un
                identificativo globale, non un indice locale, e i suoi
                intervalli si leggono da tre file diversi - vedi actor() e
                docs/walk.md §attori
    +0x14 u32   ?   (0 nel 99,8%)
    +0x18 u32   len1, lunghezza della prima stringa
    +0x1C u32   len2, lunghezza della seconda
    poi len1+len2 byte di testo, senza terminatore ne' allineamento

La prima stringa sono i **parametri** nella stessa sintassi a flag dell'API Lua
(`-g11;-o02;-f0;-e1;-ex0;`), la seconda e' *di solito* la **classe**
dell'oggetto (`Warp`, `Exit`, `EnemyObserver`, `destructionWall`...). Ma non
sempre: nel 14% dei casi e' una seconda specifica che nomina a sua volta una
mappa. Vedi destinations().

Che il layout sia questo non e' una congettura: percorrendo il file record per
record - lunghezze delle stringhe incluse - si finisce **esattamente**
sull'ultimo byte dopo w*h record, in 170 file su 170. Con una dimensione di
record sbagliata o senza le stringhe in coda si esce dal file quasi subito.

Uso:
  python mapdat.py info  <file.DAT>
  python mapdat.py graph <dir MAP_ALIGNMENT> [--pac <dir con i .pac>]
  python mapdat.py cells <file.DAT>          istogramma degli id di regione
"""
from __future__ import annotations

import collections
import pathlib
import re
import struct
import sys

def norm(name: str) -> str:
    """Chiave di confronto fra nomi di mappa: le destinazioni sono scritte
    `Field_7` mentre i file si chiamano `field_07`. Minuscolo e zeri iniziali
    tolti da ogni componente numerica."""
    return '_'.join(p.lstrip('0') or '0' for p in name.lower().split('_'))


def cells(data: bytes):
    """Percorre il file e restituisce una cella per volta."""
    _c, w, h, _d, ln = struct.unpack_from('<5I', data, 0)
    o = 20 + ln
    for i in range(w * h):
        f = struct.unpack_from('<8I', data, o)
        l1, l2 = f[6], f[7]
        s1 = data[o + 32:o + 32 + l1].decode('ascii', 'replace')
        s2 = data[o + 32 + l1:o + 32 + l1 + l2].decode('ascii', 'replace')
        m = SPAWN_SET.search(s1) or SPAWN_SET.search(s2)
        yield {'index': i, 'x': i % w, 'y': i // w, 'tag': f[0],
               'fields': f, 'params': s1, 'cls': s2,
               # L'attore e il set di piazzamento. Vedi actor() e SPAWN_SET.
               'actor': f[4] or None, 'set': m.group(1) if m else None}
        o += 32 + l1 + l2
    if o != len(data):
        raise ValueError(f'percorso finito a {o}, il file e\' lungo {len(data)}')


def header(data: bytes) -> dict:
    c, w, h, d, ln = struct.unpack_from('<5I', data, 0)
    return {'c': c, 'w': w, 'h': h, 'd': d,
            'name': data[20:20 + ln].decode('ascii', 'replace')}


# L'identificativo di un NPC di mappa: lettera, uno o due numeri di area,
# trattino basso, tre cifre. `a4_150`, `b1_010`, `a11_120`.
NPC_ID = re.compile(r'\b([a-z]\d{1,2}_\d{3})\b')

# Il **set di piazzamento** di un attore: `-sA;` ... `-sH;`, piu' `-sZ`.
#
# Non e' un attributo dell'attore, e' quale partita lo vede. Le lettere sono
# due terne e non una sequenza - A,B,C e F,G,H, con D ed E che non esistono:
#
#  - **A, B, C** sono tre piazzamenti alternativi della *stessa* popolazione.
#    Lo dicono tre misure che sbagliano in modi diversi: le tre lettere hanno
#    le stesse specie in 58 mappe su 59 (98,3%), sono equinumerose su tutto il
#    disco (1807/1824/1804), e le loro celle non si sovrappongono **mai** pur
#    coprendo la stessa area (la scatola di una lettera e' l'88% di quella
#    delle tre, e in 51 mappe su 59 sta sopra l'80%). Tre disposizioni fra cui
#    il gioco sceglie: e' il "esci dalla stanza e rientra, e i nemici si
#    ripiazzano" che i giocatori conoscono.
#  - **F, G, H** sono le stesse tre per **FROM Mode**, la difficolta' che si
#    sblocca finendo il gioco. F sta per FROM. Qui il parallelismo si rompe, ed
#    e' giusto che si rompa: sono piu' celle (in FIELD_16, 36/47/45 contro
#    19/19/19) e piu' specie (7 contro 4), che e' esattamente cio' che quella
#    modalita' dichiara di fare.
#
# Vedi docs/walk.md §attori per il confronto con la fonte esterna.
SPAWN_SET = re.compile(r'-s([A-Z])\b')

# Gli intervalli dell'identificativo di attore, cioe' del campo +0x10.
#
# La numerazione e' unica per tutto il gioco e la partizione la dichiarano
# **tre file che non si conoscono**: l'album dei nemici
# (`UserInterface/EnemyView`) copre 5002-5082 e vi si ritrova 45 volte su 46;
# i modelli NPC `c_npc_NN` cadono su 5047+NN, misurato al 94,2% su 240 celle;
# e sotto i 5000 il valore e' costante per classe di cella in 175 casi su 195.
#
#   1000-3999  ?  (8.781 celle, non ancora attribuite)
#   4000-4999  oggetti di mappa. 4100 gli osservatori e i `Warp`, 4101 le cose
#              solide (`Exit`, `destructionWall`, `WarpDoor`, `PitFall`,
#              `BlackHole`), 4115 i grilletti di evento
#   5000-5999  personaggi: nemici dove l'album lo conferma, NPC su 5047+NN
ACTOR_RANGES = ((4000, 5000, 'oggetto'), (5000, 6000, 'personaggio'))


def locations(root) -> dict:
    """Come si chiama ogni mappa, e con che musica — `MapParameter.lua.eu`.

    Un file che nessuno aveva aperto in otto sessioni, e che e' andato guardato
    per una ragione che non c'entrava: il TODO diceva di cercarci il
    pattugliamento dei nemici prima di inventarlo. Il pattugliamento non c'e',
    e non c'e' nemmeno altrove - l'API Lua ha `PlayEnemy`, `PauseEnemy` e
    `visibleEnemy`, cioe' congelare e mostrare, mai muovere. Ma il file
    dichiara **211 mappe** con il nome del posto in inglese e il brano:

        Identifier=map_manager.MS_FIELD_1,
        Location="Mt. Sabre",
        Bgm=soundList.SoundID.BGM_field05,
        Volume=1.0

    L'identificativo si aggancia al nome del file senza artifici -
    `MS_DUNGEON_1_1_1` e' `d_1_1_1`, `MS_FIELD_1` e' `field_1` - quindi il giro
    di gioco puo' finalmente dire **dove si e'**, che e' una cosa che il gioco
    vero fa.

    57 localita' distinte su 211 mappe: un posto occupa piu' schermate, ed e'
    proprio questo che rende il nome un'informazione (attraversare `field_6` e
    `field_7` e' restare a "Klovis").

    Restituisce `{nome normalizzato: {'location', 'bgm', 'volume'}}`.
    """
    import pathlib

    import ui

    root = pathlib.Path(root)
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    p = data / 'MapParameter/MapParameter.lua.eu'
    if not p.exists():
        return {}
    blk = ui.descriptor_file(p).get('MapParameter') or {}
    rows = blk if isinstance(blk, list) else \
        [v for _, v in sorted((k, v) for k, v in blk.items()
                              if isinstance(k, int))]
    out = {}
    for r in rows:
        if not isinstance(r, dict) or 'Identifier' not in r:
            continue
        ident = str(r['Identifier']).rsplit('.', 1)[-1]
        m = re.match(r'MS_(FIELD|DUNGEON|CAPTURE)_(.+)$', ident)
        if not m:
            continue
        stem = ('d_' if m.group(1) == 'DUNGEON' else
                'capture' if m.group(1) == 'CAPTURE' else 'field_') + m.group(2)
        out[norm(stem)] = {
            'location': str(r.get('Location', '')),
            'bgm': str(r.get('Bgm', '')).rsplit('.', 1)[-1],
            'volume': float(r.get('Volume', 1.0) or 1.0)}
    return out


def actor(cell) -> int | None:
    """L'attore di una cella, o `None`.

    Sta a +0x10 ed e' il campo che tiene insieme i tre censimenti che il
    progetto aveva fatto separatamente - oggetti di mappa, nemici, NPC. Che sia
    un identificativo e non un indice locale lo dice il fatto che lo stesso
    numero ricorre con lo stesso significato su mappe diverse: `4100` sono gli
    osservatori in tutte e 170 le griglie.
    """
    v = cell['fields'][4] if isinstance(cell, dict) else int(cell)
    return v or None


def npc_spots(data: bytes) -> dict:
    """Dove stanno gli NPC che la mappa ospita, per identificativo.

    Gli script nominano 99 personaggi ma ne creano 40: gli altri stanno gia'
    sulla mappa, e finora non si sapeva dove. Stanno **qui**, in celle che
    portano come classe il solo identificativo - `a1_010`, `b8_010` - senza
    parametri e senza altro.

    Il nome che usa lo script e' archetipo piu' identificativo
    (`OldWomana6_010` = `OldWoman` + `a6_010`), quindi la coda del nome e' la
    chiave. Su 50 nomi del corpus che portano un identificativo, 37 trovano
    la loro cella.

    271 celle in tutto il disco, 236 identificativi distinti.
    """
    out = {}
    for c in cells(data):
        for s in (c['cls'], c['params']):
            for m in NPC_ID.finditer(s or ''):
                out.setdefault(m.group(1), (c['x'], c['y']))
    return out


DEST = re.compile(r'^([A-Za-z]\w*);-g')


def destinations(cell: dict):
    """Le mappe che una cella nomina come destinazione.

    Attenzione: le due stringhe **non** sono sempre `(parametri, classe)`. Nel
    14% dei casi la seconda contiene a sua volta un `;` ed e' una seconda
    specifica, del tipo `D_7_1_2;-g212;-o102;`. Guardare solo la prima, o
    filtrare sulla classe `Warp`, perde archi del grafo.
    """
    for s in (cell['params'], cell['cls']):
        m = DEST.match(s)
        if m:
            yield norm(m.group(1))


def graph(root: pathlib.Path) -> dict:
    """Grafo dei passaggi: mappa -> destinazioni."""
    out = collections.defaultdict(set)
    for p in sorted(root.glob('*.DAT')):
        src = norm(p.stem)
        for c in cells(p.read_bytes()):
            for d in destinations(c):
                out[src].add(d)
    return out


def cmd_info(path: pathlib.Path) -> int:
    data = path.read_bytes()
    h = header(data)
    cl = list(cells(data))
    vuote = sum(1 for c in cl if c['tag'] == 0xffffffff)
    cls = collections.Counter(c['cls'] for c in cl if c['cls'])
    print(f'{path.name}  {len(data):,} byte   griglia {h["w"]}x{h["h"]} '
          f'= {h["w"] * h["h"]:,} celle   c={h["c"]} d={h["d"]}')
    print(f'  nome: {h["name"]!r}')
    print(f'  celle fuori mappa: {vuote:,} ({100 * vuote // len(cl)}%), '
          f'con oggetto: {sum(1 for c in cl if c["params"] or c["cls"])}')
    print('  classi:', ', '.join(f'{k}:{v}' for k, v in cls.most_common(10)))
    print('\n  oggetti:')
    for c in cl:
        if c['params'] or c['cls']:
            print(f'    ({c["x"]:3},{c["y"]:3}) tag {c["tag"]:#07x}  '
                  f'{c["cls"] or "-":<18} {c["params"]}')
    return 0


def cmd_cells(path: pathlib.Path) -> int:
    counts = collections.Counter(c['tag'] for c in cells(path.read_bytes()))
    for tag, n in counts.most_common(30):
        print(f'  tag {tag:#010x}  {n:6}')
    return 0


def cmd_graph(root: pathlib.Path) -> int:
    g = graph(root)
    pac = None
    if '--pac' in sys.argv:
        d = pathlib.Path(sys.argv[sys.argv.index('--pac') + 1])
        pac = {norm(p.stem.replace('.ps3', '')) for p in d.glob('*.pac')}
    archi = sum(len(v) for v in g.values())
    print(f'{len(g)} mappe con almeno un passaggio, {archi} archi')
    if pac is not None:
        dest = {d for v in g.values() for d in v}
        ok = len(dest & pac)
        print(f'destinazioni distinte: {len(dest)}, di cui esistenti fra i '
              f'.pac: {ok}')
        if dest - pac:
            print('  non trovate:', sorted(dest - pac)[:10])
        rec = sum(1 for a in g for b in g[a] if a in g.get(b, ()))
        print(f'archi con il ritorno presente: {rec} su {archi} '
              f'({100 * rec // archi}%)')
    for k in sorted(g):
        print(f'  {k:<14} -> {", ".join(sorted(g[k]))}')
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, target = sys.argv[1], pathlib.Path(sys.argv[2])
    if cmd == 'info':
        return cmd_info(target)
    if cmd == 'cells':
        return cmd_cells(target)
    if cmd == 'graph':
        return cmd_graph(target)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
