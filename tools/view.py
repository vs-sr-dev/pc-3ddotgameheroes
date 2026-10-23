"""
view.py - il primo render: carica una mappa (o un modello) e la disegna
texturizzata, in OpenGL.

E' il primo test di integrazione del progetto, e mette alla prova in un colpo
solo quattro formati e le tre catene di riferimenti che li legano:

    .pac  -> griglia di sezioni          (format_pac.md)
    DSBF  -> nodi, mesh, chunk, vertici  (format_dsb.md)
    chunk -> materiale -> texture        (l'indice a +0x00 e i quattro stage)
    TPKG  -> pixel DXT                   (format_tpk.md)

Se una sola di queste e' letta male non si vede un disegno storto: si vede
geometria strappata, oppure texture sbagliate su facce giuste. E' un oracolo
severo proprio perche' e' visivo.

In coda c'e' la catena di post-processing di post.py - defocus, glare,
vignetting, color modification - che e' quello che fa leggere il mondo di
voxel come un diorama in miniatura. Si spegne con --raw.

Quello che *non* fa: e' un renderer di verifica, non il renderer del gioco.
Manca il resto di renderer.md - normal map, environment map, rim light, ombre.

Uso:
  python view.py <file.pac|.dsb|.gz> [opzioni]
  python view.py play  <mappa>           ci si cammina dentro (vedi walk.py)
  python view.py sweep <dir extract>     passata di verifica, senza schermo
  python view.py char  <c_npc_05>        un personaggio con le sue pose in fila
  python view.py event <script.lua.eu>   un evento su un palco vuoto, senza mappa
  python view.py layout                  la composizione, verificata sul disco
  python view.py walkabout               il mondo, percorso a piedi e misurato
  python view.py light                   quanto cielo vede ogni mappa

  --cell x,y     da che cella comincia la partita (`play`)
  --spawn A      quale dei set di nemici mettere in mappa: A, B, C sono le tre
                 disposizioni fra cui il gioco sceglie, F, G, H quelle di FROM
                 Mode, `-` non ne mette nessuna (default A)
  --roof 2.4     quanto mondo tenere sopra la testa; --no-roof lo lascia tutto
  --talk         va accanto a un abitante e gli fa dire la sua battuta, cosi'
                 che un fermo immagine mostri il giro intero
  --map          apre subito la mappa del piano (in `play` si accende con M)

  --sec N        una sola sezione della mappa (default: tutte)
  --only <sub>   solo i pezzi il cui nome contiene <sub>
  --no-water     non disegna il mare (di norma si disegna: vedi water_parts)
  --shot out.png disegna un fotogramma, lo salva ed esce (non serve schermo)
  --size 1600x900
  --azim/--elev/--dist   inquadratura iniziale (gradi, gradi, moltiplicatore)
  --raw          niente post-processing
  --dof 0.10     ampiezza della zona a fuoco, in frazioni del raggio scena
  --aperture 0.7 quanto sfoca fuori fuoco (il Lua usa 0,70 - 1,50)
  --flat         spegne la luce direzionale (il colore per vertice basta)
  --list         elenca le sezioni e esce
  --event <script.lua.eu>  esegue un evento sopra la mappa
  --skip N       porta avanti l'evento di N secondi prima del primo fotogramma
  --at x,y,z     dove sta il giocatore: gli NPC nascono **relativi a lui**,
                 e il centro della scena spesso cade dentro un muro

  Alla tastiera: WASD e RV per muoversi, trascinare il mouse per guardarsi
  intorno, rotella per avvicinarsi, F inquadra tutto, T texture, L luce,
  C backface culling, P post-processing, [ ] fuoco, - + apertura, ESC esce.
"""
from __future__ import annotations

import ctypes
import gzip
import math
import pathlib
import struct
import sys
import time

import numpy as np

import dsb
import post
import tpk

# ---------------------------------------------------------------- geometria

# numpy sa leggere il big-endian: e' la stessa dichiarazione del vertice di
# dsb.py, tradotta in dtype invece che in formati struct.
NP_TYPE = {
    0: ('>f4', 2), 1: ('>f4', 3), 2: ('>f4', 4),
    3: ('>f2', 2), 4: ('>f2', 3), 5: ('>f2', 4),
    6: ('u1', 4),  7: ('u1', 4),
}


def attribute(d: dsb.Dsb, c: dict, sem: str):
    """Un attributo di un chunk come array (n, k), letto direttamente dal
    vertex buffer. Fa lo stesso lavoro di Dsb.vertices() ma senza costruire un
    dizionario per vertice: su una mappa intera sono milioni."""
    a = next((a for a in c['decl'] if a['sem'] == sem), None)
    if a is None or a['type_code'] not in NP_TYPE:
        return None
    dt, k = NP_TYPE[a['type_code']]
    n, stride = c['vertex_count'], c['stride']
    raw = np.frombuffer(d.data, dtype=np.uint8, count=n * stride, offset=c['vb'])
    cols = raw.reshape(n, stride)[:, a['off']:a['off'] + a['size']]
    out = np.ascontiguousarray(cols).view(dt).reshape(n, k)
    return out.astype(np.float32) / (255.0 if dt == 'u1' else 1.0)


def indices(d: dsb.Dsb, c: dict) -> np.ndarray:
    """Gli indici del chunk espansi in triangoli. Stessa regola di
    dsb.triangles(): gli strip alternano il verso e usano triangoli degeneri
    per cucire un pezzo al successivo."""
    dt = '>u4' if c['idx_size'] == 4 else '>u2'
    idx = np.frombuffer(d.data, dtype=dt, count=c['index_count'],
                        offset=c['ib']).astype(np.uint32)
    if c['prim'] != 'strip':
        n = (len(idx) // 3) * 3
        return idx[:n].reshape(-1, 3)
    a, b, cc = idx[:-2], idx[1:-1], idx[2:]
    keep = (a != b) & (b != cc) & (a != cc)
    tri = np.stack([a, b, cc], axis=1)
    odd = np.arange(len(a)) % 2 == 1
    tri[odd] = tri[odd][:, [1, 0, 2]]          # il verso si inverte a ogni passo
    return tri[keep]


def skin_bones(d: dsb.Dsb, obj: dict, by_index: dict):
    """Le matrici di un record `skin`, una per osso, gia' pronte a portare un
    vertice dallo spazio di binding al mondo.

        skin +0x20  u32  indice della mesh
             +0x30  u32  numero di ossi
             +0x60  poi n entry da 80 byte: matrice 4x4, indice del nodo
                    dell'osso (u32), 12 byte di riempimento 0xCC

    Che il layout sia questo lo dice il record stesso: 0x60 + n*0x50 da
    **esattamente** la sua dimensione.

    La matrice e' row-major con la traslazione nell'ultima riga (convenzione
    D3D), ed e' la **bind pose inversa**: il prodotto `world(osso) @ M^T` viene
    identico per tutti gli ossi di una skin, che e' proprio la proprieta' che
    definisce la posa di binding. E' anche l'oracolo che ha deciso la
    convenzione: le altre tre combinazioni danno matrici tutte diverse fra
    loro.
    """
    n = struct.unpack_from('>I', d.data, obj['off'] + 0x30)[0]
    out = []
    for k in range(n):
        e = obj['off'] + 0x60 + k * 0x50
        m = np.array(struct.unpack_from('>16f', d.data, e),
                     np.float32).reshape(4, 4)
        idx = struct.unpack_from('>I', d.data, e + 0x40)[0]
        node = by_index.get(idx)
        if node is None:
            return []
        w = np.eye(4, dtype=np.float32)
        w[:3, :] = np.array(d.world(node, by_index), np.float32).reshape(3, 4)
        out.append((w @ m.T)[:3, :])
    return out


class Part:
    """Un pezzo disegnabile: un chunk di geometria gia' portato nello spazio di
    mondo, con la texture che il suo materiale dichiara.

    `lit` dice se il pezzo va **illuminato** o se la sua luce e' gia' nel dato.
    Non e' una preferenza: la geometria di una mappa porta l'illuminazione
    precotta nei colori di vertice (vedi `sky_profile`), i modelli di libreria
    no - e non potrebbero, perche' un vaso istanziato 1.022 volte non puo'
    portare nei propri vertici la luce di 1.022 posti diversi.

    `emis` e' l'emissione del materiale: quanta luce il pezzo **non deve
    ricevere perche' la fa da se'**. La dichiara il disco in 277 materiali su
    1.792, e il caso limite dice come va letta - i 166 della tavolozza del
    `CharEditor` valgono 1 su tutti e tre i canali, cioe' colore pieno e
    nessuna illuminazione.
    """
    __slots__ = ('pos', 'nrm', 'uv', 'col', 'idx', 'tex', 'name', 'lit',
                 'emis')


CELL = 1.6      # una cella logica, che e' anche l'altezza di un personaggio


def dat_for(path: pathlib.Path):
    """La `MAP_ALIGNMENT` di una mappa. `D_1_1_1.ps3.pac.gz` -> `D_1_1_1.DAT`,
    ma i nomi sul disco non concordano sempre nelle maiuscole."""
    stem = path.name.split('.')[0]
    d = path.parent.parent / 'MAP_ALIGNMENT'
    hit = d / f'{stem.upper()}.DAT'
    if hit.exists():
        return hit
    return next((q for q in d.glob('*.DAT')
                 if q.stem.lower() == stem.lower()), None)


def water_parts(dat: pathlib.Path) -> list:
    """La superficie dell'acqua, che il `.pac` non contiene.

    Un fotogramma dell'overworld ha grandi zone nere, e non e' geometria
    mancante: e' il mare. Il gioco lo disegna per conto suo, e infatti la sua
    texture non sta in nessun pacchetto di mappa ma sciolta in
    `data/shaders/water_col.dds` - 128x128, non compressa, un reticolo blu
    notte di **16 quadretti per lato**. Sedici quadretti sono i sedici dot di
    una casella, quindi la texture si posa una volta per cella e il reticolo
    si allinea da solo.

    Dove e a che quota lo dicono la griglia logica e la collisione: vedi
    `walk.Columns.water()` e `water_level()`.
    """
    import walk

    # `data` si ricava dal file stesso - `.../data/map/MAP_ALIGNMENT/X.DAT` -
    # invece che risalendo dalla radice, che non e' sempre la stessa.
    data = dat.parent.parent.parent
    grid = walk.Grid(dat)
    col = walk.columns_for(grid, data)
    if col.empty() or col.bottom is None:
        return []
    lvl = col.water_level()
    ys, xs = np.nonzero(~np.isnan(lvl))
    if not len(xs):
        return []
    x0 = xs * CELL - grid.w * CELL / 2
    z0 = grid.h * CELL / 2 - (ys + 1) * CELL
    y = lvl[ys, xs]
    # Il giro dei quattro angoli e' quello che da' la normale in su; le UV
    # vanno con loro, una copia della texture per cella.
    corner = ((0, 0), (0, 1), (1, 1), (1, 0))
    pos = np.empty((len(xs), 4, 3), np.float32)
    uv = np.empty((len(xs), 4, 2), np.float32)
    for k, (dx, dz) in enumerate(corner):
        pos[:, k, 0] = x0 + dx * CELL
        pos[:, k, 1] = y
        pos[:, k, 2] = z0 + dz * CELL
        uv[:, k] = (dx, dz)
    base = np.arange(len(xs), dtype=np.uint32)[:, None] * 4
    idx = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
    p = Part()
    p.lit, p.emis = 1.0, (0.0, 0.0, 0.0)   # nostra: la illumina il posto
    p.name, p.tex = 'acqua', 'water_col.dds'
    p.pos = pos.reshape(-1, 3)
    p.uv = uv.reshape(-1, 2)
    p.nrm = np.tile(np.array([0, 1, 0], np.float32), (len(xs) * 4, 1))
    p.col = np.ones((len(xs) * 4, 4), np.float32)
    p.idx = idx.astype(np.uint32)
    return [p]


def screens(path: pathlib.Path):
    """Come si compone una mappa: griglia degli schermi e taglia di uno
    schermo, in celle.

    **Una sezione di `.pac` e' uno schermo**, disegnato attorno alla propria
    origine, e la mappa si ottiene mettendo la sezione `(c, r)` al suo posto
    nella griglia. Non era ovvio - e in effetti prima si disegnavano tutte
    sovrapposte, il che per un dungeon a corridoi ripetuti da un'immagine
    plausibile.

    La taglia dello schermo la dichiara la `MAP_ALIGNMENT` corrispondente: il
    rapporto fra la sua griglia logica e quella del container e' un intero,
    16 x 12 celle per i sotterranei e 16 x 16 per l'overworld, mai un numero
    a caso. `d_1_1_1` ha 7 x 8 schermi e una griglia logica 112 x 96.

    Restituisce `None` se la `.DAT` non c'e': senza taglia dichiarata non si
    inventa una composizione.
    """
    try:
        raw = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' \
            else path.read_bytes()
        # Il container e' big-endian come tutto il disco; la MAP_ALIGNMENT no,
        # e' l'unico formato little-endian del gioco. Le due righe qui sotto
        # sono l'unico punto in cui i due mondi si toccano.
        n0, n1 = struct.unpack_from('>2I', raw, 0)
    except Exception:                                            # noqa: BLE001
        return None
    if not n0 or n0 * n1 > 4096:
        return None
    dat = dat_for(path)
    if dat is None:
        return None
    w, h = struct.unpack_from('<2I', dat.read_bytes(), 4)
    # Il rapporto e' intero in quasi tutte le mappe - 16 x 12 nei sotterranei,
    # 16 x 16 nell'overworld - ma non in tutte: `d_20_9` ha 3 schermi per 38
    # celle. Gli schermi restano comunque una divisione in parti uguali, e
    # ammettere il passo frazionario alza la copertura misurata invece di
    # abbassarla, quindi non e' un caso da scartare.
    return n0, n1, w / n0, h / n1, w, h


def load(path: pathlib.Path, sec: int | None = None,
         place: bool = True,
         unfold: bool | float = False) -> tuple[list[Part], dict]:
    """Carica una scena. `unfold` **apre** i widget di interfaccia.

    Le schermate di sistema sono modellate aperte ma esportate **chiuse**: il
    nodo di ogni pezzo ha scala 0 su un asse (`(0,1,1)`, `(1,0,1)`), e ad
    aprirlo e' l'animazione che il descrittore nomina. La mesh sotto e' intera
    - `Confirm_02b` di `SelectA` misura 149x99 - quindi non c'e' niente da
    ricostruire: basta portare a 1 le scale nulle, che e' dove l'animazione
    arriva. Vedi `ui.py`.

    `unfold` e' un **fattore**, non un interruttore: `True` vale 1.0 e apre del
    tutto, ma un valore fra 0 e 1 mette il pezzo a meta' strada. Serve
    all'animazione, che di questo moto ha tutti e due gli estremi sul disco -
    la scala nulla e la mesh intera - e quindi non deve inventarne nessuno.
    """
    grow = float(unfold)
    parts: list[Part] = []
    stat = {'sections': 0, 'meshes': 0, 'tris': 0, 'verts': 0,
            'textures': set(), 'no_uv': 0, 'no_tex': 0, 'skinned': 0,
            'grid': None}
    blocks = dsb.blocks(path)
    # Anche per una mappa a schermo unico la griglia serve: lo spostamento e'
    # nullo, ma `w` e `h` sono l'unico modo di legare le celle degli script
    # alla geometria.
    grid = screens(path) if place else None
    stat['grid'] = grid
    order = range(len(blocks)) if sec is None else [sec]
    for i in order:
        name, blob = blocks[i]
        # Lo spostamento dello schermo, nel sistema della mappa: origine a un
        # angolo, X verso destra, Z **negativa** verso il basso. E' lo stesso
        # sistema in cui parlano gli script (vedi docs/world.md), riportato al
        # centro perche' la geometria del `.pac` e' centrata sullo zero.
        shift = np.zeros(3, np.float32)
        if grid:
            n0, _n1, cw, ch, w, h = grid
            c, r = i % n0, i // n0
            shift = np.array([((c + 0.5) * cw - w / 2) * CELL, 0.0,
                              -((r + 0.5) * ch - h / 2) * CELL], np.float32)
        d = dsb.Dsb(blob, name)
        stat['sections'] += 1
        mats = d.materials()
        geo = {m['name']: m for m in d.meshes()}
        by_index = {n['index']: n for n in d.nodes()}
        if unfold:
            for n in by_index.values():
                n['scale'] = tuple(grow if abs(s) < 1e-6 else s
                                   for s in n['scale'])
        for n in by_index.values():
            if n['attached'] is None:
                continue
            obj = d.object(n['attached'])
            bones = []
            if obj['type'] == 16:
                # Un nodo puo' agganciare uno `skin` invece di una mesh: il
                # record skin porta l'indice della mesh a +0x20. Senza
                # seguirlo si perdono esattamente le 77 mesh skinnate del
                # disco, tutte in Opening.ps3.dsb.
                bones = skin_bones(d, obj, by_index)
                mi = struct.unpack_from('>I', d.data, obj['off'] + 0x20)[0]
                obj = d.object(mi) if mi < d.n_objects else obj
                stat['skinned'] += 1
            mesh = geo.get(obj['name'])
            if mesh is None:
                continue
            w = np.array(d.world(n, by_index), dtype=np.float32).reshape(3, 4)
            rot, trans = w[:, :3], w[:, 3]
            stat['meshes'] += 1
            for c in mesh['chunks']:
                if not c['vertex_count']:
                    continue
                pos = attribute(d, c, 'pos')
                if pos is None:
                    continue
                p = Part()
                p.name = n['name']
                nrm = attribute(d, c, 'nrm')
                if bones:
                    # Skinning: l'indice dell'osso e' la **semantica 9**, un
                    # ubyte4 che compare solo qui - i suoi valori stanno in
                    # 0..n_ossi-1. Nessun vertice del disco porta pesi, quindi
                    # conta il primo indice e basta: e' skinning rigido.
                    m = np.stack(bones)
                    bi = attribute(d, c, 'attr9')
                    k = (np.clip(bi[:, 0] * 255, 0, len(bones) - 1).astype(int)
                         if bi is not None else np.zeros(len(pos), int))
                    r, t = m[k][:, :, :3], m[k][:, :, 3]
                    p.pos = np.einsum('nij,nj->ni', r, pos[:, :3]) + t
                    p.nrm = (np.einsum('nij,nj->ni', r, nrm[:, :3])
                             if nrm is not None else np.zeros_like(p.pos))
                else:
                    p.pos = pos[:, :3] @ rot.T + trans
                    p.nrm = (nrm[:, :3] @ rot.T) if nrm is not None else \
                        np.zeros_like(p.pos)
                uv = attribute(d, c, 'uv')
                if uv is None:
                    stat['no_uv'] += 1
                p.uv = uv[:, :2] if uv is not None else np.zeros((len(pos), 2),
                                                                 np.float32)
                mat = mats.get(c['material'])
                col = np.array(mat['diffuse'] if mat else (1, 1, 1, 1), np.float32)
                vcol = attribute(d, c, 'col')
                p.col = np.tile(col, (len(pos), 1))
                if vcol is not None and vcol.shape[1] == 4:
                    p.col *= vcol
                # La mappa sta in un posto solo, e nei suoi vertici c'e' la
                # luce di quel posto: non va illuminata una seconda volta.
                p.lit = 0.0
                p.emis = mat['emission'] if mat else (0.0, 0.0, 0.0)
                p.tex = mat['textures'][0] if mat else None
                if p.tex:
                    stat['textures'].add(p.tex)
                else:
                    stat['no_tex'] += 1
                p.idx = indices(d, c)
                if grid:
                    p.pos = p.pos + shift
                stat['tris'] += len(p.idx)
                stat['verts'] += len(pos)
                parts.append(p)
    return parts, stat


# ----------------------------------------------------------------- texture

class Texlib:
    """Trova le texture. Ne' i `.pac` ne' i `.dsb` le contengono: stanno in
    pacchetti TPKG a parte, e il riferimento del materiale e' solo un nome di
    file (`floor_01.dds`). Si guarda dove ha senso, in ordine: i pacchetti che
    portano il nome della mappa (`D_1_1_1_0.ps3.tpk` accanto a
    `D_1_1_1.ps3.pac.gz`), poi tutti quelli nella stessa cartella - per i
    personaggi la texture sta nel `character.ps3.tpk` comune - e solo se resta
    qualcosa da risolvere, tutti i 763 del disco."""

    def __init__(self, source: pathlib.Path, root: pathlib.Path):
        self.root = root
        self.index: dict[str, tuple[pathlib.Path, int]] = {}
        self.cache: dict[str, object] = {}
        self.scanned: set[pathlib.Path] = set()
        stem = source.name.split('.')[0].lower()
        for p in sorted(root.rglob('*.tpk')):
            if p.name.lower().startswith((stem + '_', stem + '.')):
                self.scan(p)
        for p in sorted(source.parent.glob('*.tpk')):
            self.scan(p)

    def scan(self, path: pathlib.Path) -> None:
        if path in self.scanned:
            return
        self.scanned.add(path)
        try:
            t = tpk.Tpk(path.read_bytes(), str(path))
        except Exception:                                        # noqa: BLE001
            return
        for i, e in enumerate(t.entries):
            self.index.setdefault(e.name.lower(), (path, i))

    def scan_all(self) -> None:
        for p in sorted(self.root.rglob('*.tpk')):
            self.scan(p)

    def image(self, name: str):
        """L'immagine RGBA di una texture, decodificata da DXT via Pillow."""
        key = name.lower()
        if key in self.cache:
            return self.cache[key]
        if key not in self.index:
            self.scan_all()
        hit = self.index.get(key)
        img = None
        if hit:
            path, i = hit
            t = tpk.Tpk(path.read_bytes(), str(path))
            try:
                img = t.image(t.entries[i]).convert('RGBA')
            except Exception:                                    # noqa: BLE001
                img = None
        if img is None:
            img = self.loose(key)
        self.cache[key] = img
        return img

    def loose(self, name: str):
        """Un `.dds` sciolto sul disco, fuori da ogni pacchetto.

        Ce ne sono due, e non e' un dettaglio di distribuzione: stanno in
        `data/shaders/` perche' non appartengono a nessuna mappa e a nessun
        personaggio: le disegna il motore. `water_col.dds` e' l'acqua,
        `Sun.dds` il sole. Vedi `render.md`.
        """
        import io

        from PIL import Image

        p = next((q for q in self.root.rglob('*.dds')
                  if q.name.lower() == name), None)
        if p is None:
            return None
        d = p.read_bytes()
        if d[:4] != b'DDS ':
            return None
        h, w = struct.unpack_from('<2I', d, 12)
        if d[84:88] == b'\0\0\0\0':
            # non compressa, 32 bit: le maschere dicono ARGB in una parola
            # little-endian, cioe' B G R A byte per byte
            px = np.frombuffer(d, np.uint8, w * h * 4, 128).reshape(h, w, 4)
            return Image.fromarray(px[:, :, [2, 1, 0, 3]].copy(), 'RGBA')
        try:
            return Image.open(io.BytesIO(d)).convert('RGBA')
        except Exception:                                        # noqa: BLE001
            return None


# -------------------------------------------------------------- personaggi

class Charlib:
    """La libreria dei personaggi.

    Sta tutta in un file solo, `Character/c_obj_all.ps3.dsb`: 22 MB, 646 nodi,
    184 radici, e sotto ognuna i fotogrammi di quel personaggio. Le famiglie
    si leggono dal prefisso - `c_npc` (31), `c_enm` (39), `c_ply` (7), `i_evt`
    (30), piu' armi e scudi.

    Estrarre una posa vuol dire prendere il nodo figlio e **buttare via la sua
    traslazione**: nella scena di authoring i fotogrammi stanno in fila
    distanziati di 2,0, ma ognuno e' modellato attorno alla propria origine,
    ai piedi e al centro (i vertici stanno in -0,8..0,8 per 0..1,6). Quindi
    quello che resta e' gia' pronto per essere messo in un punto del mondo.
    """

    LIB = 'Character/c_obj_all.ps3.dsb'

    # Gli **oggetti di mappa** stanno altrove, e non sono personaggi: un vaso
    # non ha pose, e' un nodo solo con la sua mesh. Le librerie sono le
    # quattro di `map/map_model/`, e a dire quale contenga cosa non serve una
    # regola - basta guardarci dentro, perche' i nomi dei nodi sono unici.
    # Vedi nodes.py per chi assegna un modello a una cella.
    MAPLIB = 'map/map_model'
    MAPFAM = ('m_obj_', 'd_hmw_', 'f_hmw_', 'f_ntr_')

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.files: dict[str, tuple] = {}
        self.cache: dict[tuple, list] = {}
        self.missing: set = set()
        self.mapindex: dict[str, str] | None = None

    def _map_lib(self, model: str) -> str | None:
        """In quale libreria di mappa sta un nodo. Indicizza alla prima
        richiesta: i quattro file insieme sono 12 MB, e chi non disegna
        oggetti di mappa non li apre mai."""
        if not model.startswith(self.MAPFAM):
            return None
        if self.mapindex is None:
            self.mapindex = {}
            for p in sorted((self.root / self.MAPLIB).glob('*.dsb')):
                rel = f'{self.MAPLIB}/{p.name}'
                f = self._open(rel)
                if f is None:
                    continue
                for n in f[1]:
                    if n['attached'] is not None:
                        self.mapindex.setdefault(n['name'], rel)
        return self.mapindex.get(model + '-node')

    def _open(self, rel: str):
        if rel not in self.files:
            path = self.root / rel
            if not path.exists():
                self.files[rel] = None
            else:
                name, blob = dsb.blocks(path)[0]
                d = dsb.Dsb(blob, name)
                nodes = list(d.nodes())
                self.files[rel] = (d, nodes, {n['index']: n for n in nodes},
                                   {m['name']: m for m in d.meshes()},
                                   d.materials())
        return self.files[rel]

    def children(self, model: str) -> list:
        """I fotogrammi di un personaggio, in ordine di nome.

        L'ordine conta: `SetNpcNode(nome, n)` sceglie per **ordinale**, e
        l'ordine dei nodi nel file non e' quello dei nomi (`_01`, `_02_b`,
        `_02_a`, `_03`). Ordinare per nome da' la successione che gli autori
        hanno in testa - fermo, primo passo, secondo passo, pose speciali - ed
        e' l'unica che rende `SetNpcNode(x, 1)` una cosa sensata.
        """
        rel = self._map_lib(model)
        if rel is not None:
            # Un oggetto di mappa non ha figli: e' un nodo e basta, e la
            # "posa" e' il nome stesso. Vedi `_build`.
            return [n for n in self._open(rel)[1]
                    if n['name'] == model + '-node']
        f = self._open(self.LIB)
        if f is None:
            return []
        _, nodes, _, _, _ = f
        kids = [n for n in nodes if n['name'].startswith(model + '_')
                and n['attached'] is not None]
        if kids:
            return sorted(kids, key=lambda n: n['name'])
        # Non tutti hanno fotogrammi: i 30 oggetti di evento `i_evt_NN` sono
        # nodi foglia, con la mesh appesa direttamente. Un altare non
        # cammina, e infatti non ha il ciclo di camminata.
        return [n for n in nodes if n['name'] == model + '-node'
                and n['attached'] is not None]

    def parts(self, model: str, pose: str) -> list[Part]:
        """I pezzi disegnabili di una posa, in spazio locale."""
        key = (model, pose)
        if key in self.cache:
            return self.cache[key]
        self.cache[key] = out = self._build(model, pose)
        return out

    def _build(self, model: str, pose: str) -> list[Part]:
        # Un modello puo' essere anche un file suo, quando il disco lo
        # dichiara: `Priest` e' l'unico nome di script che si risolve cosi'.
        rel = self._map_lib(model)
        if rel is not None:
            # Un oggetto di mappa e' **un nodo intero**, non una posa dentro
            # una famiglia: `m_obj_127_01` e' gia' il ciuffo d'erba. La posa
            # che l'entita' chiede si ignora, ed e' giusto - un vaso non
            # cammina.
            d, nodes, by_index, geo, mats = self._open(rel)
            picked = [n for n in nodes if n['name'] == model + '-node']
        elif model.endswith('.dsb'):
            f = self._open(model)
            if f is None:
                self.missing.add(model)
                return []
            d, nodes, by_index, geo, mats = f
            picked = [n for n in nodes if n['attached'] is not None]
        else:
            f = self._open(self.LIB)
            if f is None:
                return []
            d, nodes, by_index, geo, mats = f
            kids = self.children(model)
            if not kids:
                self.missing.add(model)
                return []
            if pose.startswith('#'):
                picked = [kids[min(int(pose[1:]), len(kids) - 1)]]
            else:
                want = f'{model}_{pose}-node'
                picked = [n for n in kids if n['name'] == want] or kids[:1]

        out = []
        for n in picked:
            obj = d.object(n['attached'])
            mesh = geo.get(obj['name'])
            if mesh is None:
                continue
            w = np.array(d.world(n, by_index), np.float32).reshape(3, 4)
            rot = w[:, :3]                 # la traslazione si butta: vedi sopra
            for c in mesh['chunks']:
                if not c['vertex_count']:
                    continue
                pos = attribute(d, c, 'pos')
                if pos is None:
                    continue
                p = Part()
                p.name = n['name']
                p.pos = pos[:, :3] @ rot.T
                nrm = attribute(d, c, 'nrm')
                p.nrm = (nrm[:, :3] @ rot.T) if nrm is not None else \
                    np.zeros_like(p.pos)
                uv = attribute(d, c, 'uv')
                p.uv = uv[:, :2] if uv is not None else \
                    np.zeros((len(pos), 2), np.float32)
                mat = mats.get(c['material'])
                col = np.array(mat['diffuse'] if mat else (1, 1, 1, 1),
                               np.float32)
                vcol = attribute(d, c, 'col')
                p.col = np.tile(col, (len(pos), 1))
                if vcol is not None and vcol.shape[1] == 4:
                    p.col *= vcol
                # Un modello di libreria e' istanziato in posti diversi, e nei
                # suoi vertici c'e' la tinta, non la luce: le sei facce di
                # `c_obj_all` stanno entro il 5% l'una dall'altra. Lo illumina
                # il posto in cui viene messo - tranne per quanto brilla di
                # suo, che le 21 lame magiche dichiarano una per una.
                p.lit = 1.0
                p.emis = mat['emission'] if mat else (0.0, 0.0, 0.0)
                p.tex = mat['textures'][0] if mat else None
                p.idx = indices(d, c)
                out.append(p)
        return out

    def poses(self, model: str) -> list[str]:
        """I suffissi disponibili, utili per sapere cosa un modello sa fare.

        Un oggetto di mappa ne ha una sola e finta (`-`): non e' un
        personaggio, non cammina, e il nodo **e'** l'oggetto.
        """
        if self._map_lib(model) is not None:
            return ['-'] if self.children(model) else []
        return [n['name'][:-5][len(model) + 1:] for n in self.children(model)]


def entity_matrix(e) -> np.ndarray:
    """Dove sta e da che parte guarda, come matrice 4x4 riga-maggiore.

    Rotazione attorno a Y e basta: i personaggi di questo gioco stanno in
    piedi e girano su quattro direzioni. La scala e' 1 perche' il modello e'
    gia' nell'unita' del mondo - alto una casella.
    """
    a = math.radians(e.angle)
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4, dtype=np.float32)
    m[0, 0], m[0, 2] = c, s
    m[2, 0], m[2, 2] = -s, c
    m[:3, 3] = e.pos
    return m


ZERO = np.zeros((4, 4), np.float32)      # niente da disegnare, senza rami


# ------------------------------------------------------------------ matrici

#: I tre cartelli di `data/Balloon`, per texture. L'ordine e' quello del
#: provino a contatto: `a` CHECK, `b` TALK, `c` OPEN.
PROMPTS = {'check': 'c_etc_03a_eng.dds', 'talk': 'c_etc_03b_eng.dds',
           'open': 'c_etc_03c_eng.dds'}


def prompt_parts(root: pathlib.Path, which: str = 'talk'):
    """Il cartello che galleggia sopra la testa: `CHECK`, `TALK`, `OPEN`.

    Non e' interfaccia, e' un oggetto del **mondo**: i tre quadri misurano
    1,6 x 0,6 unita', cioe' larghi una casella come un personaggio e' alto una
    casella. Nel file stanno impilati a y 0,0 / 0,8 / 1,6 per non sovrapporsi,
    quindi ognuno va riportato con il proprio bordo di sotto sull'origine: da
    li' basta metterlo sulla testa di chi parla.

    Che siano per un attore e non per una finestra lo dice l'API, che li crea
    cosi': `CreateBalloon(ActorType)`, 352 chiamate, con `DeleteBalloon` a
    chiuderli.
    """
    want = PROMPTS.get(which)
    p = _data_dir(root) / 'Balloon/balloon_eng.ps3.dsb'
    if want is None or not p.exists():
        return []
    out = []
    for q in load(p, place=False)[0]:
        if not q.tex or q.tex.lower() != want:
            continue
        q.pos = q.pos.copy()
        q.pos[:, 0] -= (q.pos[:, 0].min() + q.pos[:, 0].max()) / 2
        q.pos[:, 1] -= q.pos[:, 1].min()
        out.append(q)
    return out


class Prompt:
    """Un'entita' finta, quel tanto che basta a `EntityGroup`: dove sta, da che
    parte guarda, se si vede. La posizione la prende da chi si ha davanti, e
    l'angolo dalla camera, perche' un cartello si legge sempre di fronte."""

    __slots__ = ('pos', 'angle', 'visible')

    def __init__(self):
        self.pos = np.zeros(3, np.float32)
        self.angle = 0.0
        self.visible = False

    def pose(self):
        return ''


def message_frame(root: pathlib.Path):
    """Il riquadro di dialogo del gioco, nelle **due misure** che il disco
    dichiara, con dentro il posto del testo.

    Non sta in `data/Balloon` come si era scritto: quello e' un altro oggetto -
    tre cartelli `CHECK`/`TALK`/`OPEN` di 1,6x0,6 **unita' di mondo**, cioe'
    larghi una casella, che galleggiano sopra la testa. Il riquadro sta in
    `UserInterface/Message`, ed e' fatto come tutte le finestre di questo
    gioco: tre pezzi, `a` e `c` righe sottili con la scala X a zero e il corpo
    `b` con la scala Y a zero.

    Il descrittore mette il resto e non lascia niente da inventare: `X`/`Y` e
    `LargeX`/`LargeY` sono l'origine del testo, `Space` l'interlinea in piu',
    `Line` quante righe ci stanno. E il font a scala 1 misura 32 px per riga:
    con `Space=8` fa 40 di passo, e tre righe sono 120 in un corpo di 134.
    """
    import ui as ui_mod

    d = ui_mod.descriptor_file(
        _data_dir(root) / 'UserInterface/Message/Message.lua.eu'
    ).get('Message', {})
    out = []
    for keep, kx, ky, ks in ((('MessageBig_',), 'LargeX', 'LargeY',
                              'LargeSpace'),
                             (('Message_',), 'X', 'Y', 'Space')):
        img, x, y = ui_mod.widget('UserInterface/Message/Message', root, keep)
        if img is None:
            continue
        out.append({'img': img, 'x': x, 'y': y,
                    'tx': float(d.get(kx, x)), 'ty': float(d.get(ky, y)),
                    'space': float(d.get(ks, 0.0)),
                    'lines': int(d.get('Line', 3) or 3)})
    return out                                   # [grande, piccolo]


def _data_dir(root: pathlib.Path) -> pathlib.Path:
    return root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root


def message_box(page, width: int, glyphs, frames=None):
    """Compone il riquadro di dialogo con il **font del gioco**.

    Con `frames` la cornice e' quella del disco e sta dove il disco la mette:
    si compone nello schermo virtuale 1280x720, dove il font e' gia' nella sua
    misura, e si porta alla finestra alla fine. Fra le due misure si sceglie la
    piu' piccola in cui il testo ci sta.

    Restituisce `(immagine, x, y)`, l'angolo in alto a sinistra in pixel della
    finestra. Senza `frames` resta la cornice nostra, centrata in basso.
    """
    from PIL import Image, ImageDraw

    lines = [ln for ln in page.lines if ln]
    k = width / 1280.0
    if frames:
        drawn = [glyphs.render(ln, scale=1.0) for ln in lines]
        need = max((r.width for r in drawn), default=0)
        fr = next((f for f in reversed(frames)
                   if f['tx'] - f['x'] + need <= f['img'].width), frames[0])
        box = fr['img'].copy()
        y = fr['ty'] - fr['y']
        for i, img in enumerate(drawn):
            box.alpha_composite(img, (int(fr['tx'] - fr['x']), int(y)))
            # `Space` sta **fra** le righe, non su ognuna, e a dirlo e' un
            # incastro: 485 + 3x32 + 2x8 = 597, e il corpo del riquadro finisce
            # a 598. Sommandolo anche all'ultima si sfora di sette pixel.
            y += img.height + (fr['space'] if i < len(drawn) - 1 else 0)
        if k != 1.0:
            box = box.resize((max(1, int(box.width * k)),
                              max(1, int(box.height * k))), Image.LANCZOS)
        return box, int(fr['x'] * k), int(fr['y'] * k)

    scale = max(k, 1.0) * 1.4
    rendered = [glyphs.render(ln, scale=scale) for ln in lines]
    pad = int(18 * scale)
    w = min(int(width * 0.86), max((r.width for r in rendered), default=0)
            + 2 * pad)
    h = sum(r.height for r in rendered) + 2 * pad
    box = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    r = int(10 * scale)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=(18, 22, 40, 225),
                        outline=(226, 226, 236, 255), width=max(int(2 * scale), 2))
    y = pad
    for img in rendered:
        box.alpha_composite(img, (pad, y))
        y += img.height
    return box, (width - w) // 2, None


# Le due etichette non stanno in nessuno script di evento: `Event:Select()` non
# prende argomenti. Sono pero' dichiarate identiche nei 16 descrittori UI che
# hanno una scelta (`ClearSave`, `Continue`, `GameOver`...), cursore a sinistra
# e ＹＥＳ sopra ＮＯ. Le prendiamo da li'.
CHOICES = ('ＹＥＳ', 'ＮＯ')


def crop_frame(img):
    """`SelectB.ps3.tpk` contiene il riquadro **e** la punta del cursore, come
    due disegni separati sulla stessa texture. Stirare tutto porta la punta
    dove non deve stare: si taglia alla prima colonna vuota dopo il riquadro,
    che e' lo spazio che gli autori hanno lasciato fra i due."""
    import numpy as _np

    a = _np.array(img)[:, :, 3]
    cols = a.sum(axis=0) > 0
    rows = a.sum(axis=1) > 0
    if not cols.any():
        return img
    first = int(_np.argmax(cols))
    gap = first
    while gap < len(cols) and cols[gap]:
        gap += 1
    top = int(_np.argmax(rows))
    bottom = len(rows) - int(_np.argmax(rows[::-1]))
    return img.crop((first, top, gap, bottom))


def choice_box(selected: int, width: int, glyphs, frame=None):
    """Il riquadro di scelta. La cornice, quando c'e', e' quella del gioco:
    `UserInterface/Select/SelectB`, che e' un rettangolo con la punta del
    cursore gia' disegnata."""
    from PIL import Image, ImageDraw

    scale = max(width / 1280.0, 1.0) * 1.4
    labels = [glyphs.render(c, scale=scale) for c in CHOICES]
    pad = int(16 * scale)
    cur = int(20 * scale)
    w = max(i.width for i in labels) + 2 * pad + cur
    h = sum(i.height for i in labels) + 2 * pad
    box = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if frame is not None:
        box.alpha_composite(frame.resize((w, h), Image.LANCZOS))
    else:
        ImageDraw.Draw(box).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius=int(10 * scale), fill=(18, 22, 40, 225),
            outline=(226, 226, 236, 255), width=max(int(2 * scale), 2))
    y = pad
    d = ImageDraw.Draw(box)
    for i, img in enumerate(labels):
        box.alpha_composite(img, (pad + cur, y))
        if i == selected:
            m = y + img.height // 2
            d.polygon([(pad, m - cur // 3), (pad, m + cur // 3),
                       (pad + cur * 2 // 3, m)], fill=(255, 255, 255, 255))
        y += img.height
    return box


# Il profilo del cielo delle 40 mappe di campagna, in mediana: serve quando in
# scena non c'e' una mappa (il palco di `event`, `char`) e quindi non c'e'
# niente da cui leggerlo.
SKY_FIELD = (1.41, 1.0, 0.66)

# Il sole, con i numeri delle chiamate che il disco fa. `SetSunLightAngle` ha
# **8 valori distinti** in 16 chiamate, e gli autori hanno lasciato scritto
# cosa sono: `Event:SetSunLightAngle(5.65,62.59);  -- yaw, pitch`. I pitch
# stanno tutti fra 57,75 e 86 gradi - il sole di questo gioco e' sempre alto -
# e la mediana e' 73,5; gli yaw sono sparsi (da -180 a 31), cioe' l'azimut e'
# della scena e non del mondo, e qui si prende il piu' frequente.
#
# `AMBIENT` e' la frazione di luce che arriva senza direzione. Anche questa e'
# del disco: le tre `SetParallelLight`/`StartParallelLightAnime` portano due
# terne, la prima sempre piu' chiara della seconda - diffusa e ambiente - e il
# rapporto `amb/(amb+dif)` vale 0,29, 0,35 e 0,43 per componente. Mediana 0,35.
SUN_YAW, SUN_PITCH = 5.65, 73.5
AMBIENT = 0.35
SUN_DIR = (math.sin(math.radians(SUN_YAW)) * math.cos(math.radians(SUN_PITCH)),
           math.sin(math.radians(SUN_PITCH)),
           math.cos(math.radians(SUN_YAW)) * math.cos(math.radians(SUN_PITCH)))

# Sopra quanta variazione il colore di vertice di una mappa **e'** la sua
# illuminazione. Non e' una soglia scelta a occhio: le mappe si dividono in due
# gruppi, uno sotto il 25% e uno sopra il 35%, e la stessa divisione la fa una
# misura che non sa niente di questa - se la faccia in su e' piu' chiara dei
# fianchi, cioe' se la mappa vede il cielo. Le due concordano su **159 mappe su
# 166**, e le 7 che restano stanno tutte a ridosso del confine (su/fianchi fra
# 0,96 e 0,99, ricchezza fra il 29 e il 41%).
RICH = 0.30


def sky_profile(parts: list[Part], sides_min: int = 400):
    """Quanto cielo vede questa mappa, letto dai suoi colori di vertice.

    L'illuminazione di una mappa non e' dichiarata da nessuna parte - i 167
    `.pac` non contengono **nessun** record `light`, e le 400 luci del disco
    sono una per file, si chiamano tutte `ambient-environment-light` e portano
    i valori di partenza dell'esportatore (cono a 40 gradi, decadimento
    infinito). Ma non serve, perche' e' gia' cotta nei vertici, e in un mondo
    di cubi si rilegge: le normali sono sei, quindi basta raggruppare i colori
    per faccia.

    Quel che ne viene non e' una lambertiana ma una **luce d'ambiente
    verticale**: i quattro fianchi concordano entro il 2,8% (mediana delle 40
    mappe di campagna), cioe' nessuna direzione orizzontale e' privilegiata,
    mentre in su e in giu' sono diversi. E il verso si **inverte** fra aperto e
    chiuso - in campagna la faccia in su e' 1,41 volte i fianchi, al chiuso
    0,82 - che e' quel che ci si aspetta se quel numero e' luce che scende dal
    cielo: dove c'e' un soffitto, sparisce.

    Restituisce `(su, fianchi, giu, ricchezza)` con i fianchi a 1: il
    **rapporto**, non il livello. Il livello no, e per una ragione misurata:
    dove il colore di vertice e' una tinta e non una luce - `d_1_1_1` ne ha due
    soli, verdi - prenderlo vorrebbe dire tingere di verde anche chi ci cammina
    dentro.

    La `ricchezza` e' quanto il colore varia **dentro** una stessa direzione di
    faccia, dove quindi non c'e' il cielo a spiegarla: e' l'occlusione cotta
    vertice per vertice. Dice se questa mappa la propria luce ce l'ha davvero
    (campagna: 42%) o se porta solo due livelli (chiuso: 3%). Vedi `RICH`.
    """
    acc, side_lum = {}, []
    for p in parts:
        if getattr(p, 'lit', 1.0) or len(p.nrm) != len(p.col):
            continue
        n = p.nrm[:, :3]
        a = np.abs(n)
        ok = (a.max(1) > 0.99) & (a.sum(1) < 1.01)
        if not ok.any():
            continue
        lum = (p.col[:, :3] * (0.2126, 0.7152, 0.0722)).sum(1)
        key = np.round(n).astype(np.int8)
        for k in np.unique(key[ok], axis=0):
            sel = ok & (key == k).all(1)
            t = tuple(int(v) for v in k)
            s, c = acc.get(t, (0.0, 0))
            acc[t] = (s + float(lum[sel].sum()), c + int(sel.sum()))
            if t[1] == 0:
                side_lum.append(lum[sel])

    def mean(*keys):
        s = sum(acc[k][0] for k in keys if k in acc)
        c = sum(acc[k][1] for k in keys if k in acc)
        return (s / c, c) if c else (None, 0)

    side, n_side = mean((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))
    if side is None or n_side < sides_min or side < 1e-3:
        return SKY_FIELD + (0.0,)
    v = np.concatenate(side_lum)
    up, n_up = mean((0, 1, 0))
    down, _ = mean((0, -1, 0))
    return (up / side if n_up else 1.0, 1.0,
            down / side if down is not None else 1.0,
            float(v.std() / max(v.mean(), 1e-6)))


def bounds(parts: list[Part]):
    """Il parallelepipedo che contiene la scena.

    Per pezzo e poi fra i pezzi: concatenare i vertici di una mappa intera
    vuol dire 54 milioni di righe copiate per ottenere sei numeri."""
    lo = np.min([p.pos.min(axis=0) for p in parts], axis=0)
    hi = np.max([p.pos.max(axis=0) for p in parts], axis=0)
    return lo, hi


def perspective(fov: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov) / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def look_at(eye, target, up=(0, 1, 0)) -> np.ndarray:
    eye, target = np.array(eye, np.float32), np.array(target, np.float32)
    f = target - eye
    f /= np.linalg.norm(f) or 1
    s = np.cross(f, np.array(up, np.float32))
    s /= np.linalg.norm(s) or 1
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


# La mappa ha le trasformazioni gia' cotte nei vertici: e' geometria che non
# si muove, e cuocerla e' cio' che rende possibile disegnare 54 milioni di
# vertici. Le entita' no: si spostano a ogni fotogramma, e ricostruire il
# buffer a ogni passo sarebbe assurdo. Da qui la matrice `model`, che per la
# mappa e' l'identita' e per un personaggio e' dove sta e da che parte guarda.
VERT = """#version 330 core
in vec3 position;
in vec3 normal;
in vec2 uv;
in vec4 color;
in float lit;
in vec3 emis;
uniform mat4 mvp;
uniform mat4 model;
out vec3 v_nrm;
out vec3 v_pos;
out vec2 v_uv;
out vec4 v_col;
out float v_lit;
out vec3 v_emis;
void main() {
    vec4 world = model * vec4(position, 1.0);
    gl_Position = mvp * world;
    v_nrm = mat3(model) * normal;
    v_pos = world.xyz;
    v_uv = uv;
    v_col = color;
    v_lit = lit;
    v_emis = emis;
}
"""

# Il taglio in altezza (`cut`) non e' un effetto: e' l'unico modo di guardare
# dentro una mappa di questo gioco. I sotterranei hanno il soffitto - dall'alto
# sono una lastra - e chi ci cammina dentro, senza taglio, non lo vede
# nessuno.
# La luce non si aggiunge a chi ce l'ha gia'. `v_lit` vale 0 su cio' che porta
# la propria illuminazione nei colori di vertice - la geometria di una mappa di
# campagna - e 1 su tutto il resto: i modelli di libreria, che non potrebbero
# portarla (un vaso istanziato 1.022 volte non ha nei vertici la luce di 1.022
# posti), e le mappe il cui precotto e' troppo povero per essere luce.
#
# Chi va illuminato riceve **ambiente piu' sole**, che e' la forma che il disco
# dichiara con `SetParallelLight` (due terne, diffusa e ambiente) e
# `SetSunLightAngle` (yaw e pitch, con il commento degli autori accanto). Le
# proporzioni sono quelle: `AMBIENT` 0,35 dal rapporto fra le due terne, il
# sole alto dai pitch. E l'ambiente non e' piatto ma segue `sky`, il profilo
# verticale che la mappa stessa mostra nei propri vertici - cosi' chi cammina
# in una grotta prende la luce della grotta.
#
# Quel che e' sparito e' una **direzione orizzontale** che il dato non ha: la
# vecchia lambertiana veniva da (0,4, 0,8, 0,45), cioe' 42 gradi di azimut, e
# spegneva a 0,35 i due fianchi che le davano le spalle. Nel precotto della
# campagna i quattro fianchi concordano invece entro il 2,8%.
FRAG = """#version 330 core
in vec3 v_nrm;
in vec3 v_pos;
in vec2 v_uv;
in vec4 v_col;
in float v_lit;
in vec3 v_emis;
uniform sampler2D tex;
uniform vec3 sky;               // (su, fianchi, giu), fianchi a 1
uniform vec3 sun;               // direzione, da yaw e pitch del disco
uniform float ambient;
uniform int use_tex;
uniform int use_light;
uniform float cut;
out vec4 frag;
void main() {
    if (v_pos.y > cut) discard;
    vec4 base = v_col;
    if (use_tex == 1) base *= texture(tex, v_uv);
    if (base.a < 0.35) discard;          // l'alfa esplicita del DXT3 e' netta
    float d = 1.0;
    if (use_light == 1 && v_lit > 0.5) {
        vec3 n = normalize(v_nrm);
        float y = clamp(n.y, -1.0, 1.0);
        float amb = y >= 0.0 ? mix(sky.y, sky.x, y) : mix(sky.y, sky.z, -y);
        d = ambient * amb + (1.0 - ambient) * max(dot(n, sun), 0.0);
    }
    // L'emissione e' un **pavimento**, non un addendo: cosi' il caso limite
    // torna da solo - un materiale che emette 1 su tutti e tre i canali e' a
    // colore pieno e non illuminato, che e' quel che la tavolozza del
    // `CharEditor` vuole dire - e niente satura mai a bianco.
    frag = vec4(base.rgb * max(vec3(d), v_emis), 1.0);
}
"""

NO_CUT = 1e9        # niente soffitto da togliere: si disegna tutto


def start_event(args: dict, root: pathlib.Path):
    """Avvia uno script di evento del gioco sull'host Lua, e carica il font
    dell'interfaccia. Entrambi arrivano dal disco: nessuno dei due e' una
    nostra imitazione."""
    import font as font_mod
    import host as host_mod

    script = pathlib.Path(args['event'])
    data = script
    while data.name and data.name != 'data':
        data = data.parent
    evt = host_mod.Host(data, verbose=True)
    # Le librerie condivise, che `host.py coverage` carica da sempre e che qui
    # mancavano: senza `eventfunction.lua.eu` gli helper che gli eventi
    # chiamano - `setnpccamerac`, `seafterboss` - diventano stub muti, e meta'
    # delle inquadrature non succede.
    evt.load_libs()
    evt.load(script)
    _, func = host_mod.resolve(script)
    evt.start(args['func'] or func)
    glyphs = font_mod.Font(data / 'UserInterface/Font/Font.lua.eu')
    # La griglia logica della mappa: da qui l'host sa tradurre le celle di
    # `SetPlayerPosition` e i punti assoluti di `SetCamera` nel riferimento in
    # cui la geometria e' caricata, e sa dove la mappa tiene i propri NPC.
    dat = args.get('dat')
    if dat is not None:
        n = evt.load_map(dat)
        print(f'  {n} posti di NPC dichiarati da {dat.name}')
    elif args.get('grid'):
        evt.map = (args['grid'][4], args['grid'][5])
    # Il giocatore da qualche parte deve pur stare, e sul disco non c'e'
    # scritto dove: il punto d'ingresso di una mappa lo decide il codice, non
    # il dato, e `SetPlayerPosition` parla in celle di una griglia il cui
    # ancoraggio al mondo non e' ancora risolto (vedi `host._player_pos`).
    #
    # Conta piu' di quanto sembri, perche' `CreateNpc` mette gli NPC
    # **relativi al giocatore**: sbagliare qui li sposta tutti insieme. Il
    # centro della scena e' un ripiego che spesso cade dentro un muro - le
    # mappe di questo gioco sono piene e hanno anche il soffitto - quindi
    # `--at` esiste apposta per dirlo a mano.
    lo, hi = args['bounds']
    evt.world.player.pos = args['at'] or [float((lo[0] + hi[0]) / 2),
                                          float(lo[1]),
                                          float((lo[2] + hi[2]) / 2)]
    return evt, glyphs


def run(parts: list[Part], texlib: Texlib, args: dict) -> int:
    import pyglet
    from pyglet.gl import (GL_DEPTH_TEST, GL_CULL_FACE, GL_TRIANGLES, GL_BACK,
                           GL_TEXTURE_2D, GL_TEXTURE0, GL_LINEAR,
                           GL_LINEAR_MIPMAP_LINEAR, GL_REPEAT,
                           GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
                           GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T,
                           glEnable, glDisable, glCullFace, glClearColor,
                           glActiveTexture, glBindTexture, glTexParameteri,
                           glGenerateMipmap)
    from pyglet.graphics.shader import Shader, ShaderProgram
    from pyglet.math import Mat4

    w, h = args['size']
    config = pyglet.gl.Config(double_buffer=True, depth_size=24,
                              major_version=3, minor_version=3,
                              forward_compatible=True, sample_buffers=1, samples=4)
    win = pyglet.window.Window(width=w, height=h, config=config,
                               resizable=True, visible=not args['shot'],
                               caption=f'PC-3Ddot - {args["title"]}')
    program = ShaderProgram(Shader(VERT, 'vertex'), Shader(FRAG, 'fragment'))
    evt, glyphs = args['event_state'] if args['event_state'] else (None, None)
    session = args.get('session')       # la partita, quando si sta giocando
    # Tutto cio' che cambia quando cambia mappa. Sta in un dizionario e non in
    # variabili perche' `play` lo rifa' da capo a ogni passaggio, e le funzioni
    # di disegno devono vedere quello nuovo senza essere ricostruite.
    scene = {'batch': pyglet.graphics.Batch(), 'groups': {}, 'sky': SKY_FIELD,
             'texlib': texlib, 'lo': None, 'hi': None, 'center': None,
             'radius': 1.0}

    def upload(img):
        if img is None:
            return None
        data = img.tobytes()
        tex = pyglet.image.ImageData(img.width, img.height, 'RGBA', data,
                                     pitch=-img.width * 4).get_texture()
        glBindTexture(GL_TEXTURE_2D, tex.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                        GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D)
        return tex

    IDENTITY = Mat4()

    class TexGroup(pyglet.graphics.Group):
        def __init__(self, tex, order=0):
            super().__init__(order)
            self.tex = tex

        def set_state(self):
            program.use()
            program['model'] = IDENTITY
            program['cut'] = state['cut']
            program['use_tex'] = 1 if (self.tex and state['tex']) else 0
            if self.tex:
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.tex.id)

        def __hash__(self):
            return hash(self.tex.id if self.tex else 0)

        def __eq__(self, other):
            return (isinstance(other, TexGroup) and
                    (self.tex.id if self.tex else 0) ==
                    (other.tex.id if other.tex else 0))

    class EntityGroup(TexGroup):
        """Un'entita' in una posa. La matrice si legge dal registro al momento
        del disegno, quindi il movimento non costa niente: nessun buffer da
        ricostruire, solo quattro righe di uniform.

        La posa sbagliata e l'entita' nascosta si spengono con una matrice
        nulla invece che con un ramo: i triangoli collassano in un punto e il
        rasterizzatore li butta. Costa meno che togliere e rimettere una lista
        di vertici dal batch a ogni fotogramma."""

        def __init__(self, tex, ent, pose):
            super().__init__(tex, order=1)
            self.ent, self.pose = ent, pose

        def set_state(self):
            super().set_state()
            live = self.ent.visible and self.ent.pose() == self.pose
            m = entity_matrix(self.ent) if live else ZERO
            program['model'] = Mat4(*m.T.ravel().tolist())

        def __hash__(self):
            return hash((self.tex.id if self.tex else 0, id(self.ent),
                         self.pose))

        def __eq__(self, other):
            return (isinstance(other, EntityGroup) and other.ent is self.ent
                    and other.pose == self.pose and
                    (self.tex.id if self.tex else 0) ==
                    (other.tex.id if other.tex else 0))

    # Il colore per vertice **e'** l'illuminazione, dove la mappa ce l'ha: si
    # accende con `L`, ma cio' che si accende non e' una luce sopra tutto -
    # e' la luce data a chi non ce l'ha nel proprio dato. Vedi `sky_profile`.
    state = {'tex': True, 'light': args['light'], 'cull': False,
             'cut': NO_CUT, 'roof': args.get('roof')}

    cam = {'yaw': math.radians(args['azim']), 'pitch': math.radians(args['elev']),
           'dist': 1.0, 'target': np.zeros(3, np.float32), 'speed': 1.0,
           'driven': False, 'keep': {}}
    built: set = set()

    def set_scene(parts, texlib, bounds_=None, camera: bool = True):
        """Costruisce (o ricostruisce) tutto quello che si disegna.

        Cambiare mappa vuol dire buttare via il batch e rifarlo: le texture
        sono altre, la geometria e' altra, e le liste di vertici delle entita'
        appartenevano agli abitanti di prima."""
        t0 = time.time()
        scene['batch'] = pyglet.graphics.Batch()
        scene['groups'] = {}
        scene['texlib'] = texlib
        built.clear()
        missing = set()
        # Chi porta la propria luce e chi no, deciso da questa mappa e non da
        # una regola: dove il precotto e' povero - i sotterranei ne hanno due
        # livelli - la geometria torna fra quelli da illuminare, o le pareti
        # diventano una massa sola.
        up, _s, down, rich = sky_profile(parts)
        scene['sky'] = (up, 1.0, down)
        if rich < RICH:
            for p in parts:
                p.lit = 1.0
        print(f'  luce: cielo {up:.2f}/1/{down:.2f}, precotto {rich * 100:.0f}%'
              + ('  (la mappa porta la propria)' if rich >= RICH
                 else '  (la mette il renderer)'))
        # una sola texture per gruppo: i pezzi che la condividono finiscono
        # nella stessa chiamata di disegno
        for p in parts:
            if p.tex and p.tex not in scene['groups']:
                img = texlib.image(p.tex)
                if img is None:
                    missing.add(p.tex)
                scene['groups'][p.tex] = TexGroup(upload(img))
        plain = TexGroup(None)
        for p in parts:
            # `lit` sta nel vertice e non in una uniform perche' il batch e'
            # uno solo: mappa e personaggi finiscono nella stessa draw call.
            program.vertex_list_indexed(
                len(p.pos), GL_TRIANGLES, p.idx.ravel().tolist(),
                scene['batch'], scene['groups'].get(p.tex, plain),
                position=('f', p.pos.ravel()), normal=('f', p.nrm.ravel()),
                uv=('f', p.uv.ravel()), color=('f', p.col.ravel()),
                lit=('f', np.full(len(p.pos), getattr(p, 'lit', 1.0),
                                  np.float32)),
                emis=('f', np.tile(np.asarray(getattr(p, 'emis', (0, 0, 0)),
                                              np.float32)[:3], len(p.pos))))
        print(f'  {len(scene["groups"])} texture caricate in '
              f'{time.time() - t0:.1f}s'
              + (f', {len(missing)} non trovate: {sorted(missing)[:4]}'
                 if missing else ''))
        lo, hi = bounds_ if bounds_ is not None else bounds(parts)
        scene['lo'], scene['hi'] = lo, hi
        scene['center'] = (lo + hi) / 2
        scene['radius'] = float(np.linalg.norm(hi - lo)) / 2 or 1.0
        if camera:
            # inquadratura: al centro della scena, indietro quanto basta a
            # contenerla
            cam['dist'] = scene['radius'] * args['dist']
            cam['target'] = scene['center'].copy()
            cam['speed'] = scene['radius'] / 12

    set_scene(parts, texlib, args['bounds'], camera=not session)
    # Se un evento ha messo qualcuno in scena, e' lui il soggetto: inquadrare
    # la mappa intera vuol dire non vedere i personaggi, che sono alti una
    # casella su venti unita' di mappa.
    if session is not None:
        # Giocando, l'inquadratura non dipende dalla scena ma dal personaggio:
        # sempre la stessa distanza, mappa piccola o grande che sia.
        cam['dist'] = 11.0 * args['dist']
        cam['speed'] = 0.0
    elif evt and evt.world.npcs:
        who = np.array([e.pos for e in evt.world.visible_entities()], np.float32)
        cam['target'] = who.mean(axis=0) + (0, 0.8, 0)
        # Abbastanza indietro da vedere i personaggi *e* dove stanno: le
        # camere del disco stanno fra 4 e 14 unita' da un primo piano, e
        # sotto le quattro non ci si sta.
        spread = float(np.linalg.norm(who.max(0) - who.min(0)))
        cam['dist'] = max(spread * 1.5, 6.0) * args['dist']
        cam['speed'] = 0.5

    def eye():
        cy, sy = math.cos(cam['yaw']), math.sin(cam['yaw'])
        cp, sp = math.cos(cam['pitch']), math.sin(cam['pitch'])
        d = np.array([cp * sy, sp, cp * cy], np.float32)
        return cam['target'] + d * cam['dist'], d

    glEnable(GL_DEPTH_TEST)
    glClearColor(0.08, 0.09, 0.11, 1.0)
    keys = pyglet.window.key.KeyStateHandler()
    win.push_handlers(keys)

    chain = post.Post(win.width, win.height) if args['post'] else None
    if chain:
        chain.params['aperture'] = args['aperture']

    # --- interfaccia dell'evento: riquadro di messaggio e riquadro di scelta
    ui = {'batch': pyglet.graphics.Batch(), 'sprites': [], 'key': None,
          'frame': None}
    if evt:
        sel = texlib.image('selectb.dds')
        ui['frame'] = crop_frame(sel) if sel is not None else None
        try:
            ui['msg'] = message_frame(pathlib.Path(args['root']))
        except Exception:                                        # noqa: BLE001
            ui['msg'] = None

    def sprite_for(img, x, y):
        data = pyglet.image.ImageData(img.width, img.height, 'RGBA',
                                      img.tobytes(), pitch=-img.width * 4)
        return pyglet.sprite.Sprite(data, x=x, y=y, batch=ui['batch'])

    def event_ui():
        """Ricompone l'interfaccia solo quando cambia qualcosa: comporre il
        testo con PIL e caricarlo come texture costa troppo per farlo a ogni
        fotogramma."""
        page = evt.pages[evt.page] if evt and evt.pages else None
        key = (id(page), evt.page if evt else 0, win.width,
               evt.choosing if evt else False, evt.choice if evt else 0,
               ui.get('map') is not None)
        if key == ui['key']:
            return ui['sprites']
        ui['key'] = key
        ui['sprites'] = []
        if ui.get('map') is not None:
            m = ui['map']
            if m.width != win.width:
                m = m.resize((win.width, int(m.height * win.width / m.width)))
            ui['sprites'].append(sprite_for(
                m, 0, (win.height - m.height) // 2))
            return ui['sprites']
        if page is not None:
            img, x, y = message_box(page, win.width, glyphs, ui.get('msg'))
            # Il disco colloca il riquadro in uno schermo 1280x720 con la Y in
            # giu'; pyglet ha l'origine in basso, quindi si rovescia. Senza la
            # cornice del gioco resta la nostra, in basso al centro.
            sy = int(win.height * 0.04) if y is None else \
                win.height - y - img.height
            ui['sprites'].append(sprite_for(img, x, sy))
        if evt and evt.choosing:
            img = choice_box(evt.choice, win.width, glyphs, ui['frame'])
            ui['sprites'].append(sprite_for(
                img, win.width - img.width - int(win.width * 0.06),
                int(win.height * 0.30)))
        return ui['sprites']

    # --- le entita'
    #
    # Non esistono prima che l'evento le crei: `CreateNpc` puo' arrivare al
    # decimo secondo. Quindi le liste di vertici si costruiscono quando
    # servono, una per (entita', posa), e restano nel batch - una posa ne
    # occupa qualche centinaio di vertici, e un evento ne mette in scena
    # meno di dieci.
    charlib = Charlib(evt.root) if evt else None
    world = evt.world if evt else (session.world if session else None)

    def sync_entities():
        if charlib is None or world is None:
            return
        for e in world.visible_entities():
            pose = e.pose()
            key = (id(e), pose)
            if key in built:
                continue
            built.add(key)
            pieces = charlib.parts(e.model, pose)
            if not pieces:
                continue
            groups = scene['groups']
            for p in pieces:
                if p.tex and p.tex not in groups:
                    groups[p.tex] = TexGroup(upload(scene['texlib'].image(p.tex)))
                tex = groups[p.tex].tex if p.tex in groups else None
                program.vertex_list_indexed(
                    len(p.pos), GL_TRIANGLES, p.idx.ravel().tolist(),
                    scene['batch'], EntityGroup(tex, e, pose),
                    position=('f', p.pos.ravel()), normal=('f', p.nrm.ravel()),
                    uv=('f', p.uv.ravel()), color=('f', p.col.ravel()),
                    lit=('f', np.full(len(p.pos), getattr(p, 'lit', 1.0),
                                      np.float32)),
                    emis=('f', np.tile(np.asarray(
                        getattr(p, 'emis', (0, 0, 0)), np.float32)[:3],
                        len(p.pos))))

    # Il cartello «qui puoi parlare»: una sola geometria, agganciata a
    # un'entita' finta che ogni fotogramma prende il posto di chi si ha
    # davanti. Sta nel batch dall'inizio e si spegne con `visible`, che
    # `EntityGroup` traduce in una matrice nulla.
    prompt = Prompt()
    if session is not None:
        for p in prompt_parts(pathlib.Path(args.get('root') or '../extract')):
            tex = upload(scene['texlib'].image(p.tex))
            program.vertex_list_indexed(
                len(p.pos), GL_TRIANGLES, p.idx.ravel().tolist(),
                scene['batch'], EntityGroup(tex, prompt, ''),
                position=('f', p.pos.ravel()), normal=('f', p.nrm.ravel()),
                uv=('f', p.uv.ravel()), color=('f', p.col.ravel()),
                # il cartello e' interfaccia, non mondo: sta sopra la testa e
                # dev'essere leggibile anche in una grotta
                lit=('f', np.zeros(len(p.pos), np.float32)),
                emis=('f', np.zeros(len(p.pos) * 3, np.float32)))

    def floor_map(page=None):
        """La mappa di un piano, se questa mappa e' un piano di sotterraneo.

        Le stanze accese sono **tutte quelle che la griglia dichiara**: dove
        una stanza cominci e finisca il disco non lo dice - i marcatori sono
        radi e il marcatore piu vicino azzecca solo il 76% - quindi qui non si
        indovina una stanza corrente, si fa vedere il piano intero.

        `page` e' il piano da guardare, **col segno**: `B1` e' -1 e `1F` e' 0,
        che e' come il descrittore li numera (`setting = {pageMin, pageMax}`).
        Senza, si guarda il piano su cui si sta. Cambiare piano cambia
        descrittore e cambia griglia, perche' le stanze viste sono quelle di
        quel piano - e la successione dei file non e' quella dei piani: il
        sotterraneo 5 li tiene nell'ordine `1F`, `2F`, `B1`.
        """
        import ui as ui_mod
        import walk as walk_mod

        m = walk_mod.FLOOR_IN_NAME.match(session.grid.name)
        if not m:
            print('  questa mappa non e un piano di sotterraneo')
            return None
        dungeon, seq = int(m.group(1)), int(m.group(2))
        root_ = pathlib.Path(args['root'])
        piani = ui_mod.dungeon_floors(dungeon, root_)
        qui = next((f for f in piani if f['seq'] == seq), None)
        f = next((x for x in piani if x['page'] == page), None) if \
            page is not None else qui
        if f is None:
            return None
        ui['piano'] = f
        ui['piani'] = piani
        g = session.grid if f['seq'] == seq else \
            session.atlas.grid(f'd_{dungeon}_1_{f["seq"]}')
        img = ui_mod.dungeon_map(dungeon, f['seq'], root_,
                                 seen=sorted(g.rooms) if g else ())
        if img is not None:
            print(f'  piano {f["label"]}'
                  + ('' if f is qui else f' (si sta a {qui["label"]})'
                     if qui else ''))
        return img

    def sync_prompt():
        """Sopra la testa di chi si ha davanti, e solo se ha qualcosa da dire:
        il cartello e' un invito a premere, non una decorazione."""
        who = session.facing_npc() if session is not None else None
        prompt.visible = who is not None and bool(getattr(who, 'script', None))
        if prompt.visible:
            prompt.pos = np.array(who.pos, np.float32) + (0.0, CELL * 1.1, 0.0)
            prompt.angle = math.degrees(cam['yaw'])

    if session is not None and args.get('map'):
        ui['map'] = floor_map()

    @win.event
    def on_draw():
        sync_entities()
        if session is not None and not (evt and evt.pages):
            sync_prompt()
        elif session is not None:
            prompt.visible = False
        # Se un evento sta pilotando la camera, comanda lui. `dist` è in unità
        # di mondo (4-14 nelle chiamate del disco: sono primi piani su un
        # personaggio), quindi va presa così com'è, non scalata sul raggio
        # della scena.
        # Un evento pilota la camera solo se il suo bersaglio esiste per noi.
        #
        # `SetCameraAtBody` nomina un'entita', e se quella e' collocata basta
        # e avanza. `SetCamera` a sei argomenti invece porta un punto nel
        # sistema di riferimento **globale** del gioco - x fino a 158, z fino
        # a -203, distanze di 40 e 50 unita' - mentre un `.pac` si carica
        # centrato sullo zero e misura una ventina di unita' in tutto. Preso
        # alla lettera manda la camera a fissare il vuoto, ed e' esattamente
        # quello che faceva: fotogrammi neri.
        #
        # Quindi o il punto cade **dentro** la scena caricata, e ci si crede,
        # o si scarta l'inquadratura intera - distanza compresa, perche' una
        # distanza di 40 metri appartiene a quello stesso mondo che non
        # abbiamo. Meglio la vista del visualizzatore che una finta.
        take = None
        # Giocando, l'evento comanda la camera solo mentre parla: e' il suo
        # momento, ed e' anche il solo in cui il giocatore non si muove.
        if evt and evt.camera['dist'] > 0 and (session is None or busy()):
            body = evt.world.get(evt.camera.get('body'))
            if body is not None and body.created:
                take = np.array([body.pos[0], body.pos[1] + 0.8, body.pos[2]],
                                np.float32)
            elif evt.camera['target'] is not None:
                t = np.array(evt.camera['target'], np.float32)
                if (np.all(t >= scene['lo'])
                        and np.all(t <= scene['hi'])):
                    take = t
        if take is not None:
            cam['yaw'] = math.radians(evt.camera['azim'])
            cam['pitch'] = math.radians(evt.camera['elev'])
            cam['dist'] = evt.camera['dist']
            cam['target'] = take
            cam['driven'] = True
        elif session is not None:
            # La camera segue il giocatore; l'orbita resta al mouse, perche'
            # senza non si capisce dove si e'. Finito il dialogo si torna
            # all'inquadratura di gioco, non a quella dell'ultima battuta.
            if cam['driven']:
                cam.update(cam['keep'])
                cam['driven'] = False
            else:
                cam['keep'] = {k: cam[k] for k in ('yaw', 'pitch', 'dist')}
            p = session.world.player
            cam['target'] = np.array([p.pos[0], p.pos[1] + 0.8, p.pos[2]],
                                     np.float32)
        if session is not None:
            state['cut'] = (session.world.player.pos[1] + state['roof']) \
                if state['roof'] else NO_CUT
        e, d = eye()
        near, far = scene['radius'] / 500, scene['radius'] * 12
        on = chain is not None and chain.enabled
        if on:
            chain.resize(win.width, win.height)
            # Il fuoco segue il bersaglio della telecamera: e' il
            # `switchDofPointGaze()` del Lua, il fuoco che insegue un
            # soggetto. L'ampiezza nitida e' una frazione del raggio della
            # scena, cosi' il tilt-shift resta coerente da una mappa
            # all'altra.
            chain.params['focus'] = float(np.linalg.norm(e - cam['target']))
            chain.params['range'] = scene['radius'] * args['dof']
            if evt:
                # I parametri di messa a fuoco vengono dallo script, come dice
                # la specifica YEBIS: `SetParamDepthofField` e
                # `SetDofApaerture` pilotano la catena di post-processing.
                #
                # L'unita' del secondo argomento resta ignota (Fase 3), ma
                # legarla alla **distanza di fuoco** invece che al raggio
                # della scena e' l'interpretazione che regge in entrambi i
                # casi d'uso: su un primo piano a 6 metri, `0.60` da' una
                # fascia nitida di 3,6 metri; su un panorama da lontano si
                # allarga da sola, come fa un obiettivo vero.
                chain.params['range'] = (chain.params['focus']
                                         * max(evt.dof['range'], 0.05))
                chain.params['aperture'] = evt.dof['aperture']
            chain.begin()
        else:
            win.clear()
        proj = perspective(50, win.width / max(win.height, 1), near, far)
        view = look_at(e, cam['target'])
        mvp = (proj @ view).T.ravel()             # GL vuole colonne
        program.use()
        program['mvp'] = Mat4(*mvp.tolist())
        program['sky'] = scene['sky']
        program['sun'] = SUN_DIR
        program['ambient'] = AMBIENT
        program['use_light'] = 1 if state['light'] else 0
        program['tex'] = 0
        program['cut'] = state['cut']
        scene['batch'].draw()
        if on:
            glDisable(GL_DEPTH_TEST)
            chain.draw(near, far)
            glEnable(GL_DEPTH_TEST)
        # L'interfaccia sta **dopo** il post-processing: il riquadro di
        # dialogo non va sfocato dal defocus ne' scurito dal vignetting.
        if event_ui():
            glDisable(GL_DEPTH_TEST)
            ui['batch'].draw()
            glEnable(GL_DEPTH_TEST)

    @win.event
    def on_mouse_drag(x, y, dx, dy, buttons, mod):
        cam['yaw'] -= dx * 0.005
        cam['pitch'] = max(-1.5, min(1.5, cam['pitch'] + dy * 0.005))

    @win.event
    def on_mouse_scroll(x, y, sx, sy):
        cam['dist'] = max(scene['radius'] / 100, cam['dist'] * (0.9 ** sy))

    @win.event
    def on_key_press(sym, mod):
        k = pyglet.window.key
        if sym == k.T:
            state['tex'] = not state['tex']
        elif sym == k.L:
            state['light'] = not state['light']
        elif sym == k.C:
            state['cull'] = not state['cull']
            (glEnable if state['cull'] else glDisable)(GL_CULL_FACE)
            glCullFace(GL_BACK)
        elif sym == k.F:
            cam['target'] = scene['center'].copy()
            cam['dist'] = scene['radius'] * args['dist']
        elif sym == k.M and session is not None:
            ui['map'] = None if ui.get('map') else floor_map()
            print('  mappa del sotterraneo: '
                  + ('accesa' if ui['map'] else 'spenta'))
        elif sym in (k.UP, k.DOWN) and ui.get('map') and ui.get('piano') \
                and not (evt and busy()):
            # A mappa aperta le frecce non camminano: **sfogliano i piani**,
            # dentro l'intervallo che il descrittore dichiara. La freccia in
            # su sale, e salire vuol dire numero di pagina piu' grande, perche'
            # la pagina e' il piano col segno.
            piani = ui.get('piani') or []
            passo = 1 if sym == k.UP else -1
            voluto = (ui['piano']['page'] or 0) + passo
            if any(f['page'] == voluto for f in piani):
                nuova = floor_map(voluto)
                if nuova is not None:
                    ui['map'] = nuova
            else:
                estremi = [f['label'] for f in piani]
                print(f'  non c e altro piano da questa parte '
                      f'({estremi[0]}..{estremi[-1]})')
        elif sym == k.P and chain:
            chain.enabled = not chain.enabled
        elif sym in (k.BRACKETLEFT, k.BRACKETRIGHT) and chain:
            f = 0.8 if sym == k.BRACKETLEFT else 1.25
            args['dof'] *= f
            print(f'  ampiezza a fuoco: {args["dof"]:.3f} del raggio')
        elif sym in (k.MINUS, k.EQUAL) and chain:
            chain.params['aperture'] *= 0.8 if sym == k.MINUS else 1.25
            print(f'  apertura: {chain.params["aperture"]:.2f} '
                  f'(il Lua usa 0,70 - 1,50)')
        elif sym == k.K and session is not None:
            state['roof'] = None if state['roof'] else args.get('roof') or 2.4
        elif sym in (k.SPACE, k.ENTER, k.RETURN) and evt:
            if session is not None and not busy():
                talk()                      # parlare con chi si ha davanti
            else:
                evt.press()                 # il tasto atteso da WaitContinue
        elif sym in (k.UP, k.DOWN) and evt and busy():
            evt.move(-1 if sym == k.UP else 1)
        elif sym == k.ESCAPE:
            win.close()

    # ------------------------------------------------------------ giocare
    #
    # Il giro di gioco sta tutto qui: un passo, un passaggio, una battuta.
    # Quello che serviva non era codice nuovo ma il collegamento fra pezzi che
    # esistevano gia' - la griglia sa dov'e' il mondo, la colonna sa dov'e' il
    # muro, l'host sa far parlare uno script.

    def busy() -> bool:
        """C'e' una conversazione in corso? Mentre c'e', i comandi sono suoi."""
        return bool(evt and evt.co is not None and not evt.done)

    def facing_from_camera(dx: int, dz: int) -> int:
        """Il comando e' relativo a **chi guarda**: premere avanti vuol dire
        andare dove punta la telecamera, non verso una direzione fissa del
        mondo. Con la mappa girata, il contrario e' disorientante."""
        import entity as ent

        _, d = eye()
        f = np.array([-d[0], 0.0, -d[2]], np.float32)   # avanti, orizzontale
        f /= np.linalg.norm(f) or 1
        r = np.array([-f[2], 0.0, f[0]], np.float32)    # destra
        want = f * dz + r * dx
        return max(range(4), key=lambda i: float(np.dot(
            np.array(ent.DIRS[i], np.float32), want)))

    def walk_step(dx: int, dz: int) -> None:
        got = session.step(facing_from_camera(dx, dz))
        if got == 'varco' and session.pending is not None:
            change_map(session.pending)

    def change_map(link) -> None:
        got = session.atlas.resolve(link)
        if got is None:
            return
        grid, cell = got
        pac = session.atlas.pac_for(grid.name)
        if pac is None:
            print(f'  {grid.name}: nessuna geometria sul disco')
            return
        t0 = time.time()
        new, _stat = load(pac)
        lib = Texlib(pac, args['root'])
        session.enter(grid, cell, args['directory'],
                      walk.columns_for(grid, args['root'], new))
        session.place(*cell)
        if evt is not None:
            evt.grid, evt.map = grid, (grid.w, grid.h)
        set_scene(new, lib, camera=False)
        win.set_caption(f'PC-3Ddot - {grid.name}')
        print(f'-> {grid.name} alla cella {cell} '
              f'({time.time() - t0:.1f}s, {len(session.world.npcs)} abitanti)')

    def talk() -> None:
        who = session.facing_npc()
        if who is None:
            return
        if not getattr(who, 'script', None):
            print(f'  {who.name} non ha niente da dire su questo disco')
            return
        who.facing = (session.world.player.facing ^ 1)   # ci si guarda in faccia
        print(f'  {who.name}: {who.script.name}')
        evt.begin(who.script)

    def update(dt):
        k = pyglet.window.key
        if session is not None:
            # Tenendo premuto si cammina: un passo per volta, e il successivo
            # parte quando il precedente e' arrivato. E' il passo del gioco a
            # griglia, non uno scorrimento continuo.
            # A mappa aperta non si cammina: le frecce stanno sfogliando i
            # piani.
            if not busy() and not session.world.player.moving \
                    and not ui.get('map'):
                for key, (dx, dz) in ((k.UP, (0, 1)), (k.W, (0, 1)),
                                      (k.DOWN, (0, -1)), (k.S, (0, -1)),
                                      (k.LEFT, (-1, 0)), (k.A, (-1, 0)),
                                      (k.RIGHT, (1, 0)), (k.D, (1, 0))):
                    if keys[key]:
                        walk_step(dx, dz)
                        break
            if evt:
                evt.update(dt)
            else:
                session.world.tick(dt)
            session.animate(dt)
            return
        _, d = eye()
        fwd = -d
        right = np.cross(fwd, np.array([0, 1, 0], np.float32))
        right /= np.linalg.norm(right) or 1
        v = np.zeros(3, np.float32)
        if keys[k.W]: v += fwd
        if keys[k.S]: v -= fwd
        if keys[k.A]: v -= right
        if keys[k.D]: v += right
        if keys[k.R]: v += (0, 1, 0)
        if keys[k.V]: v -= (0, 1, 0)
        if v.any():
            cam['target'] += v * cam['speed'] * dt * 60 / 10
        if evt:
            evt.update(dt)

    if args['shot']:
        win.switch_to()
        on_draw()
        pyglet.image.get_buffer_manager().get_color_buffer().save(args['shot'])
        print(f'  fotogramma -> {args["shot"]}')
        win.close()
        return 0

    pyglet.clock.schedule_interval(update, 1 / 60)
    pyglet.app.run()
    return 0


def cmd_sweep(root: pathlib.Path) -> int:
    """Carica *tutto* quello che si potrebbe disegnare e verifica che ogni
    riferimento a texture si risolva in un pacchetto TPKG. Un render bello e'
    un aneddoto; questo e' la misura."""
    src = sorted(root.rglob('*.pac')) + sorted(root.rglob('*.dsb'))
    tot = {'files': 0, 'sections': 0, 'chunks': 0, 'verts': 0, 'tris': 0,
           'no_uv': 0, 'no_tex': 0, 'skinned': 0}
    refs, unresolved, failed = 0, {}, []
    t0 = time.time()
    lib = Texlib(root, root)            # un indice solo, tutti i 763 pacchetti
    lib.scan_all()
    print(f'  {len(lib.index):,} texture indicizzate in '
          f'{len(lib.scanned)} pacchetti ({time.time() - t0:.0f}s)')
    for i, p in enumerate(src):
        print(f'  {i + 1}/{len(src)} {p.name:<40}', end='\r')
        try:
            parts, stat = load(p)
        except Exception as ex:                                  # noqa: BLE001
            failed.append(f'{p.name}: {type(ex).__name__} {ex}')
            continue
        tot['files'] += 1
        for k in ('sections', 'verts', 'tris', 'no_uv', 'no_tex', 'skinned'):
            tot[k] += stat[k]
        tot['chunks'] += len(parts)
        for name in stat['textures']:
            refs += 1
            if name.lower() not in lib.index:
                unresolved.setdefault(name, []).append(p.name)
    print(' ' * 60, end='\r')
    print(f'{tot["files"]} file su {len(src)}, {tot["sections"]:,} sezioni, '
          f'{tot["chunks"]:,} chunk')
    print(f'{tot["verts"]:,} vertici, {tot["tris"]:,} triangoli, '
          f'in {time.time() - t0:.0f}s')
    print(f'chunk senza UV: {tot["no_uv"]}, senza texture: {tot["no_tex"]}, '
          f'mesh raggiunte via skin: {tot["skinned"]}')
    print(f'riferimenti a texture: {refs}, non risolti: {len(unresolved)}')
    for name, where in sorted(unresolved.items())[:15]:
        print(f'  {name}  ({len(where)} file, es. {where[0]})')
    for f in failed[:10]:
        print(f'  ! {f}')
    return 1 if (failed or unresolved) else 0


def cmd_char(root: pathlib.Path, model: str, args: dict) -> int:
    """Un personaggio solo, con le sue pose in fila.

    Serve a guardare in faccia quello che il registro nomina - e a rispondere
    a occhio all'unica cosa che nei dati non c'era: da che parte guarda un
    modello a riposo. La posa `01` e' authorata verso +Z, cioe' verso la
    direzione 0, se qui il personaggio guarda **verso di noi** con
    `--azim 180`.
    """
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() else root
    lib = Charlib(data)
    # Piu' modelli separati da virgola: serve a confrontarli, ed e' cosi' che
    # si e' verificata a occhio la tabella degli archetipi - un cane e una
    # gallina non si confondono con nient'altro.
    wanted = [m.strip() for m in model.split(',') if m.strip()]
    parts, x = [], 0.0
    for mi, one in enumerate(wanted):
        poses = lib.poses(one)
        if not poses:
            raise SystemExit(f'{one}: nessun nodo in {Charlib.LIB} '
                             '(prova c_npc_05, c_enm_12, c_ply_01, i_evt_03)')
        show = poses if len(wanted) == 1 else poses[:1]
        print(f'{one}: {len(poses)} pose {poses}')
        for pose in show:
            for p in lib.parts(one, pose):
                q = Part()
                q.name, q.uv, q.col = p.name, p.uv, p.col
                q.idx, q.tex, q.nrm = p.idx, p.tex, p.nrm
                q.lit, q.emis = p.lit, p.emis
                q.pos = p.pos + np.array([x, 0, 0], np.float32)
                parts.append(q)
            x += 2.0
        x += 1.0 if len(wanted) > 1 else 0.0
    args['bounds'] = bounds(parts)
    args['title'] = model
    return run(parts, Texlib(data / 'Character/character.ps3.tpk', data), args)


def ground(n: int = 24) -> Part:
    """Un pavimento a scacchi di caselle, tutto nostro.

    Non e' un asset del gioco e non vuole esserlo: serve a dare al palco vuoto
    una scala leggibile. Una casella e' `entity.TILE`, cosi' si vede a occhio
    che un personaggio e' alto esattamente un quadretto - che e' il fatto su
    cui poggia tutto il resto.
    """
    import entity as ent

    s = ent.TILE
    v, c, idx = [], [], []
    for i in range(-n, n):
        for j in range(-n, n):
            base = len(v)
            for dx, dz in ((0, 0), (1, 0), (1, 1), (0, 1)):
                v.append(((i + dx) * s, 0.0, (j + dz) * s))
            t = 0.34 if (i + j) % 2 else 0.28
            c += [(t, t * 1.06, t * 0.92, 1.0)] * 4
            idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    p = Part()
    p.lit, p.emis = 1.0, (0.0, 0.0, 0.0)
    p.name = 'palco'
    p.pos = np.array(v, np.float32)
    p.nrm = np.tile(np.array([0, 1, 0], np.float32), (len(v), 1))
    p.uv = np.zeros((len(v), 2), np.float32)
    p.col = np.array(c, np.float32)
    p.idx = np.array(idx, np.uint32).reshape(-1, 3)
    p.tex = None
    return p


def cmd_event(script: pathlib.Path, args: dict) -> int:
    """Un evento su un palco vuoto, senza mappa.

    Serve perche' le due cose sono sottosistemi diversi e finora si
    ostacolavano: una mappa di questo gioco e' piena, ha anche il soffitto, e
    dove ci sia terreno libero non e' scritto da nessuna parte - il punto
    d'ingresso lo decideva il codice. Risultato: gli NPC finivano dentro un
    muro e non si vedeva se il registro funzionasse.

    Senza mappa restano solo le entita', ed e' esattamente quello che qui si
    vuole guardare: dove le mette lo script, da che parte le gira, come si
    muovono.
    """
    data = script
    while data.name and data.name != 'data':
        data = data.parent
    args['bounds'] = (np.array([-16.0, 0.0, -16.0], np.float32),
                      np.array([16.0, 3.2, 16.0], np.float32))
    args['at'] = args['at'] or [0.0, 0.0, 0.0]
    args['title'] = script.name
    args['event'] = str(script)
    evt, glyphs = start_event(args, data)
    for _ in range(int(args['skip'] * 60)):
        evt.update(1 / 60)
        if evt.awaiting and not evt.choosing:
            evt.press()
        if evt.done or evt.choosing:
            break
    args['event_state'] = (evt, glyphs)
    placed = evt.world.visible_entities()
    print(f'{len(placed)} entita in scena:')
    for e in placed:
        print(f'  {e!r}')
    lost = evt.world.unplaced()
    if lost:
        print(f'{len(lost)} nominate ma non collocate (stanno gia\' sulla '
              f'mappa): ' + ', '.join(e.name for e in lost))
    return run([ground()], Texlib(data / 'Character/character.ps3.tpk', data),
               args)


def cmd_play(target: str, args: dict) -> int:
    """Il giro di gioco: una mappa, i suoi abitanti, e il giocatore che ci
    cammina dentro.

    E' la prima cosa del progetto che si **gioca** invece di guardarla, ed e'
    anche la prova di integrazione piu' severa che ci sia: mette in fila la
    geometria composta, la griglia logica, il grafo dei passaggi, la rubrica
    degli NPC, il registro delle entita' e la VM Lua. Se un solo riferimento e'
    storto, si cammina dentro un muro o si esce in una mappa sbagliata.
    """
    import entity as ent
    import font as font_mod
    import host as host_mod
    import mapdat
    import walk

    root = pathlib.Path(args.get('root') or '../extract')
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() else root
    atlas = walk.Atlas(data)

    # Il bersaglio puo' essere un file o solo il nome di una mappa: `play
    # d_1_1_1` vale quanto il percorso del suo container.
    p = pathlib.Path(target)
    if p.exists():
        name, pac = mapdat.norm(p.name.split('.')[0]), p
    else:
        name = mapdat.norm(target)
        pac = atlas.pac_for(name)
        if pac is None:
            raise SystemExit(f'{target}: nessuna mappa con questo nome')
    grid = atlas.grid(name)
    if grid is None:
        raise SystemExit(f'{name}: manca la MAP_ALIGNMENT, e senza quella non '
                         'si sa dove ci sia mondo')

    t0 = time.time()
    parts, stat = load(pac)
    print(f'{pac.name}: {stat["sections"]} schermi, {stat["verts"]:,} vertici '
          f'in {time.time() - t0:.1f}s')

    # L'host serve solo a far parlare gli NPC, ma il mondo dev'essere lo
    # stesso: se il registro fosse suo, un evento sposterebbe un altro
    # personaggio da quello che si vede.
    evt = host_mod.Host(data, verbose=True)
    evt.load_libs()
    evt.grid, evt.map = grid, (grid.w, grid.h)
    session = walk.Walk(atlas, grid, evt.world)
    session.columns = walk.columns_for(grid, data, parts)
    directory = ent.npc_directory(data)
    n = session.populate(directory)
    # E gli oggetti: la cella li nomina con un numero, e il numero e' il
    # modello - `4000 + m_obj_NN`. Vedi nodes.py. `--no-props` li toglie, che
    # serve a confrontare un fotogramma con quelli delle sessioni precedenti.
    if '--no-props' not in sys.argv:
        import nodes as nodes_mod

        catalogo = nodes_mod.props(data)
        pr = session.populate_props(catalogo)
        muti = sum(1 for v in grid.props.values() if v not in catalogo)
        print(f'{pr} oggetti di mappa disegnati'
              + (f', {muti} celle senza modello' if muti else ''))
    # I nemici: la griglia dichiara specie e cella, e il set dice quale delle
    # tre disposizioni. `--spawn` la sceglie, `--spawn -` non ne mette nessuna.
    spawn = args.get('spawn') or 'A'
    if spawn != '-':
        actors = ent.actor_directory(data)
        # E i nemici si muovono da soli, perche' il disco dice come: ogni
        # specie ha il proprio script in `all.lua.eu` e lo esegue una VM Lua,
        # come gia' fanno gli eventi. `--still` li lascia fermi, che serve a
        # confrontare un fotogramma con quelli delle sessioni precedenti.
        if '--still' not in sys.argv:
            session.hire(data)
        m = session.populate_enemies(actors, spawn, ent.enemy_motion(data))
        # Il minigioco dichiara il ciclo di dodici specie; per le altre lo dice
        # il modello stesso, ed e' l'unica fonte che le copre tutte: un paio
        # `NN_a`/`NN_b` **e'** il ciclo di camminata, e quale sia il numero
        # cambia da nemico a nemico (l'ape usa 04, non 02).
        lib = Charlib(data)
        for e in evt.world.npcs.values():
            if e.kind != 'enemy' or e.frames:
                continue
            have = lib.poses(e.model)
            pair = sorted({p[:-2] for p in have if p.endswith('_a')
                           and f'{p[:-2]}_b' in have})
            if pair:
                e.frames = ['01' if '01' in have else have[0],
                            f'{pair[0]}_a', f'{pair[0]}_b']
        print(f'{n} abitanti, {m} nemici del set {spawn} '
              f'(dei set {"".join(sorted(grid.enemies)) or "nessuno"})')
    where = atlas.where(name)
    if where.get('location'):
        print(f'  «{where["location"]}», musica {where["bgm"]}')
    cell = tuple(int(v) for v in args['cell'].split(',')) if args.get('cell') \
        else session.start_cell()
    session.place(*cell)
    evt.world.spots = {k: grid.local(*xy) for k, xy in grid.spots.items()}

    if '--talk' in sys.argv:
        # Serve a fermare in un'immagine il giro intero - passo, incontro,
        # battuta - senza avere qualcuno che prema i tasti: si va accanto al
        # primo abitante che ha un dialogo e glielo si fa dire.
        # Non il primo che capita: quello **piu' all'aperto**. Le camere del
        # gioco stanno a sei unita' dal soggetto e non evitano i muri - e' il
        # gioco vero a spostarle - quindi un abitante addossato a una parete
        # da' un fermo immagine di intonaco.
        def air(e):
            cx, cy = grid.cell_of(e.pos)
            return sum(session.standable(cx + dx, cy + dy)[0]
                       for dx in range(-3, 4) for dy in range(-3, 4))

        who = max((e for e in evt.world.npcs.values() if e.script),
                  key=air, default=None)
        if who is not None:
            wx, wy = grid.cell_of(who.pos)
            cell = (wx, wy + 1)
            session.place(*cell)
            session.world.player.facing = 0
            who.facing = 1
            evt.begin(who.script)
            for _ in range(int(max(args['skip'], 2.0) * 60)):
                evt.update(1 / 60)
                if evt.pages:
                    break
    # Con `--skip N` si lascia vivere la mappa N secondi prima del primo
    # fotogramma: serve a fotografare i nemici **dopo** che si sono mossi, che
    # e' l'unico modo di vedere in un'immagine ferma una cosa che si muove.
    if session.troupe is not None and args.get('skip'):
        for _ in range(int(args['skip'] * 60)):
            session.animate(1 / 60)
            session.world.tick(1 / 60)
    print(f'{grid!r}')
    if session.troupe is not None:
        print(f'  {len(session.troupe.actors)} nemici con il proprio script, '
              f'{len(session.troupe.animated)} col ciclo di pose che il file '
              f'dichiara, {len(session.troupe.unknown)} metodi ancora da '
              f'scrivere')
    print(f'  {n} abitanti collocati, {sum(1 for e in evt.world.npcs.values() if e.script)} '
          f'con un dialogo')
    print(f'  giocatore alla cella {cell} = '
          f'({session.world.player.pos[0]:.1f}, '
          f'{session.world.player.pos[1]:.1f}, '
          f'{session.world.player.pos[2]:.1f})')
    # Gli oggetti che la mappa dichiara e che nessuna delle due geometrie
    # contiene: sono attori, e per ora si sanno e basta. Vedi `walk.md`.
    obj = {k: v for k, v in grid.objects.items()
           if k not in ('Exit', 'Warp')}
    if obj:
        top = sorted(obj.items(), key=lambda kv: -len(kv[1]))[:6]
        print('  oggetti: ' + ', '.join(f'{k}x{len(v)}' for k, v in top)
              + (f' (+{len(obj) - len(top)} classi)' if len(obj) > 6 else ''))
    print('  frecce o WASD per camminare, spazio per parlare, K il soffitto, '
          'ESC esce')

    wet = water_parts(grid.path)
    if wet:
        print(f'  acqua: {len(wet[0].pos) // 4:,} celle')
        parts = parts + wet
    args['bounds'] = bounds(parts)
    args['title'] = grid.name
    args['session'] = session
    args['event_state'] = (evt, font_mod.Font(
        data / 'UserInterface/Font/Font.lua.eu'))
    args['root'] = data
    args['directory'] = directory
    return run(parts, Texlib(pac, data), args)


def cmd_walkabout(root: pathlib.Path, limit: int | None = None) -> int:
    """La misura del giro di gioco: si cammina davvero, su tutto il disco?

    Un fotogramma con un personaggio in mezzo a una mappa e' un aneddoto.
    Questo e' il numero: per ogni mappa si carica la geometria, si costruiscono
    le colonne, si parte dal punto d'ingresso che il dato dichiara e si guarda
    **dove si arriva a piedi**. Poi si chiede la cosa che conta davvero: dei
    passaggi che si raggiungono camminando, quanti portano in una cella
    dell'altra mappa in cui si sta in piedi?

    E' la prova di integrazione piu' severa del progetto: coinvolge la
    composizione degli schermi, la griglia logica, il grafo dei passaggi e la
    scala del mondo tutti insieme, e non perdona un riferimento storto.
    """
    import walk

    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() else root
    atlas = walk.Atlas(data)
    names = sorted(atlas.files)[:limit]
    cols: dict[str, walk.Columns] = {}

    def columns_of(name: str):
        """Le colonne di una mappa, caricando la geometria una volta sola: una
        destinazione viene chiesta piu' volte, ed e' il caricamento a costare."""
        if name not in cols:
            g, pac = atlas.grid(name), atlas.pac_for(name)
            if g is None or pac is None:
                cols[name] = None
            else:
                try:
                    parts, _ = load(pac)
                    c = walk.columns_for(g, data, parts)
                except Exception:                                # noqa: BLE001
                    cols[name] = None
                    return None
                cols[name] = c
        return cols[name]

    t0 = time.time()
    keys = ('maps', 'start', 'world', 'reach', 'gates', 'seen', 'ok',
            'spots', 'spots_ok', 'water')
    # I sotterranei e la campagna vanno contati a parte: sono due mondi con
    # due geometrie, e mescolarli nasconde che uno dei due funziona.
    tot = {k: 0 for k in keys}
    fam = {'sotterranei': dict.fromkeys(keys, 0),
           'campagna': dict.fromkeys(keys, 0)}
    worst = []
    for i, name in enumerate(names):
        print(f'  {i + 1}/{len(names)} {name:<24}', end='\r')
        g = atlas.grid(name)
        c = columns_of(name)
        if c is None or c.empty():
            continue
        here = dict.fromkeys(keys, 0)
        here['maps'] = 1
        w = walk.Walk(atlas, g)
        w.columns = c
        start = w.start_cell()
        # Da tutte le porte, non da una: la mappa si entra da ognuna delle sue
        # `Exit`, e sceglierne una sola misura quella porta invece della mappa.
        seen, floor, standable = walk.reachable(
            c, list(dict.fromkeys([start, *g.exits.values()])))
        # Le celle che contano sono quelle che la griglia logica attribuisce a
        # una regione **e** su cui si sta in piedi: il resto e' soffitto, muro
        # o fuori mappa.
        # `standable` viene per piano: qui conta la cella, cioe' se in quella
        # colonna c'e' almeno un posto in cui si sta in piedi.
        standable = standable.any(axis=2)
        # E il fondo del mondo non e' mondo: dove l'unico piano di una cella e'
        # il fondale steso sotto la mappa, li' c'e' acqua o un fossato, e il
        # gioco non ci mette niente. Vedi `Columns.bury()`.
        water = c.water()
        here['water'] = int((g.inside & water).sum())
        here['world'] = int((g.inside & standable & ~water).sum())
        here['reach'] = int((g.inside & seen).sum())
        here['start'] = int(standable[start[1], start[0]])
        if here['world']:
            worst.append((here['reach'] / here['world'], name,
                          here['reach'], here['world']))
        # Gli abitanti sono la misura che conta piu' delle celle: una cella
        # irraggiungibile puo' essere il tetto di una casa, un abitante
        # irraggiungibile e' un pezzo di gioco che non si vede.
        for xy in g.spots.values():
            here['spots'] += 1
            here['spots_ok'] += bool(seen[xy[1], xy[0]])
        for cell, link in g.links.items():
            here['gates'] += 1
            if not seen[cell[1], cell[0]]:
                continue
            here['seen'] += 1
            got_dest = atlas.resolve(link)
            if got_dest is None:
                continue
            dg, dcell = got_dest
            dc = columns_of(dg.name)
            if dc is None or dc.empty():
                continue
            here['ok'] += dc.ground(*dcell) is not None
        who = fam['campagna' if name.startswith('field') else 'sotterranei']
        for k in keys:
            tot[k] += here[k]
            who[k] += here[k]
    print(' ' * 60, end='\r')

    def report(label, t):
        if not t['maps']:
            return
        print(f'{label:<12} {t["maps"]:>3} mappe, ingresso calpestabile in '
              f'{t["start"]}')
        print(f'             celle raggiunte a piedi   {t["reach"]:>7,}/'
              f'{t["world"]:<7,} = {t["reach"] * 100 / max(t["world"], 1):.0f}%'
              f'   (acqua e fossati {t["water"]:,} a parte)')
        print(f'             abitanti raggiunti        {t["spots_ok"]:>7}/'
              f'{t["spots"]:<7} = '
              f'{t["spots_ok"] * 100 / max(t["spots"], 1):.0f}%')
        print(f'             passaggi raggiunti        {t["seen"]:>7}/'
              f'{t["gates"]:<7}, con l arrivo in piedi {t["ok"]}')

    print(f'{tot["maps"]} mappe percorse in {time.time() - t0:.0f}s')
    report('in tutto', tot)
    for k, v in fam.items():
        report(k, v)
    worst.sort()
    print('le peggiori:')
    for f, n, got, world in worst[:8]:
        print(f'  {n:<14} {got:>6}/{world:<6} = {f * 100:.0f}%')
    return 0


def cmd_layout(root: pathlib.Path) -> int:
    """Verifica la composizione delle mappe, e lo fa con un oracolo esterno.

    La griglia logica di `MAP_ALIGNMENT` dice, cella per cella, se li' c'e'
    mappa o si e' fuori (`0xFFFFFFFF` nel 56% delle celle del disco). E' un
    file diverso, scritto per un altro scopo, in un altro endianness. Se la
    composizione degli schermi e' giusta, la geometria deve cadere **dove
    quel file dice che c'e' mappa** - e non altrove.

    E' la stessa forma di prova che ha risolto gli altri formati: due
    dichiarazioni indipendenti che devono coincidere.

    **Ma la griglia logica e' il denominatore sbagliato**, e per due sessioni
    ha fatto sembrare mancante il 9% della geometria. Fra le celle che marca
    come regione ce ne sono che non contengono mondo ma **acqua e vuoto**: il
    fossato, il mare, la gola fra due altipiani. La mappa lo dichiara - quelle
    celle portano un identificativo di regione tutto loro - ma per capirlo
    bisogna chiedere a qualcun altro cosa sia solido, e quel qualcuno e' il
    file di collisione.

    Quindi la misura si fa due volte, e la seconda e' quella onesta: la
    geometria copre il 90% delle celle che la griglia chiama regione, e il
    **99,3%** di quelle che il gioco stesso considera solide.
    """
    import mapdat
    import walk

    pac = sorted((root / 'map/pac_data').glob('*.pac.gz')) or \
        sorted(root.rglob('*.pac.gz'))
    tot_in = tot_hit = tot_out = tot_off = 0
    tot_solid = tot_solid_hit = 0
    tot_black = tot_wet = 0
    worst, skipped = [], 0
    t0 = time.time()
    for i, p in enumerate(pac):
        print(f'  {i + 1}/{len(pac)} {p.name:<32}', end='\r')
        g = screens(p)
        if g is None:
            skipped += 1
            continue
        n0, n1, cw, ch, w, h = g
        stem = p.name.split('.')[0]
        dat = next((q for q in (root / 'map/MAP_ALIGNMENT').glob('*.DAT')
                    if q.stem.lower() == stem.lower()), None)
        if dat is None:
            skipped += 1
            continue
        raw = dat.read_bytes()
        inside = np.zeros((h, w), bool)
        for c in mapdat.cells(raw):
            if c['tag'] != 0xFFFFFFFF:
                inside[c['y'], c['x']] = True
        try:
            parts, _ = load(p)
        except Exception:                                        # noqa: BLE001
            skipped += 1
            continue
        occ = np.zeros((h, w), bool)
        for q in parts:
            gx = np.floor((q.pos[:, 0] + w * CELL / 2) / CELL).astype(int)
            gy = np.floor((h * CELL / 2 - q.pos[:, 2]) / CELL).astype(int)
            m = (gx >= 0) & (gx < w) & (gy >= 0) & (gy < h)
            occ[gy[m], gx[m]] = True
        hit = int((occ & inside).sum())
        off = int((occ & ~inside).sum())
        tot_in += int(inside.sum()); tot_hit += hit
        tot_out += int((~inside).sum()); tot_off += off
        # Il secondo denominatore: cosa il gioco stesso considera solido.
        col = walk.columns_for(walk.Grid(dat), root)
        if not col.empty():
            # Il fondale non e' terra: dove e' l'unica superficie della cella
            # c'e' acqua, e quelle celle non sono da coprire.
            wet = col.water()
            solid = (col.solid > -np.inf).any(axis=2) & inside & ~wet
            tot_solid += int(solid.sum())
            tot_solid_hit += int((solid & occ).sum())
            # E quello che resta **nero** in un fotogramma: dentro la mappa,
            # senza geometria e senza acqua.
            tot_black += int((inside & ~occ & ~wet).sum())
            tot_wet += int((inside & wet).sum())
        if inside.sum():
            worst.append((hit / inside.sum(), stem, hit, int(inside.sum())))
    print(' ' * 60, end='\r')
    print(f'{len(pac) - skipped} mappe verificate ({skipped} senza griglia '
          f'dichiarata) in {time.time() - t0:.0f}s')
    print(f'celle di mappa coperte dalla geometria: {tot_hit:,}/{tot_in:,} = '
          f'{tot_hit * 100 / tot_in:.1f}%')
    print(f'  delle sole celle solide (collisione):  {tot_solid_hit:,}/'
          f'{tot_solid:,} = {tot_solid_hit * 100 / max(tot_solid, 1):.1f}%')
    print(f'  il resto e acqua e vuoto:              '
          f'{tot_in - tot_solid:,} celle')
    print(f'  di cui acqua, ora disegnata:           {tot_wet:,} celle')
    print(f'  restano nere in un fotogramma:         {tot_black:,} celle = '
          f'{tot_black * 100 / tot_in:.1f}% della mappa')
    print(f'geometria fuori mappa:                  {tot_off:,}/{tot_out:,} = '
          f'{tot_off * 100 / tot_out:.1f}%')
    worst.sort()
    for f, n, hit, tot in worst[:8]:
        print(f'  {n:<14} {hit:>6}/{tot:<6} = {f * 100:.0f}%')
    return 0 if tot_hit / tot_in > 0.95 else 1


def cmd_light(root: pathlib.Path, limit: int | None = None) -> int:
    """Quanto cielo vede ogni mappa, misurato sui suoi colori di vertice.

    E' la misura da cui viene `sky_profile`, su tutto il disco invece che su
    una mappa. La riga da guardare non e' il valore ma il **verso**: dove c'e'
    il cielo la faccia in su e' la piu' chiara, dove c'e' un soffitto e' la
    piu' scura, e i quattro fianchi restano concordi in tutti e due i casi.
    """
    import mapdat
    data = root / 'PS3_GAME/USRDIR/data'
    pac = sorted((root / 'pac').glob('*.pac'))
    if limit:
        pac = pac[:limit]
    try:
        locs = mapdat.locations(data)
    except Exception:
        locs = {}
    t0, rows = time.time(), []
    for i, p in enumerate(pac):
        print(f'  {i + 1}/{len(pac)} {p.name:<24}', end='\r')
        try:
            parts, _ = load(p, place=False)
        except Exception as e:
            print(f'  {p.name}: {e}')
            continue
        stem = p.name.split('.')[0]
        up, _s, down, rich = sky_profile(parts)
        rows.append((up, down, rich, stem,
                     (locs.get(stem.lower()) or {}).get('location', '')))
    print(' ' * 60, end='\r')
    if not rows:
        return 1
    rows.sort(reverse=True)
    cielo = [r for r in rows if r[0] > 1]
    ricche = [r for r in rows if r[2] >= RICH]
    concordi = sum(1 for r in rows if (r[0] > 1) == (r[2] >= RICH))
    print(f'{len(rows)} mappe misurate in {time.time() - t0:.0f}s '
          f'(fianchi = 1 per definizione)')
    print(f'  vedono il cielo (faccia in su piu chiara):   {len(cielo)}')
    print(f'  portano la propria luce (precotto >= {RICH:.0%}):  {len(ricche)}')
    print(f'  le due misure concordano su {concordi}/{len(rows)} = '
          f'{concordi * 100 / len(rows):.1f}%')
    print(f'\n{"mappa":<12}{"su":>7}{"giu":>7}{"precotto":>10}   posto')
    for up, down, rich, stem, loc in rows[:10]:
        print(f'{stem:<12}{up:>7.2f}{down:>7.2f}{rich * 100:>9.0f}%   {loc}')
    print(f'{"...":<12}')
    for up, down, rich, stem, loc in rows[-10:]:
        print(f'{stem:<12}{up:>7.2f}{down:>7.2f}{rich * 100:>9.0f}%   {loc}')
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == 'light':
        n = next((int(a) for a in argv[1:] if a.isdigit()), None)
        return cmd_light(pathlib.Path(
            next((a for a in argv[1:] if not a.isdigit()), '../extract')), n)
    if argv[0] == 'sweep':
        return cmd_sweep(pathlib.Path(argv[1] if len(argv) > 1
                                      else '../extract'))
    if argv[0] == 'walkabout':
        n = next((int(a) for a in argv[1:] if a.isdigit()), None)
        return cmd_walkabout(pathlib.Path(
            next((a for a in argv[1:] if not a.isdigit()), '../extract')), n)
    if argv[0] == 'layout':
        return cmd_layout(pathlib.Path(
            argv[1] if len(argv) > 1
            else '../extract/PS3_GAME/USRDIR/data'))
    char, stage = argv[0] == 'char', argv[0] == 'event'
    play = argv[0] == 'play'
    src = pathlib.Path(argv[1] if stage or play else '.' if char else argv[0])
    if not (src.exists() or play):
        raise SystemExit(f'non trovato: {src}')

    def opt(name, default=None, cast=str):
        return cast(argv[argv.index(name) + 1]) if name in argv else default

    if '--list' in argv:
        for i, (name, blob) in enumerate(dsb.blocks(src)):
            n = struct.unpack_from('>I', blob, 0x28)[0]
            print(f'  {i:>4}  {name:<28} {n:>5} oggetti  {len(blob):>9,} B')
        return 0

    size = opt('--size', '1600x900').split('x')
    args = {
        'size': (int(size[0]), int(size[1])),
        'shot': opt('--shot'),
        'map': '--map' in argv,
        'azim': opt('--azim', 0.0 if play else 35.0, float),
        'elev': opt('--elev', 42.0 if play else 30.0, float),
        'dist': opt('--dist', 1.3, float),
        'light': '--flat' not in argv,
        'post': '--raw' not in argv,
        'event': opt('--event'),
        'func': opt('--func'),
        'skip': opt('--skip', 0.0, float),
        'at': [float(v) for v in opt('--at', '').split(',')] if opt('--at')
              else None,
        'event_state': None,
        'dof': opt('--dof', 0.10, float),
        'aperture': opt('--aperture', post.DEFAULTS['aperture'], float),
        'title': src.name,
        'root': opt('--root'),
        'cell': opt('--cell'),
        'spawn': opt('--spawn'),
        # Quanto mondo tenere sopra la testa del giocatore. I sotterranei
        # hanno il soffitto: senza taglio si guarda una lastra.
        'roof': None if '--no-roof' in argv else opt('--roof', 2.4, float),
        'session': None,
    }

    if char:
        return cmd_char(pathlib.Path(opt('--root', '../extract')), argv[1], args)
    if play:
        return cmd_play(argv[1], args)
    if stage:
        return cmd_event(src, args)

    t0 = time.time()
    parts, stat = load(src, opt('--sec', None, int))
    only = opt('--only')
    if only:
        # Utile piu' di quanto sembri: in Opening.ps3.dsb un solo quad nero -
        # la tendina di dissolvenza - e' grande quanto tutto il resto e si
        # mangia sia l'inquadratura sia la vista.
        subs = [s.lower() for s in only.split(',')]
        keep = [p for p in parts
                if any(s in p.name.lower() for s in subs)]
        print(f'  --only {only!r}: {len(keep)} chunk su {len(parts)}')
        parts = keep
    if not parts:
        raise SystemExit('nessuna geometria da disegnare: una sezione di mappa '
                         'puo\' essere vuota (--list per vederle tutte)')
    print(f'{src.name}: {stat["sections"]} sezioni, {stat["meshes"]} mesh, '
          f'{len(parts)} chunk, {stat["verts"]:,} vertici, '
          f'{stat["tris"]:,} triangoli in {time.time() - t0:.1f}s')
    print(f'  {len(stat["textures"])} texture distinte; '
          f'{stat["no_tex"]} chunk senza texture, {stat["no_uv"]} senza UV')
    args['bounds'] = bounds(parts)
    args['grid'] = stat['grid']
    args['dat'] = dat_for(src) if stat['grid'] else None
    if stat['grid']:
        n0, n1, cw, ch, w, h = stat['grid']
        print(f'  composta da {n0}x{n1} schermi di {cw}x{ch} celle: '
              f'{w}x{h} celle, {w * CELL:.0f}x{h * CELL:.0f} unita di mondo')

    root = src.parent
    for _ in range(4):                    # risali fino a extract/
        if (root / 'PS3_GAME').exists() or root.name == 'extract':
            break
        root = root.parent
    if args['dat'] and '--no-water' not in argv:
        wet = water_parts(args["dat"])
        if wet:
            print(f'  acqua: {len(wet[0].pos) // 4:,} celle a pelo '
                  f'{wet[0].pos[1, 1]:+.1f}')
            parts = parts + wet
            args['bounds'] = bounds(parts)
    if args['event']:
        evt, glyphs = start_event(args, root)
        # `--skip` porta avanti l'evento prima del primo fotogramma: gli
        # eventi cominciano con secondi di attese e movimenti di camera, e
        # per un fermo immagine non ha senso aspettarli davvero.
        for _ in range(int(args['skip'] * 60)):
            evt.update(1 / 60)
            # Durante il salto si preme da soli per far scorrere le battute,
            # ma ci si ferma davanti a una scelta: e' li' che vale la pena
            # arrivare per un fermo immagine.
            if evt.awaiting and not evt.choosing:
                evt.press()
            if evt.done or evt.choosing:
                break
        args['event_state'] = (evt, glyphs)

    return run(parts, Texlib(src, root), args)


if __name__ == '__main__':
    raise SystemExit(main())
