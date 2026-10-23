"""
actor.py - i nemici, eseguiti dagli script originali del disco.

E' `host.py` applicato a un secondo dominio, e la tesi e' la stessa: **girano
gli script che stanno sul disco, verbatim**. Non una traduzione del
comportamento, non una nostra idea di come si muove uno scheletro.

## Cosa era scritto qui prima, e perche' era sbagliato

Per tre sessioni il TODO ha detto che il pattugliamento dei nemici «non e'
dichiarato in chiaro da nessuna parte», e che restavano due strade: aprire
l'EBOOT oppure inventarselo dichiarando che era una nostra scelta. Era vero
dei posti in cui era stato cercato - `MapParameter`, `GameParamData`, l'API - e
falso del disco. Il moto sta in `all.lua.eu`, che **non e' un file**: e' la
concatenazione di 869 sorgenti, con l'albero delle cartelle lasciato nei
commenti.

    -- Start ../lua/Object/06Bee.lua.eu

Sotto `../lua/Object/` ci sono 55 file di nemico. Quarantasei chiamano
`setBookRegistInfo`, cioe' si registrano nel bestiario, ed e' **esattamente il
numero di voci dell'album**; 37 portano il comportamento per esteso.

## Come e' fatto un nemico

Due funzioni globali e una macchina a stati esplicita, con la fase in un campo
dell'attore e i tempi in slot numerati:

    function BeeInitialize(Object)
        Object:SetType(actor_manager.AT_ENEMY);
        Object:AddNode(package_manager.EN_ENEMY_06_01);
        Object:SetHp( HP );
        Object:SetInitVector();
    end

    function BeeUpdate(Object)
        if(Object:GetPhase()==0 and Object:IsTimeZero()) then
            Object:SetPhase(1);
            CommonRandomDirection(Object,WallDistance);
            if( Object:IsActorMoveArea( MoveArea ) ) then
                Object:SetDirectionToInit();
            end
        end
        ...

e `MoveArea` e' un `local` del file, con il commento degli autori:
出現位置からの行動可能範囲, *il raggio d'azione dal punto di comparsa*. Il
pattugliamento e' quello: vaga a caso, e se esce dal raggio torna verso il
punto in cui e' nato.

## Cosa fa questo modulo, e cosa no

Fornisce l'oggetto che il Lua vede come `Object` e lo attacca a una
`entity.Entity` gia' collocata sulla mappa da `walk.populate_enemies`. I
metodi che governano fase, tempo, moto e percezione sono implementati contro
la griglia e le colonne che il progetto ha gia'; **tutti gli altri sono
contati invece che falliti**, che e' il criterio di `host.py` e il modo in cui
si misura quanto manca senza inventare.

Un metodo ignoto restituisce `0` e non `nil`, e la differenza non e' un
dettaglio: `Object:GetUserFloat() + dt * Accel` con `nil` fa cadere lo script
alla prima riga, mentre con `0` il nemico si muove male ma si muove, e il
contatore dice che manca.

Uso:
  python actor.py census <dir data>     quali metodi chiedono i nemici
  python actor.py run <dir data> <c_enm_39> [classe]   una Update al secondo
"""
from __future__ import annotations

import collections
import math
import pathlib
import re
import sys

import entity

# Le quattro direzioni, nella convenzione di `entity.DIRS`: 0 e 1 sono l'asse
# Z, 2 e 3 l'asse X. Che sia questa lo dice Togetoge, il solo attore che
# dichiari l'asse nel proprio commento e lo scelga in codice:
#
#   0 : 縦移動  (verticale)    ->  Togetoge0Initialize: SetDirection( 0 )
#   1 : 横移動  (orizzontale)  ->  Togetoge1Initialize: SetDirection( 2 )
#
# cioe' 0 e' l'asse verticale dello schermo e 2 l'orizzontale, che e' proprio
# la partizione di DIRS. E l'inverso di una direzione e' il suo compagno di
# coppia, da cui `SetReverseDirection` come XOR con 1.
REVERSE = (1, 0, 3, 2)

# Il file di un nemico si chiama `NN<Nome>.lua`, e `NN` e' il numero del
# modello: `01Rabbit` -> `c_enm_01`, `39` non c'e' perche' Togetoge sta sotto
# `69Togetoge` (il numero del file non e' sempre quello del modello, e a
# decidere e' `AddNode`). Per questo l'aggancio si fa sul **nodo caricato**,
# non sul nome del file: e' la stessa scelta di `entity.enemy_motion`.
# `EN_ENEMY_39_01` e `NP_NPC05_01` - ma anche `NP_NPC_09_01`, perche' gli NPC
# sono scritti in due convenzioni: senza trattino basso i modelli 02..08, con
# il trattino l'01 e tutti quelli da 09 in su. Due mani diverse sullo stesso
# disco, e nessuna delle due sbaglia il numero.
NODE = re.compile(r'package_manager\.(EN_ENEMY_(\d+)|NP_NPC_?(\d+))')
START = re.compile(r'-- Start \.\./lua/Object/(N?\d\d[A-Za-z0-9_]*)\.lua')
PAIR = re.compile(r'function\s+([A-Za-z_0-9]+?)(Initialize|Update)\s*\(')


def sources(data: pathlib.Path) -> dict[str, str]:
    """I file di nemico dentro `all.lua.eu`, per nome di sorgente.

    Il file e' una concatenazione, e i commenti `-- Start` sono l'unico indice
    che abbia: nessuna tabella lo dichiara. Sono **1.486**, e qui servono i 55
    di `../lua/Object/NN*.lua`.

    *Corretto in sessione 12.* Erano dati per 869, che e' il conto dei soli
    `../lua/`: sotto ci sono altri ventotto alberi (`Event/`, `MiniGame/`,
    `UserInterface/`...). Cercare il confine solo fra i `../lua/` fa
    inghiottire a un sorgente tutto quel che lo segue - qui succedeva a
    `Object/npc/n05oldmana11_290`, che si prendeva quindici file di evento.
    Il confine e' il marcatore successivo, qualunque albero nomini.
    """
    p = pathlib.Path(data) / 'all.lua.eu'
    if not p.exists():
        return {}
    src = p.read_text(encoding='utf-8', errors='replace')
    out = {}
    for m in START.finditer(src):
        b = src.find('-- Start ', m.end())
        out[m.group(1)] = src[m.end():b if b > 0 else len(src)]
    return out


def behaviours(data: pathlib.Path) -> dict[str, list[dict]]:
    """Da modello a comportamenti: `{'c_enm_39': [{...}], ...}`.

    Un file dichiara **una o piu'** coppie `<base>Initialize`/`<base>Update`.
    Una sola nel caso comune; cinque in `69Togetoge`, dove la base finisce con
    una cifra ed e' quella che la cella sceglie come "classe". Quindi la
    chiave e' il modello e il valore e' una lista, ordinata per come il file
    le presenta.

    Il modello si legge da `AddNode(package_manager.EN_ENEMY_39_01)`, che e'
    `c_enm_39_01` con un altro prefisso - l'aggancio che la sessione 8 aveva
    gia' verificato sui nomi, dodici volte su dodici, per il minigioco.
    """
    out = collections.defaultdict(list)
    for nome, t in sources(data).items():
        # `EN_ENEMY_39` e' `c_enm_39`, `NP_NPC05` e' `c_npc_05`: gli stessi
        # modelli con il prefisso che il gestore dei pacchetti usa. Il secondo
        # e' la conferma, da un file ancora diverso, della tabella
        # archetipo -> modello che la sessione 4 aveva dedotto dai nomi dei
        # 237 script `npcevent_`.
        nodi = [(('c_enm_' if m.group(2) else 'c_npc_')
                 + f'{int(m.group(2) or m.group(3)):02d}')
                for m in NODE.finditer(t)]
        if not nodi:
            continue
        mod = collections.Counter(nodi).most_common(1)[0][0]
        basi, viste = [], set()
        for m in PAIR.finditer(t):
            b = m.group(1)
            if b in viste or f'{b}Initialize' not in t:
                continue
            viste.add(b)
            basi.append(b)
        for b in basi:
            # Chi non ha una `Update` **non si muove**, e non e' una lacuna:
            # sono il Re, i sei saggi, l'eroe leggendario, il Re delle
            # medaglie e il fantasma - 10 file su 33, ed e' esattamente la
            # categoria di chi in questo gioco sta seduto ad aspettarti. Il
            # disco dichiara l'immobilita' con un'assenza.
            out[mod].append({'base': b, 'file': nome,
                             'moves': f'{b}Update' in t,
                             'classe': b[-1] if b[-1].isdigit() else None})
    return dict(out)


class Stub:
    """Il valore che restituisce un **comando** non ancora implementato.

    Serve perche' gli script incatenano: `local club =
    Object:SetChildObject("CyclopsClub",0,0,0); club:setVisible(false)`. Con
    `nil` o con un numero la seconda riga fa cadere il Ciclope; con questo,
    qualunque metodo gli si chieda risponde e non fa niente.
    """

    def __getattr__(self, _name):
        return lambda *_a, **_k: None

    # Lua indicizza: `club:setVisible(false)` arriva qui come `club['setVisible']`
    # e non come attributo, perche' e' cosi' che lupa espone un oggetto Python.
    def __getitem__(self, _name):
        return lambda *_a, **_k: None


def _absent(name: str):
    """Cosa rispondere a un metodo che non abbiamo ancora scritto.

    Non e' una sfumatura: **in Lua `0` e' vero**, e solo `nil` e `false` sono
    falsi. Rispondere zero a tutto vorrebbe dire che ogni `if
    Object:IsQualcosa()` prende il ramo affermativo - un nemico che crede
    sempre di vedere il giocatore e di avere un muro davanti. Sarebbe un
    comportamento inventato da noi, che e' la cosa che questo progetto non fa.

    A dare la risposta giusta e' la convenzione di nome del **codice
    originale**, che e' regolare su tutti e 55 i file: `Is...` e' un predicato,
    `Get...` restituisce un numero, il resto e' un comando. Quindi un predicato
    ignoto risponde «no» - il nemico non percepisce cio' che non sappiamo
    ancora leggere - un getter risponde zero, e un comando restituisce
    qualcosa a cui si possono chiedere altri metodi.
    """
    if name.startswith(('Is', 'Has', 'Can')):
        return False
    if name.startswith(('Get', 'get')):
        return 0
    return Stub()


class Actor:
    """Lo stato di un nemico, e l'oggetto che il Lua riceve come `Object`.

    Il pattern e' quello di `host.Api` e per la stessa ragione: in Lua
    `Object:SetSpeed(7)` significa `Object.SetSpeed(Object, 7)`, quindi ogni
    metodo dev'essere una chiusura che assorbe il primo argomento. Definirli
    come metodi Python non funziona - riceverebbero l'oggetto due volte.
    """

    def __init__(self, ent, world, num: int = 0, base: str = ''):
        self.e = ent                       # la entity.Entity da muovere
        self.w = world                     # chi sa dove sono muri e giocatore
        self.num = num
        self.base = base
        self.phase = 0
        self.timers = collections.defaultdict(float)
        self.speed = 0.0
        self.budget = 0.0                  # quanto resta da percorrere
        self.hp = 1
        self.amount = 0
        self.ints = collections.defaultdict(int)
        self.floats = collections.defaultdict(float)
        self.nodes = []                    # nell'ordine di AddNode
        self.anim: list[tuple[int, float]] = []   # il ciclo di AddAnimation
        self.anim_dirty = False
        self.node = 0
        self.start = list(ent.pos)
        self.init_dir = ent.facing
        self.dt = 1 / 60
        self.jump = 0.0
        self.fly_speed = 0.0
        self.fly_height = 0.0
        self.hit = False
        self.calls = collections.Counter()
        self.unknown = collections.Counter()
        self._methods: dict = {}

    # -- il ponte verso il Lua

    def __getattr__(self, name):
        """Il metodo che il Lua ha chiesto, come chiusura che assorbe `self`.

        Le chiusure sono **memoizzate**, e non e' un'ottimizzazione di
        principio: un solo nemico chiede `GetPhase` una decina di volte per
        fotogramma, e crearne una nuova ogni volta significa consegnare al Lua
        decine di migliaia di oggetti Python temporanei al secondo, che nessuno
        tiene vivi. Tenendole nell'attore vivono quanto lui.
        """
        if name.startswith('_') or name in self.__dict__:
            raise AttributeError(name)
        got = self._methods.get(name)
        if got is not None:
            return got
        impl = _IMPL.get(name)

        def call(_self=None, *args):
            self.calls[name] += 1
            if impl is None:
                self.unknown[name] += 1
                return _absent(name)
            return impl(self, *args)
        self._methods[name] = call
        return call

    # -- il tempo, che scorre fuori dallo script

    def tick(self, dt: float) -> None:
        self.dt = dt
        for k in list(self.timers):
            self.timers[k] = max(0.0, self.timers[k] - dt)

    # -- lo spazio, contro la griglia e le colonne

    @property
    def cell(self):
        return self.w.grid.cell_of(self.e.pos)

    def walkable(self, cx: int, cy: int) -> float | None:
        """La quota su cui si sta in piedi in quella cella, o `None`.

        E' la stessa domanda che si fa il giocatore, e passa dallo stesso
        codice: un nemico non ha una collisione propria nel dato.
        """
        q = self.w.columns.ground(cx, cy)
        if q is None:
            return None
        return q if abs(q - self.e.pos[1]) <= entity.TILE else None


def _set_phase(a, n=0):
    a.phase = int(n)


def _get_phase(a):
    return a.phase


def _set_time(a, x=0.0, y=None):
    """`SetTime(s)` e `SetTime(slot, s)`.

    Le due forme convivono nello stesso file - `Object:SetTime(StepWait)` e
    `Object:SetTime(2, FlyWait)` - e si distinguono per il numero di
    argomenti, non per il tipo. Lo slot 0 e' il temporizzatore del
    comportamento, l'1 quello dell'attacco: lo dice il commento di
    `69Togetoge`, «このタイマーが0でなければ攻撃しない».
    """
    if y is None:
        a.timers[0] = float(x)
    else:
        a.timers[int(x)] = float(y)


def _is_time_zero(a, slot=0):
    return a.timers[int(slot or 0)] <= 0.0


def _elapsed(a):
    return a.dt


def _set_speed(a, v=0.0):
    a.speed = float(v)


def _set_distance(a, d=0.0):
    a.budget = float(d)


def _is_distance_zero(a):
    return a.budget <= 0.0


def _set_direction(a, d=0):
    a.e.facing = int(d) % 4


def _reverse(a):
    a.e.facing = REVERSE[a.e.facing % 4]


def _random_direction(a):
    import random
    a.e.facing = random.randrange(4)


def _dir_to_player(a):
    """La direzione cardinale che punta al giocatore.

    Cardinale e non libera: questo gioco muove tutto su quattro direzioni, e
    lo dichiara il fatto che `SetDirection` prenda 0..3. Si sceglie l'asse in
    cui la distanza e' maggiore, che e' il modo in cui un inseguimento a
    griglia si legge sullo schermo.
    """
    dx = a.w.player.pos[0] - a.e.pos[0]
    dz = a.w.player.pos[2] - a.e.pos[2]
    if abs(dx) >= abs(dz):
        a.e.facing = 3 if dx > 0 else 2
    else:
        a.e.facing = 0 if dz > 0 else 1


def _dir_to_init(a):
    a.e.facing = a.init_dir


def _move(a, _flag=None):
    """Un passo nella direzione corrente, se non c'e' un muro.

    Il budget di `SetDistance` cala di quanto si e' percorso: e' cosi' che
    `IsDistanceZero` diventa vero, ed e' il modo in cui il tipo a carica di
    Togetoge si ferma dopo quattro caselle.

    L'argomento c'e' - 17 chiamate lo passano, sempre `false` - ma **cosa
    significhi non e' dichiarato da nessuna parte**, e le due chiamate con un
    vettore (`Move(vec)`) non bastano a deciderlo. Si accetta e non si
    interpreta: fingere di saperlo sarebbe inventare un comportamento.
    """
    v = entity.DIRS[a.e.facing % 4]
    step = a.speed * a.dt
    if step <= 0.0:
        return
    nx = a.e.pos[0] + v[0] * step
    nz = a.e.pos[2] + v[2] * step
    cx, cy = a.w.grid.cell_of((nx, a.e.pos[1], nz))
    q = a.walkable(cx, cy)
    if q is None:
        a.hit = True
        return
    a.hit = False
    a.e.pos[0], a.e.pos[2] = nx, nz
    a.e.pos[1] = q
    a.e.walk += a.dt
    a.budget -= step


def _is_hit_wall(a):
    """Vero se davanti non si cammina.

    Si guarda **la cella davanti**, non l'esito dell'ultimo passo: un nemico
    fermo che ha appena cambiato fase deve poterlo sapere prima di muoversi.
    """
    v = entity.DIRS[a.e.facing % 4]
    cx, cy = a.cell
    return a.walkable(int(cx + v[0]), int(cy - v[2])) is None


def _is_hit_object(a):
    return False


def _distance_to_player(a):
    dx = a.w.player.pos[0] - a.e.pos[0]
    dz = a.w.player.pos[2] - a.e.pos[2]
    return math.hypot(dx, dz)


def _is_lesser_distance(a, d=0.0, _angle=None):
    return _distance_to_player(a) < float(d or 0.0)


def _is_lesser_distance_x(a, d=0.0):
    return abs(a.w.player.pos[0] - a.e.pos[0]) < float(d or 0.0)


def _is_lesser_distance_z(a, d=0.0):
    return abs(a.w.player.pos[2] - a.e.pos[2]) < float(d or 0.0)


def _is_equal_player_x(a):
    """Vero se il giocatore e' incolonnato con l'attore.

    La tolleranza e' **mezza casella**, e non e' una taratura: e' la stessa
    soglia con cui la griglia decide in che cella si sta. Su questo si regge
    il tipo a carica di Togetoge, che parte quando 軸が揃ったら, «quando gli
    assi si allineano».
    """
    return abs(a.w.player.pos[0] - a.e.pos[0]) <= entity.TILE / 2


def _is_equal_player_z(a):
    return abs(a.w.player.pos[2] - a.e.pos[2]) <= entity.TILE / 2


def _is_equal_player_xz(a, tol=None):
    """Allineato su uno dei due assi.

    Prende una tolleranza facoltativa - `ScorpionBlue` la passa, `Togetoge`
    no - e dove manca vale mezza casella, come per i due assi separati.
    """
    if tol is None:
        return _is_equal_player_x(a) or _is_equal_player_z(a)
    t = float(tol)
    return (abs(a.w.player.pos[0] - a.e.pos[0]) <= t
            or abs(a.w.player.pos[2] - a.e.pos[2]) <= t)


def _is_equal_player_floor(a):
    return abs(a.w.player.pos[1] - a.e.pos[1]) <= entity.TILE


def _is_player_area(a):
    """Se il giocatore non e' «nella stanza», l'attore non fa niente.

    E' la prima riga di ogni `Update` di Togetoge, ed e' esattamente cio' che
    il walkthrough osserva senza saperlo: *«if you don't move at all upon
    entering a room, you are not technically "in" it yet, and thus traps won't
    activate»*. Qui la stanza e' lo schermo 16x12, che e' l'unita' con cui
    questo gioco inquadra: vedi walk.md.
    """
    px, py = a.w.grid.cell_of(a.w.player.pos)
    cx, cy = a.cell
    return (px // 16, py // 12) == (cx // 16, cy // 12)


def _is_actor_move_area(a, r=0.0):
    """Vero se l'attore e' uscito dal raggio d'azione dal punto di comparsa.

    Il verso lo dichiara l'uso: `if IsActorMoveArea(MoveArea) then
    SetDirectionToInit()` - se fosse «sono dentro l'area» il nemico tornerebbe
    indietro proprio mentre e' a casa. `MoveArea` porta il commento
    出現位置からの行動可能範囲, e vale 10.0 per l'ape e 20 per altri due.
    """
    dx = a.e.pos[0] - a.start[0]
    dz = a.e.pos[2] - a.start[2]
    return math.hypot(dx, dz) > float(r or 0.0)


def _is_start_position(a):
    dx = a.e.pos[0] - a.start[0]
    dz = a.e.pos[2] - a.start[2]
    return math.hypot(dx, dz) <= entity.TILE / 4


class Vec:
    """La posizione dell'attore, vista dal Lua - e **scrivibile**.

    Non e' una comodita': gli script assegnano dentro il valore restituito,

        Object:GetPosition().y = Object:GetFloor()*1.6 + 4.0*1.6;

    quindi `GetPosition` non puo' restituire una copia. Le tre proprieta'
    leggono e scrivono direttamente `Entity.pos`, e l'unita' e' quella del
    mondo: il `1.6` di quella riga e' `entity.TILE`, cioe' il lato della
    casella, che e' l'ennesima conferma della scala.
    """

    def __init__(self, ent):
        self._e = ent

    @property
    def x(self):
        return self._e.pos[0]

    @x.setter
    def x(self, v):
        self._e.pos[0] = float(v)

    @property
    def y(self):
        return self._e.pos[1]

    @y.setter
    def y(self, v):
        self._e.pos[1] = float(v)

    @property
    def z(self):
        return self._e.pos[2]

    @z.setter
    def z(self, v):
        self._e.pos[2] = float(v)


def _get_position(a):
    return Vec(a.e)


def _get_floor(a):
    """La quota in **caselle**, che e' l'unita' in cui gli script contano.

    `GetPosition().y = GetFloor()*1.6 + 4.0*1.6` non lascia scelta: quel che
    torna va moltiplicato per il lato della casella per diventare mondo.
    """
    return int(round(a.e.pos[1] / entity.TILE))


def _grid_height(a):
    """La quota del terreno sotto l'attore, in unita' di mondo."""
    q = a.w.columns.ground(*a.cell)
    return 0.0 if q is None else q


def _is_wall(a, d=None):
    """Un muro davanti entro `d`, che gli script chiamano `WallDistance`.

    Diverso da `IsHitWall`, che guarda la cella adiacente: qui la distanza e'
    un parametro e vale tipicamente 0,8 - mezza casella.
    """
    v = entity.DIRS[a.e.facing % 4]
    d = entity.TILE / 2 if d in (None, 0) else float(d)
    p = (a.e.pos[0] + v[0] * d, a.e.pos[1], a.e.pos[2] + v[2] * d)
    return a.walkable(*a.w.grid.cell_of(p)) is None


def _set_fly_speed(a, v=0.0, h=None):
    a.fly_speed = float(v)
    if h is not None:
        a.fly_height = float(h) * entity.TILE


def _fly(a, _gravity=None):
    """Sale verso la propria quota di volo, e ci resta.

    Gli script passano una gravita' e la usano per la discesa; qui il moto
    verticale e' un avvicinamento alla quota dichiarata da `SetFlySpeed`, che
    e' quanto serve perche' l'ape stia in aria e il disegnatore la metta li'.
    """
    target = _grid_height(a) + a.fly_height
    dy = target - a.e.pos[1]
    step = max(abs(a.fly_speed), 1.0) * a.dt
    a.e.pos[1] += math.copysign(min(abs(dy), step), dy)


def _is_fly(a):
    return a.e.pos[1] > _grid_height(a) + entity.TILE / 4


def _set_jump_speed(a, v=0.0):
    a.jump = float(v)


def _do_jump(a, _g=None):
    a.jump -= 9.8 * a.dt
    a.e.pos[1] = max(_grid_height(a), a.e.pos[1] + a.jump * a.dt)


def _is_jump_finish(a):
    return a.e.pos[1] <= _grid_height(a) + 1e-3


def _is_player_to_direction(a, d=None):
    """Il giocatore e' **davanti**, entro la distanza data.

    Usato sempre nella stessa forma - `IsPlayerToDirection2( SenceDistance )
    and IsEqualPlayerFloor()` - cioe' come cono di vista: e' la percezione che
    fa scattare l'inseguimento. Il quadrante davanti, non l'angolo esatto,
    perche' qui tutto si muove su quattro direzioni.
    """
    if d is not None and _distance_to_player(a) > float(d):
        return False
    v = entity.DIRS[a.e.facing % 4]
    dx = a.w.player.pos[0] - a.e.pos[0]
    dz = a.w.player.pos[2] - a.e.pos[2]
    return dx * v[0] + dz * v[2] > 0.0


def _set_angle(a, deg=0.0, _snap=None):
    """L'angolo attorno a Y, che qui si arrotonda alla direzione piu' vicina.

    L'attore ha quattro direzioni e non un angolo libero: `entity.ANGLES` da'
    i gradi di ognuna, e questo prende la piu' vicina. Gli script lo chiamano
    sette volte in tutto, quasi sempre per rimettere dritto un nemico.
    """
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        return
    best = min(range(4), key=lambda d: abs(
        (entity.ANGLES[d] - deg + 180.0) % 360.0 - 180.0))
    a.e.facing = best


def _angle_from_direction(a):
    return None


def _set_user_int(a, v=0, slot=None):
    a.ints[0 if slot is None else int(v)] = int(v if slot is None else slot)


def _get_user_int(a, slot=0):
    return a.ints[int(slot or 0)]


def _set_user_float(a, v=0.0):
    a.floats[0] = float(v)


def _get_user_float(a):
    return a.floats[0]


def _add_node(a, name=''):
    a.nodes.append(str(name))


# Il suffisso di posa dentro il nome di un nodo, qualunque sia la famiglia:
# `EN_ENEMY_06_04_a` -> `04_a`, `NP_NPC_09_01` -> `01`, `NP_NPC05_01` -> `01`.
# Le due convenzioni degli NPC sono quelle misurate in sessione 11. Il nome
# arriva col prefisso che il Lua scrive (`package_manager.`), quindi si cerca
# dentro la stringa e non dall'inizio - come fa gia' `SetNode`.
POSE = re.compile(r'[A-Z]+_[A-Z]+_?\d+_(\d+(?:_[ab])?)$')


def _pose_of(name: str) -> str | None:
    m = POSE.search(str(name))
    return m.group(1) if m else None


def _init_animation(a):
    """Svuota il ciclo. 143 chiamate in 63 moduli, e senza di lei il ciclo si
    allungherebbe a ogni cambio di stato."""
    a.anim.clear()
    a.anim_dirty = True


def _add_animation(a, i=0, wait=0.5):
    """Una posa del ciclo: **il nodo `i`**, mostrato per `wait` secondi.

    Che il primo argomento sia un indice nell'ordine di `AddNode` non e' una
    scelta di lettura: e' l'unica che il corpus permette. In **314 file su
    314** l'indice massimo che `AddAnimation` usa e' minore del numero di
    `AddNode` di quel file, senza una sola eccezione.

    E il ciclo che ne esce e' quello che il progetto deduceva dai suffissi.
    `06Bee` aggiunge `EN_ENEMY_06_01`, `06_04_a`, `06_04_b`, `06_06` e poi
    chiede `1, 2, 1, 2, 1, 2`: alterna esattamente i due nodi appaiati. E'
    la conferma, dichiarata dal file, del «`_a` e `_b` sono i due passi»
    dedotto in sessione 4 dalla sola geometria - e adesso non serve piu'
    dedurlo.

    Il secondo argomento e' un'attesa, e lo dice il nome che gli script gli
    danno: `AnimationWait`, `DashAnimationWait`, `patapataSpeed` (パタパタ, lo
    sbattere delle ali). Vale `0.5` in 702 chiamate su 916.

    **Non si chiama nella `Initialize`**, ma nella `Update`, al cambio di
    stato: `06Bee` rifa' il proprio `1, 2` ogni volta che passa da fermo a
    volo. Per questo il ciclo va riportato nell'entita' dopo ogni fotogramma
    e non una volta sola.
    """
    a.anim.append((int(i), float(wait)))
    a.anim_dirty = True


def _period(seq: list) -> list:
    """La sequenza ridotta al suo periodo: `1,2,1,2,1,2` -> `1,2`.

    Serve perche' gli script **non svuotano** il ciclo prima di rifarlo - solo
    63 moduli su 192 chiamano `InitializeAnimation` - quindi `06Bee` che
    ridichiara il proprio `1, 2` a ogni cambio di stato lo allungherebbe
    all'infinito. Una sequenza ripetuta N volte e' indistinguibile dalla
    sequenza sola, quindi tenere il periodo non cambia cosa si vede; e cosi'
    la lista non cresce.
    """
    n = len(seq)
    for p in range(1, n // 2 + 1):
        if n % p == 0 and all(seq[i] == seq[i % p] for i in range(n)):
            return seq[:p]
    return seq


def _apply_animation(a) -> bool:
    """Porta il ciclo dichiarato dentro l'entita', nella forma che il
    disegnatore usa gia': `frames = [riposo, *ciclo]` e `step` la durata.

    Il riposo e' **il primo nodo che il ciclo non usa** - in `06Bee` il ciclo
    e' `1,2` e il nodo `0` e' la posa ferma - e se il ciclo li usa tutti e' il
    primo del ciclo, che e' il caso di `01Rabbit` (due nodi, ciclo `0,1`).
    """
    if not a.anim:
        return False
    cycle = [_pose_of(a.nodes[i]) for i, _w in a.anim
             if 0 <= i < len(a.nodes)]
    cycle = [p for p in cycle if p]
    if not cycle:
        return False
    cycle = _period(cycle)
    usati = {i for i, _w in a.anim}
    rest = next((_pose_of(n) for k, n in enumerate(a.nodes)
                 if k not in usati and _pose_of(n)), None)
    a.e.frames = [rest or cycle[0]] + cycle
    a.e.step = max(a.anim[0][1], 1e-3)
    # e la lista non deve crescere per sempre: si tiene il periodo anche li'
    if len(a.anim) > 2 * len(cycle):
        a.anim = _period(a.anim)
    return True


def _set_node(a, i=0):
    """Quale posa mostrare, per indice nell'ordine di `AddNode`.

    Il Lua nomina i nodi con le costanti di `package_manager`
    (`EN_ENEMY_06_04_a`), che sono gli stessi `NodeStrings` dell'album con un
    altro prefisso. Qui si traduce nel suffisso che il disegnatore cerca,
    perche' e' la stessa strada di `entity.Entity.pose`.
    """
    a.node = int(i)
    if 0 <= a.node < len(a.nodes):
        m = re.search(r'EN_ENEMY_\d+_(.+)$', a.nodes[a.node])
        if m:
            a.e.node = m.group(1)


def _set_hp(a, v=1):
    a.hp = int(v)


def _set_amount(a, v=0):
    a.amount = int(v)


def _set_init_vector(a):
    a.init_dir = a.e.facing
    a.start = list(a.e.pos)


_IMPL = {
    # fase e tempo, che sono i due terzi di tutte le chiamate
    'SetPhase': _set_phase, 'GetPhase': _get_phase,
    'SetTime': _set_time, 'IsTimeZero': _is_time_zero,
    'GetElapsedTime': _elapsed,
    # moto
    'SetSpeed': _set_speed, 'Move': _move,
    'SetDistance': _set_distance, 'IsDistanceZero': _is_distance_zero,
    'SetDirection': _set_direction, 'SetReverseDirection': _reverse,
    'SetRandomDirection': _random_direction, 'SetRandomDirection8':
        _random_direction,
    'SetDirectionToPlayer': _dir_to_player,
    'SetDirectionToPlayer2': _dir_to_player,
    'SetDirectionToPlayer360': _dir_to_player,
    'SetDirectionToInit': _dir_to_init,
    'IsHitWall': _is_hit_wall, 'IsHitObject': _is_hit_object,
    'IsWall': _is_wall,
    # dove si sta, in verticale
    'GetPosition': _get_position, 'GetFloor': _get_floor,
    'GetGridHeight': _grid_height,
    'SetFlySpeed': _set_fly_speed, 'Fly': _fly, 'IsFly': _is_fly,
    'SetJumpSpeed': _set_jump_speed, 'Jump': _do_jump,
    'IsJumpFinish': _is_jump_finish,
    # percezione
    'IsLesserDistance': _is_lesser_distance,
    'IsLesserDistanceX': _is_lesser_distance_x,
    'IsLesserDistanceZ': _is_lesser_distance_z,
    'IsEqualPlayerX': _is_equal_player_x,
    'IsEqualPlayerZ': _is_equal_player_z,
    'IsEqualPlayerXZ': _is_equal_player_xz,
    'IsEqualPlayerFloor': _is_equal_player_floor,
    'IsPlayerArea': _is_player_area,
    'IsPlayerToDirection': _is_player_to_direction,
    'IsPlayerToDirection2': _is_player_to_direction,
    'setAngle': _set_angle, 'SetAngleFromDirection': _angle_from_direction,
    'IsActorMoveArea': _is_actor_move_area,
    'IsStartPosition': _is_start_position,
    # stato dell'attore
    'SetUserInt': _set_user_int, 'GetUserInt': _get_user_int,
    'SetUserFloat': _set_user_float, 'GetUserFloat': _get_user_float,
    'AddNode': _add_node, 'SetNode': _set_node,
    'AddAnimation': _add_animation, 'InitializeAnimation': _init_animation,
    'SetHp': _set_hp, 'SetAmount': _set_amount,
    'SetInitVector': _set_init_vector,
}


class Troupe:
    """La VM con dentro tutti i nemici del disco, e chi li fa girare.

    Si carica **una volta sola**: `all.lua.eu` sono 3,7 MB e 869 sorgenti, e
    la VM ci mette un decimo di secondo. Poi ogni nemico piazzato in mappa
    riceve il proprio `Actor`, e a ogni fotogramma si chiama la sua `Update`
    con quello come argomento - che e' esattamente la firma che gli script
    dichiarano.
    """

    def __init__(self, data: pathlib.Path, world):
        import host

        self.data = pathlib.Path(data)
        self.world = world
        self.host = host.Host(self.data, verbose=False)
        self.host.load_libs()
        self.host.load(self.data / 'all.lua.eu')
        self.lua = self.host.lua.globals()
        self.by_model = behaviours(self.data)
        self.actors: dict[str, Actor] = {}
        self.failed = collections.Counter()
        self.animated = set()      # chi ha preso il ciclo dal proprio file

    def behaviour(self, model: str, classe=None):
        """Il comportamento di un modello, e quale se ne dichiara piu' d'uno.

        La cella porta una "classe" solo per Togetoge, ed e' il numero che
        sceglie fra `Togetoge0`..`Togetoge4`: il tipo di movimento. Per tutti
        gli altri il file ne dichiara uno solo.

        Il modello si accetta in tutte e due le forme in cui il progetto lo
        scrive - `c_enm_39_01` e' quello che l'album chiama `NodeStrings`, cioe'
        **una posa**, e `c_enm_39` la radice che il disegnatore apre.
        """
        m = re.match(r'(c_enm_\d+)', str(model or ''))
        model = m.group(1) if m else model
        opts = self.by_model.get(model) or []
        if not opts:
            return None
        if classe is not None:
            for o in opts:
                if o['classe'] == str(classe):
                    return o
        return opts[0]

    def cast(self, name: str, ent, num: int, model: str, classe=None):
        """Da' un comportamento a un nemico gia' collocato sulla mappa."""
        b = self.behaviour(model, classe)
        if b is None:
            return None
        a = Actor(ent, self.world, num, b['base'])
        fn = self.lua[f'{b["base"]}Initialize']
        if fn is None:
            return None
        try:
            fn(a)
        except Exception as ex:                                  # noqa: BLE001
            self.failed[f'{b["base"]}Initialize: {type(ex).__name__}'] += 1
            return None
        if _apply_animation(a):
            self.animated.add(name)
        self.actors[name] = a
        return a

    def update(self, dt: float) -> int:
        """Un fotogramma per tutti. Restituisce quanti sono girati."""
        n = 0
        for nome, a in self.actors.items():
            fn = self.lua[f'{a.base}Update']
            if fn is None:
                continue
            a.tick(dt)
            try:
                fn(a)
                n += 1
            except Exception as ex:                              # noqa: BLE001
                self.failed[f'{a.base}Update: {type(ex).__name__} {ex}'] += 1
            # Il ciclo di pose lo rifa' la `Update` a ogni cambio di stato,
            # non la `Initialize`: va riportato nell'entita' qui.
            if a.anim_dirty:
                a.anim_dirty = False
                if _apply_animation(a):
                    self.animated.add(nome)
        return n

    @property
    def calls(self) -> collections.Counter:
        c = collections.Counter()
        for a in self.actors.values():
            c.update(a.calls)
        return c

    @property
    def unknown(self) -> collections.Counter:
        c = collections.Counter()
        for a in self.actors.values():
            c.update(a.unknown)
        return c


def cmd_census(data: pathlib.Path) -> int:
    src = sources(data)
    api = collections.Counter()
    for t in src.values():
        for m in re.finditer(r'\b\w+:(\w+)\s*\(', t):
            api[m.group(1)] += 1
    tot = sum(api.values())
    ha = sum(v for k, v in api.items() if k in _IMPL)
    print(f'{len(src)} file di nemico, {len(api)} metodi distinti, '
          f'{tot} chiamate')
    print(f'implementati {sum(1 for k in api if k in _IMPL)} su {len(api)}, '
          f'che coprono {ha}/{tot} chiamate = {100 * ha / tot:.1f}%')
    print('\ni piu chiesti che mancano:')
    for k, v in api.most_common():
        if k not in _IMPL:
            print(f'   {k:<26} {v:4}')
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, root = sys.argv[1], pathlib.Path(sys.argv[2])
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    if cmd == 'census':
        return cmd_census(data)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
