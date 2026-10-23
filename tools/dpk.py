"""
dpk.py - `MAPCOLLISION/*.DPK`, la collisione delle mappe.

171 file, 5,4 MB in tutto: una **mesh di triangoli** per mappa, cioe' un
centesimo dei poligoni con cui la mappa si disegna (420.301 triangoli contro
30,9 milioni). E' il muro che il gioco usa davvero, e finora si era approssimato
con i vertici della geometria di rendering (vedi `walk.py`).

Formato

  +0x00 u32                 numero di mesh
  poi n coppie (u32, u32)   offset e dimensione di ogni mesh

  ogni mesh, all'offset dichiarato:
    +0x00 u32               numero di **float**, cioe' 3 x i vertici
    poi n float32 big-endian, (x, y, z)
    +0x00 u32               numero di indici
    poi n u16 big-endian, tre per triangolo

Che il layout sia questo lo dice il formato stesso, con lo stesso oracolo che
ha risolto `MAP_ALIGNMENT`: percorrendo ogni mesh dal suo offset si deve finire
**esattamente** sulla sua dimensione dichiarata, e l'ultima sull'ultimo byte del
file. Succede in **171 file su 171**, per tutte e 301 le mesh.

Il conto dei float invece dei vertici e' l'unico campo che non si indovina: in
`PLANE.DPK` vale 12 per quattro vertici, e leggerlo come numero di vertici fa
uscire dal file immediatamente.

## Il sistema di riferimento

Lo **stesso** del `.pac`: origine al centro della mappa, X verso destra, Z verso
l'alto della griglia. Non c'e' niente da convertire, ed e' verificabile a
confronto - `DUNGEON_21_1` copre x da -20,0 a 18,4 e z da -18,4 a 20,0, che sono
esattamente gli estremi della geometria disegnata.

`PLANE.DPK` e' l'unico senza mappa: un quadrato di 102,4 unita', cioe' 64
caselle, con l'origine a un angolo. E' il pavimento di prova degli sviluppatori.

## Da mesh a colonne

Chi cammina non ha bisogno di triangoli ma di due risposte per cella - dove si
posa il piede, e cosa c'e' all'altezza del corpo. `samples()` semina i triangoli
di punti a passo di un quarto di casella, che e' la risoluzione delle colonne di
`walk.py`, e restituisce con ogni punto la **normale del suo triangolo**.

La normale non e' un di piu': e' cio' che distingue un pavimento da un muro, e
prenderla dal triangolo invece che dal vertice la rende esatta invece che
interpolata.

Uso:
  python dpk.py info  <file.DPK>
  python dpk.py check [dir MAPCOLLISION]     l'oracolo su tutti i file
"""
from __future__ import annotations

import pathlib
import struct
import sys

import numpy as np


def blocks(data: bytes) -> list[tuple[np.ndarray, np.ndarray]]:
    """Le mesh di un file: `(vertici (n,3), triangoli (m,3))` per ognuna."""
    n = struct.unpack_from('>I', data, 0)[0]
    hdr = struct.unpack_from(f'>{2 * n}I', data, 4)
    out = []
    for i in range(n):
        off, size = hdr[2 * i], hdr[2 * i + 1]
        o = off
        nf = struct.unpack_from('>I', data, o)[0]
        verts = np.frombuffer(data, '>f4', nf, o + 4).reshape(-1, 3)
        o += 4 + nf * 4
        ni = struct.unpack_from('>I', data, o)[0]
        idx = np.frombuffer(data, '>u2', ni - ni % 3, o + 4)
        o += 4 + ni * 2
        if o != off + size:
            raise ValueError(f'mesh {i}: finita a {o}, dichiarata {off + size}')
        out.append((verts.astype(np.float32), idx.reshape(-1, 3).astype(np.int32)))
    return out


def mesh(path: pathlib.Path):
    """Tutte le mesh di un file cucite in una sola."""
    verts, tris, base = [], [], 0
    for v, t in blocks(path.read_bytes()):
        verts.append(v)
        tris.append(t + base)
        base += len(v)
    if not verts:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int32)
    return np.concatenate(verts), np.concatenate(tris)


def seed(verts: np.ndarray, tris: np.ndarray, step: float = 0.4,
         batch: int = 1 << 21):
    """Semina i triangoli di punti, **a gruppi**: `(punti, normali)` per volta.

    Il passo e' quello delle colonne di `walk.py`: seminare piu' fitto non
    aggiunge informazione, seminare piu' rado lascia buchi in mezzo a un
    triangolo grande - e in una mesh di collisione i triangoli **sono** grandi,
    perche' un pavimento di venti caselle e' due triangoli. In `FIELD_07` il
    lato piu' lungo misura 190 unita', cioe' 119 caselle.

    Il numero di suddivisioni **non ha un tetto**, e la ragione e' che un tetto
    non e' una scelta conservativa: limitarlo a 96 rendeva il passo di semina
    di quei triangoli 2,0 unita', piu' largo di una casella, e quindi lasciava
    scoperte celle intere - fra cui quattordici punti d'ingresso di mappa.
    Costa il 27% di punti in piu' su tutto il disco, e non lascia buchi.

    A gruppi, perche' senza tetto una mappa sola arriva a 22 milioni di punti:
    tenerli tutti insieme sono mezzo gigabyte, versarli nelle colonne un gruppo
    per volta non e' niente. I triangoli si raggruppano per numero di
    suddivisioni, cosi' ogni gruppo si semina in un colpo solo.
    """
    if not len(tris):
        return
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    e1, e2 = b - a, c - a
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = nrm / np.maximum(ln, 1e-12)
    longest = np.maximum(np.maximum(np.linalg.norm(e1, axis=1),
                                    np.linalg.norm(e2, axis=1)),
                         np.linalg.norm(c - b, axis=1))
    k = np.maximum(np.ceil(longest / step).astype(np.int64), 1)
    for kk in np.unique(k):
        sel = np.nonzero(k == kk)[0]
        # griglia baricentrica: tutti gli (i, j) con i + j <= kk
        i, j = np.meshgrid(np.arange(kk + 1), np.arange(kk + 1), indexing='ij')
        keep = (i + j) <= kk
        u = (i[keep] / kk).astype(np.float32)
        v = (j[keep] / kk).astype(np.float32)
        # quanti triangoli per volta stanno nel budget di punti
        chunk = max(1, batch // max(len(u), 1))
        for s in range(0, len(sel), chunk):
            g = sel[s:s + chunk]
            p = (a[g][:, None, :] + u[None, :, None] * e1[g][:, None, :]
                 + v[None, :, None] * e2[g][:, None, :])
            yield p.reshape(-1, 3), np.repeat(nrm[g], len(u), axis=0)


def samples(verts: np.ndarray, tris: np.ndarray, step: float = 0.4):
    """Tutti i punti seminati in una volta. Comodo per guardare, non per
    lavorare: su una mappa grande sono decine di milioni."""
    out = list(seed(verts, tris, step))
    if not out:
        return np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)
    return (np.concatenate([p for p, _ in out]),
            np.concatenate([n for _, n in out]))


# I nomi non concordano con quelli delle mappe: la collisione si chiama
# `DUNGEON_1_1_1.DPK` dove la mappa e' `D_1_1_1`, e in un file lo sviluppatore
# ha scritto `DANGEON`. Il refuso e' sul disco stampato, quindi va gestito.
def map_name(stem: str) -> str:
    return stem.replace('DANGEON', 'D').replace('DUNGEON', 'D')


def for_map(root: pathlib.Path, name: str) -> pathlib.Path | None:
    """Il file di collisione di una mappa, per nome normalizzato."""
    import mapdat

    d = root if root.name.upper() == 'MAPCOLLISION' else root / 'MAPCOLLISION'
    if not d.is_dir():
        return None
    key = mapdat.norm(name)
    for p in d.glob('*.DPK'):
        if mapdat.norm(map_name(p.stem)) == key:
            return p
    return None


def cmd_info(path: pathlib.Path) -> int:
    bl = blocks(path.read_bytes())
    v, t = mesh(path)
    lo, hi = (v.min(0), v.max(0)) if len(v) else (0, 0)
    print(f'{path.name}  {path.stat().st_size:,} byte  {len(bl)} mesh, '
          f'{len(v):,} vertici, {len(t):,} triangoli')
    for i, (vv, tt) in enumerate(bl):
        print(f'  mesh {i}: {len(vv):>6,} vertici, {len(tt):>6,} triangoli')
    if len(v):
        print(f'  x [{lo[0]:8.1f} {hi[0]:8.1f}]  y [{lo[1]:8.1f} {hi[1]:8.1f}]'
              f'  z [{lo[2]:8.1f} {hi[2]:8.1f}]')
        tot = up = 0
        for p, n in seed(v, t):
            tot += len(p)
            up += int((n[:, 1] > 0.5).sum())
        print(f'  seminata: {tot:,} punti, {up * 100 // max(tot, 1)}% '
              f'su superfici calpestabili')
    return 0


def cmd_check(root: pathlib.Path) -> int:
    """L'oracolo: ogni mesh deve finire esattamente sulla sua dimensione
    dichiarata, e l'ultima sull'ultimo byte del file."""
    files = sorted(root.glob('*.DPK'))
    ok = bad = 0
    tv = tt = tm = 0
    for p in files:
        data = p.read_bytes()
        try:
            bl = blocks(data)
        except Exception as ex:                                  # noqa: BLE001
            print(f'  ! {p.name}: {ex}')
            bad += 1
            continue
        n = struct.unpack_from('>I', data, 0)[0]
        hdr = struct.unpack_from(f'>{2 * n}I', data, 4)
        end = max(hdr[2 * i] + hdr[2 * i + 1] for i in range(n))
        if end != len(data):
            print(f'  ! {p.name}: ultima mesh finisce a {end}, file {len(data)}')
            bad += 1
            continue
        ok += 1
        tm += len(bl)
        tv += sum(len(v) for v, _ in bl)
        tt += sum(len(t) for _, t in bl)
    print(f'{ok} file su {len(files)} percorsi fino in fondo esattamente, '
          f'{bad} no')
    print(f'{tm} mesh, {tv:,} vertici, {tt:,} triangoli di collisione')
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    arg = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else \
        pathlib.Path('../extract/PS3_GAME/USRDIR/data/MAPCOLLISION')
    if cmd == 'info':
        return cmd_info(arg)
    if cmd == 'check':
        return cmd_check(arg)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
