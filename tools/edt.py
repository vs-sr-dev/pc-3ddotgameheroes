"""
edt.py - i personaggi voxel dell'editor, che sono il cuore di questo gioco.

`EDTFILE1.9`, 90 file sotto `data/edt`: i sei personaggi di partenza, i
preset, e le prove rimaste sul disco. E' il formato con cui il gioco descrive
un personaggio disegnato dot per dot - quello che da' il titolo a
*3D Dot Game Heroes* - quindi leggerlo vuol dire poter mostrare il protagonista
che il giocatore ha fatto invece di uno di riserva.

    python edt.py info   <file.edt>          intestazione, parti, voxel
    python edt.py sheet  <dir> <out.png>     un provino a contatto dei preset
    python edt.py check  <dir edt>           le verifiche interne

## Il modello del file

Tutto big-endian, e **niente allineamento**: e' un flusso di byte, quindi una
stringa dispari sposta di uno tutto quel che segue.

    'EDTFILE1.9' + 2 byte a zero
    u32 len + len byte   nome dell'autore, UTF-8   ('プレイヤー')
    u32                  una bandiera, 0 o 1
    u32 len + len byte   nome del personaggio      ('勇者の子孫')
    float[14]            parametri dell'editor, tutti interi piccoli
    u32                  **numero di parti**, che e' 6 in tutti e 90 i file
    per ogni parte:
        u32              numero di voxel
        voxel[]          20 byte l'uno
        float[6]         coda della parte

Il voxel e' `u32 posizione` piu' `float[4]`:

    posizione   0x00 XX YY ZZ   -  il primo byte e' sempre zero, e i tre
                                   seguenti stanno **tutti fra 0 e 15**
    float[0..2] il colore, RGB in 0..1
    float[3]    da 0 a 6, sette valori distinti: la finitura

Sedici per lato non e' un caso: e' la stessa griglia di `water_col.dds`, che
ha 16 quadretti per lato perche' una casella del mondo e' sedici dot. Il
personaggio dell'editor sta in un cubo di **16x16x16 per parte**.

## Le sei parti sono sei pose

I conti non lo nascondono: in `angel.edt` sono 261, 256, 246, 240, 263, 267
voxel, cioe' sei volte lo stesso personaggio e non sei pezzi di uno. Lo
conferma il contenuto - fra la prima parte e le altre cinque il **60,4%** dei
voxel sta nello stesso posto - e le sei scatole, che si sovrappongono tutte.

E' la stessa cosa vista da [`entities.md`](../docs/entities.md): i personaggi
di questo gioco non hanno scheletro, e i figli di un nodo sono **fotogrammi
interi**. Li' erano da 2 a 6; qui sono sei, sempre.

## I `.SAV`

Sono un'altra cosa: nessun magic, e cominciano subito con la stessa coppia
`u32 len + UTF-8`. `test.SAV` porta dentro `edt/preset/pumpkin.edt`, quindi un
salvataggio **riferisce** un preset per percorso invece di incorporarlo. Non e'
letto qui.
"""
from __future__ import annotations

import pathlib
import struct
import sys

import numpy as np

MAGIC = b'EDTFILE1.9'
GRID = 16          # lato del cubo di un personaggio, in dot


def parse(data: bytes) -> dict:
    """Un personaggio: intestazione, parametri e le sei pose.

    Il percorso e' l'oracolo: se il layout e' giusto si finisce **esattamente**
    sull'ultimo byte. Vale qui come e' valso per `MAP_ALIGNMENT` e per il
    `.DPK`, e per la stessa ragione - i record hanno lunghezza variabile, e
    sbagliare un campo fa deragliare tutto il resto invece di produrre un
    numero solo un po' storto.
    """
    if data[:len(MAGIC)] != MAGIC:
        raise ValueError(f'magic {data[:10]!r}, atteso {MAGIC!r}')
    o = 12
    author, o = _string(data, o)
    flag = struct.unpack_from('>I', data, o)[0]
    o += 4
    name, o = _string(data, o)
    params = struct.unpack_from('>14f', data, o)
    o += 56
    n = struct.unpack_from('>I', data, o)[0]
    o += 4
    poses = []
    for _ in range(n):
        c = struct.unpack_from('>I', data, o)[0]
        o += 4
        if c:
            raw = np.frombuffer(data, '>u4', count=c * 5, offset=o)
            flt = np.frombuffer(data, '>f4', count=c * 5, offset=o)
            pos = raw.reshape(c, 5)[:, 0]
            col = flt.reshape(c, 5)[:, 1:4]
            fin = flt.reshape(c, 5)[:, 4]
        else:
            pos = np.zeros(0, '>u4')
            col = np.zeros((0, 3), '>f4')
            fin = np.zeros(0, '>f4')
        o += 20 * c
        tail = struct.unpack_from('>6f', data, o)
        o += 24
        poses.append({'pos': np.array(pos), 'color': np.array(col),
                      'finish': np.array(fin), 'tail': tail})
    return {'author': author, 'flag': flag, 'name': name, 'params': params,
            'poses': poses, 'end': o, 'size': len(data)}


def _string(data: bytes, o: int) -> tuple[str, int]:
    n = struct.unpack_from('>I', data, o)[0]
    return data[o + 4:o + 4 + n].decode('utf-8', 'replace'), o + 4 + n


def xyz(pos: np.ndarray) -> np.ndarray:
    """Da posizione impacchettata a `(x, y, z)`, ognuno fra 0 e 15."""
    return np.stack([(pos >> 16) & 255, (pos >> 8) & 255, pos & 255], axis=1)


def front(pose: dict, scale: int = 18, back: bool = False):
    """La posa vista di fronte: per ogni colonna il voxel piu' avanti.

    Non e' un render, e' un modo di guardare i dati; basta pero' a riconoscere
    un personaggio, che e' la verifica che conta.

    **Avanti e' la Z minima**, e non e' una convenzione scelta qui: prendendo
    la massima si ottengono le nuche - niente occhi, solo capelli - e prendendo
    la minima compaiono le facce. Cioe' i personaggi sono authorati **verso
    -Z**, che e' esattamente quello che `entities.md` aveva gia' dedotto in
    un'altra sessione guardando le mesh del gioco con `view.py char --azim 180`.
    Due file diversi, la stessa convenzione.
    """
    from PIL import Image

    img = np.zeros((GRID, GRID, 3), np.float32)
    best = np.full((GRID, GRID), -1.0 if back else 99.0)
    p = xyz(pose['pos'])
    for i in range(len(p)):
        x, y, z = int(p[i, 0]), int(p[i, 1]), int(p[i, 2])
        if (z > best[y, x]) if back else (z < best[y, x]):
            best[y, x] = z
            img[y, x] = pose['color'][i]
    a = (np.clip(img, 0, 1) * 255).astype(np.uint8)[::-1]     # la Y va in su
    return Image.fromarray(a).resize((GRID * scale, GRID * scale),
                                     Image.NEAREST)


# ------------------------------------------------------------- da riga di comando

def cmd_info(p: pathlib.Path) -> int:
    e = parse(p.read_bytes())
    print(f'{p.name}: autore {e["author"]!r} bandiera {e["flag"]} '
          f'nome {e["name"]!r}')
    print(f'  parametri: {[round(x, 3) for x in e["params"]]}')
    for i, q in enumerate(e['poses']):
        if not len(q['pos']):
            print(f'  posa {i}: vuota')
            continue
        b = xyz(q['pos'])
        print(f'  posa {i}: {len(q["pos"]):>5} voxel  '
              f'x[{b[:, 0].min()},{b[:, 0].max()}] '
              f'y[{b[:, 1].min()},{b[:, 1].max()}] '
              f'z[{b[:, 2].min()},{b[:, 2].max()}]  '
              f'finiture {sorted(set(q["finish"].tolist()))}')
    print(f'  percorso finito a {e["end"]}, file {e["size"]}'
          + ('' if e['end'] == e['size'] else '  <-- NON torna'))
    return 0 if e['end'] == e['size'] else 1


def cmd_sheet(d: pathlib.Path, out: pathlib.Path, cols: int = 8) -> int:
    from PIL import Image

    files = sorted(d.rglob('*.edt'))
    if not files:
        print(f'nessun .edt sotto {d}')
        return 1
    s = 8
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * GRID * s, rows * GRID * s), (18, 18, 22))
    for i, p in enumerate(files):
        try:
            e = parse(p.read_bytes())
        except Exception:                                        # noqa: BLE001
            continue
        sheet.paste(front(e['poses'][0], s),
                    ((i % cols) * GRID * s, (i // cols) * GRID * s))
    sheet.save(out)
    print(f'{len(files)} personaggi -> {out}')
    return 0


def cmd_check(d: pathlib.Path) -> int:
    """Le verifiche che si eseguono da sole."""
    bad = 0

    def ok(cond, what):
        nonlocal bad
        print(f'  {"ok " if cond else "NO "} {what}')
        bad += not cond

    files = sorted(d.rglob('*.edt'))
    exact = vox = 0
    nparts, lo, hi, fins = set(), 255, 0, set()
    shared = total = 0
    for p in files:
        e = parse(p.read_bytes())
        exact += e['end'] == e['size']
        nparts.add(len(e['poses']))
        for q in e['poses']:
            vox += len(q['pos'])
            if len(q['pos']):
                b = xyz(q['pos'])
                lo = min(lo, int(b.min()))
                hi = max(hi, int(b.max()))
                fins.update(q['finish'].tolist())
                # il primo byte della posizione non e' mai usato
                assert int(((q['pos'] >> 24) & 255).max()) == 0
        a = set(e['poses'][0]['pos'].tolist())
        for q in e['poses'][1:]:
            b = set(q['pos'].tolist())
            total += len(a | b)
            shared += len(a & b)
    print(f'{len(files)} file, {vox:,} voxel')
    ok(exact == len(files),
       f'{exact}/{len(files)} percorsi fino all ultimo byte esatto')
    ok(nparts == {6}, f'sei parti in ogni file (viste: {sorted(nparts)})')
    ok((lo, hi) == (0, GRID - 1),
       f'le coordinate stanno fra 0 e {GRID - 1} (viste: {lo}-{hi})')
    ok(len(fins) <= 8, f'le finiture sono poche e intere: {sorted(fins)}')

    # I personaggi guardano verso -Z: davanti c'e' meno roba che dietro,
    # perche' una faccia e' incavata (occhi, bocca) e una nuca e' piena.
    e = parse((d / 'preset/black_smith.edt').read_bytes())
    b = xyz(e['poses'][0]['pos'])
    zmin, zmax = int(b[:, 2].min()), int(b[:, 2].max())
    n_front = int((b[:, 2] == zmin).sum())
    n_back = int((b[:, 2] == zmax).sum())
    print(f'  black_smith: {n_front} voxel sul piano z={zmin}, '
          f'{n_back} su z={zmax}')
    ok(n_front < n_back,
       'il davanti e la Z minima (una faccia e incavata, una nuca e piena)')
    q = 100 * shared / max(total, 1)
    print(f'  voxel in comune fra la prima posa e le altre: {q:.1f}%')
    ok(40 < q < 90, 'le sei parti sono sei pose dello stesso personaggio')
    print(f'\n{"tutto a posto" if not bad else str(bad) + " verifiche fallite"}')
    return 1 if bad else 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == 'info' and len(argv) > 1:
        return cmd_info(pathlib.Path(argv[1]))
    if argv[0] == 'sheet' and len(argv) > 2:
        return cmd_sheet(pathlib.Path(argv[1]), pathlib.Path(argv[2]))
    if argv[0] == 'check':
        return cmd_check(pathlib.Path(argv[1] if len(argv) > 1
                                      else '../extract/PS3_GAME/USRDIR/data/edt'))
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
