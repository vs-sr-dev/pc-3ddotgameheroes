"""
ui.py - le schermate di sistema, che sul disco sono **dato e non codice**.

109 file Lua sotto `data/` dichiarano 137 schermate: salvataggio, opzioni,
pausa, game over, negozio, album dei nemici, mappa dei sotterranei. Ognuna
nomina il proprio pacchetto di texture e la propria scena 3D, e poi elenca
dove vanno le scritte, dove va il cursore e cosa fa il tasto di annullamento.

    ClearSave = {
        TexturePackageName = "UserInterface/Select/SelectA",
        ScenePackageName   = "UserInterface/Select/SelectA",
        Animation = { In={Start=0.0,Size=0.4}, Main={...}, Out={...}, Cursor={...} },
        Message = { Size=1, {X=640.0, Y=500.0, String="Okay to save?", Align="Center"} },
        Select  = { Size=2, {CursorX=927.0, CursorY=525.0, X=961.0, Y=518.0, ...} },
        Cancel  = { Enable=0, Index=1 },
    }

Finora erano lette e basta. Qui si **eseguono**: si carica la scena, si mettono
le scritte dove il descrittore dice, e viene fuori la schermata - e poi si
naviga, perche' anche i tasti sono dichiarati.

    python ui.py list                        le schermate dichiarate
    python ui.py show ClearSave out.png      una schermata composta
    python ui.py menus Pause                 le voci, e cosa spiegano
    python ui.py keys EnemyAlbum             la barra: azioni e tasti
    python ui.py drive Pause giu,giu,croce out.png   navigata
    python ui.py floors 5                    i piani di un sotterraneo
    python ui.py clips Option                la tabella delle clip, per indice
    python ui.py anim ClearSave frame.png    i fotogrammi dell'apertura
    python ui.py check                       le verifiche interne

## Anche l'input e' dichiarato

Sembrava la parte da inventare, ed e' quasi tutta sul disco. Le **voci** si
riconoscono dal fatto che il cursore ci puo' stare (`CursorX`/`CursorY`), e
sono 23 blocchi per 60 voci - non solo i 19 si/no di `Select`, ma il menu del
titolo, quello di pausa, e `ClearMenu`, che e' il titolo **a gioco finito**,
con `NEW GAME+` in piu'. L'**asse** lo dice la geometria: 23 blocchi su 23
hanno le voci incolonnate, quindi si sale e si scende. Il **tasto di
annullamento** ha il proprio campo, `Cancel = {Enable, Index}`, e non vuol
dire «esci»: sceglie una voce precisa, che in tutte e 19 le schermate e' `NO`.
Le **pagine** hanno i propri estremi, `setting = {pageMin, pageMax}`.

Resta nostra una cosa sola, e si spegne: che dall'ultima voce si torni alla
prima (`Screen(..., wrap=False)`).

## Due difetti di lettura, e trecento scritte che non si vedevano

I file Lua sono UTF-8 nei dati e **Shift-JIS nei commenti**: gli autori hanno
lasciato le proprie note nella codifica di casa. Il ripiego di prima - «se
UTF-8 non va, rileggi tutto in Shift-JIS» - buttava via l'intero file per
colpa di una nota, e le scritte tornavano indietro stroppiate: **319 su 358**.

E `descriptors()` non caricava le tabelle permissive di `host.BOOT`, quindi
11 file cadevano in silenzio: **17 schermate** in meno, fra cui l'album dei
nemici e tutte e sette le mappe dei sotterranei. Sono 136, non 119.

Messi a posto tutti e due, si e' visto il terzo: dei **432** posti in cui il
disco colloca una scritta se ne disegnavano **85**, perche' si guardava solo
in `Message` e `Select`. Ora la mappa del sotterraneo dice «Dark Tower» e
«3F», che e' proprio la cosa che una mappa deve dire.

## Lo schermo virtuale, e che sia lo stesso

Le coordinate dei descrittori sono in uno schermo **1280x720** (`X=640` e' il
centro), quindi l'interfaccia e' risoluzione-indipendente per costruzione.
Questo era gia' noto. La cosa che non lo era, ed e' quella che permette di
comporre, e' che le **scene 3D vivono nello stesso schermo**: la larghezza
mediana delle 115 e' 1280,0 esatti, e `Fade/Fade.ps3.dsb` - la dissolvenza a
piena pagina, che per definizione copre lo schermo e basta - misura
`x [0, 1280]` e `y [-720, 0]` al decimale.

Da cui le due conversioni, che non sono una taratura ma una lettura:

    schermo_x = modello_x
    schermo_y = -modello_y        la Y del modello cresce verso l'alto
    z                             non e' profondita': e' il piano di
                                  sovrapposizione (-90 la dissolvenza,
                                  -50 il fondo, 0 il fronte)

## Perche' si puo' comporre invece di rasterizzare

Perche' l'interfaccia e' fatta di rettangoli: dei **16.494 triangoli** delle 115
scene, 16.492 sono piatti in Z e **16.494 su 16.494** hanno due lati sugli assi.
Quindi ogni coppia di triangoli e' un rettangolo allineato, e disegnarlo vuol
dire ritagliare un pezzo di texture e incollarlo - esatto al pixel, senza una
pipeline 3D.

## Perche' non bastava leggerli

I descrittori erano letti da tre sessioni e non eseguiti, e provando si capisce
perche': **a riposo le schermate sono chiuse**. Il nodo di ogni pezzo di
`SelectA` ha scala 0 su un asse - `(0,1,1)`, `(1,0,1)` - mentre la mesh sotto e'
intera, 149x99. E le schermate a scorrimento hanno i pezzi parcheggiati fuori
campo: il menu degli oggetti arriva a `x=2193`, quasi il doppio dello schermo.

Ad aprirle e' l'animazione, ed e' la quarta cosa che il descrittore dichiara:
`Animation = {In, Main, Out, Cursor}`. Il `.dsb` non contiene curve - fra i
suoi otto tipi di oggetto non c'e' l'animazione - quindi il moto lo mette il
motore, e la posa finale e' la scala a 1.

## Le clip, e il campo che il suo nome fa leggere male

`Start` sembra l'inizio della clip sulla linea del tempo. Non lo e': vale 0 in
tutte e 36 le `In`, 1 in tutte e 33 le `Main`, 2 in tutte e 36 le `Out`. Un
tempo determinato dal nome della clip non e' un tempo, e' **un indice** in una
tabella - e nelle schermate grosse gli indici sono densi e consecutivi fino a
38. `Size` invece varia, ed e' la durata in secondi.

## Due animazioni, non una

**L'apertura** ha tutti e due gli estremi sul disco: il pezzo e' esportato con
la scala a zero, la mesh sotto e' intera, e la durata e' dichiarata. Si
ricostruisce senza inventare niente, e `unfold` percio' non e' un interruttore
ma un fattore: `compose(..., grow=0.4)` e' un fotogramma.

**Lo scorrimento** no. Le schermate a scorrimento non sono chiuse da una scala,
sono *spostate*, e il disco porta solo il parcheggio (`Window01` a `x=-600`,
`Window03` a `x=1300`). Il moto e' orizzontale - 33 pezzi su 38 sono fuori
campo solo in X, e la Y e' gia' quella definitiva - ma dove atterrino non sta
ne' nella scena ne' nel descrittore. Sono 15 pezzi in 5 schermate, ed e' la
sola parte che serva davvero chiedere all'EBOOT.
"""
from __future__ import annotations

import pathlib
import re
import sys

import numpy as np

SCREEN = (1280, 720)


# ------------------------------------------------------------ i descrittori

def _plain(v):
    """Da tabella Lua a dizionario/lista Python, ricorsivamente.

    Una **costante nativa** torna indietro come tabella permissiva che ricorda
    il proprio nome (vedi `host.BOOT`): `LIVING.FIELD_GRASS` non ha un valore
    su questo disco, ma il nome e' esattamente quello che serve. Qui diventa
    la stringa, invece di un dizionario con dentro una chiave sola."""
    if type(v).__name__ != '_LuaTable':
        return v
    keys = list(v.keys())
    if keys == ['__name']:
        return str(v['__name'])
    if keys and all(isinstance(k, int) for k in keys):
        return [_plain(v[k]) for k in sorted(keys)]
    return {k: _plain(v[k]) for k in keys if k != '__name'}


def source(path: pathlib.Path) -> str:
    """Un file Lua del disco, letto **sempre** come UTF-8.

    I file sono UTF-8 nei dati e **Shift-JIS nei commenti**: gli autori hanno
    lasciato le proprie note nella codifica di casa, e sono 21 file su 618 -
    fra cui `all.lua.eu`, che da solo dichiara quasi tutte le schermate.

    Il ripiego di prima - «se UTF-8 non va, rileggi tutto in Shift-JIS» -
    buttava via l'intero file per colpa di una nota, e le scritte
    dell'interfaccia tornavano indietro stroppiate: **319 su 358**. Il byte
    guasto sta solo dentro un commento, che Lua ignora fino a fine riga, quindi
    sostituirlo non costa niente e tiene buono tutto il resto.
    """
    return path.read_bytes().decode('utf-8', errors='replace')


def descriptors(root: pathlib.Path) -> dict:
    """Tutte le schermate dichiarate sul disco, per nome.

    Si caricano con la VM Lua e non con un parser nostro, per la stessa ragione
    per cui il font si carica cosi': **sono Lua**, e la VM li legge meglio di
    qualunque cosa scritta da noi. `all.lua.eu` le contiene quasi tutte, ma non
    tutte, quindi si passano tutti i file che ne dichiarano una.

    Le **tabelle permissive** di `host.BOOT` servono anche qui: i descrittori
    piu' ricchi nominano costanti native (`GameDataMapFlags`, `map_manager`,
    `LIVING`) che nessuno script definisce, e senza di loro il file non gira
    affatto. Erano 11 file che cadevano in silenzio, cioe' **17 schermate** -
    fra cui l'album dei nemici e tutte e sette le mappe di sotterraneo.
    """
    from lupa import LuaRuntime

    import host

    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(host.BOOT)
    out: dict[str, dict] = {}
    for p in sorted(data.rglob('*.lua.eu')):
        src = source(p)
        if 'TexturePackageName' not in src:
            continue
        before = set(lua.globals().keys())
        try:
            lua.execute(src)
        except Exception:                                        # noqa: BLE001
            continue
        for k in set(lua.globals().keys()) - before:
            t = _plain(lua.globals()[k])
            if isinstance(t, dict) and 'TexturePackageName' in t:
                out.setdefault(k, t)['__file'] = str(p)
    return out


# ------------------------------------------------- le scritte e le voci

#: Le tre coppie di nomi con cui un descrittore dichiara una scritta. Il
#: campo si chiama `String` quasi sempre, `Strings` nella barra dei tasti e
#: nelle etichette di piano; e una voce di menu puo' portare il proprio testo
#: col prefisso del blocco (`MenuString`, `MenuX`, `MenuAlign`).
_TEXT_KEYS = (('String', 'X', 'Y', 'Align'),
              ('Strings', 'X', 'Y', 'Align'),
              ('MenuString', 'MenuX', 'MenuY', 'MenuAlign'),
              ('DescriptionString', 'DescriptionX', 'DescriptionY',
               'DescriptionAlign'),
              ('MessageString', 'MessageX', 'MessageY', 'MessageAlign'))


def texts(desc: dict) -> list[dict]:
    """Ogni scritta che una schermata **colloca**: `{string, x, y, align, at}`.

    Le scritte non stanno solo in `Message` e `Select`, che erano le uniche due
    che si disegnavano: stanno anche nella barra dei tasti (`canselStrings`),
    nei nomi di posto e di piano delle mappe (`mapStrings`, `floorStrings`),
    nei cartigli (`TitleText`, `Font`) e nelle voci dei menu. In tutto il disco
    ne colloca **402**, e ne restavano fuori tre su quattro.

    Si riconosce una scritta collocata dal fatto che ha un testo **e** un
    posto: i 61 blocchi senza `X`/`Y` sono elenchi di dati (`ItemList`,
    `LivingList`, `WarpItem`), cioe' nomi che un'altra parte della schermata
    andra' a pescare, non testo da mettere sullo schermo.
    """
    out: list[dict] = []

    def walk(node, path):
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])
            return
        if not isinstance(node, dict):
            return
        for i, (s_k, x_k, y_k, a_k) in enumerate(_TEXT_KEYS):
            if isinstance(node.get(s_k), str) and x_k in node and y_k in node:
                out.append({'string': node[s_k],
                            'x': float(node[x_k]), 'y': float(node[y_k]),
                            'align': str(node.get(a_k) or 'Left'),
                            'at': '.'.join(path) or '(radice)',
                            # una spiegazione appartiene alla voce che la
                            # dichiara, e si disegna solo quando il cursore
                            # sta li'
                            'kind': 'description' if i >= 3 else 'text',
                            'owner': node if i >= 3 else None})
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                walk(v, path + [str(k)])

    walk(desc, [])
    return out


def entries(block) -> list[dict]:
    """Le voci a indice di un blocco: `Size` dice quante sono, e stanno nella
    parte a indice della stessa tabella."""
    if not isinstance(block, dict):
        return []
    return [v for _, v in sorted((k, v) for k, v in block.items()
                                 if isinstance(k, int) and isinstance(v, dict))]


def menus(desc: dict) -> list[dict]:
    """I blocchi che si navigano: `{name, entries}`.

    **Una voce e' una voce se il cursore ci puo' stare.** Il criterio e'
    `CursorX`/`CursorY`, non il nome del blocco - che infatti sono tre, e
    prenderne uno solo faceva perdere i menu veri: `Select` sono i 19 si/no,
    ma `Menu` e' il menu del titolo e quello di pausa, e `ClearMenu` e' il
    menu del titolo **a gioco finito**, con `NEW GAME+` in piu'.

    Sono **23 blocchi per 60 voci**, e la geometria dice come si percorrono:
    23 su 23 hanno le voci incolonnate, zero in riga.
    """
    out: list[dict] = []

    def walk(node, path):
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])
            return
        if not isinstance(node, dict):
            return
        es = entries(node)
        if es and all('CursorX' in e and 'CursorY' in e for e in es):
            out.append({'name': '.'.join(path) or '(radice)', 'entries': es})
            return
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                walk(v, path + [str(k)])

    walk(desc, [])
    return out


def label(entry: dict) -> str:
    """Il testo di una voce, comunque il blocco lo chiami."""
    for k in ('String', 'MenuString', 'Strings'):
        if isinstance(entry.get(k), str):
            return entry[k]
    return ''


def description(entry: dict) -> dict | None:
    """La riga che spiega la voce su cui sta il cursore, se c'e'.

    E' l'unico pezzo di interfaccia che **cambia al muoversi del cursore**:
    il menu del titolo e quello di pausa dichiarano per ogni voce la propria
    frase, sempre nello stesso posto in fondo allo schermo."""
    for s_k, x_k, y_k, a_k in _TEXT_KEYS[3:]:
        if isinstance(entry.get(s_k), str) and x_k in entry:
            return {'string': entry[s_k], 'x': float(entry[x_k]),
                    'y': float(entry[y_k]),
                    'align': str(entry.get(a_k) or 'Left')}
    return None


def cancel_choice(desc: dict) -> int | None:
    """Quale voce sceglie il tasto di annullamento, o `None` se non e' ammesso.

    `Cancel = {Enable, Index}`, e **l'indice si conta da zero**: tutte e 19 le
    schermate che lo dichiarano hanno le stesse due voci `YES`/`NO` e tutte e
    19 dicono `Index=1`. Contando da uno sarebbe `YES` in tutte, cioe'
    annullare vorrebbe dire acconsentire; contando da zero e' `NO` in tutte.
    E' la stessa base di `Start`, che vale 0 per la clip `In`.

    Le quattro che dichiarano `Enable=0` sono `ClearSave`,
    `DeleteSaveDataSelect`, `GameOverSaveSelect`, `GameOverResurrectSelect`:
    schermate in cui il gioco pretende una risposta invece di lasciar uscire.
    """
    c = desc.get('Cancel')
    if not isinstance(c, dict) or not int(c.get('Enable', 0)):
        return None
    return int(c.get('Index', 0))


def pages(desc: dict) -> tuple[int, int] | None:
    """L'intervallo di pagine che una schermata dichiara, o `None`.

    Lo dice `setting = {pageMin, pageMax}`, e sulle mappe dei sotterranei la
    pagina e' **il piano con il segno**: `B1` e' -1, `1F` e' 0, `2F` e' +1.
    Due conti indipendenti lo mettono alla prova e tornano tutti e due:

    - `pageMax - pageMin + 1` e' il numero di descrittori di piano di quel
      sotterraneo, **7 sotterranei su 7** (21 descrittori, 21 pagine);
    - le etichette che i descrittori stampano (`B2`, `5F`) cadono dentro
      l'intervallo del proprio sotterraneo, **19 su 19** in quelli a piu'
      piani.

    I due che restano fuori sono i sotterranei a **un piano solo**, che
    dichiarano `0..0` e `1..1` pur essendo tutti e due `B1`: dove non c'e'
    niente da sfogliare il numero non e' mantenuto.
    """
    s = desc.get('setting')
    if not isinstance(s, dict) or 'pageMin' not in s or 'pageMax' not in s:
        return None
    return int(s['pageMin']), int(s['pageMax'])


def opens(desc: dict, known) -> list[str]:
    """Le schermate che questa schermata **apre**, se lo dichiara.

    Il legame fra una schermata e la successiva quasi mai e' scritto: su 136
    schermate lo dichiarano **due**, per tre legami in tutto, e sempre nella
    stessa forma - un campo in fondo alla tabella, con la chiave uguale al
    valore:

        Pause = { ... , PauseTitleSelect = "PauseTitleSelect" };

    Sono `Pause` che apre `PauseTitleSelect` e `GameOver` che apre
    `GameOverSaveSelect` e `GameOverResurrectSelect`, cioe' tutte e tre la
    **finestra di conferma** di una scelta che non si torna indietro. Dove il
    seguito e' una domanda il disco lo dice; dove e' un'altra schermata no.
    """
    return sorted({v for v in desc.values()
                   if isinstance(v, str) and v in known})


def keybar(desc: dict, root: pathlib.Path) -> list[dict]:
    """La barra dei tasti: `{action, string, x, icon, hue}`.

    Ogni schermata che ne ha una dichiara **quali azioni offre** - in fondo
    allo schermo, una scritta per azione: `moveStrings`, `pageStrings`,
    `detailsStrings`, `canselStrings`. Le scritte stanno nel descrittore, le
    icone dei tasti nella scena, sotto un nodo che si chiama `KeyAssign`, e le
    une accanto alle altre: ogni scritta comincia **7-8 px dopo** la fine di
    un'icona.

    La striscia e' continua e alterna icona e piastra: nell'album dei nemici i
    sette rettangoli vanno da 673 a 1176 senza un buco, e i tre stretti sono
    la croce direzionale, la ✕ e la ○.

    `hue` e' il colore dominante dell'icona, che su questo hardware **e'** il
    tasto: la ✕ e' blu e la ○ e' rossa, e le due si separano da sole. Il
    grigio invece non separa niente - croce direzionale e dorsali sono tutti
    senza tinta - ed e' giusto che resti un nome solo.

    Dove la schermata **scorre** l'accoppiamento non si puo' fare, e non e' un
    difetto: la striscia e' parcheggiata fuori campo con il resto della scena
    mentre le scritte sono gia' al proprio posto, quindi non sono vicine a
    niente. Sono le stesse 5 schermate di sempre.

    E un'azione puo' non avere icona affatto: nell'album `PAGE` e' la prima
    scritta della striscia e non ha niente a sinistra, perche' a sfogliare
    sono le due frecce ai lati della pagina - `Left_Cursor` e `Right_Cursor`,
    che nella scena sono nodi per conto loro.
    """
    parts, lib = scene(desc.get('ScenePackageName', ''), root)
    if not parts:
        return []
    strip = [r for r in rects(parts) if 'KeyAssign' in r[11]]
    if not strip:
        return []
    lo, hi = min(r[1] for r in strip), max(r[3] for r in strip)
    icons = sorted((r for r in strip if (r[2] - r[0]) < 60),
                   key=lambda r: r[0])
    out = []
    for t in sorted(texts(desc), key=lambda t: t['x']):
        if not (lo - 8 <= t['y'] <= hi + 8):
            continue
        prima = [r for r in icons if r[2] <= t['x'] + 1]
        icon = max(prima, key=lambda r: r[2]) if prima else None
        if icon is not None and t['x'] - icon[2] > 40:
            icon = None                      # troppo lontana: non e' la sua
        out.append({'action': t['at'].split('.')[0], 'string': t['string'],
                    'x': t['x'], 'icon': icon,
                    'hue': _hue(icon, lib) if icon is not None else None})
    return out


#: Il colore con cui questo hardware nomina i propri tasti. Non e' una
#: convenzione presa da fuori: sulle texture del disco la ✕ e' disegnata blu e
#: la ○ rossa, e si guarda (`ui.py keys --png`).
HUES = ((210, 'croce'), (350, 'cerchio'), (300, 'quadrato'), (120, 'triangolo'))


def _hue(rect, lib):
    """Il colore dominante di un'icona, fra quelli che nominano un tasto."""
    import colorsys

    src = lib.image(rect[9])
    if src is None:
        return None
    w, h = src.size
    box = (int(rect[4] * w), int(rect[5] * h), int(rect[6] * w),
           int(rect[7] * h))
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    a = np.asarray(src.crop(box).convert('RGB'), dtype=np.float32) / 255.0
    hs = []
    for px in a.reshape(-1, 3):
        hh, ll, ss = colorsys.rgb_to_hls(*px)
        if ss > 0.35 and 0.15 < ll < 0.85:
            hs.append(hh * 360.0)
    if len(hs) < 8:
        # Grigio. Il colore qui non decide: la croce direzionale e i dorsali
        # `L1`/`R1` sono tutti e due senza tinta, e a separarli e' la forma.
        return 'grigio'
    m = float(np.median(hs))
    return min(HUES, key=lambda k: min(abs(k[0] - m),
                                       360 - abs(k[0] - m)))[1]


#: Un'etichetta di piano: `B3` o `5F`.
_FLOOR = re.compile(r'^(B?)(\d+)F?$')


def floor_label(page: int) -> str:
    """L'etichetta di un piano dal numero di pagina: -1 e' `B1`, 0 e' `1F`."""
    return f'B{-page}' if page < 0 else f'{page + 1}F'


def floor_page(label: str) -> int | None:
    """Il numero di pagina di un'etichetta: `B3` e' -3, `5F` e' 4."""
    m = _FLOOR.match(_ascii(label).strip())
    if not m:
        return None
    return -int(m.group(2)) if m.group(1) == 'B' else int(m.group(2)) - 1


# --------------------------------------------------------- la composizione

def rects(parts):
    """I rettangoli di una scena di interfaccia: `(x0,y0,x1,y1, u0,v0,u1,v1,
    z, texture)`, gia' in coordinate di schermo.

    Le coppie di triangoli si ricompongono in rettangoli. Il verso della V si
    prende dai dati e non si assume: si accoppia il vertice piu' in alto sullo
    schermo con la V che gli tocca."""
    out = []
    for p in parts:
        tri = p.idx.reshape(-1, 3)
        for i in range(0, len(tri) - 1, 2):
            v = sorted(set(tri[i].tolist()) | set(tri[i + 1].tolist()))
            if len(v) != 4:
                continue
            xy = p.pos[v]
            uv = p.uv[v]
            x0, x1 = float(xy[:, 0].min()), float(xy[:, 0].max())
            # la Y del modello cresce verso l'alto: sullo schermo si rovescia
            y0, y1 = float(-xy[:, 1].max()), float(-xy[:, 1].min())
            if x1 - x0 < 0.5 or y1 - y0 < 0.5:
                continue
            u0, u1 = float(uv[:, 0].min()), float(uv[:, 0].max())
            v0, v1 = float(uv[:, 1].min()), float(uv[:, 1].max())
            # chi sta in alto sullo schermo ha la V piu' piccola? lo dice il
            # dato, confrontando un vertice alto con la sua V
            top = int(np.argmax(xy[:, 1]))
            flip = uv[top, 1] > (v0 + v1) / 2
            out.append((x0, y0, x1, y1, u0, v0, u1, v1,
                        float(xy[0, 2]), p.tex, flip, p.name))
    out.sort(key=lambda r: r[8])            # dal fondo al fronte
    return out


def scene(name: str, root: pathlib.Path, grow: float = 1.0):
    """La scena di una schermata: `(parti, libreria di texture)`.

    Il nome del descrittore e' un percorso senza estensione
    (`UserInterface/Select/SelectA`), e le due lingue stanno in file diversi:
    si preferisce quello inglese quando c'e', perche' e' il disco europeo.

    `grow` e' quanto la schermata e' aperta, da 0 (com'e' sul disco) a 1."""
    import view

    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    base = data / name
    for suffix in ('_eng.ps3.dsb', '.ps3.dsb'):
        p = base.with_name(base.name + suffix)
        if p.exists():
            return view.load(p, unfold=grow)[0], view.Texlib(p, data)
    return None, None


# ------------------------------------------------------------- l'animazione

def clips(desc: dict) -> list[dict]:
    """Le clip che una schermata dichiara, anche quelle annidate.

    `Animation` e' un albero: le schermate semplici hanno le quattro clip in
    cima (`In`, `Main`, `Out`, `Cursor`), quelle grosse le raggruppano per
    pannello (`Menu.WindowIn`, `Display.MessageOut`). Ogni foglia si riconosce
    perche' porta insieme `Start` e `Size`.

    E qui c'e' la cosa che il nome fa credere sbagliata: **`Start` non e' un
    tempo, e' un indice**. Sulle 36 schermate che dichiarano `In` vale 0 tutte
    e 36 volte, `Main` vale 1 tutte e 33, `Out` vale 2 tutte e 36: un tempo che
    non cambia mai non e' un tempo. Nelle schermate grosse i valori sono densi
    e consecutivi - `Option` va da 0 a 38 senza buchi - cioe' e' la posizione
    in una tabella di clip. `Size` invece varia (0,4 / 0,5 / 1,0) ed e' la
    **durata in secondi**.
    """
    out: list[dict] = []

    def walk(node, path):
        # Un gruppo puo' essere un **array** invece che un dizionario: le dieci
        # tacche del volume in `Option` stanno in `Volume={{Start=10,...},...}`,
        # e sono esattamente i dieci indici che altrimenti mancherebbero fra
        # `Display` e `Sound`. Chi scende solo nei dizionari li perde.
        if isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])
            return
        if not isinstance(node, dict):
            return
        if 'Start' in node and 'Size' in node:
            out.append({'name': '.'.join(path),
                        'index': int(node['Start']),
                        'seconds': float(node['Size']),
                        'extra': {k: v for k, v in node.items()
                                  if k not in ('Start', 'Size')}})
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                walk(v, path + [k])

    walk(desc.get('Animation'), [])
    out.sort(key=lambda c: (c['index'], c['name']))
    return out


def clip(desc: dict, name: str) -> dict | None:
    """Una clip per nome, anche annidata (`Menu.Cursor`)."""
    for c in clips(desc):
        if c['name'] == name or c['name'].rsplit('.', 1)[-1] == name:
            return c
    return None


def grow_at(c: dict | None, t: float) -> float:
    """Quanto e' aperta una schermata al tempo `t`, in secondi dall'inizio
    della clip.

    Di questo moto il disco da' tutti e due gli estremi - il pezzo e' esportato
    con la scala a zero e la mesh e' intera - e la durata (`Size`). **La curva
    no**: fra i tipi di oggetto del `.dsb` l'animazione non c'e'. Qui si
    interpola lineare, che e' l'unica scelta che non aggiunge un numero
    inventato; se l'EBOOT dira' che c'e' un'attenuazione, cambia una riga.
    """
    if not c or c['seconds'] <= 0:
        return 1.0
    return min(1.0, max(0.0, t / c['seconds']))


def compose(desc: dict, root: pathlib.Path, glyphs=None, cursor: int = 0,
            size=SCREEN, grow: float = 1.0, keep=None, menu: int = 0):
    """Una schermata, composta: la scena, poi le scritte che dichiara.

    `menu` e' quale blocco navigabile comanda e `cursor` quale sua voce e'
    evidenziata; il descrittore dice anche dove va il cursore per ognuna
    (`CursorX`, `CursorY`). `grow` e' quanto la schermata e' aperta: a 1 e' la
    posa finale, sotto e' un fotogramma dell'animazione d'apertura.
    """
    from PIL import Image

    img = Image.new('RGBA', size, (0, 0, 0, 255))
    sx, sy = size[0] / SCREEN[0], size[1] / SCREEN[1]
    pkg = desc.get('ScenePackageName', '')
    parts, lib = scene(pkg, root, grow)
    tint = diffuse_by_node(pkg, root) if parts else {}

    # Il blocco navigabile su cui sta il cursore, se la schermata ne ha uno:
    # la sua voce corrente porta con se' la propria riga di spiegazione, e le
    # altre otto non si disegnano - se no le nove frasi del menu di pausa
    # finiscono tutte nello stesso punto.
    blocks = menus(desc)
    block = blocks[menu] if 0 <= menu < len(blocks) else None
    here = block['entries'][cursor] if block and \
        0 <= cursor < len(block['entries']) else None

    rs = rects(parts) if parts else []
    parked, per_voce = cursor_art(rs, block)
    # I cursori che non toccano a questa voce non si disegnano, e quello
    # parcheggiato non si disegna all'origine: va messo dove dice la voce.
    salta = {id(r) for i, r in per_voce.items() if i != cursor}
    if parked is not None:
        salta.add(id(parked))
    if parts:
        for r in rs:
            (x0, y0, x1, y1, u0, v0, u1, v1, _z, tex, flip, _nm) = r
            if id(r) in salta or (keep is not None and not keep(_nm)):
                continue
            src = lib.image(tex) if tex else None
            if src is None:
                continue
            w, h = src.size
            box = (max(0, int(round(u0 * w))), max(0, int(round(v0 * h))),
                   min(w, int(round(u1 * w))), min(h, int(round(v1 * h))))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            piece = _tinted(src.crop(box), tint.get(_nm))
            if flip:
                piece = piece.transpose(Image.FLIP_TOP_BOTTOM)
            dw, dh = max(1, int(round((x1 - x0) * sx))), \
                max(1, int(round((y1 - y0) * sy)))
            img.alpha_composite(piece.resize((dw, dh), Image.NEAREST),
                                (int(round(x0 * sx)), int(round(y0 * sy))))
    if glyphs is None or grow < 1.0:
        # A schermata non ancora aperta le scritte non si disegnano: cadrebbero
        # fuori dal riquadro che le contiene. Il disco non lo dichiara - e'
        # una scelta nostra, ed e' l'unica cosa qui dentro che lo sia.
        return img

    # Una schermata puo' dichiarare piu' blocchi navigabili **alternativi**:
    # il titolo ha `Menu` e `ClearMenu`, che sono lo stesso menu prima e dopo
    # aver finito il gioco. Si disegna quello che comanda, non tutti e due.
    altri = {m['name'].split('.')[0] for m in blocks} - \
        ({block['name'].split('.')[0]} if block else set())

    occupato: set[tuple[int, int]] = set()
    for t in texts(desc):
        if t['kind'] == 'description' and t['owner'] is not here:
            continue
        if t['at'].split('.')[0] in altri:
            continue
        posto = (int(t['x']), int(t['y']))
        # Una schermata puo' dichiarare piu' scritte **nello stesso punto**:
        # sono alternative fra cui il motore sceglie (l'album dei nemici ne ha
        # tre a (594,64) - il conto, «completo?» e «completo!»). Qui si mette
        # la prima invece di sovrapporle.
        if posto in occupato:
            continue
        occupato.add(posto)
        _text(img, t, glyphs, sx, sy)
    if here is not None and 'CursorX' in here and parked is not None:
        _blit(img, parked, lib, tint, float(here['CursorX']) * sx,
              float(here['CursorY']) * sy, sx, sy)
    elif here is not None and 'CursorX' in here and cursor not in per_voce:
        _mark(img, float(here['CursorX']) * sx, float(here['CursorY']) * sy, sy)
    return img


def cursor_art(rs, block) -> tuple:
    """Il disegno del cursore, che sta **nella scena**: `(parcheggiato, per
    voce)`.

    Era l'ultimo pezzo di interfaccia che ci mettevamo noi, e non ce n'era
    bisogno: le scene lo portano, in due modi diversi.

    - **Parcheggiato all'origine**, come tutto cio' che il descrittore
      colloca: un `Cursor_01` di 16-17 px per lato a `(0, 0)`. Cosi' fanno 6
      delle 7 scene con un menu, e va messo dove dice `CursorX`/`CursorY`.
    - **Uno per riga, gia' collocato**: il menu di pausa ha nove marcatori
      alti 31 px, e le loro posizioni sono quelle che il descrittore dichiara
      voce per voce, a un paio di pixel (530 contro 529, 86 contro 84). Li' il
      cursore non si sposta: se ne accende uno.

    Nel secondo caso vanno spenti gli altri otto, che e' la stessa forma della
    mappa del sotterraneo - la scena porta tutti gli stati e il dato dice
    quale.
    """
    parked = per_voce = None
    for r in rs:
        if r[11].lower().startswith('cursor') and abs(r[0]) < 40 \
                and abs(r[1]) < 40 and (r[2] - r[0]) < 48 \
                and (r[3] - r[1]) < 48:
            parked = r
            break
    per_voce = {}
    if block:
        for i, e in enumerate(block['entries']):
            cx, cy = float(e['CursorX']), float(e['CursorY'])
            vicino = [r for r in rs if r is not parked
                      and abs(r[0] - cx) <= 6 and abs(r[1] - cy) <= 6]
            if len(vicino) == 1:
                per_voce[i] = vicino[0]
        # Vale come marcatore solo se ce n'e' uno **per ogni** voce: uno che
        # ne copre due o tre e' un pezzo di finestra capitato li' vicino.
        if len(per_voce) != len(block['entries']):
            per_voce = {}
    return parked, per_voce


def _blit(img, r, lib, tint, x, y, sx, sy):
    """Un rettangolo della scena, messo dove dice il descrittore invece che
    dove sta parcheggiato."""
    from PIL import Image

    src = lib.image(r[9]) if r[9] else None
    if src is None:
        return
    w, h = src.size
    box = (max(0, int(round(r[4] * w))), max(0, int(round(r[5] * h))),
           min(w, int(round(r[6] * w))), min(h, int(round(r[7] * h))))
    if box[2] <= box[0] or box[3] <= box[1]:
        return
    piece = _tinted(src.crop(box), tint.get(r[11]))
    if r[10]:
        piece = piece.transpose(Image.FLIP_TOP_BOTTOM)
    dw = max(1, int(round((r[2] - r[0]) * sx)))
    dh = max(1, int(round((r[3] - r[1]) * sy)))
    img.alpha_composite(piece.resize((dw, dh), Image.NEAREST),
                        (int(round(x)), int(round(y))))


def _text(img, t, glyphs, sx, sy):
    """Una scritta al suo posto.

    Due numeri che erano tarati e adesso sono misurati. La **scala** e' 1: la
    cella del font e' 32x32, che e' l'altezza di riga con cui il riquadro di
    dialogo torna (`485 + 3x32 + 2x8 = 597` contro un corpo che finisce a
    598). E `Y` e' il **bordo alto** della riga, non il suo centro - lo dice
    il cursore, che il descrittore mette 7 px piu' in giu' della scritta:
    alto 16 px dentro una riga di 32, cade esattamente in mezzo.
    """
    s = t.get('string')
    if not s:
        return
    tile = glyphs.render(s, scale=max(sy, 0.1))
    x, y = t['x'] * sx, t['y'] * sy
    align = str(t.get('align') or 'Left').lower()
    if align == 'center':
        x -= tile.width / 2
    elif align == 'right':
        x -= tile.width
    img.alpha_composite(tile, (int(x), int(y)))


def _mark(img, x, y, sy):
    """Il cursore. Il descrittore ne dichiara la posizione ma non il disegno:
    quello sta nella scena, ed e' l'unico pezzo qui dentro che e' nostro."""
    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    r = max(6.0, 9.0 * sy)
    d.polygon([(x - r, y - r), (x - r, y + r), (x + r * 0.9, y)],
              fill=(255, 255, 255, 255))


def _tinted(piece, rgb):
    """Il pezzo moltiplicato per il diffuse del suo materiale. L'alfa non si
    tocca: a spegnere un pezzo e' il colore, non la trasparenza."""
    if not rgb:
        return piece
    a = np.array(piece, dtype=np.float32)
    a[:, :, 0] *= rgb[0]
    a[:, :, 1] *= rgb[1]
    a[:, :, 2] *= rgb[2]
    from PIL import Image as _I

    return _I.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


def diffuse_by_node(name: str, root: pathlib.Path) -> dict:
    """Il colore diffuso che ogni nodo di una scena porta, per nome.

    Serve perche' l'interfaccia di questo gioco **tinge**: i tre stati di una
    stanza sulla mappa del sotterraneo sono la stessa mesh, con le stesse UV,
    sulla stessa texture, e a distinguerli e' solo il diffuse del materiale -
    `room_on` 1,0, `room_off` 0,5, `room_still` 0,0. Chi compone guardando la
    sola texture li disegna tutti e tre identici.
    """
    import dsb

    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    base = data / name
    p = None
    for suffix in ('_eng.ps3.dsb', '.ps3.dsb'):
        q = base.with_name(base.name + suffix)
        if q.exists():
            p = q
            break
    if p is None:
        return {}
    f = dsb.Dsb(p.read_bytes(), str(p))
    mats = f.materials()
    geo = {m['name']: m for m in f.meshes()}
    out = {}
    for n in f.nodes():
        if n['attached'] is None:
            continue
        m = geo.get(f.object(n['attached'])['name'])
        if not m or not m['chunks']:
            continue
        d = mats.get(m['chunks'][0]['material'], {}).get('diffuse')
        if d and tuple(d[:3]) != (1.0, 1.0, 1.0):
            out[n['name']] = tuple(d[:3])
    return out


# ------------------------------------------------------------------ l'input

class Screen:
    """Una schermata come cosa che risponde ai tasti.

    Di questa parte il disco dichiara **quasi tutto**, e conviene dire cosa e
    cosa no, perche' e' l'unico posto dell'interfaccia dove qualcosa resta
    nostro.

    Letto dal disco:

    - **quali voci ci sono** e dove: 23 blocchi per 60 voci, riconosciuti dal
      fatto che il cursore ci puo' stare (`menus()`);
    - **su quale asse si scorre**: le voci sono incolonnate in 23 blocchi su
      23, quindi si sale e si scende, non si va a destra e a sinistra. Il
      passo del cursore e' di 32 px fra due voci, cioe' **una riga di font** -
      lo stesso 32 con cui il riquadro di dialogo torna a 597 contro un corpo
      che finisce a 598;
    - **dove sta il cursore**: `CursorX`/`CursorY` per ogni voce, che sono 34
      px a sinistra e 7 in su rispetto alla scritta, sempre gli stessi;
    - **cosa fa il tasto di annullamento**: `Cancel = {Enable, Index}`, e
      l'indice si conta da zero (`cancel_choice()`);
    - **quante pagine si sfogliano**: `setting = {pageMin, pageMax}`;
    - **quali azioni la schermata offre**, con l'icona del tasto: `keybar()`.

    Scelto da noi, perche' il disco non lo dice: che dall'ultima voce si torni
    alla prima (`wrap`). Con nove voci in pausa serve, ma resta una scelta e
    non una lettura - si spegne con `wrap=False`.
    """

    def __init__(self, desc: dict, root: pathlib.Path, wrap: bool = True):
        self.desc = desc
        self.root = root
        self.blocks = menus(desc)
        self.menu = 0
        self.cursor = 0
        self.wrap = wrap
        self.chosen: int | None = None
        self.cancelled = False
        rng = pages(desc)
        self.page_range = rng
        self.page = rng[0] if rng else None

    # --- lo stato

    @property
    def entries(self) -> list[dict]:
        if not (0 <= self.menu < len(self.blocks)):
            return []
        return self.blocks[self.menu]['entries']

    @property
    def here(self) -> dict | None:
        es = self.entries
        return es[self.cursor] if 0 <= self.cursor < len(es) else None

    @property
    def done(self) -> bool:
        return self.chosen is not None

    def labels(self) -> list[str]:
        return [label(e) for e in self.entries]

    # --- i tasti

    def move(self, step: int) -> None:
        """Su e giu' fra le voci. L'asse non e' una scelta: le voci sono
        incolonnate in tutti e 23 i blocchi del disco."""
        n = len(self.entries)
        if n < 2:
            return
        self.cursor = (self.cursor + step) % n if self.wrap \
            else max(0, min(n - 1, self.cursor + step))

    def decide(self) -> int | None:
        """La ✕: sceglie la voce su cui sta il cursore."""
        if self.entries:
            self.chosen = self.cursor
        return self.chosen

    def cancel(self) -> int | None:
        """La ○: sceglie la voce che il descrittore nomina, se lo ammette.

        Non e' «esci»: e' **scegliere una voce precisa**, quella di indice
        `Cancel.Index`, che su tutte e 19 le schermate che lo dichiarano e'
        `NO`. Dove `Enable=0` il tasto non fa niente, ed e' dichiarato cosi'
        nelle quattro schermate in cui il gioco pretende una risposta.
        """
        i = cancel_choice(self.desc)
        if i is None:
            return None
        self.cursor = min(max(i, 0), max(len(self.entries) - 1, 0))
        self.cancelled = True
        self.chosen = self.cursor
        return self.chosen

    def turn(self, step: int) -> bool:
        """Sfoglia, dove la schermata dichiara di avere pagine.

        L'intervallo e' quello del disco e non si esce: sulla torre oscura va
        da 0 a 6, cioe' dal primo al settimo piano."""
        if self.page_range is None:
            return False
        lo, hi = self.page_range
        nuovo = min(max(self.page + step, lo), hi)
        cambia = nuovo != self.page
        self.page = nuovo
        return cambia

    # --- il disegno

    def draw(self, glyphs=None, size=SCREEN, grow: float = 1.0):
        return compose(self.desc, self.root, glyphs, cursor=self.cursor,
                       size=size, grow=grow, menu=self.menu)

    def state(self) -> str:
        """Una riga che dice dove si e', per il registro e per le verifiche."""
        es = self.labels()
        voce = es[self.cursor] if 0 <= self.cursor < len(es) else '-'
        r = f'voce {self.cursor + 1}/{len(es)} {_ascii(voce)!r}'
        if self.page_range is not None:
            lo, hi = self.page_range
            r += f'  pagina {self.page} [{lo},{hi}] = {floor_label(self.page)}'
        if self.done:
            r += f'  -> scelto {_ascii(voce)!r}' \
                 + ('  (annullando)' if self.cancelled else '')
        return r


#: I tasti, e cosa fanno. I nomi sono quelli che la barra dichiara.
KEYS = {'su': lambda s: s.move(-1), 'giu': lambda s: s.move(+1),
        'croce': lambda s: s.decide(), 'cerchio': lambda s: s.cancel(),
        'l1': lambda s: s.turn(-1), 'r1': lambda s: s.turn(+1)}


def _ascii(s: str) -> str:
    """Le scritte del disco sono a **larghezza piena** (`ＹＥＳ`), che e' come
    il font le disegna. Per stamparle in un registro si riportano ad ASCII."""
    out = []
    for ch in str(s):
        o = ord(ch)
        out.append(chr(o - 0xFEE0) if 0xFF01 <= o <= 0xFF5E
                   else (' ' if o == 0x3000 else ch))
    return ''.join(out)


def descriptor_file(path: pathlib.Path) -> dict:
    """I descrittori dichiarati da **un solo** file Lua.

    `descriptors()` percorre i 109 file del disco, che costa qualche secondo;
    quando si sa gia' dove sta quello che serve - il riquadro di dialogo sta in
    `UserInterface/Message/Message.lua.eu` - conviene aprire solo quello."""
    from lupa import LuaRuntime

    try:
        src = source(path)
    except OSError:
        return {}
    import host

    # I descrittori piu' ricchi nominano costanti native che nessuno script
    # definisce - `LIVING.FIELD_GRASS`, `GameDataFlags.MONSTERBOOK_Rabbit`,
    # `item.Item.IL_RED_APPLE` - e senza di loro il file non gira affatto.
    # E' lo stesso ostacolo degli eventi, e la soluzione e' gia' scritta: le
    # tabelle permissive di `host.BOOT`, che ricordano il proprio nome.
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(host.BOOT)
    before = set(lua.globals().keys())
    try:
        lua.execute(src)
    except Exception:                                            # noqa: BLE001
        return {}
    out = {}
    for k in set(lua.globals().keys()) - before:
        t = _plain(lua.globals()[k])
        if isinstance(t, dict):
            out[k] = t
    return out


def widget(name: str, root: pathlib.Path, keep: tuple[str, ...] = (),
           grow: float = 1.0):
    """Un singolo pezzo d'interfaccia, ritagliato dalla sua scena:
    `(immagine RGBA, x, y)` nello schermo virtuale 1280x720.

    `keep` sono i prefissi dei nodi da tenere. Serve perche' una scena porta
    piu' varianti dello stesso oggetto: `UserInterface/Message` contiene il
    riquadro di dialogo in due misure - `Message_a/b/c` (505x142) e
    `MessageBig_a/b/c` (686x158) - e la grande contiene la piccola, quindi non
    si separano ritagliando.
    """
    from PIL import Image

    parts, lib = scene(name, root, grow)
    if not parts:
        return None, 0, 0
    tint = diffuse_by_node(name, root)
    rs = [r for r in rects(parts)
          if not keep or any(r[11].startswith(k) for k in keep)]
    rs = [r for r in rs if (lib.image(r[9]) if r[9] else None) is not None]
    if not rs:
        return None, 0, 0
    ox = min(r[0] for r in rs)
    oy = min(r[1] for r in rs)
    w = int(round(max(r[2] for r in rs) - ox))
    h = int(round(max(r[3] for r in rs) - oy))
    img = Image.new('RGBA', (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    for (x0, y0, x1, y1, u0, v0, u1, v1, _z, tex, flip, _nm) in rs:
        src = lib.image(tex)
        sw, sh = src.size
        box = (max(0, int(round(u0 * sw))), max(0, int(round(v0 * sh))),
               min(sw, int(round(u1 * sw))), min(sh, int(round(v1 * sh))))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        piece = _tinted(src.crop(box), tint.get(_nm))
        if flip:
            piece = piece.transpose(Image.FLIP_TOP_BOTTOM)
        dw, dh = max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))
        img.alpha_composite(piece.resize((dw, dh), Image.NEAREST),
                            (int(round(x0 - ox)), int(round(y0 - oy))))
    return img, ox, oy


#: I tre stati che la scena di una mappa di sotterraneo disegna per ogni
#: stanza. Non sono tre disegni: sono la **stessa** mesh, con le stesse UV,
#: sulla stessa texture, e a distinguerli e' il diffuse del materiale -
#: `room_on` 1,0, `room_off` 0,5, `room_still` 0,0. Una scala, e la scala li
#: ordina: il piu' scuro e' quello che non si e' ancora visto.
#:
#: Il nome dei tre stati non dice a cosa servano, e questa corrispondenza
#: resta **nostra**; ma non e' un'ipotesi al buio, perche' 0,0 su una mappa
#: vuol dire una stanza che non si vede.
ROOM_STATES = {'ignota': 'room_still', 'vista': 'room_off',
               'qui': 'room_on'}


def dungeon_map(dungeon: int, floor: int, root: pathlib.Path,
                seen=(), here=None, size=SCREEN):
    """La mappa di un piano di sotterraneo, con le stanze viste accese.

    Era ferma su «serve uno stato di partita che non esiste». Lo stato adesso
    c'e': la griglia dichiara a quale **stanza** appartiene ogni cella (vedi
    `walk.Grid.rooms`), e questa scena ha un pezzo per stanza e per stato.

    Che i due insiemi di stanze siano lo stesso e' misurato: 404 numeri su 413
    in 21 piani. E il descrittore chiude il cerchio nominando i campi che nella
    griglia sono cifre mute - le porte dichiarano `groupId` e `objectId`, che
    sono il `-g` e il `-o` della cella.
    """
    p = _map_descriptor(root, dungeon, floor)
    if p is None:
        return None
    desc = None
    for t in descriptor_file(p).values():
        if isinstance(t, dict) and 'ScenePackageName' in t:
            desc = t
    if desc is None:
        return None
    seen = set(seen)

    def keep(name: str) -> bool:
        head = name.split('-')[0]
        m = re.match(r'room_(on|off|still)_(\d+)$', head)
        if not m:
            return True                      # sfondo, cornice, porte, cursori
        state, n = m.group(1), int(m.group(2))
        want = ROOM_STATES['qui'] if n == here else \
            ROOM_STATES['vista'] if n in seen else ROOM_STATES['ignota']
        return f'room_{state}' == want

    return compose(desc, root, size=size, keep=keep)


def dungeon_floors(dungeon: int, root: pathlib.Path) -> list[dict]:
    """I piani di un sotterraneo: `{seq, page, label}`, dal basso in su.

    `seq` e' il numero nel nome del descrittore (`dungeonMap06_03`), `page` il
    numero di pagina - il **piano con il segno** - e `label` l'etichetta che il
    disco stampa (`B3`).

    I due non vanno d'accordo per costruzione: il sotterraneo 5 tiene i propri
    descrittori nell'ordine `1F`, `2F`, `B1`, cioe' la successione dei file non
    e' la successione dei piani. E il primo descrittore, che e' quello che
    porta `setting`, **non dichiara il proprio piano**: elenca in un array le
    etichette di tutti i piani del sotterraneo, perche' disegna il selettore.

    Il suo piano si ricava per differenza: e' quello che gli altri non hanno
    preso. Torna in tutti e cinque i sotterranei a piu' piani.
    """
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    d = data / f'UserInterface/radar/dungeonMap/{dungeon:02d}'
    if not d.is_dir():
        return []
    trovati = {}
    rng = None
    for p in sorted(d.glob(f'dungeonMap{dungeon:02d}*.lua.eu')):
        m = re.search(r'_(\d+)\.lua\.eu$', p.name)
        seq = int(m.group(1)) if m else 1
        for t in descriptor_file(p).values():
            if not isinstance(t, dict) or 'TexturePackageName' not in t:
                continue
            rng = rng or pages(t)
            solo = [x['string'] for x in texts(t)
                    if x['at'].split('.')[0] == 'floorStrings']
            if not solo:
                # Il primo descrittore elenca in `fontStrings` le etichette di
                # tutti i piani, perche' disegna il selettore. Se il
                # sotterraneo ha **un piano solo** quell'elenco ne nomina uno
                # e basta, quindi lo dichiara.
                solo = [x['string'] for x in texts(t)
                        if x['at'].split('.')[0] == 'fontStrings'
                        and _FLOOR.match(_ascii(x['string']).strip())]
                if len(solo) != 1:
                    solo = []
            trovati[seq] = _ascii(solo[0]).strip() if solo else None
    if rng is None or not trovati:
        return []
    lo, hi = rng
    tutte = [floor_label(p) for p in range(lo, hi + 1)]
    prese = {v for v in trovati.values() if v}
    resto = [x for x in tutte if x not in prese]
    out = []
    for seq in sorted(trovati):
        lab = trovati[seq] or (resto.pop(0) if resto else None)
        out.append({'seq': seq, 'page': floor_page(lab) if lab else None,
                    'label': lab})
    return sorted(out, key=lambda r: (r['page'] is None, r['page']))


def _map_descriptor(root: pathlib.Path, dungeon: int, floor: int):
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    d = data / f'UserInterface/radar/dungeonMap/{dungeon:02d}'
    for name in (f'dungeonMap{dungeon:02d}_{floor:02d}.lua.eu',
                 f'dungeonMap{dungeon:02d}.lua.eu'):
        if (d / name).exists():
            return d / name
    return None


def _parked(data: pathlib.Path) -> tuple[int, int]:
    """Quanta geometria d'interfaccia e' parcheggiata fuori campo, e su quale
    asse: `(fuori campo, fuori solo in X)`.

    Le schermate a scorrimento non sono chiuse da una scala, sono **spostate**:
    il menu degli oggetti tiene le sue finestre a `x=-600` e `x=1300`. Il conto
    che conta e' su quale asse, perche' dice che il moto e' orizzontale."""
    import dsb

    off = offx = 0
    for p in sorted((data / 'UserInterface').rglob('*.ps3.dsb')):
        try:
            f = dsb.Dsb(p.read_bytes(), str(p))
        except Exception:                                        # noqa: BLE001
            continue
        by_index = {n['index']: n for n in f.nodes()}
        meshes = {m['name']: m['bbox'] for m in f.meshes()}
        for n in by_index.values():
            if n['attached'] is None:
                continue
            bb = meshes.get(f.object(n['attached'])['name'])
            if bb is None:
                continue
            b0, b1 = bb
            w = f.world(n, by_index)
            xs, ys = [], []
            for i in range(4):
                q = dsb.apply(w, (b0[0] if i & 1 else b1[0],
                                  b0[1] if i & 2 else b1[1], 0.0))
                xs.append(q[0])
                ys.append(-q[1])            # sullo schermo la Y si rovescia
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            if x1 - x0 < 1 or y1 - y0 < 1:
                continue                     # gia' chiuso da una scala nulla
            ox = x1 <= 2 or x0 >= SCREEN[0] - 2
            oy = y1 <= 2 or y0 >= SCREEN[1] - 2
            off += ox or oy
            offx += ox and not oy
    return off, offx


# ------------------------------------------------------------- da riga di comando

def _root(argv, i=2):
    return pathlib.Path(argv[i] if len(argv) > i else '../extract')


def cmd_list(root: pathlib.Path) -> int:
    d = descriptors(root)
    print(f'{len(d)} schermate dichiarate')
    for k in sorted(d):
        t = d[k]
        n_m = len(texts(t))
        n_s = sum(len(m['entries']) for m in menus(t))
        anim = 'anim' if isinstance(t.get('Animation'), dict) else '    '
        pag = f'{pages(t)[0]}..{pages(t)[1]}' if pages(t) else ''
        print(f'  {k:<26} {n_m:>2} scritte {n_s:>2} voci  {anim} {pag:<7} '
              f'{t.get("ScenePackageName", "")}')
    return 0


def cmd_show(name: str, out: pathlib.Path, root: pathlib.Path,
             size=SCREEN) -> int:
    import font as font_mod

    d = descriptors(root)
    if name not in d:
        near = [k for k in d if name.lower() in k.lower()]
        print(f'{name} non e una schermata dichiarata'
              + (f'; forse: {", ".join(near[:6])}' if near else ''))
        return 1
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    glyphs = font_mod.Font(data / 'UserInterface/Font/Font.lua.eu')
    img = compose(d[name], root, glyphs, size=size)
    img.convert('RGB').save(out)
    t = d[name]
    ms = menus(t)
    print(f'{name}: scena {t.get("ScenePackageName")}, '
          f'{len(texts(t))} scritte, '
          f'{sum(len(m["entries"]) for m in ms)} voci in {len(ms)} blocchi '
          f'-> {out}')
    return 0


def cmd_clips(name: str, root: pathlib.Path) -> int:
    """La tabella delle clip di una schermata, per indice."""
    d = descriptors(root)
    names = [name] if name in d else sorted(k for k in d
                                            if name.lower() in k.lower())
    if not names:
        print(f'{name} non e una schermata dichiarata')
        return 1
    for k in names:
        cl = clips(d[k])
        if not cl:
            print(f'{k}: nessuna clip')
            continue
        idx = [c['index'] for c in cl]
        gaps = sorted(set(range(max(idx) + 1)) - set(idx))
        print(f'{k}: {len(cl)} clip, indici 0..{max(idx)}'
              + (f', buchi {gaps}' if gaps else ', densi'))
        for c in cl:
            extra = '  ' + ' '.join(f'{a}={b}' for a, b in c['extra'].items()) \
                if c['extra'] else ''
            print(f'  [{c["index"]:>2}] {c["name"]:<28} {c["seconds"]:>4}s{extra}')
    return 0


def cmd_anim(name: str, out: pathlib.Path, root: pathlib.Path,
             which: str = 'In', frames: int = 8, size=SCREEN) -> int:
    """I fotogrammi di una clip d'apertura, uno per file."""
    import font as font_mod

    d = descriptors(root)
    if name not in d:
        print(f'{name} non e una schermata dichiarata')
        return 1
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    glyphs = font_mod.Font(data / 'UserInterface/Font/Font.lua.eu')
    c = clip(d[name], which)
    if c is None:
        print(f'{name} non dichiara la clip {which}; clip: '
              + ', '.join(x['name'] for x in clips(d[name])))
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    for i in range(frames):
        t = c['seconds'] * i / max(frames - 1, 1)
        g = grow_at(c, t)
        img = compose(d[name], root, glyphs, size=size, grow=g)
        p = out.with_name(f'{out.stem}_{i:02d}{out.suffix or ".png"}')
        img.convert('RGB').save(p)
        print(f'  t={t:.3f}s  aperta {g*100:>5.1f}%  -> {p.name}')
    print(f'{name}: clip {c["name"]} [indice {c["index"]}], '
          f'{c["seconds"]}s, {frames} fotogrammi')
    return 0


def cmd_map(argv, root: pathlib.Path) -> int:
    """La mappa di un piano di sotterraneo.

    Senza `--seen`, le stanze viste sono quelle che la **griglia** dichiara,
    cioe' tutte quelle del piano: e' il modo piu' onesto di far vedere che i
    due file parlano della stessa cosa."""
    import walk

    dungeon = int(argv[1])
    floor = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 1
    out = pathlib.Path(next((a for a in argv[3:]
                             if a.endswith('.png')), 'map.png'))
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    g = walk.Atlas(data).grid(f'd_{dungeon}_1_{floor}')
    seen = sorted(g.rooms) if g else []
    if '--seen' in argv:
        seen = [int(x) for x in argv[argv.index('--seen') + 1].split(',')]
    here = int(argv[argv.index('--here') + 1]) if '--here' in argv else \
        (seen[0] if seen else None)
    img = dungeon_map(dungeon, floor, root, seen=seen, here=here)
    if img is None:
        print(f'sotterraneo {dungeon} piano {floor}: nessun descrittore')
        return 1
    img.convert('RGB').save(out)
    print(f'sotterraneo {dungeon} piano {floor}: {len(seen)} stanze dalla '
          f'griglia, stanza corrente {here} -> {out}')
    return 0


def cmd_menus(name: str, root: pathlib.Path) -> int:
    """I blocchi navigabili: quali voci ha una schermata e cosa spiegano."""
    d = descriptors(root)
    names = [name] if name in d else sorted(
        k for k in d if not name or name.lower() in k.lower())
    n_b = n_v = 0
    for k in names:
        ms = menus(d[k])
        if not ms:
            continue
        for m in ms:
            n_b += 1
            n_v += len(m['entries'])
            can = cancel_choice(d[k])
            print(f'{k}.{m["name"]}: {len(m["entries"])} voci'
                  + (f', annulla su {can + 1}a' if can is not None
                     else ', annullare non e ammesso'))
            for i, e in enumerate(m['entries']):
                desc_ = description(e)
                print(f'  {i + 1:>2}. {_ascii(label(e)):<16} '
                      f'cursore ({float(e["CursorX"]):.0f},'
                      f'{float(e["CursorY"]):.0f})'
                      + (f'   {_ascii(desc_["string"])}' if desc_ else ''))
    print(f'\n{n_b} blocchi navigabili, {n_v} voci')
    return 0


def cmd_keys(name: str, root: pathlib.Path) -> int:
    """La barra dei tasti: quali azioni una schermata offre, e con che tasto."""
    d = descriptors(root)
    names = [name] if name in d else sorted(
        k for k in d if not name or name.lower() in k.lower())
    tot = con = 0
    for k in names:
        kb = keybar(d[k], root)
        if not kb:
            continue
        print(f'{k}:')
        for b in kb:
            tot += 1
            con += b['hue'] is not None
            print(f'  {b["action"]:<18} {_ascii(b["string"]):<12} '
                  f'x={b["x"]:>6.0f}  '
                  + (f'tasto {b["hue"]}' if b['hue'] else 'senza icona'))
    print(f'\n{tot} azioni dichiarate, {con} con l icona accanto')
    return 0


def cmd_floors(dungeon: int, root: pathlib.Path) -> int:
    """I piani di un sotterraneo, dal basso in su."""
    fs = dungeon_floors(dungeon, root)
    if not fs:
        print(f'sotterraneo {dungeon}: nessun descrittore di mappa')
        return 1
    for f in fs:
        print(f'  pagina {str(f["page"]):>3}  {f["label"]:<4} '
              f'dungeonMap{dungeon:02d}_{f["seq"]:02d}')
    print(f'{len(fs)} piani')
    return 0


def cmd_drive(name: str, tasti: str, out: pathlib.Path,
              root: pathlib.Path) -> int:
    """Una schermata guidata dai tasti, un fotogramma per premuta.

        python ui.py drive Pause giu,giu,giu,croce out.png
        python ui.py drive ClearSave cerchio out.png
    """
    import font as font_mod

    d = descriptors(root)
    if name not in d:
        near = [k for k in d if name.lower() in k.lower()]
        print(f'{name} non e una schermata dichiarata'
              + (f'; forse: {", ".join(near[:6])}' if near else ''))
        return 1
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    glyphs = font_mod.Font(data / 'UserInterface/Font/Font.lua.eu')
    s = Screen(d[name], root)
    if not s.entries and s.page_range is None:
        print(f'{name} non dichiara ne voci ne pagine: non si naviga')
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    passi = [t.strip().lower() for t in tasti.split(',') if t.strip()]
    print(f'{name}: {s.state()}')
    for i, t in enumerate(passi):
        if t not in KEYS:
            print(f'  tasto sconosciuto {t!r}; sono: {", ".join(KEYS)}')
            return 1
        KEYS[t](s)
        p = out.with_name(f'{out.stem}_{i:02d}{out.suffix or ".png"}')
        s.draw(glyphs).convert('RGB').save(p)
        print(f'  {t:<8} {s.state()}  -> {p.name}')
        if s.done:
            break
    return 0


def cmd_check(root: pathlib.Path) -> int:
    """Le verifiche che si eseguono da sole."""
    import view

    bad = 0

    def ok(cond, what):
        nonlocal bad
        print(f'  {"ok " if cond else "NO "} {what}')
        bad += not cond

    d = descriptors(root)
    print(f'{len(d)} schermate dichiarate')
    ok(len(d) >= 100, 'oltre cento schermate dichiarate')
    ok('ClearSave' in d and 'GameOver' in d,
       'ci sono le schermate di sistema attese')

    # lo schermo virtuale e' lo stesso per i descrittori e per le scene
    data = root / 'PS3_GAME/USRDIR/data' if (root / 'PS3_GAME').exists() \
        else root
    import collections

    box, n, flat, ortho, tri = collections.Counter(), 0, 0, 0, 0
    for p in sorted((data / 'UserInterface').rglob('*.ps3.dsb')):
        try:
            parts, _ = view.load(p)
        except Exception:                                        # noqa: BLE001
            continue
        if not parts:
            continue
        n += 1
        b0, b1 = view.bounds(parts)
        box[(round(float(b1[0] - b0[0])), round(float(b1[1] - b0[1])))] += 1
        for q in parts:
            t = q.idx.reshape(-1, 3)
            tri += len(t)
            a, b, c = q.pos[t[:, 0]], q.pos[t[:, 1]], q.pos[t[:, 2]]
            flat += int(((np.abs(a[:, 2] - b[:, 2]) < 1e-3) &
                         (np.abs(a[:, 2] - c[:, 2]) < 1e-3)).sum())
            e = np.stack([b - a, c - b, a - c])
            ax = (np.abs(e[:, :, 0]) < 1e-3) | (np.abs(e[:, :, 1]) < 1e-3)
            ortho += int((ax.sum(axis=0) >= 2).sum())
    common, how_many = box.most_common(1)[0]
    print(f'{n} scene di interfaccia, {tri:,} triangoli; il riquadro piu '
          f'comune e {common[0]}x{common[1]} in {how_many} scene')
    # L'oracolo non e' il massimo ne' la moda: le schermate a scorrimento
    # parcheggiano i pezzi fuori campo (il menu degli oggetti arriva a x=2193)
    # e la moda porta 12 unita' di abbondanza. Il quadrato **giusto** e' la
    # dissolvenza a piena pagina, che per definizione copre lo schermo e basta.
    fade, _ = view.load(data / 'UserInterface/Fade/Fade.ps3.dsb')
    b0, b1 = view.bounds(fade)
    print(f'  la dissolvenza copre x [{b0[0]:.0f}, {b1[0]:.0f}]  '
          f'y [{b0[1]:.0f}, {b1[1]:.0f}]')
    ok(abs(b0[0]) < 1 and abs(b1[0] - SCREEN[0]) < 1 and
       abs(b1[1]) < 1 and abs(b0[1] + SCREEN[1]) < 1,
       f'la dissolvenza copre lo schermo virtuale {SCREEN[0]}x{SCREEN[1]}')
    ok(abs(common[0] - SCREEN[0]) <= 16 and abs(common[1] - SCREEN[1]) <= 16,
       'il riquadro piu comune e lo schermo, a meno di un margine')
    ok(flat >= tri - 4, f'{flat:,}/{tri:,} triangoli piatti in Z')
    ok(ortho == tri, f'{ortho:,}/{tri:,} triangoli con due lati sugli assi')

    # e una schermata si compone davvero
    import font as font_mod
    glyphs = font_mod.Font(data / 'UserInterface/Font/Font.lua.eu')
    img = compose(d['ClearSave'], root, glyphs)
    px = np.array(img.convert('RGB'))
    ok(px.max() > 40, 'ClearSave composta non e uno schermo nero')
    ok(len(entries(d["ClearSave"].get("Select"))) == 2,
       'ClearSave dichiara due scelte')

    # --- l'animazione: Start e' un indice, non un tempo
    fixed = collections.defaultdict(collections.Counter)
    dense = same = 0
    n_anim = 0
    for t in d.values():
        cl = clips(t)
        if not cl:
            continue
        n_anim += 1
        for c in cl:
            if c['name'] in ('In', 'Main', 'Out'):
                fixed[c['name']][c['index']] += 1
        idx = sorted(c['index'] for c in cl)
        dense += idx == list(range(len(idx)))
        same += len(set(idx)) == len(idx)
    print(f'\n{n_anim} schermate dichiarano clip')
    for k, want in (('In', 0), ('Main', 1), ('Out', 2)):
        tot = sum(fixed[k].values())
        print(f'  {k:<5} Start={want} in {fixed[k][want]}/{tot} schermate')
    ok(all(fixed[k][w] == sum(fixed[k].values()) for k, w in
           (('In', 0), ('Main', 1), ('Out', 2))),
       'Start e determinato dal nome della clip: In=0, Main=1, Out=2')
    print(f'  indici densi da 0 in {dense}/{n_anim}, senza ripetizioni in '
          f'{same}/{n_anim}')
    ok(dense >= n_anim * 0.7,
       'gli indici sono densi e consecutivi nella maggioranza delle schermate')

    # --- il parcheggio e' orizzontale
    off, offx = _parked(data)
    print(f'  {off} pezzi parcheggiati fuori campo, {offx} solo in X')
    ok(offx >= off * 0.8,
       f'il parcheggio e orizzontale: {offx}/{off} fuori solo in X')

    # --- la mappa del sotterraneo, guidata dalle stanze della griglia
    import walk

    g = walk.Atlas(data).grid('d_1_1_1')
    rooms = sorted(g.rooms) if g else []
    m_none = dungeon_map(1, 1, root, seen=(), here=None)
    m_all = dungeon_map(1, 1, root, seen=rooms, here=rooms[0] if rooms else None)
    # I tre stati coprono la **stessa area**: contare i pixel accesi da lo
    # stesso numero in tutti e tre. A distinguerli e' il disegno, quindi le
    # due immagini si confrontano invece di misurarle.
    b = int((np.array(m_all.convert('L')) > 8).sum()) if m_all else 0
    diff = 0
    if m_none is not None and m_all is not None:
        diff = int((np.array(m_none.convert('RGB')) !=
                    np.array(m_all.convert('RGB'))).any(axis=2).sum())
    print(f'  mappa di d_1_1_1: {len(rooms)} stanze dalla griglia; '
          f'{b:,} px disegnati, {diff:,} cambiano fra nessuna vista e tutte')
    ok(m_all is not None and b > 0, 'la mappa del sotterraneo si compone')
    ok(diff > 1000, 'le stanze viste cambiano quello che si disegna')

    # --- le scritte: quante ne colloca il disco, e che siano leggibili
    tutte = [x for t in d.values() for x in texts(t)]
    rotte = [x for x in tutte if '�' in x['string']]
    print(f'\n{len(tutte)} scritte collocate dai descrittori')
    ok(len(tutte) > 350, f'{len(tutte)} scritte collocate, non solo le 85 di '
       'Message e Select')
    ok(not rotte, f'nessuna scritta stroppiata dalla codifica '
       f'({len(rotte)} con un carattere perduto)')
    ok(_ascii(d['ClearSave']['Select'][1]['String']) == 'YES',
       'le scritte tornano indietro leggibili')

    # --- i blocchi navigabili, e l'asse che li percorre
    blocchi = [(k, m) for k in d for m in menus(d[k])]
    n_v = sum(len(m['entries']) for _k, m in blocchi)
    colonna = riga = 0
    scarti = collections.Counter()
    for _k, m in blocchi:
        xs = [float(e['CursorX']) for e in m['entries']]
        ys = [float(e['CursorY']) for e in m['entries']]
        colonna += (max(ys) - min(ys)) > (max(xs) - min(xs))
        riga += (max(xs) - min(xs)) > (max(ys) - min(ys))
        for e in m['entries']:
            scarti[(round(float(e.get('X', e.get('MenuX', 0)))
                          - float(e['CursorX'])),
                    round(float(e.get('Y', e.get('MenuY', 0)))
                          - float(e['CursorY'])))] += 1
    quali = collections.Counter(m['name'] for _k, m in blocchi)
    print(f'{len(blocchi)} blocchi navigabili, {n_v} voci; per nome '
          f'{dict(quali)}')
    print(f'  incolonnati {colonna}, in riga {riga}; scarto voce-cursore piu '
          f'comune {scarti.most_common(1)[0]}')
    ok(len(blocchi) >= 20 and n_v >= 55,
       'i blocchi navigabili sono piu dei soli si/no')
    ok(riga == 0, f'le voci sono incolonnate in tutti e {colonna} i blocchi: '
       'su e giu, non destra e sinistra')
    ok(len(quali) >= 3, 'il criterio non e il nome del blocco: sono tre nomi '
       f'diversi ({", ".join(sorted(quali))})')

    # --- il cursore viene dalla scena, e ci sta dentro la riga
    LINEA = 32.0                              # la cella del font
    scarti_v = []
    n_art = n_par = n_riga = 0
    viste = set()
    for k in d:
        for m in menus(d[k]):
            pkg = d[k].get('ScenePackageName', '')
            if (pkg, m['name']) in viste:
                continue
            viste.add((pkg, m['name']))
            parts, _lib = scene(pkg, root)
            if not parts:
                continue
            parked, per_voce = cursor_art(rects(parts), m)
            n_art += bool(parked) or bool(per_voce)
            n_par += bool(parked)
            n_riga += bool(per_voce)
            for i, e in enumerate(m['entries']):
                r = parked or per_voce.get(i)
                if r is None:
                    continue
                alto = r[3] - r[1]
                y = float(e.get('Y', e.get('MenuY', e['CursorY'])))
                scarti_v.append(abs((float(e['CursorY']) + alto / 2)
                                    - (y + LINEA / 2)))
    peggio = max(scarti_v) if scarti_v else 99
    print(f'\n{n_art} blocchi hanno il cursore nella scena: {n_par} '
          f'parcheggiato all origine, {n_riga} uno per riga')
    print(f'  il cursore cade in mezzo alla riga a meno di {peggio:.0f} px, '
          f'su {len(scarti_v)} voci')
    ok(n_art >= 7, 'il disegno del cursore viene dalla scena, non da noi')
    ok(peggio <= 8, 'il cursore e centrato sulla riga di font (32 px), '
       'quindi Y e il bordo alto e la scala e 1')

    # --- l'annullamento sceglie NO, e l'indice si conta da zero
    da_zero = da_uno = n_can = 0
    for t in d.values():
        c = t.get('Cancel')
        es = menus(t)
        if not isinstance(c, dict) or not es:
            continue
        voci = [_ascii(label(e)).strip() for e in es[0]['entries']]
        i = int(c.get('Index', 0))
        n_can += 1
        da_zero += 0 <= i < len(voci) and voci[i] == 'NO'
        da_uno += 1 <= i <= len(voci) and voci[i - 1] == 'NO'
    print(f'{n_can} schermate dichiarano Cancel; l indice cade su NO '
          f'{da_zero} volte contando da zero, {da_uno} contando da uno')
    ok(da_zero == n_can and da_uno == 0,
       'Cancel.Index si conta da zero, come Start')

    # --- e il tasto si comporta come dichiarato
    aperta = Screen(d['Continue'], root)
    aperta.cancel()
    chiusa = Screen(d['ClearSave'], root)
    chiusa.cancel()
    ok(aperta.done and _ascii(aperta.labels()[aperta.chosen]).strip() == 'NO',
       'dove Enable=1 il tasto di annullamento sceglie NO')
    ok(not chiusa.done,
       'dove Enable=0 il tasto di annullamento non fa niente')

    # --- le pagine sono i piani, e i piani sono i descrittori
    quadra = piani = etichette = 0
    for n in range(1, 8):
        fs = dungeon_floors(n, root)
        if not fs:
            continue
        piani += 1
        rng = next((pages(t) for k, t in d.items()
                    if k.startswith(f'dungeonMap{n:02d}') and pages(t)), None)
        if rng:
            quadra += (rng[1] - rng[0] + 1) == len(fs)
        etichette += sum(f['label'] is not None for f in fs)
    print(f'{piani} sotterranei con la mappa, {etichette} piani con l '
          f'etichetta; l intervallo di pagine quadra col numero di piani in '
          f'{quadra}/{piani}')
    ok(quadra == piani, 'pageMax - pageMin + 1 e il numero di piani')
    ok(etichette == 21, f'tutti e {etichette} i piani hanno un nome')

    # --- il seguito di una schermata, dove e' dichiarato
    legami = {k: opens(t, d) for k, t in d.items()}
    legami = {k: v for k, v in legami.items() if v}
    print(f'{len(legami)} schermate su {len(d)} nominano la schermata che '
          f'aprono: ' + '; '.join(f'{k} -> {", ".join(v)}'
                                  for k, v in sorted(legami.items())))
    ok(all(cancel_choice(d[x]) is not None or x.endswith('Select')
           for v in legami.values() for x in v),
       'le schermate nominate sono finestre di conferma')

    # --- la barra dei tasti, e le due tinte che nominano un tasto
    tinte = collections.Counter()
    n_bar = 0
    for k in d:
        for b in keybar(d[k], root):
            n_bar += 1
            tinte[b['hue']] += 1
    print(f'{n_bar} azioni dichiarate sulla striscia dei tasti; tinte '
          f'{dict(tinte)}')
    ok(tinte['croce'] and tinte['cerchio'],
       'la ✕ e la ○ si distinguono dal colore dell icona')

    # --- e la posa a meta' strada e' davvero a meta' strada
    half = compose(d['ClearSave'], root, grow=0.5)
    shut = compose(d['ClearSave'], root, grow=0.0)
    a = (np.array(shut.convert('L')) > 8).sum()
    b = (np.array(half.convert('L')) > 8).sum()
    c = (np.array(img.convert('L')) > 8).sum()
    print(f'  ClearSave: chiusa {a:,} px, a meta {b:,} px, aperta {c:,} px')
    ok(a < b < c, 'la schermata cresce con il fattore d apertura')
    print(f'\n{"tutto a posto" if not bad else str(bad) + " verifiche fallite"}')
    return 1 if bad else 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == 'list':
        return cmd_list(_root(argv, 1))
    if argv[0] == 'show':
        size = SCREEN
        if '--size' in argv:
            w, h = argv[argv.index('--size') + 1].split('x')
            size = (int(w), int(h))
        out = pathlib.Path(argv[2]) if len(argv) > 2 else \
            pathlib.Path('ui.png')
        root = pathlib.Path(argv[3]) if len(argv) > 3 and \
            not argv[3].startswith('--') else pathlib.Path('../extract')
        return cmd_show(argv[1], out, root, size)
    if argv[0] == 'map':
        return cmd_map(argv, pathlib.Path('../extract'))
    if argv[0] == 'clips':
        return cmd_clips(argv[1] if len(argv) > 1 else '', _root(argv, 2))
    if argv[0] == 'anim':
        which = argv[argv.index('--clip') + 1] if '--clip' in argv else 'In'
        frames = int(argv[argv.index('--frames') + 1]) \
            if '--frames' in argv else 8
        out = pathlib.Path(argv[2]) if len(argv) > 2 and \
            not argv[2].startswith('--') else pathlib.Path('anim.png')
        root = pathlib.Path(argv[3]) if len(argv) > 3 and \
            not argv[3].startswith('--') else pathlib.Path('../extract')
        return cmd_anim(argv[1], out, root, which, frames)
    if argv[0] == 'menus':
        return cmd_menus(argv[1] if len(argv) > 1 else '', _root(argv, 2))
    if argv[0] == 'keys':
        return cmd_keys(argv[1] if len(argv) > 1 else '', _root(argv, 2))
    if argv[0] == 'floors':
        return cmd_floors(int(argv[1]), _root(argv, 2))
    if argv[0] == 'drive':
        out = pathlib.Path(argv[3]) if len(argv) > 3 else \
            pathlib.Path('drive.png')
        return cmd_drive(argv[1], argv[2] if len(argv) > 2 else '', out,
                         _root(argv, 4))
    if argv[0] == 'check':
        return cmd_check(_root(argv, 1))
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
