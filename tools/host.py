"""
host.py - il primo pezzo di host: VM Lua, scheduler a coroutine, messaggi.

Esegue **gli script originali, verbatim**. Non una loro traduzione, non un
sottoinsieme: il file `.lua.eu` che sta sul disco, dato in pasto a una VM Lua
vera (`lupa`). E' la tesi del progetto messa alla prova per la prima volta.

## Come e' fatto uno script di evento

    function DevilEvent()
        local Event = EventClass.Event;
        Event:LockPlayer();
        Event:PlayScene(0,14,0)
        Event:Wait(0.9);
        coroutine.yield();
        ...
        Event:Print("Ｌｅｅ：　ＴｈーＴｈａｔ　ｉｓ．．．/r．．．/b/cl");
        Event:WaitContinue();
        coroutine.yield();
        Event:CloseMessage();
    end

Il ritmo e' sempre lo stesso: si chiede qualcosa all'host, si cede il controllo
con `coroutine.yield()`, l'host riprende quando la richiesta e' soddisfatta.
Lo scheduler quindi non deve interpretare niente: gli basta sapere **quando**
riprendere. Tre condizioni bastano per gli eventi visti finora: un tempo
scaduto (`Wait`), un input del giocatore (`WaitContinue`), la fine di una
sequenza (`WaitScene`).

## I globali nativi

`EventClass` e `soundList` non li definisce **nessuno** script: sono globali
che forniva il codice C++ della PS3. Qui `EventClass.Event` e' l'oggetto host,
mentre gli altri diventano tabelle permissive che restituiscono il nome della
costante invece del suo valore numerico - che infatti non conosciamo, e sta
nell'EBOOT (Fase 3). `soundList.SoundID.SE_quake` vale `"SE_quake"`: abbastanza
per far girare lo script e per registrare cosa chiede.

Ogni metodo non implementato viene **contato invece che fallire**. E' il
criterio della Fase 5: uno script che gira senza chiamare metodi ignoti e' un
sottosistema finito. `coverage` misura esattamente questo.

## Il markup dei messaggi

Nove codici, censiti in RECON §6.4: `/r` a capo, `/b` fine blocco e attendi,
`/co` chiudi, `/cl` pulisci e continua, `/pl` terminatore alternativo,
`/vn` `/vh` `/vl` tono del bip (ipotesi), `/pa` ignoto.

Uso:
  python host.py run      <script.lua.eu> [NomeFunzione]
  python host.py coverage <dir>      quali metodi servono, in ordine di uso
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

import entity

MARKUP = re.compile(r'/(r|b|co|cl|pl|vn|vh|vl|pa)')

# Bootstrap dei globali nativi. Tutto cio' che uno script cerca e non trova
# diventa una tabella permissiva, e viene registrato.
BOOT = """
__missing = {}
-- Una tabella permissiva e' ricorsiva: `soundList.SoundID.SE_quake` deve
-- reggere due livelli e restituire qualcosa di nominato, non nil. Il nome
-- completo resta leggibile in `__name`, cosi' l'host puo' registrare *quale*
-- costante nativa e' stata chiesta anche senza conoscerne il valore.
local function permissive(name)
    local t = setmetatable({}, {
        __index = function(_, k)
            return permissive(name and (name .. '.' .. k) or tostring(k))
        end,
        __tostring = function() return name or '?' end,
        -- Chiamabile: una funzione che non esiste deve restituire nil, non
        -- fermare lo script. Senza questo un solo helper mancante uccide
        -- l'evento alla prima riga.
        __call = function() return nil end,
    })
    rawset(t, '__name', name)
    return t
end
setmetatable(_G, {__index = function(t, k)
    __missing[k] = (__missing[k] or 0) + 1
    local stub = permissive(tostring(k))
    rawset(t, k, stub)
    return stub
end})

-- Lo scheduler tiene il thread **dentro** il Lua: un oggetto coroutine che
-- attraversa il confine con Python torna indietro come funzione, e
-- coroutine.resume lo rifiuta.
function __start(fn) __co = coroutine.create(fn) end
function __step()
    if coroutine.status(__co) == 'dead' then return 'dead' end
    local ok, err = coroutine.resume(__co)
    if not ok then return 'error', tostring(err) end
    return coroutine.status(__co)
end
"""


def read_script(path: pathlib.Path) -> str:
    """Il corpus ha **codifiche miste**: quasi tutti i file sono UTF-8, ma 13
    script di evento su 378 sono in Shift-JIS (cp932) - i commenti giapponesi
    degli sviluppatori, del tipo `--ボスを倒した場合`. Provarli in ordine e'
    sufficiente: UTF-8 fallisce in modo netto sui byte 0x80-0x9F."""
    raw = path.read_bytes()
    for enc in ('utf-8', 'cp932'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1')


class Page:
    """Un blocco di messaggio: le righe da mostrare insieme, e cosa fare quando
    il giocatore preme il tasto."""
    __slots__ = ('lines', 'after', 'voice')

    def __init__(self, lines, after, voice):
        self.lines, self.after, self.voice = lines, after, voice

    def __repr__(self) -> str:
        return f'Page({self.lines!r}, {self.after}, {self.voice})'


def parse_message(text: str) -> list[Page]:
    """Da una stringa con markup alle pagine da mostrare."""
    pages, lines, cur, voice = [], [], '', None
    after = 'close'
    for part in MARKUP.split(text):
        if part in ('r',):
            lines.append(cur); cur = ''
        elif part in ('vn', 'vh', 'vl'):
            voice = part
        elif part == 'b':
            lines.append(cur); cur = ''
            pages.append(Page([l for l in lines if l is not None], None, voice))
            lines = []
        elif part in ('co', 'pl', 'cl'):
            if pages:
                pages[-1].after = 'clear' if part == 'cl' else 'close'
        elif part == 'pa':
            pass
        else:
            cur += part
    if cur or lines:
        lines.append(cur)
        pages.append(Page(lines, after, voice))
    return pages


class Api:
    """L'oggetto che il Lua vede come `EventClass.Event`.

    In Lua `Event:Wait(0.9)` significa `Event.Wait(Event, 0.9)`: il primo
    argomento e' l'oggetto stesso, e va assorbito. Per questo ogni metodo e'
    una chiusura generata al volo, che serve anche a **contare** le chiamate.
    """

    def __init__(self, host):
        self.host = host
        self.calls = collections.Counter()
        self.unknown = collections.Counter()
        self.impl = {
            'Wait': self._wait,
            'WaitContinue': self._wait_input,
            'WaitScene': self._wait_scene,
            'Print': self._print,
            'CloseMessage': self._close,
            'Select': self._select,
            'GetSelect': self._get_select,
            'GetPlayerName': self._player_name,
            'GetEventFlag': self._get_flag,
            'SetEventFlag': self._set_flag,
            'GetMoney': self._get_money,
            'SetMoney': self._set_money,
            'SetCamera': self._set_camera,
            'SetCameraAtBody': self._set_camera_at,
            'BackupCamera': self._backup_camera,
            'RestoreCamera': self._restore_camera,
            'SetParamDepthofField': self._set_dof,
            'SetDofApaerture': self._set_aperture,
            'BackupDof': self._backup_dof,
            'RestoreDof': self._restore_dof,
            'switchDofPointGaze': self._gaze_on,
            'resetDofPointGaze': self._gaze_off,
            # -- entita'
            'Pause': self._pause,
            'Play': self._play,
            'PauseNpc': self._pause_npc,
            'PlayNpc': self._play_npc,
            'PauseEnemy': self._pause_enemy,
            'PlayEnemy': self._play_enemy,
            'LockPlayer': self._lock,
            'UnlockPlayer': self._unlock,
            'SetPlayerDirection': self._player_dir,
            'SetNpcDirection': self._npc_dir,
            'CreateNpc': self._create_npc,
            'SetNpcVisible': self._npc_visible,
            'SetPlayerVisible': self._player_visible,
            'SetNpcNode': self._npc_node,
            'MoveNpc': self._move_npc,
            'MoveNpcAndY': self._move_npc_y,
            'MovePlayer': self._move_player,
            'SetPlayerPosition': self._player_pos,
            'SetStatusVisible': self._status_visible,
            'SavePlayerAngle': self._save_angle,
            'RestorPlayerAngle': self._restore_angle,
            'setPlayerAngle': self._set_angle,
        }

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        impl = self.impl.get(name)

        def call(_self=None, *args):
            self.calls[name] += 1
            if impl is None:
                self.unknown[name] += 1
                self.host.log(f'? {name}({", ".join(map(_short, args))})')
                return None
            return impl(*args)
        return call

    # -- metodi implementati

    def _wait(self, seconds=0.0):
        self.host.timer = float(seconds)
        self.host.log(f'. attesa {seconds}s')

    def _wait_input(self):
        self.host.awaiting = True
        self.host.log('. attesa input')

    def _wait_scene(self):
        self.host.timer = 0.5          # non c'e' ancora un sistema di scene
        self.host.log('. attesa fine sequenza')

    def _print(self, text=''):
        pages = parse_message(str(text))
        self.host.pages.extend(pages)
        for p in pages:
            self.host.log(f'> {" | ".join(p.lines)}')

    def _close(self):
        self.host.pages.clear()
        self.host.page = 0
        self.host.log('. riquadro chiuso')

    # `Select()` non prende argomenti in nessuna delle 298 chiamate del disco:
    # e' un si'/no fisso. Lo si vede anche dai confronti che seguono -
    # `GetSelect()` viene confrontato con 0 in 288 punti e con 1 in 9, mai con
    # altro. Le due etichette non stanno in nessuno script: sono native, e le
    # prendiamo per analogia dai 16 descrittori UI che le dichiarano (`ＹＥＳ`
    # / `ＮＯ`, cursore a sinistra).
    def _select(self):
        self.host.choice = 0
        self.host.choosing = True
        self.host.awaiting = True
        self.host.log('. scelta aperta')

    def _get_select(self):
        return self.host.choice

    def _player_name(self):
        # Compare **dentro** le stringhe di dialogo (`""..GetPlayerName()..`),
        # quindi senza non e' che manchi un nome: lo script muore su una
        # concatenazione con nil.
        return self.host.player_name

    def _get_flag(self, flag=None):
        return int(self.host.flags.get(_short(flag), 0))

    def _set_flag(self, flag=None, value=1):
        self.host.flags[_short(flag)] = int(value or 0)

    def _get_money(self):
        return self.host.money

    def _set_money(self, value=0):
        self.host.money = int(value or 0)

    # -- camera
    #
    # Le firme si leggono dai dati, con un aiuto involontario degli autori.
    # `eventfunction.lua.eu` definisce due helper commentati 家NPCカメラ右から
    # ("camera NPC da destra") e 左から ("da sinistra"), e fra i due cambia
    # **solo il segno del terzo argomento**: quindi il terzo e' un azimut in
    # gradi. Restano (6.12, 19.61) e (4.1, 20.19): distanza e elevazione, con
    # le elevazioni tutte fra 19 e 30 gradi, come ci si aspetta da una camera
    # che guarda dall'alto.
    #
    # Ipotesi da confermare in Fase 3: nella forma a 6 argomenti il primo vale
    # 0.10 in 170 chiamate su 170, e ha la forma di un tempo di transizione;
    # gli ultimi tre sono coordinate di mondo, cioe' il punto inquadrato.

    def _set_camera(self, *args):
        # La forma a sei argomenti non porta una distanza: il secondo scende a
        # **-17,72**, e una distanza negativa non esiste. Sono
        # `(tempo, elevazione, azimut, x, y, z)` - il primo vale 0,10 in 140
        # chiamate su 142, l'elevazione sta fra -17,7 e +64,8 gradi e
        # l'azimut fra -180 e +338. Gli ultimi tre sono un punto nel
        # riferimento della mappa, quello con l'origine all'angolo.
        c = self.host.camera
        if len(args) >= 6:
            t = self.host.to_local(args[3], args[4], args[5])
            c.update(elev=float(args[1]), azim=float(args[2]),
                     target=t if t is not None
                     else (float(args[3]), float(args[4]), float(args[5])))
            if not c['dist']:
                c['dist'] = 8.0        # la chiamata non la dice: un default
        elif len(args) >= 3:
            c.update(dist=float(args[0]), elev=float(args[1]),
                     azim=float(args[2]))
        self.host.log(f'. camera {c["dist"]:.1f}m elev {c["elev"]:.0f} '
                      f'azim {c["azim"]:.0f}')

    def _set_camera_at(self, dist=6.0, elev=20.0, azim=0.0, target=None):
        # Finche' non c'era un registro, `body` era solo un nome annotato e la
        # camera restava al centro della scena. Ora e' un'entita', e il
        # bersaglio e' il suo petto: mezzo personaggio da terra, cioe' mezza
        # casella - le altre camere del disco guardano tutte all'altezza del
        # busto (`EnemyView` dichiara `AtY=0.7`).
        name = _short(target)
        self.host.camera.update(dist=float(dist), elev=float(elev),
                                azim=float(azim), body=name)
        # `require` e non `get`: il bersaglio e' quasi sempre un NPC che sta
        # gia' sulla mappa e che nessuno script ha creato - dei 99 nomi del
        # corpus solo 40 passano da `CreateNpc`. Materializzarlo e' la stessa
        # scelta gia' fatta per `SetNpcDirection`, e per lo stesso motivo:
        # un'entita' nel posto sbagliato si vede e si corregge, una chiamata
        # persa no.
        e = self.host.world.require(name)
        self.host.camera['target'] = (e.pos[0], e.pos[1] + entity.TILE / 2,
                                      e.pos[2])
        self.host.log(f'. camera su {name}: {float(dist):.1f}m '
                      f'elev {float(elev):.0f} azim {float(azim):.0f}'
                      + ('' if e.created else ' (NPC di mappa, posizione ignota)'))

    def _backup_camera(self):
        self.host.camera_stack.append(dict(self.host.camera))

    def _restore_camera(self):
        if self.host.camera_stack:
            self.host.camera = self.host.camera_stack.pop()
            self.host.log('. camera ripristinata')

    # -- profondita' di campo, che finisce dritta nella catena di post.py

    def _set_dof(self, focus=None, width=None, _t=0.0):
        d = self.host.dof
        if focus is not None:
            d['focus'] = float(focus)
        if width is not None:
            d['range'] = float(width)
        self.host.log(f'. fuoco {d["focus"]:.2f} ampiezza {d["range"]:.2f}')

    def _set_aperture(self, value=0.7, _mode=0):
        self.host.dof['aperture'] = float(value)
        self.host.log(f'. apertura {float(value):.2f}')

    def _backup_dof(self):
        self.host.dof_stack.append(dict(self.host.dof))

    def _restore_dof(self):
        if self.host.dof_stack:
            self.host.dof = self.host.dof_stack.pop()

    def _gaze_on(self):
        self.host.dof['gaze'] = True

    def _gaze_off(self):
        self.host.dof['gaze'] = False

    # -- entita'
    #
    # Ventidue metodi che chiedono tutti la stessa cosa - un mondo con dentro
    # dei personaggi - e che insieme valgono 1.664 chiamate misurate, il 25%
    # del corpus. Lo stato sta in `entity.World`; qui c'e' solo la traduzione
    # dalle firme degli script. Vedi docs/entities.md.

    def _pause(self):
        """`Pause()` / `Play()`, 397 chiamate, sempre senza argomenti: e' il
        mondo intero che si ferma perche' qualcuno deve parlare."""
        self.host.world.frozen.update(npc=True, enemy=True, player=True)
        self.host.log('. mondo in pausa')

    def _play(self):
        self.host.world.frozen.update(npc=False, enemy=False, player=False)
        self.host.log('. mondo ripreso')

    def _pause_npc(self):
        self.host.world.frozen['npc'] = True

    def _play_npc(self):
        self.host.world.frozen['npc'] = False

    def _pause_enemy(self):
        self.host.world.frozen['enemy'] = True

    def _play_enemy(self):
        self.host.world.frozen['enemy'] = False

    def _lock(self):
        # Ferma il *giocatore*, non il mondo: 133 chiamate, quasi sempre in
        # apertura di evento e appaiate a UnlockPlayer in chiusura.
        self.host.world.player_locked = True

    def _unlock(self):
        self.host.world.player_locked = False

    def _player_dir(self, d=0):
        self.host.world.player.facing = int(d) % 4
        self.host.log(f'. giocatore verso {entity.DIRS[int(d) % 4]}')

    def _npc_dir(self, name=None, d=0):
        e = self.host.world.require(_short(name))
        e.facing = int(d) % 4
        self.host.log(f'. {e.name} verso {entity.DIRS[e.facing]}')

    def _create_npc(self, x=0.0, y=0.0, z=0.0, name=None):
        e = self.host.world.create(_short(name), (float(x), float(y), float(z)))
        p = ', '.join(f'{v:.1f}' for v in e.pos)
        self.host.log(f'+ {e.name} a ({p}) come {e.model}')
        return None

    def _npc_visible(self, name=None, on=1):
        e = self.host.world.require(_short(name))
        e.visible = bool(int(on))
        self.host.log(f'. {e.name} {"visibile" if e.visible else "nascosto"}')

    def _player_visible(self, on=1):
        self.host.world.player.visible = bool(int(on))

    def _npc_node(self, name=None, node=0):
        # Sceglie quale figlio del modello mostrare: e' il metodo che ha
        # confermato che i figli sono pose e non pezzi.
        e = self.host.world.require(_short(name))
        e.node = int(node)
        self.host.log(f'. {e.name} posa {e.node}')

    # `MoveNpc(nome, dx, dz, velocita [, flag])` e
    # `MoveNpcAndY(nome, dx, dy, dz, velocita)`: il nome del secondo dichiara
    # la differenza fra i due, cioe' che il primo non ha la Y. Lo conferma la
    # velocita', che resta l'ultimo argomento in entrambi e vale 3,2 in 76
    # chiamate su 87.
    def _move_npc(self, name=None, dx=0.0, dz=0.0, speed=3.2, _flag=0):
        e = self.host.world.require(_short(name))
        e.move_by((float(dx), 0.0, float(dz)), speed)
        self.host.log(f'. {e.name} si sposta di ({float(dx):.1f}, '
                      f'{float(dz):.1f}) a {float(speed):.1f}')

    def _move_npc_y(self, name=None, dx=0.0, dy=0.0, dz=0.0, speed=3.2):
        e = self.host.world.require(_short(name))
        e.move_by((float(dx), float(dy), float(dz)), speed)

    def _move_player(self, dx=0.0, dz=0.0, speed=3.2):
        self.host.world.player.move_by((float(dx), 0.0, float(dz)), speed)
        self.host.log(f'. giocatore si sposta di ({float(dx):.1f}, '
                      f'{float(dz):.1f})')

    def _player_pos(self, x=0, y=0, z=0):
        """`SetPlayerPosition(12, 4, 0)`: qui gli argomenti sono **interi
        piccoli** (7..89, 1..83, 0..10), non i multipli di 0,8 di tutto il
        resto. Sono celle della griglia logica della mappa, quella dei file
        `MAP_ALIGNMENT` (`D_1_1_1` e' 112 x 96), e il terzo non e' una
        coordinata ma il piano: vale 0 in 48 chiamate su 71.

        Una cella vale `TILE`, e l'origine sta a un **angolo**: X cresce verso
        destra, Z verso il basso ma **negativa**. Lo dicono gli argomenti
        stessi delle camere assolute degli script, che hanno X sempre positiva
        (8,33..130,53) e Z sempre negativa (-206,36..-11,19), e lo conferma
        che ogni punto cosi' letto cade dentro `[0, w*1,6] x [-h*1,6, 0]` in
        17 casi su 17 fra gli eventi che le `MAP_ALIGNMENT` sanno attribuire a
        una mappa.

        Senza una mappa caricata la cella si registra e basta: non c'e' `w` e
        `h` con cui portarla nel riferimento centrato della geometria.
        """
        self.host.cell = (int(x), int(y), int(z))
        p = self.host.cell_to_local(x, y)
        if p is None:
            self.host.log(f'. giocatore alla cella ({int(x)}, {int(y)}) '
                          f'piano {int(z)} (nessuna mappa caricata)')
            return
        pl = self.host.world.player
        pl.pos = [p[0], pl.pos[1], p[2]]
        pl.stop()
        self.host.log(f'. giocatore alla cella ({int(x)}, {int(y)}) '
                      f'piano {int(z)} = ({p[0]:.1f}, {p[2]:.1f})')

    def _status_visible(self, on=1):
        self.host.world.status_visible = bool(int(on))

    # L'angolo fine, in gradi: `setPlayerAngle(45)` e le sue tre sorelle
    # usano i diagonali, che le quattro direzioni non sanno dire. La pila
    # Save/Restor (senza la "e", nel gioco) e' la stessa idea di
    # BackupCamera/RestoreCamera.
    def _save_angle(self):
        w = self.host.world
        w.angle_stack.append(w.player_angle
                             if w.player_angle is not None
                             else entity.facing_angle(w.player.facing))

    def _restore_angle(self):
        w = self.host.world
        if w.angle_stack:
            self._set_angle(w.angle_stack.pop())

    def _set_angle(self, deg=0.0):
        w = self.host.world
        w.player_angle = float(deg)
        # la direzione cardinale piu' vicina, cosi' il resto del sistema
        # continua a funzionare con quattro valori
        best = min(range(4), key=lambda d: abs(
            (entity.facing_angle(d) - float(deg) + 180) % 360 - 180))
        w.player.facing = best


def _short(v) -> str:
    """Le costanti native arrivano come tabelle permissive: quello che
    interessa registrare e' il loro nome (`soundList.SoundID.SE_quake`), non
    il valore, che non conosciamo."""
    try:
        name = v['__name']
        if name:
            return str(name)
    except (TypeError, KeyError, AttributeError):
        pass
    s = str(v)
    return s if len(s) <= 28 else s[:25] + '...'


class Host:
    def __init__(self, root: pathlib.Path, verbose: bool = True):
        from lupa import LuaRuntime

        self.root = root
        self.verbose = verbose
        self.lines: list[str] = []
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(BOOT)
        self.api = Api(self)
        self.lua.globals().EventClass = self.lua.table(Event=self.api)

        self.co = None
        self.timer = 0.0
        self.awaiting = False
        self.pages: list[Page] = []
        self.page = 0
        self.done = False
        self.failed: str | None = None
        self.time = 0.0
        # stato di gioco, quel poco che serve a far prendere agli script i
        # rami veri invece di sempre il primo
        self.choosing = False
        self.choice = 0
        self.player_name = 'ＨＥＲＯ'
        self.flags: dict[str, int] = {}
        self.money = 0
        # Camera e messa a fuoco: per volume di chiamate sono il grosso di un
        # evento di questo gioco. I valori di partenza sono quelli mediani del
        # disco (vedi render.md).
        self.camera = {'dist': 0.0, 'elev': 25.0, 'azim': 0.0,
                       'target': None, 'body': None}
        self.camera_stack: list[dict] = []
        self.dof = {'focus': 0.79, 'range': 0.70, 'aperture': 0.70,
                    'gaze': False}
        self.dof_stack: list[dict] = []
        # Il mondo: posizioni, direzioni, pose. Vive di tempo suo, avanzato
        # da `update`, perche' il moto degli script non blocca (entity.py).
        self.world = entity.World()
        self.cell = (0, 0, 0)      # ultima cella logica dichiarata
        # La griglia logica della mappa caricata, `(w, h)` da MAP_ALIGNMENT.
        # Serve a tradurre fra i due sistemi di riferimento del gioco: gli
        # script parlano in celle con l'origine a un **angolo**, la geometria
        # del `.pac` e' centrata sullo zero. Senza mappa resta None e le
        # posizioni assolute si limitano a essere registrate.
        self.map: tuple[int, int] | None = None
        # La griglia stessa, quando qualcuno l'ha caricata: celle, passaggi e
        # abitanti. Resta `None` quando un evento gira senza mappa.
        self.grid = None

    def to_local(self, x, y, z):
        """Da un punto del sistema della mappa (angolo, Z negativa verso il
        basso) a quello della geometria caricata (centrato)."""
        if self.map is None:
            return None
        w, h = self.map
        return (float(x) - w * entity.TILE / 2, float(y),
                float(z) + h * entity.TILE / 2)

    def cell_to_local(self, cx, cy):
        """Il centro di una cella. Quando c'e' una griglia caricata risponde
        lei, cosi' il posto in cui l'host mette un personaggio e quello in cui
        ce lo mette chi cammina (`walk.py`) sono lo stesso posto."""
        if self.grid is not None:
            return self.grid.local(cx, cy)
        return self.to_local((float(cx) + 0.5) * entity.TILE, 0.0,
                             -(float(cy) + 0.5) * entity.TILE)

    def load_map(self, dat: pathlib.Path) -> int:
        """Carica la griglia logica di una mappa: le sue dimensioni e i posti
        dei suoi NPC.

        E' quello che trasforma `require()` da ripiego in collocamento: i 59
        nomi su 99 che nessuno script crea stanno qui, dichiarati per
        identificativo in una cella della `MAP_ALIGNMENT`.
        """
        import walk

        self.grid = walk.Grid(dat)
        self.map = (self.grid.w, self.grid.h)
        self.world.spots = {k: self.grid.local(x, y)
                            for k, (x, y) in self.grid.spots.items()}
        return len(self.world.spots)

    def log(self, s: str) -> None:
        self.lines.append(f'[{self.time:6.2f}] {s}')
        if not self.verbose:
            return
        try:
            print(self.lines[-1])
        except UnicodeEncodeError:
            # I dialoghi sono in full-width e la console di Windows e' cp1252:
            # senza questa rete l'eccezione risalirebbe fino dentro il Lua, e
            # l'evento morirebbe sulla sua prima battuta.
            enc = sys.stdout.encoding or 'ascii'
            print(self.lines[-1].encode(enc, 'replace').decode(enc))

    # -- caricamento ed esecuzione

    # Le librerie condivise. Gli script di evento chiamano funzioni come
    # `seafterboss()` o `setnpccamerac()` che non sono metodi dell'host ma Lua
    # normale, definito altrove: e' il package manager del gioco a caricarle
    # prima. Senza, un evento su due muore alla prima riga.
    PRELUDE = ('Event/eventfunction.lua.eu', 'Event/eventflag.lua.eu')

    def load_libs(self) -> int:
        n = 0
        for rel in self.PRELUDE:
            p = self.root / rel
            if p.exists():
                self.lua.execute(read_script(p))
                n += 1
        return n

    def load(self, path: pathlib.Path) -> None:
        self.lua.execute(read_script(path))

    def start(self, func: str) -> None:
        fn = self.lua.globals()[func]
        if fn is None:
            raise SystemExit(f'funzione {func} non definita dallo script')
        self.lua.globals()['__start'](fn)
        self.co = func
        self.log(f'evento {func} avviato')

    def begin(self, path: pathlib.Path, func: str | None = None) -> None:
        """Comincia una conversazione, da capo.

        Serve a chi gioca: parlare con un NPC vuol dire far partire il **suo**
        script, e poterlo rifare, e poi parlare con un altro. Il mondo resta
        dov'e' - non si ricarica niente - mentre lo stato del dialogo
        (pagine, attese, coroutine) riparte pulito, altrimenti la seconda
        battuta arriverebbe gia' finita.
        """
        self.pages.clear()
        self.page = 0
        self.choosing, self.choice = False, 0
        self.awaiting, self.timer = False, 0.0
        self.done, self.failed, self.co = False, None, None
        self.load(path)
        self.start(func or resolve(path)[1])

    def move(self, delta: int) -> None:
        """Cursore della scelta. Le opzioni sono sempre due."""
        if self.choosing:
            self.choice = (self.choice + delta) % 2

    def press(self) -> None:
        """Il tasto del giocatore: conferma una scelta, oppure avanza la
        pagina; se non ce ne sono altre, sblocca lo script."""
        if self.choosing:
            self.choosing = False
            self.awaiting = False
            self.log(f'. scelta confermata: {self.choice}')
            return
        if self.pages and self.page < len(self.pages) - 1:
            self.page += 1
            return
        if self.pages and self.pages[self.page].after == 'clear':
            self.pages.clear()
            self.page = 0
        self.awaiting = False

    def update(self, dt: float) -> None:
        """Un fotogramma. Riprende la coroutine appena la sua condizione di
        attesa e' soddisfatta - e ne riprende **una sola** per fotogramma, che
        e' il comportamento dello scheduler originale: gli script sono scritti
        aspettandosi un yield per frame."""
        # Il mondo avanza sempre, anche mentre lo script aspetta e anche dopo
        # che e' finito: `MoveNpc` non blocca, quindi un personaggio puo'
        # ancora essere a meta' strada quando l'evento si chiude.
        self.world.tick(dt)
        if self.done or self.co is None:
            return
        self.time += dt
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)
            return
        if self.awaiting:
            return
        res = self.lua.globals()['__step']()
        status, rest = (res[0], res[1:]) if isinstance(res, tuple) else (res, ())
        if status == 'error':
            self.failed = str(rest[0]) if rest else '?'
            self.log(f'! errore Lua: {self.failed}')
            self.done = True
        elif status == 'dead':
            self.done = True
            self.log('evento concluso')

    # -- risultati

    def missing_globals(self) -> dict:
        # In una classe Python `.__missing` diventa `._Host__missing`: qui
        # serve l'indicizzazione esplicita.
        m = self.lua.globals()['__missing']
        return {k: int(v) for k, v in (m.items() if m else [])}


def resolve(path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Il nome della funzione di evento non e' dichiarato da nessuna parte:
    per convenzione lo script `Devil.lua.eu` definisce `DevilEvent()`. Se non
    c'e', si prende la prima funzione globale del file."""
    text = read_script(path)
    guess = path.name.split('.')[0] + 'Event'
    if re.search(rf'function\s+{guess}\s*\(', text):
        return path, guess
    m = re.search(r'function\s+([A-Za-z_]\w*)\s*\(', text)
    if not m:
        raise SystemExit(f'{path}: nessuna funzione globale')
    return path, m.group(1)


def cmd_run(path: pathlib.Path, func: str | None) -> int:
    root = path
    while root.name and root.name != 'data':
        root = root.parent
    host = Host(root)
    host.load_libs()
    host.load(path)
    _, func = (path, func) if func else resolve(path)
    host.start(func)

    dt, t, presses = 1 / 60, 0.0, 0
    while not host.done and t < 120.0:
        host.update(dt)
        t += dt
        if host.awaiting:
            # nessun giocatore: si preme da soli dopo mezzo secondo
            if int(t * 60) % 30 == 0:
                host.press()
                presses += 1
                if presses > 200:
                    break
    print()
    print(f'{"concluso" if host.done else "interrotto"} a t={host.time:.1f}s, '
          f'{sum(host.api.calls.values())} chiamate all API, '
          f'{len(host.api.unknown)} metodi non implementati')
    for name, n in host.api.unknown.most_common(12):
        print(f'  {n:>3}  {name}')
    miss = host.missing_globals()
    if miss:
        print(f'globali native richieste: '
              + ', '.join(f'{k} ({v})' for k, v in miss.items()))
    return 0


def cmd_coverage(root: pathlib.Path) -> int:
    """Esegue ogni script di evento del disco e misura quali metodi servono.
    E' la lista della spesa dell'host, in ordine di urgenza reale."""
    scripts = sorted(root.rglob('*.lua.eu'))
    calls, per_script, failed = collections.Counter(), {}, []
    data = root
    while data.name and data.name != 'data':
        data = data.parent
    ran = 0
    for p in scripts:
        try:
            host = Host(data, verbose=False)
            host.load_libs()
            host.load(p)
            _, func = resolve(p)
            host.start(func)
            for _ in range(3000):
                host.update(1 / 60)
                if host.awaiting:
                    host.press()
                if host.done:
                    break
        except SystemExit:
            continue
        except Exception as ex:                                  # noqa: BLE001
            failed.append(f'{p.name}: {type(ex).__name__} {ex}')
            continue
        ran += 1
        calls.update(host.api.calls)
        per_script[p.name] = (host.done and not host.failed, host.failed)
        if host.failed:
            failed.append(f'{p.name}: {host.failed}')
    finished = sum(1 for ok, _ in per_script.values() if ok)
    impl = Host(data, verbose=False).api.impl
    done = sum(n for k, n in calls.items() if k in impl)
    tot = sum(calls.values())
    print(f'{ran} script eseguiti su {len(scripts)}, {finished} arrivati in '
          f'fondo, {len(failed)} in errore')
    print(f'{len(calls)} metodi distinti, {tot} chiamate')
    print(f'{sum(1 for k in calls if k in impl)} implementati su {len(calls)} '
          f'usati, che coprono {done} chiamate su {tot} '
          f'({done * 100 // tot}%)\n')
    print('i piu\' chiamati (implementarli in quest\'ordine):')
    for name, n in calls.most_common(25):
        mark = '*' if name in impl else ' '
        print(f'  {mark} {n:>5}  {name}')
    for f in failed[:8]:
        print(f'  ! {f}')
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, target = sys.argv[1], pathlib.Path(sys.argv[2])
    if cmd == 'run':
        return cmd_run(target, sys.argv[3] if len(sys.argv) > 3 else None)
    if cmd == 'coverage':
        return cmd_coverage(target)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
