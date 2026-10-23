"""
walk.py - il giro di gioco: stare su una mappa, camminare di cella in cella,
attraversare un passaggio, parlare con chi ci abita.

E' l'anello che mancava, e non ha richiesto nessun formato nuovo: tutti i
pezzi c'erano gia' e nessuno li aveva ancora messi in fila. La mappa si compone
per intero (`view.load`), la griglia logica dice dove c'e' mondo
(`mapdat.cells`), il registro sa dove sta chi (`entity.World`), e il `.pac` sa
disegnarlo. Qui in mezzo c'e' la regola: **una cella per volta**.

Non disegna niente. Questo lo rende verificabile da solo, su tutte le 170
mappe del disco, senza aprire una finestra:

    python walk.py              le verifiche interne, su tutto il disco

## I passaggi, usati invece che contati

Che una cella di partenza dichiari **mappa, varco e direzione** e che nella
destinazione ci sia la cella che quel varco lo dichiara come proprio era gia'
stabilito (`format_mapdat.md`): 508 partenze su 517 si chiudono.

    Warp        D_1_2;-gfrom_d_1;-right      (D_1_1_1, cella 55,11)
    Exit        -gfrom_d_1                   (D_1_2,   cella 12,17)

Quello che qui cambia e' che quel numero smette di essere una statistica sul
grafo e diventa il modo in cui si cambia mappa. Il varco ha due forme e
servono tutte e due, perche' la seconda e' il grosso dei passaggi interni:

- **a nome** (`from_d_1`, `dungeon1`, `tf11_2`): l'arrivo e' una cella di
  classe `Exit` con lo stesso `-g`;
- **a numero** (`-g11;-o101;`): l'arrivo e' la cella che porta quella coppia
  come **propria** identita'. Sono le scale, e infatti le due celle si nominano
  a vicenda - `A` dichiara di portare all'identita' di `B`, e `B` a quella di
  `A`. Leggendo solo la prima forma si risolve il 46% invece del 98%.

E la domanda nuova, che solo camminando si puo' porre: **all'arrivo si sta in
piedi?** Su 303 passaggi che si raggiungono a piedi, 281.

## Chi abita una mappa

Le celle che portano come classe il solo identificativo (`a1_010`) sono i
posti degli NPC. Erano 236 posti per 37 nomi: gli altri 199 non li nominava
nessuno script di evento.

Li nominano i **loro** script. I 243 file `npcevent_n<NN><archetipo><id>` sono
uno per NPC di mappa: dicono il modello (`n05` = `c_npc_05`), l'archetipo
(`oldman`) e l'identificativo (`a1_300`), e 151 di loro si nominano anche per
esteso al proprio interno (`setnpccamerac("OldMana1_300")`), che e' da dove
viene la scrittura esatta del nome.

Il risultato e' che una mappa si popola da sola, con il nome che gli script
userebbero: **225 posti su 236** hanno nome, modello e dialogo.

## Le due griglie e il muro

Le celle fuori mappa (`0xFFFFFFFF`) sono un muro, ma **grossolano**: la
griglia logica marca regioni rettangolari, non corridoi. Da sola lascerebbe
camminare dentro le pareti.

La parete vera la dice `MAPCOLLISION/*.DPK` (vedi `dpk.py`): una mesh di
triangoli per mappa, nello stesso riferimento del `.pac`, che e' proprio cio'
con cui il gioco ferma il giocatore. Dove manca - i palchi degli eventi, la
scena d'apertura - si ripiega sulla geometria disegnata, che e' una
approssimazione e non lo nasconde.

Da mesh a risposte: ogni cella tiene una **colonna** di 64 fette da un quarto
di casella, e per ogni fetta la quota piu' alta che vi si e' trovata. I
triangoli si seminano di punti a passo di una fetta, e ogni punto porta la
normale del proprio triangolo.

Da qui le due domande che servono a camminare, e nient'altro:

- **si passa?** la colonna e' libera all'altezza del corpo (da +0,3 a +1,3
  sopra i piedi);
- **a che altezza si posa il piede?** la superficie piu' alta entro un
  gradino dai piedi - che e' anche come si sale una scala senza sapere che e'
  una scala.

E il gradino non e' una soglia scelta a mano: e' **una casella**. I dislivelli
fra celle vicine calpestabili sono multipli esatti di 1,6 (85,3% a zero, 8,6%
a 1,60, 3,3% a 3,20, quasi niente in mezzo), e spostare la soglia fra 1,7 e 2,5
non cambia un solo numero. Non c'era un parametro da tarare, c'era un quanto da
riconoscere - lo stesso di tutto il resto di questo gioco.

Una sola cosa non si poteva indovinare, e infatti e' costata un errore: **si
sta in piedi solo su cio' che guarda in su**. Un blocco pieno ha vertici solo
sulle sue facce, quindi il pavimento di un sotterraneo alto 1,6 ne offre due -
la faccia di sopra e quella di sotto - e la piu' bassa sembra un pavimento con
un metro e mezzo di aria libera sopra. Contandole tutte e due si cammina dentro
la roccia, la mappa si spezza in isole, e sembra un problema di collisione.
A separarle e' la **normale**.

E una cella non ha **un** pavimento ma fino a quattro: il ballatoio sopra la
sala, il ponte sopra il fossato, il tetto sopra la casa. Chi ne tiene uno solo
trasforma un posto in cui si e' gia' stati in un dislivello invalicabile.
"""
from __future__ import annotations

import pathlib
import re

import numpy as np

import entity
import mapdat

TILE = entity.TILE

# Il valore che la griglia logica usa per "qui non c'e' mappa": il 56% delle
# celle del disco.
OUTSIDE = 0xFFFFFFFF

# La colonna di una cella: fette da un quarto di casella. **Quante**, e da che
# quota parta la prima, non si assumono: li dichiara la mesh di collisione, e
# assumerli e' costato caro. Lo zero non e' il fondo del mondo - 69 file su 171
# scendono sotto, fino a -4,35 - e 25,6 unita' non sono il cielo: `FIELD_07` e'
# una montagna e arriva a 51,2. Ancorare la colonna a zero e alta 64 fette
# buttava via il pavimento di mezzo disco e la cima dell'altro.
SLAB = TILE / 4
SLABS = 64
# Un tetto, perche' un vertice sperduto non faccia allocare un gigabyte: 256
# fette sono 102,4 unita', il doppio della mappa piu' alta del disco.
MAX_SLABS = 256

# Le misure di un passo, in unita' di mondo.
#
# `STEP_UP` e' **una casella**, e non e' una soglia scelta a mano: i dislivelli
# fra celle vicine calpestabili sono quantizzati in multipli esatti di 1,6 -
# 85,3% a zero, 8,6% a 1,60, 3,3% a 3,20, e praticamente nulla in mezzo. Il
# mondo e' costruito a gradini alti quanto un personaggio, come ogni altra cosa
# in questo gioco, quindi 1,6 e' il gradino e 3,2 e' la rupe. Provando a
# spostare la soglia non cambia niente fra 1,7 e 2,5: non c'e' un parametro da
# tarare, c'e' un quanto da riconoscere.
#
# `CHEST` e `HEAD` delimitano la fascia in cui il corpo sbatte: sotto ci sta un
# gradino, sopra ci passa la testa.
STEP_UP, CHEST, HEAD = TILE, 0.3, 1.3

# Quanti piani distinti tenere per cella. Uno non basta - il ballatoio sopra la
# sala e il ponte sopra il fossato sono posti diversi nella stessa cella - e
# oltre il quarto non si trova quasi nulla.
LEVELS = 4

# Da direzione (entity.DIRS) a passo di cella. Le direzioni 0/1 sono l'asse Z,
# e la Z del mondo cresce verso l'alto della griglia: la riga `cy` **cala**
# quando ci si muove verso +Z.
STEP = ((0, -1), (0, 1), (-1, 0), (1, 0))

# `D_1_2;-gfrom_d_1;-right` - mappa, varco, e opzionalmente l'oggetto.
DEST = re.compile(r'^([A-Za-z]\w*);-g([^;]*)(?:;-o([^;]*))?')
# `d_3_1_2`: sotterraneo 3, piano 2. Il piano non e' un dettaglio del nome -
# e' la prima cifra dei varchi numerici che la mappa dichiara.
FLOOR_IN_NAME = re.compile(r'^d_(\d+)_1_(\d+)$')
FLAG_G = re.compile(r'-g([^;]*)')
FLAG_O = re.compile(r'-o([^;]*)')

# Il nome di classe di un oggetto di mappa: una stringa che non e' una
# destinazione, non comincia con un flag, e non e' l'identificativo di un NPC.
CLASS = re.compile(r'^[A-Za-z_][\w]*$')

# Le classi che sono in realta' il nome di una **funzione Lua** da eseguire
# quando il giocatore entra nella cella. Il TODO le dava per irrisolte - «solo
# 3 nomi su 25 trovano il file» - e a sbagliare era la ricerca, non il dato:
# non sono file ma funzioni *dentro* un file per elemento, e `gimmick_grass4`
# vive in `Event/gimmickevent/gimmick_grass.lua.eu` insieme agli altri sei
# `gimmick_grass`. Cercate cosi', si risolvono tutte e 25. Vedi
# `Grid.triggers` e docs/walk.md §grilletti.
TRIGGER_NAME = re.compile(r'^(gimmick|mainevent|coffer|npcevent)_\w+$')


class Link:
    """Una cella di partenza: dove porta e con quale varco."""
    __slots__ = ('cell', 'dest', 'gate', 'obj', 'side')

    def __init__(self, cell, dest, gate, obj, side):
        self.cell, self.dest, self.gate, self.obj, self.side = \
            cell, dest, gate, obj, side

    def __repr__(self) -> str:
        return f'<link {self.cell} -> {self.dest}:{self.gate}>'


class Grid:
    """La griglia logica di una mappa: cosa c'e' in ogni cella.

    Legge una `MAP_ALIGNMENT/*.DAT` e ne tiene le quattro cose che servono a
    starci dentro: le dimensioni, dove c'e' mondo, i posti degli NPC, e i
    passaggi - sia quelli in uscita (`links`) sia quelli in entrata
    (`arrivals`, indicizzati per varco).
    """

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.name = mapdat.norm(path.stem)
        raw = path.read_bytes()
        h = mapdat.header(raw)
        self.w, self.h = h['w'], h['h']
        self.inside = np.zeros((self.h, self.w), bool)
        self.spots: dict[str, tuple[int, int]] = {}
        self.links: dict[tuple[int, int], Link] = {}
        self.arrivals: dict[tuple[str, str | None], tuple[int, int]] = {}
        # Le celle di classe `Exit`: sono i punti d'ingresso veri, quelli in
        # cui il gioco stesso fa comparire qualcuno. `arrivals` invece contiene
        # ogni cella che dichiara un `-g`, e sono centinaia - osservatori,
        # interruttori, gimmick - quindi non e' un posto da cui partire.
        self.exits: dict[str, tuple[int, int]] = {}
        # Gli oggetti di mappa, per classe: `destructionWall`, `PitFall`,
        # `SwitchObserver`, `WarpDoor`... Sono **attori**, non pezzi di mappa -
        # vedi `walk.md` - quindi non stanno ne' nella geometria ne' nella
        # collisione, e l'unico posto in cui esistono e' questa griglia.
        self.objects: dict[str, list[tuple[int, int]]] = {}
        # Le **stanze**. Il `-g` numerico di una cella non e' un indirizzo: e'
        # `(piano)(stanza)`, locale alla mappa. Lo dice un incastro fra due
        # file che non si conoscono - la prima cifra e' il piano che il *nome
        # del file* dichiara, su 2.550 celle su 2.555 - e lo conferma un terzo:
        # le stanze cosi' ricavate sono le stesse che i descrittori
        # `dungeonMapNN_MM` disegnano come `room_on_NN`, 404 su 413 in 21 piani.
        self.floor = FLOOR_IN_NAME.match(self.name)
        self.floor = self.floor.group(2) if self.floor else None
        self.rooms: dict[int, list[tuple[int, int]]] = {}
        # I **nemici piazzati**: `{set: {cella: id di specie}}`. Il TODO dava
        # per buono che il disco dicesse solo *dove vivono* le specie (l'album
        # ha un campo `LivingId`) e che a metterle in mappa fosse il codice.
        # Le mette la griglia, cella per cella: 10.196 celle in tutto il disco.
        # Il `set` e' la lettera di `-s`, vedi mapdat.SPAWN_SET - `A`,`B`,`C`
        # sono tre disposizioni alternative, `F`,`G`,`H` le stesse per FROM
        # Mode. Chi sia la specie lo dice entity.actor_directory().
        self.enemies: dict[str, dict[tuple[int, int], int]] = {}
        # La variante dell'attore, dove la cella la dichiara come cifra al
        # posto di un nome di classe: `{cella: '0'}`. Sono i soli Togetoge.
        self.variants: dict[tuple[int, int], str] = {}
        # Le celle che fanno **scattare un evento**: `{cella: nome}`. Il nome
        # e' quello di una funzione Lua globale, non di un file - `gimmick_grass4`
        # sta dentro `gimmickevent/gimmick_grass.lua.eu`. Cosi' letti, i 25
        # nomi che le celle citano si risolvono tutti e 25 (erano 3).
        self.triggers: dict[tuple[int, int], str] = {}
        # Gli **oggetti di mappa piazzati**: `{cella: identificativo}`, per la
        # sola banda che nomina un modello. Un vaso, un cartello, un ciuffo
        # d'erba, una torcia non hanno un nome nel dato - la cella dichiara
        # un numero, e il numero e' `4000 + m_obj_NN` (oppure `3000 + d_hmw_NN`
        # nei sotterranei). Chi sia il modello lo dice `nodes.props()`.
        self.props: dict[tuple[int, int], int] = {}
        for c in mapdat.cells(raw):
            xy = (c['x'], c['y'])
            if c['tag'] != OUTSIDE:
                self.inside[c['y'], c['x']] = True
            link = None
            for s in (c['params'], c['cls']):
                m = DEST.match(s or '')
                if m and link is None:
                    side = 'right' if '-right' in s else \
                        'down' if '-down' in s else None
                    link = Link(xy, mapdat.norm(m.group(1)), m.group(2),
                                m.group(3), side)
            if link is not None:
                self.links.setdefault(xy, link)
            # L'identita' della cella sta nella stringa che **non** e' una
            # destinazione: una cella puo' avere le due cose insieme, ed e'
            # anzi il caso normale delle scale (`A` dice dove porta, e dice
            # anche chi e' perche' `B` possa portare qui).
            g = o = None
            for s in (c['params'], c['cls']):
                if not s or DEST.match(s):
                    continue
                mg, mo = FLAG_G.search(s), FLAG_O.search(s)
                if mg and g is None:
                    g = mg.group(1)
                if mo and o is None:
                    o = mo.group(1)
                for m in mapdat.NPC_ID.finditer(s):
                    self.spots.setdefault(m.group(1), xy)
                # e la classe, se questa stringa e' un nome invece che dei
                # flag: `Barricade` sta nella stringa dei *parametri* e i suoi
                # flag in quella della classe, quindi si guardano tutte e due
                head = s.rstrip(';').split(';')[0]
                if (CLASS.match(head) and not mapdat.NPC_ID.match(head)
                        and head not in ('right', 'down')):
                    self.objects.setdefault(head, []).append(xy)
                    if TRIGGER_NAME.match(head):
                        self.triggers.setdefault(xy, head)
            if c['actor'] and 3000 <= c['actor'] < 5000:
                self.props[xy] = c['actor']
            if c['set'] and c['actor'] and c['actor'] >= 5000:
                self.enemies.setdefault(c['set'], {})[xy] = c['actor']
                # Dove la "classe" e' una cifra non e' un nome di oggetto ma
                # una variante dell'attore: sono i 94 Togetoge, e la cifra
                # sceglie fra le cinque coppie Initialize/Update che il loro
                # file dichiara. Vedi actor.Troupe.behaviour.
                cl = (c['cls'] or '').rstrip(';')
                if cl.isdigit():
                    self.variants[xy] = cl
            if g is not None:
                self.arrivals.setdefault((g, o), xy)
                self.arrivals.setdefault((g, None), xy)
                r = self.room_of(g)
                if r is not None:
                    self.rooms.setdefault(r, []).append(xy)
                if 'Exit' in (c['cls'], c['params']):
                    self.exits.setdefault(g, xy)

    def room_of(self, gate: str) -> int | None:
        """La stanza che un varco numerico nomina, se questa mappa ha piani.

        `-g122` in `d_1_1_1` e' il piano 1 e la stanza 22; `-g37` in `d_7_1_3`
        e' il piano 3 e la stanza 7. Non e' una lettura arbitraria: la prima
        cifra coincide con il piano scritto nel **nome del file** su 2.550
        celle su 2.555, e le stanze che ne escono sono le stesse che lo schermo
        della mappa del sotterraneo disegna una per una.
        """
        if not self.floor or not gate.isdigit() \
                or not gate.startswith(self.floor):
            return None
        rest = gate[len(self.floor):]
        return int(rest) if rest.isdigit() and rest else None

    # -- da cella a mondo

    def local(self, cx: float, cy: float, y: float = 0.0):
        """Il **centro** della cella, nel riferimento in cui la geometria e'
        caricata (origine al centro della mappa, Z verso l'alto della griglia).

        Il mezzo passo non e' un dettaglio: senza, un personaggio sta
        sull'angolo di quattro celle invece che dentro una, e a occhio sembra
        sempre mezza casella fuori posto."""
        return (float(cx + 0.5) * TILE - self.w * TILE / 2, float(y),
                self.h * TILE / 2 - float(cy + 0.5) * TILE)

    def cell_of(self, pos) -> tuple[int, int]:
        """La cella in cui cade un punto del mondo. L'inverso di `local`."""
        return (int(np.floor((pos[0] + self.w * TILE / 2) / TILE)),
                int(np.floor((self.h * TILE / 2 - pos[2]) / TILE)))

    def on_map(self, cx: int, cy: int) -> bool:
        return 0 <= cx < self.w and 0 <= cy < self.h

    def outside(self, cx: int, cy: int) -> bool:
        """Fuori dal mondo: oltre il bordo, o in una cella che la griglia
        logica non attribuisce a nessuna regione."""
        return not self.on_map(cx, cy) or not self.inside[cy, cx]

    def arrival(self, link: Link) -> tuple[int, int] | None:
        """Dove si arriva entrando da un varco. Vedi il docstring del modulo:
        prima la coppia esatta, poi il solo nome del varco."""
        return self.arrivals.get((link.gate, link.obj)) or \
            self.arrivals.get((link.gate, None))

    def __repr__(self) -> str:
        return (f'<grid {self.name} {self.w}x{self.h} '
                f'{int(self.inside.sum())} celle di mondo, '
                f'{len(self.links)} passaggi, {len(self.spots)} abitanti, '
                f'{sum(len(v) for v in self.objects.values())} oggetti, '
                f'{sum(len(v) for v in self.enemies.values())} nemici in '
                f'{len(self.enemies)} set>')


class Atlas:
    """Tutte le griglie del disco, caricate a richiesta.

    Serve perche' un passaggio si risolve **nell'altra mappa**: per sapere dove
    si arriva bisogna avere aperto la destinazione.
    """

    def __init__(self, root: pathlib.Path):
        # `root` e' `.../data`, oppure direttamente la cartella MAP_ALIGNMENT
        self.dir = root if root.name.upper() == 'MAP_ALIGNMENT' \
            else root / 'map/MAP_ALIGNMENT'
        self.files = {mapdat.norm(p.stem): p for p in self.dir.glob('*.DAT')}
        self.cache: dict[str, Grid] = {}

    def grid(self, name: str) -> Grid | None:
        key = mapdat.norm(name)
        if key not in self.cache:
            p = self.files.get(key)
            self.cache[key] = Grid(p) if p else None
        return self.cache[key]

    def where(self, name: str) -> dict:
        """Come si chiama il posto, e con che musica. Vedi mapdat.locations().

        Si carica una volta sola: e' un file di 211 righe per tutto il disco.
        """
        if not hasattr(self, '_loc'):
            self._loc = mapdat.locations(self.dir.parent.parent)
        return self._loc.get(mapdat.norm(name), {})

    def resolve(self, link: Link):
        """Da una cella di partenza al punto d'arrivo: `(griglia, cella)`."""
        g = self.grid(link.dest)
        if g is None:
            return None
        cell = g.arrival(link)
        return (g, cell) if cell else None

    def pac_for(self, name: str) -> pathlib.Path | None:
        """Il container di geometria di una mappa. I nomi non concordano nelle
        maiuscole (`FIELD_16.DAT` / `Field_16.ps3.pac.gz`), quindi si confronta
        con la chiave normalizzata."""
        d = self.dir.parent / 'pac_data'
        key = mapdat.norm(name)
        for p in d.glob('*.pac*'):
            if mapdat.norm(p.name.split('.')[0]) == key:
                return p
        return None


# ------------------------------------------------------- il muro vero

class Columns:
    """L'occupazione della mappa, cella per cella e fetta per fetta.

    Per ogni cella una colonna di 64 fette, e per ogni fetta **la quota piu'
    alta** che vi si e' trovata. Si riempie con i vertici della geometria gia'
    caricata: non costa un secondo passaggio sul disco, e non serve nessun
    formato nuovo.

    Tenere la quota e non solo un si/no e' quello che rende la colonna
    utilizzabile. Un pavimento e un muro possono cadere nella stessa fetta, e
    distinguerli e' esattamente la differenza fra "ci cammino sopra" e "ci
    sbatto contro".

    Il `DPK` (171 file) resta la strada giusta per la collisione vera; questa
    e' la strada che si puo' percorrere oggi, ed e' abbastanza per la domanda
    che il giro di gioco pone: *da qui, di la', ci passo?*
    """

    def __init__(self, grid: Grid, parts=(), base: float = 0.0,
                 slabs: int = SLABS):
        self.grid = grid
        # La quota della prima fetta e quante fette. Vedi `span()`: non e' una
        # costante, e' una misura della mappa.
        self.base, self.slabs = float(base), int(slabs)
        # La quota del fondo del mondo, quando `bury()` l'ha riconosciuto.
        self.bottom: float | None = None
        # -inf vuol dire "in questa fetta non c'e' niente": tutti i confronti
        # con una quota lo escludono da soli, senza una maschera a parte.
        #
        # Due tabelle e non una, e la ragione e' costata un errore: un blocco
        # pieno ha vertici **solo sulle sue facce**, sopra e sotto. Contando
        # tutto insieme, il pavimento di un sotterraneo alto 1,6 offre due
        # quote - 1,6 sopra e 0,0 sotto - e la piu' bassa sembra un pavimento
        # perfettamente calpestabile con un metro e mezzo di aria libera
        # sopra. Cioe' si cammina **dentro la roccia**, e la mappa si spezza
        # in isole scollegate.
        #
        # A dire quale delle due facce e' un pavimento e' la **normale**: si
        # sta in piedi su cio' che guarda in su. Quindi `top` raccoglie solo
        # quelle, e `solid` tutto il resto - perche' per sbatterci contro la
        # normale non conta.
        self.top = np.full((grid.h, grid.w, self.slabs), -np.inf, np.float32)
        self.solid = np.full((grid.h, grid.w, self.slabs), -np.inf, np.float32)
        self.filled = False
        for p in parts:
            self.add(p.pos, getattr(p, 'nrm', None))

    def add(self, pos: np.ndarray, nrm: np.ndarray | None = None) -> None:
        g = self.grid
        cx = np.floor((pos[:, 0] + g.w * TILE / 2) / TILE).astype(np.int32)
        cy = np.floor((g.h * TILE / 2 - pos[:, 2]) / TILE).astype(np.int32)
        sl = np.floor((pos[:, 1] - self.base) / SLAB).astype(np.int32)
        keep = ((cx >= 0) & (cx < g.w) & (cy >= 0) & (cy < g.h) &
                (sl >= 0) & (sl < self.slabs))
        idx = (cy[keep], cx[keep], sl[keep])
        y = pos[keep, 1]
        # `maximum.at` e non `top[...] = ...`: gli indici si ripetono - in una
        # cella cadono migliaia di vertici - e l'assegnazione indicizzata ne
        # terrebbe uno solo, a caso.
        np.maximum.at(self.solid, idx, y)
        if nrm is None:
            np.maximum.at(self.top, idx, y)
        else:
            n = nrm[keep]
            ln = np.linalg.norm(n, axis=1)
            up = (ln > 1e-3) & (n[:, 1] > 0.5 * ln)
            np.maximum.at(self.top, tuple(i[up] for i in idx), y[up])
        self.filled = self.filled or bool(keep.any())

    def add_parts(self, parts) -> None:
        for p in parts:
            self.add(p.pos, p.nrm)

    def add_mesh(self, verts, tris) -> bool:
        """Una mesh di triangoli versata nelle colonne, a gruppi.

        Ogni punto porta la normale del **suo triangolo**, che e' esatta invece
        che interpolata."""
        import dpk

        if not len(tris):
            return False
        for pts, nrm in dpk.seed(verts, tris, SLAB):
            self.add(pts, nrm)
        return True

    def bury(self) -> int:
        """Toglie dai pavimenti il **fondo del mondo** dove sopra c'e' terra.

        Ogni mappa di campagna posa su un unico quadrilatero piatto steso sotto
        tutto - in `FIELD_22` sono **due triangoli** per 10.368 caselle, su una
        mappa che ne ha 16.384 - a -3,2 o giu' di li'. Guarda in su, quindi e'
        un pavimento a tutti gli effetti; solo che sopra ha metri di roccia.

        Chi ci si mette cammina dentro la terra, e siccome e' il piano piu'
        basso e' anche quello da cui la mappa comincia: la campagna scendeva a
        84 celle percorse su 10.219. Non e' un difetto della lettura, e' che
        la geometria non distingue un pavimento da un fondale - lo stesso
        motivo per cui serviva la normale, un piano piu' in giu'.

        A separarli e' un conto, non una soglia: le celle a due piani sono
        163.878, e in **758** soltanto quello di sotto non e' il fondo della
        mappa. Il ballatoio sopra la sala esiste - e resta, perche' il suo
        piano di sotto non sta alla quota minima - ma e' lo 0,16% del mondo.
        Tutto il resto della sovrapposizione e' questo fondale.

        Le celle in cui il fondo e' l'**unico** piano non si toccano: sono il
        mare e i fossati, e restano riconoscibili proprio da questo.

        Un fondale va riconosciuto, non assunto, perche' in un sotterraneo la
        quota minima **e'** il pavimento e toglierlo svuoterebbe la mappa. Tre
        cose insieme, e nessuna delle tre da sola basta:

        - e' **piatto** - tutte le sue quote entro una fetta, che e' quanto
          basta per un quadrilatero unico;
        - e' **esteso** - copre almeno un terzo delle celle che hanno un
          pavimento (`FIELD_22`: 10.368 caselle su 16.384);
        - ha **terra sopra** - in almeno un quarto delle celle che copre c'e'
          un altro pavimento piu' in alto. E' questa la terza che separa il
          fondale dal pavimento di `d_1_2`, che pure copre il 69% della sua
          mappa ma non ha niente sopra di se'.
        """
        fin = self.top > -np.inf
        if not fin.any():
            return 0
        lo = float(self.top[fin].min())
        at = fin & (self.top < lo + SLAB)
        above = (fin & (self.top >= lo + SLAB)).any(axis=2)
        n_at = int(at.any(axis=2).sum())
        if not n_at or n_at < fin.any(axis=2).sum() / 3:
            return 0
        if int((at.any(axis=2) & above).sum()) < n_at / 4:
            return 0
        drop = at & above[:, :, None]
        self.top[drop] = -np.inf
        self.bottom = lo
        return int(drop.sum())

    def add_collision(self, path) -> bool:
        """Il muro vero, da `MAPCOLLISION/*.DPK`.

        La mesh di collisione e' un centesimo dei poligoni della mappa e vive
        nello stesso riferimento, quindi non c'e' niente da convertire."""
        import dpk

        return self.add_mesh(*dpk.mesh(path))

    def water(self) -> np.ndarray:
        """Le celle di **acqua e vuoto**: quelle in cui l'unica superficie e' il
        fondale steso sotto la mappa.

        Il mare, il fossato, la gola fra due altipiani. Il gioco non ci mette
        niente - ne' geometria ne' collisione oltre al fondale - e infatti in un
        fotogramma dell'overworld sono le grandi zone nere. Serve saperlo in due
        posti: per non contarle fra le celle da raggiungere a piedi, e per non
        contarle fra le celle che la composizione degli schermi deve coprire.
        """
        here = self.top > -np.inf
        if self.bottom is None:
            return np.zeros(here.shape[:2], bool)
        return here.any(axis=2) & ~(here & (self.top > self.bottom + SLAB)
                                    ).any(axis=2)

    def water_level(self) -> np.ndarray:
        """La quota del pelo dell'acqua, cella per cella (`nan` dove non c'e').

        Non e' dichiarata da nessuna parte - gli script parlano di ambienti
        (`FIELD_WATER` e' un posto in cui vivono delle creature, non un piano)
        - quindi si deriva, e il mondo la stringe da tutte e due le parti:
        il fondale sta **due caselle esatte** sotto la riva nel 52,9% dei casi,
        e la riva sta a 0,00 nel 50%. Fra i due c'e' un solo multiplo di una
        casella, ed e' li'.

        Ogni specchio d'acqua prende la sua: si parte dalle celle di riva - la
        terra piu' bassa che le tocca, meno una casella - e si propaga il
        minimo dentro l'acqua, cosi' un lago di montagna e il mare non finiscono
        alla stessa quota. Propagare il **minimo** e non la media e' quello che
        la tiene piatta su tutto lo specchio.
        """
        w = self.water()
        lvl = np.full(w.shape, np.nan, np.float32)
        if not w.any():
            return lvl
        here = self.top > -np.inf
        above = here & (self.top > self.bottom + SLAB)
        land = np.where(above.any(axis=2),
                        np.where(above, self.top, np.inf).min(axis=2), np.nan)
        # le rive: una cella d'acqua che tocca la terra
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n = np.full(w.shape, np.nan, np.float32)
            n[max(0, dy):w.shape[0] + min(0, dy),
              max(0, dx):w.shape[1] + min(0, dx)] = \
                land[max(0, -dy):w.shape[0] + min(0, -dy),
                     max(0, -dx):w.shape[1] + min(0, -dx)]
            take = w & ~np.isnan(n) & (np.isnan(lvl) | (n - TILE < lvl))
            lvl[take] = n[take] - TILE
        # e poi il minimo si propaga nell'acqua aperta
        for _ in range(max(w.shape)):
            grown = lvl.copy()
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                n = np.full(w.shape, np.nan, np.float32)
                n[max(0, dy):w.shape[0] + min(0, dy),
                  max(0, dx):w.shape[1] + min(0, dx)] = \
                    lvl[max(0, -dy):w.shape[0] + min(0, -dy),
                        max(0, -dx):w.shape[1] + min(0, -dx)]
                take = w & ~np.isnan(n) & (np.isnan(grown) | (n < grown))
                grown[take] = n[take]
            if np.array_equal(np.isnan(grown), np.isnan(lvl)) and \
                    np.allclose(np.nan_to_num(grown), np.nan_to_num(lvl)):
                break
            lvl = grown
        # uno specchio senza riva - tutto mare fino al bordo - sta una casella
        # sopra il proprio fondale
        lvl[w & np.isnan(lvl)] = self.bottom + TILE
        return lvl

    def slab_of(self, y: float) -> int:
        """La fetta in cui cade una quota. Arrotonda **verso il basso** e non
        verso lo zero: con una base negativa `int()` sbaglia di una fetta
        proprio attorno all'origine, che e' dove sta il pavimento."""
        return int(np.floor((y - self.base) / SLAB))

    def levels(self, cx: int, cy: int):
        """Le quote su cui c'e' qualcosa, dal basso verso l'alto."""
        col = self.top[cy, cx]
        for s in range(self.slabs):
            if col[s] > -np.inf:
                yield float(col[s])

    def ground(self, cx: int, cy: int) -> float | None:
        """La quota piu' bassa su cui si sta in piedi, o `None` se in quella
        colonna non si sta.

        E' la domanda giusta per **comparire** in una cella, e la risposta non
        e' ne' "la cosa piu' in alto" ne' "la cosa piu' in basso": dall'alto si
        finirebbe sul tetto - le mappe di questo gioco hanno il soffitto - e
        dal basso su un pavimento che non esiste, perche' il pavimento vero di
        un sotterraneo sta a 1,6 e non a zero.
        """
        if not self.grid.on_map(cx, cy):
            return None
        for t in self.levels(cx, cy):
            if not self.blocked(cx, cy, t):
                return t
        return None

    def ground_near(self, cx: int, cy: int) -> float | None:
        """La quota del pavimento **accanto**, per chi e' piazzato dove non ce
        n'e'.

        Serve ai nemici che la griglia mette dentro il muro, ed e' misurato
        che il caso e' sempre lo stesso: nei sotterranei 546 nemici su 4.099
        stanno su una cella senza pavimento, e **tutti e 546** ne hanno almeno
        uno degli otto vicini - da uno a tre, mai zero e mai piu' di tre.
        Nessuno e' piu' di una cella oltre il bordo. In campagna il caso non
        si presenta mai: **0 su 6.097**.

        Non e' uno scarto nostro fra la griglia e la collisione, ed e' stato
        misurato: spostare *tutti* i nemici di una cella porta i sotterranei
        dall'86,7% all'87,6% di celle calpestabili, cioe' un guadagno che e'
        rumore. Il piazzamento sborda di una cella dentro il muro perche' e'
        disegnato sul rettangolo della stanza; in campagna non c'e' muro in
        cui sbordare.

        Quale delle celle accanto non e' una scelta difficile: in 497 casi su
        546 i vicini con pavimento stanno **tutti alla stessa quota**. Qui si
        prende la piu' bassa.
        """
        h = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1)
             if (dx or dy)
             for q in (self.ground(cx + dx, cy + dy),) if q is not None]
        return min(h) if h else None

    def surface(self, cx: int, cy: int, feet: float) -> float | None:
        """La quota su cui si posa il piede entrando in una cella, o `None` se
        non c'e' niente su cui posarlo.

        Si guarda la superficie piu' alta che stia entro **un gradino** dai
        piedi: e' cosi' che si sale una scala senza sapere che e' una scala, e
        che non si sale una rupe."""
        if not self.grid.on_map(cx, cy):
            return None
        col = self.top[cy, cx]
        hi = min(self.slab_of(feet + STEP_UP), self.slabs - 1)
        for s in range(hi, -1, -1):
            if col[s] > -np.inf:
                return float(col[s])
        return None

    def blocked(self, cx: int, cy: int, floor: float) -> bool:
        """C'e' qualcosa all'altezza del corpo, sopra quel pavimento?

        Dal petto (+0,3) alla testa (+1,3): sotto ci sta un gradino, sopra ci
        si passa. Il confronto e' sulla **quota**, non sulla fetta, perche' il
        pavimento stesso cade spesso nella prima fetta della fascia."""
        if not self.grid.on_map(cx, cy):
            return True
        a = max(0, self.slab_of(floor + CHEST))
        b = min(self.slab_of(floor + HEAD), self.slabs - 1)
        if b < a:
            return False
        band = self.solid[cy, cx, a:b + 1]
        return bool(((band > floor + CHEST) & (band < floor + HEAD)).any())

    def empty(self) -> bool:
        return not self.filled

    def field(self, levels: int = LEVELS):
        """I **piani** di ogni cella: `(quote (h, w, k), validi (h, w, k))`.

        La stessa regola di `ground()`, scritta per il tabellone invece che per
        una cella - la misura deve percorrere 170 mappe e non puo' farlo cella
        per cella in Python - ma con una differenza che conta: una colonna puo'
        avere **piu' di un piano** su cui si sta in piedi, e tenerne uno solo
        falsa tutto.

        Il ballatoio sopra la sala, il ponte sopra il fossato, il tetto sopra
        la casa: se di quella cella si ricorda solo il piano piu' basso, il
        ballatoio diventa un dislivello invalicabile invece che un posto in
        cui si e' gia' stati. Con un piano per cella la campagna risultava
        raggiungibile all'1%; con quattro, tutt'altra cosa.

        La fascia del corpo tocca al massimo cinque fette a partire da quella
        del pavimento - lo dicono le misure, non una scelta - quindi bastano
        cinque confronti per fetta invece di sessantaquattro.
        """
        top, solid = self.top, self.solid
        h, w = top.shape[:2]
        here = top > -np.inf
        floor = np.full((h, w, levels), np.nan, np.float32)
        n = np.zeros((h, w), np.int32)
        for s in range(self.slabs):
            todo = here[:, :, s] & (n < levels)
            if not todo.any():
                continue
            t = top[:, :, s]
            hit = np.zeros_like(todo)
            for u in range(s, min(s + 5, self.slabs)):
                band = solid[:, :, u]
                hit |= (band > t + CHEST) & (band < t + HEAD)
            good = todo & ~hit
            ys, xs = np.nonzero(good)
            floor[ys, xs, n[good]] = t[good]
            n[good] += 1
        return floor, ~np.isnan(floor)


def span(y, margin: int = 1) -> tuple[float, int]:
    """Da che quota parte la colonna e quante fette servono, **dal dato**.

    Una fetta di margine sotto e una sopra, perche' il pavimento di un
    sotterraneo sta a `-0,000002` e non a zero - lo scarto di un float32 che ha
    attraversato una somma baricentrica - e una fetta ancorata allo zero se lo
    perde per intero.
    """
    if not len(y):
        return 0.0, SLABS
    lo, hi = float(np.min(y)), float(np.max(y))
    base = (np.floor(lo / SLAB) - margin) * SLAB
    n = int(np.ceil((hi - base) / SLAB)) + margin
    return float(base), int(np.clip(n, 8, MAX_SLABS))


def columns_for(grid: Grid, root: pathlib.Path, parts=None) -> Columns:
    """Le colonne di una mappa, dalla fonte migliore disponibile.

    Il file di collisione se c'e' - e c'e' per 170 mappe su 170 - altrimenti la
    geometria disegnata, che resta l'unica strada per un modello senza `.DPK`
    (i palchi degli eventi, la scena d'apertura).

    Le due fonti non sono equivalenti e non pretendono di esserlo: il `.DPK` e'
    quello che il gioco usa per fermare il giocatore, la geometria e' quello
    che si vede. Dove il gioco lascia passare in mezzo all'erba alta, il
    secondo dice muro.

    La fonte, qualunque sia, dice anche **quanto e' alto il mondo**: la colonna
    si dimensiona su di lei prima di allocarla.
    """
    import dpk

    p = dpk.for_map(root, grid.name)
    if p is not None:
        v, t = dpk.mesh(p)
        if len(t):
            base, n = span(v[:, 1])
            c = Columns(grid, base=base, slabs=n)
            c.add_mesh(v, t)
            c.bury()
            return c
    ys = [q.pos[:, 1] for q in (parts or ()) if len(q.pos)]
    if ys:
        ends = np.array([min(y.min() for y in ys), max(y.max() for y in ys)],
                        np.float32)
        base, n = span(ends)
        c = Columns(grid, base=base, slabs=n)
        c.add_parts(parts)
        return c
    return Columns(grid)


def reachable(columns: Columns, start):
    """Dove si arriva a piedi, partendo da una cella **o da tutte le porte**.

    La stessa regola del passo - un dislivello che si sale, niente addosso
    all'altezza del corpo - applicata a tutta la mappa insieme invece che a una
    cella per volta. Serve alla misura: una mappa in cui il punto d'ingresso
    non porta da nessuna parte e' una mappa in cui qualcosa, da qualche parte,
    e' letto male.

    Lo stato non e' la cella ma **la cella e il piano**: chi sta sul ballatoio e
    chi sta sotto sono nello stesso posto e non si incontrano.

    `start` e' una cella oppure un elenco di celle. L'elenco non e' una comodita':
    una mappa si entra da **tutte** le sue porte, e prenderne una sola misura la
    porta invece della mappa. In `field_14` la prima delle sei `Exit` da' su un
    ripiano di 16 celle sotto una rupe, e le altre cinque sulle 3.213 che sono
    la mappa.

    Restituisce `(raggiunte, quote, calpestabili)`, le ultime due per piano.
    """
    floor, ok = columns.field()
    val = np.nan_to_num(floor, nan=1e9)
    lv = floor.shape[2]
    seen = np.zeros_like(ok)
    cells = [start] if isinstance(start[0], (int, np.integer)) else list(start)
    for sx, sy in cells:
        if columns.grid.on_map(sx, sy) and ok[sy, sx].any():
            seen[sy, sx, np.argmax(ok[sy, sx])] = True
    if not seen.any():
        return seen.any(axis=2), floor, ok
    # Le adiacenze fra piani, calcolate una volta: `east[i, j]` dice se dal
    # piano i di una cella si passa al piano j di quella a destra.
    east = [[(ok[:, :-1, i] & ok[:, 1:, j] &
              (np.abs(val[:, :-1, i] - val[:, 1:, j]) <= STEP_UP))
             for j in range(lv)] for i in range(lv)]
    south = [[(ok[:-1, :, i] & ok[1:, :, j] &
               (np.abs(val[:-1, :, i] - val[1:, :, j]) <= STEP_UP))
              for j in range(lv)] for i in range(lv)]
    while True:
        # una dilatazione per volta, finche' non cresce piu': su una griglia da
        # 16.000 celle sono qualche centinaio di passate di numpy, cioe' meno
        # di quanto costerebbe una coda in Python
        grown = seen.copy()
        for i in range(lv):
            for j in range(lv):
                grown[:, 1:, j] |= seen[:, :-1, i] & east[i][j]
                grown[:, :-1, i] |= seen[:, 1:, j] & east[i][j]
                grown[1:, :, j] |= seen[:-1, :, i] & south[i][j]
                grown[:-1, :, i] |= seen[1:, :, j] & south[i][j]
        if grown.sum() == seen.sum():
            return seen.any(axis=2), floor, ok
        seen = grown


# ------------------------------------------------------------ la sessione

class Walk:
    """Una partita: una mappa, il suo mondo, e il giocatore che ci cammina.

    Tiene insieme i tre pezzi che finora vivevano separati - la griglia
    (`Grid`), il registro (`entity.World`) e l'occupazione (`Columns`) - e
    aggiunge l'unica regola nuova: **si va di una cella per volta**, e ci si
    va solo se di la' ci si sta.
    """

    SPEED = 4.8               # unita' al secondo: tre caselle, come `MoveNpc`

    def __init__(self, atlas: Atlas, grid: Grid, world=None):
        self.atlas = atlas
        self.grid = grid
        self.world = world if world is not None else entity.World()
        self.columns = Columns(grid)
        self.cell = (grid.w // 2, grid.h // 2)
        self.pending: Link | None = None      # passaggio da attraversare
        self.troupe = None                    # gli script dei nemici, se attivi

    @property
    def player(self):
        """Il giocatore, per chi ha bisogno di sapere dov'e' - i nemici."""
        return self.world.player

    # -- popolamento

    def populate(self, directory: dict) -> int:
        """Mette sulla mappa i suoi abitanti.

        Il nome e' quello che gli script userebbero (`OldMana1_300`), quindi un
        evento che piu' tardi nomini quell'NPC trova **questo**, gia' al suo
        posto, invece di materializzarne un altro senza posizione.
        """
        n = 0
        for ident, xy in self.grid.spots.items():
            info = directory.get(ident)
            name = info['name'] if info else ident
            e = self.world.npcs.get(name)
            if e is None:
                e = entity.Entity(name, model=info['model'] if info else None)
                self.world.npcs[name] = e
                self.world.order.append(name)
            x, _y, z = self.grid.local(*xy)
            f = self.columns.ground(*xy)
            e.pos = [x, f if f is not None else 0.0, z]
            e.created = True                  # collocato: si puo' disegnare
            e.facing = 1                      # verso il basso dello schermo
            if info:
                e.script = info['script']
            # E anche gli abitanti hanno il proprio script: `N05OldMan.lua`
            # gironzola di quattro caselle alla volta, il Re non si muove
            # affatto perche' il suo file non ha una `Update`. Vedi actor.py.
            if self.troupe is not None and info:
                self.troupe.cast(name, e, 0, info.get('model') or '')
            n += 1
        return n

    def populate_enemies(self, actors: dict, spawn: str = 'A',
                         motion: dict | None = None) -> int:
        """Mette sulla mappa i nemici del set richiesto.

        `spawn` e' la lettera di `-s`: `A`, `B` o `C` sono le tre disposizioni
        fra cui il gioco sceglie, `F`, `G`, `H` le stesse per FROM Mode (vedi
        mapdat.SPAWN_SET). Cambiarla ripopola la mappa con **le stesse specie
        in altri posti**, che e' esattamente cio' che si vede uscendo da una
        stanza e rientrando.

        I nemici non hanno un nome nel dato - la cella dichiara la specie, non
        l'individuo - quindi il nome e' costruito dalla cella e serve solo a
        tenerli distinti nel registro. Uno script non li nomina mai.

        Il set `Z` si aggiunge **sempre**, qualunque lettera si chieda, e non e'
        una comodita': sono i 94 Togetoge, gli spuntoni, che non sono nemici da
        ripiazzare ma parte della stanza. Una trappola non cambia posto quando
        esci e rientri - e infatti e' l'unico set con una lettera fuori dalle
        due terne. Vedi mapdat.SPAWN_SET e docs/walk.md.
        """
        n = 0
        posti = dict(self.grid.enemies.get(spawn, {}))
        if spawn != 'Z':
            posti.update(self.grid.enemies.get('Z', {}))
        for xy, num in posti.items():
            info = actors.get(num)
            if not info or not info.get('draw'):
                continue
            name = f'@enemy_{xy[0]}_{xy[1]}'
            e = self.world.npcs.get(name)
            if e is None:
                e = entity.Entity(name, kind='enemy', model=info['draw'])
                self.world.npcs[name] = e
                self.world.order.append(name)
            x, _y, z = self.grid.local(*xy)
            f = self.columns.ground(*xy)
            if f is None:
                f = self.columns.ground_near(*xy)
            e.pos = [x, f if f is not None else 0.0, z]
            e.created = True
            e.facing = 1
            mv = (motion or {}).get(num)
            if mv:
                e.frames = list(mv['poses'])
                if mv['wait']:
                    e.step = float(mv['wait'])
            if self.troupe is not None:
                self.troupe.cast(name, e, num, info.get('model') or '',
                                 self.grid.variants.get(xy))
            n += 1
        return n

    def populate_props(self, catalog: dict) -> int:
        """Mette sulla mappa i suoi oggetti: vasi, cartelli, torce, erba.

        `catalog` e' `nodes.props()`, cioe' da identificativo di cella al nodo
        da disegnare. Non sono attori con un comportamento - il loro script ha
        `Update` vuota quasi sempre - ma stanno nel registro come tutti gli
        altri, perche' il disegnatore sa gia' disegnare un'entita' e non deve
        imparare una seconda strada.

        Gli identificativi senza modello si saltano, e non sono un buco: sono
        i marcatori invisibili (`Warp`, `Exit`, gli osservatori), che
        `walk.md` aveva gia' misurato assenti sia dalla geometria sia dalla
        collisione. Che non abbiano nemmeno un `m_obj` e' la stessa cosa
        detta dal lato delle librerie.
        """
        n = 0
        for xy, num in self.grid.props.items():
            info = catalog.get(num)
            if not info:
                continue
            name = f'@prop_{xy[0]}_{xy[1]}'
            e = self.world.npcs.get(name)
            if e is None:
                e = entity.Entity(name, kind='prop', model=info['node'])
                self.world.npcs[name] = e
                self.world.order.append(name)
            x, _y, z = self.grid.local(*xy)
            f = self.columns.ground(*xy)
            if f is None:
                f = self.columns.ground_near(*xy)
            e.pos = [x, f if f is not None else 0.0, z]
            e.created = True
            n += 1
        return n

    def hire(self, data) -> int:
        """Accende gli script dei nemici, e li fa girare da qui in avanti.

        Separato dal popolamento perche' costa: carica una VM Lua con dentro
        `all.lua.eu`. Chi vuole solo misurare dove si cammina non ne ha
        bisogno, e infatti `walkabout` non lo chiama.

        Restituisce quanti nemici hanno trovato il proprio comportamento.
        """
        import actor

        self.troupe = actor.Troupe(data, self)
        return 0

    def animate(self, dt: float) -> int:
        """Un fotogramma di vita per i nemici. Zero se non sono stati assunti."""
        return self.troupe.update(dt) if self.troupe is not None else 0

    # -- il giocatore

    def place(self, cx: int, cy: int) -> None:
        self.cell = (cx, cy)
        x, _, z = self.grid.local(cx, cy)
        f = self.columns.ground(cx, cy)
        self.world.player.pos = [x, f if f is not None else 0.0, z]
        self.world.player.stop()

    def start_cell(self) -> tuple[int, int]:
        """Da dove si comincia, quando nessuno lo dice.

        Prima un varco d'ingresso - e' un posto in cui il gioco stesso fa
        arrivare qualcuno, quindi ci si sta di sicuro - poi la cella libera
        piu' vicina al centro del mondo dichiarato.
        """
        for xy in self.grid.exits.values():
            if self.standable(*xy)[0]:
                return xy
        ys, xs = np.nonzero(self.grid.inside)
        if not len(xs):
            return (self.grid.w // 2, self.grid.h // 2)
        cx, cy = int(xs.mean()), int(ys.mean())
        # dal centro delle celle di mondo verso l'esterno, e ci si ferma alla
        # prima in cui si sta in piedi
        order = np.argsort((xs - cx) ** 2 + (ys - cy) ** 2)
        for i in order:
            xy = (int(xs[i]), int(ys[i]))
            if self.standable(*xy)[0]:
                return xy
        return (cx, cy)

    def standable(self, cx: int, cy: int, feet: float | None = None):
        """Ci si sta, in quella cella? E su cosa si posa il piede?

        Senza geometria caricata resta il solo confine dichiarato dalla
        griglia logica - un muro grossolano, ma e' quello che il dato dice da
        solo, e le verifiche girano cosi'."""
        if self.grid.outside(cx, cy):
            return False, None
        if self.columns.empty():
            return True, None
        if feet is None:                      # comparire, non camminare
            return self.columns.ground(cx, cy) is not None,                 self.columns.ground(cx, cy)
        f = self.columns.surface(cx, cy, feet)
        # Ne' un muro ne' un salto nel vuoto: un dislivello piu' alto di un
        # gradino non si sale **e non si scende**, che e' anche cio' che
        # impedisce di camminare fuori da un tetto.
        if f is None or abs(f - feet) > STEP_UP + 1e-3:
            return False, None
        return not self.columns.blocked(cx, cy, f), f

    def step(self, facing: int) -> str:
        """Un passo. Restituisce cosa e' successo, che e' anche cosa il
        chiamante deve disegnare: `'gira'`, `'passo'`, `'muro'`, `'varco'`.

        Girarsi **non e'** camminare: se si guarda da un'altra parte, il primo
        comando gira e basta. E' il comportamento dei giochi a griglia, ed e'
        anche l'unico modo di parlare con chi si ha di fianco.
        """
        p = self.world.player
        if p.moving:
            return 'occupato'
        if p.facing != facing:
            p.facing = facing
            return 'gira'
        dx, dy = STEP[facing]
        cx, cy = self.cell[0] + dx, self.cell[1] + dy
        link = self.grid.links.get((cx, cy))
        if link is not None and self.atlas.resolve(link) is not None:
            self.pending = link
            return 'varco'
        can, f = self.standable(cx, cy, p.pos[1])
        if not can:
            return 'muro'
        self.cell = (cx, cy)
        x, _, z = self.grid.local(cx, cy)
        p.move_to([x, f if f is not None else p.pos[1], z], self.SPEED)
        return 'passo'

    def facing_cell(self) -> tuple[int, int]:
        dx, dy = STEP[self.world.player.facing]
        return (self.cell[0] + dx, self.cell[1] + dy)

    def facing_npc(self):
        """Chi si ha davanti. E' la sola domanda che serve per parlare."""
        want = self.facing_cell()
        for e in self.world.npcs.values():
            if not e.created or not e.visible:
                continue
            if self.grid.cell_of(e.pos) == want:
                return e
        return None

    def enter(self, grid: Grid, cell: tuple[int, int], directory: dict,
              columns: Columns | None = None) -> None:
        """Cambia mappa: nuova griglia, nuovi abitanti, giocatore all'arrivo.

        Il registro si svuota perche' gli NPC appartengono alla mappa: tenerli
        vorrebbe dire portarsi dietro gli abitanti del villaggio dentro il
        sotterraneo.
        """
        self.grid = grid
        # Le colonne prima degli abitanti: e' da loro che si sa a che quota
        # posare i piedi di ognuno.
        self.columns = columns if columns is not None else Columns(grid)
        self.world.npcs.clear()
        self.world.order.clear()
        self.pending = None
        self.populate(directory)
        self.place(*cell)

    def __repr__(self) -> str:
        return (f'<walk {self.grid.name} cella {self.cell} '
                f'{len(self.world.npcs)} abitanti>')


# ------------------------------------------------------------- verifiche

def _check(root: pathlib.Path) -> int:
    """Le verifiche, su tutto il disco. Non c'e' niente da guardare a occhio:
    o i passaggi si chiudono o no."""
    import time

    bad = 0

    def ok(cond, what):
        nonlocal bad
        print(f'  {"ok  " if cond else "NO  "}{what}')
        bad += not cond

    t0 = time.time()
    atlas = Atlas(root)
    grids = {}
    for name in sorted(atlas.files):
        grids[name] = atlas.grid(name)
    print(f'{len(grids)} griglie lette in {time.time() - t0:.1f}s')

    # i passaggi
    tot = res = nomap = nogate = 0
    for g in grids.values():
        for link in g.links.values():
            tot += 1
            if atlas.grid(link.dest) is None:
                nomap += 1
            elif atlas.resolve(link) is None:
                nogate += 1
            else:
                res += 1
    print(f'passaggi: {tot}, risolti {res} ({100 * res / tot:.0f}%), '
          f'mappa assente {nomap}, varco assente {nogate}')
    ok(res / tot > 0.95, 'oltre il 95% dei passaggi trova la cella d arrivo')

    # gli abitanti
    directory = entity.npc_directory(root.parent if root.name == 'map'
                                     else root)
    spots = {i for g in grids.values() for i in g.spots}
    cells = sum(len(g.spots) for g in grids.values())
    named = {i for i in spots if i in directory}
    print(f'posti di NPC: {cells} celle, {len(spots)} identificativi distinti, '
          f'con nome e modello dichiarati: {len(named)} '
          f'({100 * len(named) / len(spots):.0f}%)')
    ok(len(named) / len(spots) > 0.9,
       'oltre il 90% degli identificativi ha un nome e un modello')
    ok(len(directory) > 200, f'{len(directory)} identificativi nella rubrica')

    # gli oggetti di mappa: ci sono, e le classi note stanno dove si sa
    import collections as _c
    objs = _c.Counter()
    for n in sorted(atlas.files):
        for k, v in atlas.grid(n).objects.items():
            objs[k] += len(v)
    print(f'oggetti di mappa: {sum(objs.values())} celle, '
          f'{len(objs)} classi; le prime '
          f'{[k for k, _ in objs.most_common(4)]}')
    ok(objs['destructionWall'] >= 40 and objs['PitFall'] >= 20,
       'i muri rompibili e le trappole sono nell inventario')
    ok(objs['Exit'] > objs['Warp'] > 200,
       'i passaggi restano le classi piu numerose')

    # Le stanze: il `-g` numerico e' `(piano)(stanza)`, e a dirlo sono due
    # file che non si conoscono. Il primo e' il nome del file stesso; il
    # secondo e' lo schermo della mappa del sotterraneo, che disegna una
    # stanza per volta e le nomina `room_on_NN`.
    import re as _re

    import ui as _ui

    floors = [n for n in sorted(atlas.files) if FLOOR_IN_NAME.match(n)]
    n_cells = n_ok = 0
    for n in floors:
        gg = atlas.grid(n)
        for (gate, _o) in gg.arrivals:
            if not gate.isdigit():
                continue
            n_cells += 1
            n_ok += gate.startswith(gg.floor)
    print(f'{len(floors)} piani di sotterraneo, {n_cells} varchi numerici')
    print(f'  la prima cifra del varco e il piano che dice il nome del file: '
          f'{n_ok}/{n_cells}')
    ok(n_ok >= n_cells * 0.97,
       'il varco numerico e (piano)(stanza), non un indirizzo')

    ud = atlas.dir.parent.parent / 'UserInterface/radar/dungeonMap'
    decl = common = 0
    if ud.exists():
        for p in sorted(ud.rglob('dungeonMap*.lua.eu')):
            m = _re.match(r'dungeonMap(\d+)(?:_(\d+))?$',
                          p.stem.replace('.lua', ''))
            if not m:
                continue
            gg = atlas.grid(f'd_{int(m.group(1))}_1_{int(m.group(2) or 1)}')
            if gg is None:
                continue
            want = set()
            for t in _ui.descriptor_file(p).values():
                for k in t:
                    mm = _re.match(r'room_(?:on|off|still)_(\d+)$', str(k))
                    if mm:
                        want.add(int(mm.group(1)))
            decl += len(want)
            common += len(want & set(gg.rooms))
    print(f'  stanze disegnate dallo schermo che la griglia dichiara: '
          f'{common}/{decl}')
    ok(decl and common >= decl * 0.95,
       'le stanze della griglia sono quelle che la mappa del sotterraneo disegna')

    # ---- gli attori: i nemici piazzati e i grilletti di evento

    sets = _c.defaultdict(int)
    same_species = same_count = withabc = 0
    trig = _c.Counter()
    for nm in sorted(atlas.files):
        gg = atlas.grid(nm)
        for s, cells_ in gg.enemies.items():
            sets[s] += len(cells_)
        for t in gg.triggers.values():
            trig[t] += 1
        if all(gg.enemies.get(L) for L in 'ABC'):
            withabc += 1
            spec = [set(gg.enemies[L].values()) for L in 'ABC']
            if spec[0] == spec[1] == spec[2]:
                same_species += 1
            if len({len(gg.enemies[L]) for L in 'ABC'}) == 1:
                same_count += 1
    tot = sum(sets.values())
    print(f'\nnemici piazzati sulla griglia: {tot} celle in {len(sets)} set '
          f'{dict(sorted(sets.items()))}')
    ok(tot > 10000, f'{tot} celle dichiarano un nemico')
    ok(set(sets) == set('ABCFGHZ'),
       'i set sono le due terne A,B,C e F,G,H (piu\' lo Z isolato)')
    # Il cuore della lettura: A, B, C sono tre disposizioni della *stessa*
    # popolazione. Se un giorno cadesse, cadrebbe con essa il senso di `-s`.
    print(f'  mappe con A,B,C: {withabc}; stesse specie fra le tre: '
          f'{same_species}; stesso numero: {same_count}')
    ok(same_species >= withabc * 0.95,
       'A, B e C portano le stesse specie: sono tre piazzamenti, non tre popolazioni')

    # F, G, H sono FROM Mode, e a dirlo e' una proprieta' che si misura: quella
    # difficolta' mette in campagna i nemici dei sotterranei. Non e' una
    # preferenza statistica, e' uno stacco di settanta volte.
    dungeon = {e['num'] for e in entity.bestiary(atlas.dir.parent.parent)
               if e['living'].startswith('LIVING.DUNGEON')}
    share = {}
    for grp in ('ABC', 'FGH'):
        tot = dn = 0
        for nm in sorted(atlas.files):
            if not nm.startswith('field'):
                continue
            for L in grp:
                for v in atlas.grid(nm).enemies.get(L, {}).values():
                    tot += 1
                    dn += v in dungeon
        share[grp] = dn / max(tot, 1)
        print(f'  {grp} in campagna: {tot} nemici, {dn} di specie da '
              f'sotterraneo = {100 * share[grp]:.1f}%')
    ok(share['FGH'] > share['ABC'] * 10,
       'F, G, H portano in campagna i nemici dei sotterranei: sono FROM Mode')

    # E si **aggiungono** ad A,B,C invece di sostituirli. Era un'inferenza
    # aritmetica ed e' diventata una misura, per assurdo: ci sono mappe che
    # dichiarano A,B,C e nessun F,G,H, e sostituendo quelle resterebbero
    # **vuote** proprio nella difficolta' piu' dura.
    solo_abc = solo_fgh = tutte = 0
    vuote = []
    for nm in sorted(atlas.files):
        gg = atlas.grid(nm)
        a = sum(len(gg.enemies.get(L, {})) for L in 'ABC')
        f = sum(len(gg.enemies.get(L, {})) for L in 'FGH')
        tutte += bool(a and f)
        if a and not f:
            solo_abc += 1
            vuote.append((nm, a))
        elif f and not a:
            solo_fgh += 1
    print(f'  mappe con A,B,C e F,G,H: {tutte}; con i soli A,B,C: {solo_abc} '
          f'(la piu popolosa {max(vuote, key=lambda v: v[1]) if vuote else "-"}'
          f'); con i soli F,G,H: {solo_fgh}')
    ok(solo_abc > 0 and solo_fgh == 0,
       'F, G, H si aggiungono ad A, B, C invece di sostituirli: '
       f'sostituendo, {solo_abc} mappe resterebbero senza nemici in FROM Mode')

    # ---- i due identificativi che l'album non elenca

    # 5024. L'album non lo dichiara, ma la sua stessa numerazione lo predice:
    # nel tratto 5018..5026 lo scarto fra identificativo e numero di modello e'
    # costante, e 5024 e' l'unico buco di quel tratto.
    best = {e['num']: e for e in entity.bestiary(atlas.dir.parent.parent)}
    tratto = [n for n in range(5018, 5027) if n in best]
    scarti = set()
    for n in tratto:
        m = _re.match(r'(?:EN_ENEMY_|c_enm_)(\d+)', str(best[n]['node']))
        if m:
            scarti.add(n - int(m.group(1)))
    print(f'\n5018..5026: {len(tratto)} dichiarati, scarto identificativo - '
          f'modello {sorted(scarti)}, buco {sorted(set(range(5018, 5027)) - set(tratto))}')
    ok(scarti == {5016} and set(range(5018, 5027)) - set(tratto) == {5024},
       '5024 e il solo buco di un tratto a scarto costante: e c_enm_08')

    # 5080 e' **Togetoge**, gli spuntoni - e la sua classe non e' un nome ma il
    # **tipo di movimento**, che il disco dichiara in testa al proprio file:
    #
    #   ../lua/Object/69Togetoge.lua      0 :縦移動   verticale
    #                                     1 : 横移動   orizzontale
    #                                     2 : 縦移動（突撃タイプ） verticale, a carica
    #                                     3 : 横移動（突撃タイプ） orizzontale, a carica
    #
    # e `Togetoge4Update` chiama `TogetogeDashUpdate(Object,2)`, cioe' 縦横:
    # ferma finche' il giocatore non si allinea, poi carica su **tutti e due**
    # gli assi. Le tre classi che le griglie usano sono 0, 1 e 4.
    #
    # La geometria e' la controprova, e ha la forma giusta per esserlo: chi va
    # su e giu' non puo' condividere la colonna con un altro, chi va a destra e
    # sinistra non puo' condividere la riga - si scontrerebbero al primo passo.
    # Chi invece sta fermo agli angoli le condivide per forza.
    per_gruppo = _c.defaultdict(list)
    for nm in sorted(atlas.files):
        for c in mapdat.cells(atlas.files[nm].read_bytes()):
            if c['actor'] == 5080:
                cl = (c['cls'] or '').rstrip(';')
                per_gruppo[(nm, cl, c['x'] // 16, c['y'] // 12)].append(
                    (c['x'], c['y']))
    assi = _c.Counter()
    ang = _c.Counter()
    for (_nm, cl, _sc, _sr), pts in per_gruppo.items():
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        assi[cl, 'gruppi'] += 1
        if cl == '0':
            assi[cl, 'ok'] += len(set(xs)) == len(xs)
        elif cl == '1':
            assi[cl, 'ok'] += len(set(ys)) == len(ys)
        elif cl == '4':
            assi[cl, 'ok'] += len(set(xs)) == 2 and len(set(ys)) == 2
            for x, y in pts:
                ang[(x % 16, y % 12)] += 1
    print(f'\n5080 = Togetoge, {sum(len(v) for v in per_gruppo.values())} '
          f'spuntoni in {len(per_gruppo)} gruppi: '
          + ', '.join(f'classe {c} {assi[c, "ok"]}/{assi[c, "gruppi"]}'
                      for c in ('0', '1', '4')))
    ok(all(assi[c, 'ok'] == assi[c, 'gruppi'] for c in ('0', '1', '4')),
       'classe 0 su colonne distinte, classe 1 su righe distinte, classe 4 '
       'ferma agli angoli: il tipo di movimento che il Lua dichiara')
    ok(set(ang) == {(1, 1), (14, 1), (1, 10), (14, 10)},
       'i Togetoge a carica stanno ai quattro vertici di uno schermo, '
       'rientrati di una cella')

    # Il campo +0x08 sono **due byte**, e la sola misura senza eccezioni e'
    # che il primo non e' mai minore del secondo: e' un intervallo. La lettura
    # precedente (`n*257`) era lo stesso fatto visto sul 92% in cui i due byte
    # coincidono. Cosa misuri l'intervallo resta aperto - vedi mapdat.py.
    coppie = alte = mask1 = celle = 0
    sat = _c.Counter()
    for nm in sorted(atlas.files):
        for c in mapdat.cells(atlas.files[nm].read_bytes()):
            a, m = c['fields'][2], c['fields'][3]
            if a == 0xffffffff:
                continue
            celle += 1
            b0, b1 = a & 255, (a >> 8) & 255
            alte += (a >> 16) == 0
            coppie += b1 >= b0
            if bin(m).count('1') > 1:
                sat[nm, b0, b1, m] += 1
            else:
                mask1 += 1
    print(f'\n+0x08 su {celle:,} celle dentro mappa: byte alti a zero {alte:,}, '
          f'b1 >= b0 {coppie:,}, +0x0C con al piu un bit {mask1:,}; '
          f'le altre {sum(sat.values())} '
          + ', '.join(f'in {n} con b={b0}/{b1} e maschera {m:#x}'
                      for (n, b0, b1, m) in sat))
    ok(coppie == celle and alte == celle,
       '+0x08 e una coppia di byte con b1 >= b0, in tutte le celle del disco')
    # Le sole celle in cui +0x0C ha piu di un bit stanno tutte in `field_7`,
    # portano b0 = b1 = **31** - il massimo rappresentabile in una maschera a
    # 32 bit - e la maschera e' 0x7FFFFFFF, cioe' tutti i bit. E' una
    # saturazione, ed e' l'indizio piu' forte che b sia una quota: field_7 e'
    # la mappa piu' alta del disco, quella che in sessione 6 costringeva a
    # misurare l'altezza della colonna invece di assumerla.
    ok(set(n for (n, _, _, _) in sat) <= {'field_7'}
       and all(b0 == b1 == 31 and m == 0x7fffffff for (_, b0, b1, m) in sat),
       'dove +0x0C ha piu di un bit, b vale 31 e la maschera e satura: '
       'e la mappa piu alta del gioco, e sono le sole del disco')

    # E il modello c'e', per tutti e due quelli che l'album non elenca: nessuno
    # dei due si registra nel bestiario, quindi l'album e' esatto e la lacuna
    # era nostra. Vedi entity.LUA_ACTORS.
    _dir = entity.actor_directory(atlas.dir.parent.parent)
    _mod = {i: (_dir.get(i) or {}).get('draw') for i in (5024, 5080)}
    print(f'  gli attori che l\'album non elenca: {_mod}')
    ok(_mod[5024] == 'c_enm_08' and _mod[5080] == 'c_enm_39',
       '5024 e 5080 hanno il modello che il loro file Lua carica')

    # ---- dove il disco mette un nemico, e dove no

    fuori = _c.Counter()
    dentro = _c.Counter()
    piu_di_uno = adiacenti = 0
    for nm in sorted(atlas.files):
        gg = atlas.grid(nm)
        if not gg.enemies:
            continue
        dove = 'sotterraneo' if nm.startswith('d_') else 'campagna'
        cols = columns_for(gg, atlas.dir.parent.parent)
        for L, cells_ in gg.enemies.items():
            for xy in cells_:
                if cols.ground(*xy) is not None:
                    dentro[dove] += 1
                    continue
                fuori[dove] += 1
                vicini = sum(cols.ground(xy[0] + dx, xy[1] + dy) is not None
                             for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                             if dx or dy)
                adiacenti += vicini > 0
                piu_di_uno += vicini > 3
    for dove in ('campagna', 'sotterraneo'):
        t = fuori[dove] + dentro[dove]
        print(f'  in {dove}: {fuori[dove]}/{t} nemici su una cella senza '
              f'pavimento = {100 * fuori[dove] / max(t, 1):.1f}%')
    ok(fuori['campagna'] == 0,
       f'in campagna il disco mette tutti e {dentro["campagna"]} i nemici '
       'su una cella con pavimento')
    ok(adiacenti == fuori['sotterraneo'],
       f'nei sotterranei i {fuori["sotterraneo"]} che ne sono senza hanno il '
       'pavimento accanto: nessuno sborda di piu di una cella')

    # I nomi delle mappe, e la correzione che portano con se'.
    loc = mapdat.locations(atlas.dir.parent.parent)
    named = sum(1 for n in atlas.files if n in loc)
    places = {v['location'] for v in loc.values() if v['location']}
    print(f'\nmappe con un nome: {named}/{len(atlas.files)}, '
          f'{len(places)} localita\' distinte')
    ok(named >= len(atlas.files) - 2,
       'ogni mappa vera ha un nome e una musica dichiarati')
    ok(len(places) < named,
       'un posto occupa piu\' schermate: e\' cio\' che rende il nome utile')

    # `LivingId` **non** dice dove un nemico e' piazzato. Il nome inglese del
    # tempio e l'habitat della specie concordano nel 47%, che con sette habitat
    # e' sopra il caso ma lontanissimo da una regola: e' la famiglia del
    # nemico, e il piazzamento lo dichiara la griglia.
    WORD = {'GRASS': 'Grass', 'FOREST': 'Forest', 'SANDS': 'Desert',
            'WATER': 'Aqua', 'FIRE': 'Flame', 'EARO': 'Wind'}
    best = {e['num']: e['living'] for e in entity.bestiary(atlas.dir.parent.parent)}
    tot = agree = 0
    for nm in sorted(atlas.files):
        L = loc.get(nm, {}).get('location', '')
        if 'Temple' not in L:
            continue
        for s in 'ABC':
            for v in atlas.grid(nm).enemies.get(s, {}).values():
                liv = best.get(v, '')
                if not liv.startswith('LIVING.DUNGEON'):
                    continue
                tot += 1
                agree += WORD.get(liv.split('_', 1)[1], '?') in L
    print(f'  nemici nei templi: {tot}; il cui habitat e\' il tempio in cui '
          f'stanno: {agree} = {100 * agree / max(tot, 1):.1f}%')
    ok(tot and 0.3 < agree / tot < 0.7,
       'l habitat correla col posto ma non lo decide: e la famiglia, non la casa')

    # I nomi di grilletto sono funzioni Lua, e devono trovarsi tutti.
    ev = atlas.dir.parent.parent / 'Event'
    fn = set()
    if ev.exists():
        for p in ev.rglob('*.lua.eu'):
            for m in _re.finditer(r'^\s*function\s+(\w+)\s*\(',
                                  p.read_text('utf-8', 'replace'), _re.M):
                fn.add(m.group(1))
    got = sum(1 for t in trig if t in fn)
    print(f'  grilletti di evento: {sum(trig.values())} celle, {len(trig)} nomi, '
          f'{got} risolti come funzione Lua')
    ok(fn and got == len(trig),
       'ogni cella che nomina un evento nomina una funzione che esiste')

    # un giro di prova su una mappa che si conosce
    g = atlas.grid('d_1_1_1')
    w = Walk(atlas, g)
    n = w.populate(directory)
    print(f'{g!r}, {n} abitanti collocati')
    w.place(*w.start_cell())
    ok(not g.outside(*w.cell), 'la cella di partenza sta dentro la mappa')
    x, _, z = g.local(*w.cell)
    ok(g.cell_of((x, 0, z)) == w.cell, 'cella -> mondo -> cella e l identita')

    # senza geometria caricata il muro e' solo il bordo del mondo: si cammina
    p = w.world.player
    start = w.cell
    moved = turns = 0
    for facing in (3, 3, 1, 1, 2, 0):
        r = w.step(facing)
        if r == 'gira':                       # il primo comando gira e basta
            turns += 1
            r = w.step(facing)
        moved += r == 'passo'
        for _ in range(60):                   # 1 s: un passo dura 0,33 s
            w.world.tick(1 / 60)
    ok(moved == 6, f'{moved} passi su 6 vanno a buon fine')
    ok(turns == 4, f'{turns} comandi su 6 sono serviti solo a girarsi')
    ok(w.cell == (start[0] + 1, start[1] + 1),
       'due passi a destra, due in giu, uno a sinistra e uno su tornano indietro')
    ok(abs(p.pos[0] - g.local(*w.cell)[0]) < 1e-3 and
       abs(p.pos[2] - g.local(*w.cell)[2]) < 1e-3,
       'il giocatore arriva al centro della cella dichiarata')

    # Un pavimento finto con un muro sopra una cella sola: e' il caso che
    # separa il pavimento dall'ostacolo, ed e' il motivo per cui la colonna
    # tiene le quote invece dei soli si/no.
    col = Columns(g)
    cx, cy = w.cell
    ahead, left, up = (cx + 1, cy), (cx - 1, cy), (cx, cy - 1)
    floor = [g.local(x, y, 0.0)
             for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)]
    # Un muro alto due caselle: una sola sarebbe un **gradino**, e si sale.
    wall = [g.local(*ahead, 0.4 * k) for k in range(1, 9)]   # da 0,4 a 3,2
    step_up = [g.local(*up, TILE)]                           # un gradino solo
    col.add(np.array(floor + wall + step_up, np.float32))
    w.columns = col
    w.place(cx, cy)
    ok(abs(w.world.player.pos[1]) < 1e-6,
       'il piede si posa sul pavimento, non sulla fetta che lo contiene')
    ok(not w.columns.blocked(*left, 0.0), 'il pavimento da solo non ostruisce')
    ok(w.columns.blocked(*ahead, 0.0), 'il muro occupa l altezza del corpo')
    can, f = w.standable(*up, 0.0)
    ok(can and abs(f - TILE) < 1e-6, 'un gradino da una casella si sale')
    ok(w.standable(*ahead, 0.0)[0] is False, 'un muro da due caselle no')
    ok(w.step(3) == 'gira' and w.step(3) == 'muro',
       'contro un ostacolo il passo non parte')
    ok(w.step(2) == 'gira' and w.step(2) == 'passo',
       'girandosi dall altra parte si riparte')

    # il varco porta dove dice
    src = next(iter(g.links.values()))
    got = atlas.resolve(src)
    ok(got is not None, f'{src} si risolve')
    if got:
        dest, cell = got
        w.enter(dest, cell, directory)
        ok(w.grid.name == src.dest and w.cell == cell,
           f'entrando si e in {src.dest} alla cella {cell}')
        ok(all(e.created for e in w.world.npcs.values()),
           'gli abitanti della nuova mappa sono tutti collocati')

    # ---- i nemici, mossi dai loro script (vedi actor.py)

    print('\ni nemici eseguono il proprio script:')
    prove = (('d_1_1_1', (56, 48)), ('d_6_1_4', (23, 44)),
             ('d_7_1_4', (71, 54)), ('d_4_1_2', (103, 90)),
             ('field_16', (64, 64)))
    vivi = piazzati = mossi = usciti = errori = 0
    for nome, cella in prove:
        gg = grids[nome]
        ww = Walk(atlas, gg)
        ww.columns = columns_for(gg, root)
        ww.place(*cella)
        ww.hire(root)
        piazzati += ww.populate_enemies(_dir, 'A')
        vivi += len(ww.troupe.actors)
        prima = {k: ww.columns.ground(*a.cell) is not None
                 for k, a in ww.troupe.actors.items()}
        p0 = {k: list(a.e.pos) for k, a in ww.troupe.actors.items()}
        for _ in range(300):                       # cinque secondi
            ww.troupe.update(1 / 60)
        for k, a in ww.troupe.actors.items():
            mossi += sum(abs(p - q) for p, q in zip(a.e.pos, p0[k])) > 0.1
            # uscire dal calpestabile **muovendosi** sarebbe un difetto nostro;
            # partirci e' il caso noto dei 546 che sbordano nel muro
            usciti += prima[k] and ww.columns.ground(*a.cell) is None
        errori += sum(ww.troupe.failed.values())
    print(f'  {vivi} attori su {piazzati} nemici piazzati, {mossi} si sono '
          f'mossi in 5s, {errori} errori di script, {usciti} usciti dal '
          f'calpestabile')
    ok(vivi == piazzati and piazzati > 0,
       f'tutti e {piazzati} i nemici piazzati trovano il proprio '
       'comportamento in all.lua.eu')
    ok(errori == 0, 'nessuno script di nemico cade')
    ok(usciti == 0, 'nessun nemico attraversa un muro muovendosi')
    ok(mossi > piazzati // 2,
       f'{mossi} nemici su {piazzati} si muovono da soli: il pattugliamento '
       'e letto, non inventato')

    # E la prova che chiude il cerchio su Togetoge: la classe della cella
    # dichiara l'asse (0 縦 verticale, 1 横 orizzontale), e **eseguendo lo
    # script** gli spuntoni si muovono proprio su quello. Una lettura statica
    # e una dinamica che si confermano a vicenda.
    def spostamento(nome, cella, classe):
        gg = grids[nome]
        ww = Walk(atlas, gg)
        ww.columns = columns_for(gg, root)
        ww.place(*cella)
        ww.hire(root)
        ww.populate_enemies(_dir, 'A')
        toge = {k: a for k, a in ww.troupe.actors.items()
                if a.num == 5080 and a.base.endswith(classe)}
        p0 = {k: list(a.e.pos) for k, a in toge.items()}
        for _ in range(300):
            ww.troupe.update(1 / 60)
        return (sum(abs(a.e.pos[0] - p0[k][0]) for k, a in toge.items()),
                sum(abs(a.e.pos[2] - p0[k][2]) for k, a in toge.items()),
                len(toge))

    ox, oz, n1 = spostamento('d_6_1_4', (23, 44), '1')
    vx, vz, n0 = spostamento('d_7_1_4', (71, 54), '0')
    print(f'  Togetoge classe 1 ({n1}): X {ox:.1f} Z {oz:.1f};  '
          f'classe 0 ({n0}): X {vx:.1f} Z {vz:.1f}')
    ok(ox > 1 and oz < 0.01 and vz > 1 and vx < 0.01,
       'gli spuntoni si muovono sull asse che la loro classe dichiara: '
       'la lettura del dato e l esecuzione dello script concordano')

    # E gli abitanti, che hanno i loro script nella stessa cartella. Chi non
    # ha una `Update` non si muove, e sono il Re, i sei saggi, l'eroe
    # leggendario e il Re delle medaglie: il disco dichiara l'immobilita' con
    # un'assenza, e la categoria e' esattamente quella giusta.
    gg = grids['field_91']
    ww = Walk(atlas, gg)
    ww.columns = columns_for(gg, root)
    ww.place(gg.w // 2, gg.h // 2)
    ww.hire(root)
    ab = ww.populate(directory)
    p0 = {k: list(a.e.pos) for k, a in ww.troupe.actors.items()}
    for _ in range(600):
        ww.troupe.update(1 / 60)
    girano = sum(1 for k, a in ww.troupe.actors.items()
                 if sum(abs(p - q) for p, q in zip(a.e.pos, p0[k])) > 0.1)
    persi = sum(1 for a in ww.troupe.actors.values()
                if ww.columns.ground(*a.cell) is None)
    print(f'  la corte del castello: {ab} abitanti, '
          f'{len(ww.troupe.actors)} con il proprio script, {girano} gironzolano')
    ok(len(ww.troupe.actors) >= ab - 1 and girano > 0 and persi == 0
       and not ww.troupe.failed,
       'gli abitanti gironzolano per la corte senza uscire dal pavimento')

    # Un file e' fermo se **nessuna** delle sue basi ha una `Update`: dentro
    # `69Togetoge` c'e' anche una `TogetogeInitialize` comune che le cinque
    # varianti richiamano, e quella da sola non vuol dire immobile.
    per_file = _c.defaultdict(list)
    for v in ww.troupe.by_model.values():
        for b in v:
            per_file[b['file']].append(b['moves'])
    fermi = sorted(f for f, m in per_file.items() if not any(m))
    print(f'  file senza nessuna Update: {fermi}')
    ok(fermi and all(f.startswith('N') for f in fermi),
       f'i {len(fermi)} personaggi immobili sono tutti NPC, mai un nemico: '
       'il Re, i saggi, l eroe leggendario')

    # E dove stanno, i fermi. La direzione con cui li mettiamo giu' non e'
    # dichiarata da nessuna parte - non negli script, non nella griglia - ma
    # **il piazzamento la implica**: chi non si muove sta sempre piu' in alto
    # della porta da cui si entra, quindi gli si cammina incontro e lui guarda
    # verso chi arriva. Nella sala del trono di Dotnia il Re e' a y=11 e la
    # porta a y=36, con sei cortigiani schierati in mezzo.
    fmod = {mod for f, m in per_file.items() if not any(m)
            for mod, v in ww.troupe.by_model.items()
            if any(b['file'] == f for b in v)}
    dentro = giusti = 0
    for nome in sorted(atlas.files):
        gg2 = grids[nome]
        porte = [xy for xy in gg2.arrivals.values()]
        porte += [xy for xy in gg2.exits.values()]
        if not porte or not nome.startswith('d_'):
            continue
        for ident, xy in gg2.spots.items():
            info = directory.get(ident)
            if not info or info.get('model') not in fmod:
                continue
            vicina = min(porte, key=lambda q: abs(q[0] - xy[0]) + abs(q[1] - xy[1]))
            dentro += 1
            giusti += vicina[1] > xy[1]
    print(f'  personaggi immobili al chiuso: {dentro}, '
          f'con la porta piu vicina piu in basso: {giusti}')
    ok(dentro and giusti == dentro,
       'chi sta fermo al chiuso ha sempre l ingresso davanti a se: la '
       'direzione non e dichiarata, ma il piazzamento la implica')

    # Gli oggetti di mappa: l'identificativo della cella e' 4000 piu' il
    # numero del modello che lo script del gimmick carica. Lo si mette alla
    # prova dove la cella si nomina da sola, che sono le sole tre famiglie di
    # classe che corrispondono a un file di `Object/` - Signboard, Stonemark,
    # Well - e sono tre numeri diversi su tre gruppi che non si conoscono.
    import nodes as nodes_mod

    catalogo = nodes_mod.props(root)
    carica = nodes_mod.loaders(root)
    tab = nodes_mod.nodelist(root)
    concordi = discordi = 0
    for nome in sorted(atlas.files):
        gg2 = grids[nome]
        for cls, celle in gg2.objects.items():
            enums = carica.get(cls)
            if not enums:
                continue
            numeri = {int(m.group(1)) for e in enums
                      for m in [re.match(r'm_obj_(\d+)',
                                         tab.get(e, {}).get('node', ''))] if m}
            if not numeri:
                continue
            for xy in celle:
                idv = gg2.props.get(xy)
                if idv is None:
                    continue
                if idv - 4000 in numeri:
                    concordi += 1
                else:
                    discordi += 1
    print(f'  celle che si nominano per classe: {concordi + discordi}, '
          f'con id = 4000 + il modello che lo script carica: {concordi}')
    ok(concordi and not discordi,
       'l identificativo di cella e 4000 piu il numero del modello')

    # E l'assenza: la banda 4100..4105 e' quella dei marcatori invisibili -
    # `Warp`, `Exit`, gli osservatori - e infatti e' l'unico tratto lungo
    # della numerazione in cui un modello non esiste. Vedi docs/objects.md.
    ok(not any(4100 + k in catalogo for k in range(6)),
       'i sei identificativi dei marcatori invisibili non hanno un modello')

    print(f'\n{"tutto a posto" if not bad else str(bad) + " verifiche fallite"}')
    return 1 if bad else 0


if __name__ == '__main__':
    import sys

    r = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                     else '../extract/PS3_GAME/USRDIR/data')
    raise SystemExit(_check(r))
