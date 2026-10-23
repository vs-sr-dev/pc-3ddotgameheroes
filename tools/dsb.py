"""
dsb.py - parser del formato DSBF (scene/model) di 3D Dot Game Heroes.

Stato: container, geometria, grafo di scena e materiali risolti e validati su
tutti i 460 file `.dsb` e sui 167 `.pac` delle mappe. Resta da mappare lo
skinning. Per il contenitore delle mappe vedi docs/format_pac.md.

Modello del file
----------------
Il file e' un header di 16 byte seguito da un'immagine di memoria che il motore
carica di blocco. **Tutti gli offset interni sono relativi al byte 0x10**, non
all'inizio del file: il valore 0x520 indica il byte 0x530. Questo, insieme al
riempimento 0xCC (stack non inizializzato di MSVC) che compare dentro le
struct, dice che l'exporter scriveva struct C++ con memcpy: il layout su disco
rispecchia quello in memoria del motore originale.

Header (big-endian come tutto il resto)

  0x00  char[4]  'DSBF'
  0x04  u16      versione exporter (0x019D, 0x01A4, 0x01A5 sul disco)
  0x06  u16      0x0027, costante
  0x08  u32      dimensione della regione delle strutture = OFFSET DEI BUFFER
  0x0C  u32      dimensione del file
  0x10  u32      1, costante
  0x14  u32      3, costante
  0x18  u32      dimensione della regione dei buffer  (0x08 + 0x18 == filesize)
  0x1C  u32      offset della tabella degli offset di stringa
  0x20  u32      numero di stringhe
  0x24  u32      112, costante
  0x28  u32      numero di oggetti
  0x2C  u32      0xFFFFFFFF, costante
  0x30  u32[2]   zero
  0x38  u32      offset, ruolo da chiarire
  0x3C  u32      0xCCCCCCCC (riempimento MSVC)
  0x80  u32[]    tabella degli offset degli oggetti, 0x28 elementi

Il file e' quindi in due regioni: le **strutture** da 0 a 0x08, i **buffer**
di vertici e indici da 0x08 alla fine. Gli offset dei vertex buffer nei record
mesh sono relativi all'inizio della seconda regione.

Gli oggetti sono referenziati per **CRC32 (IEEE, quello di zlib) del nome**.
I nomi vivono nella tabella stringhe; il suffisso ne indica la classe:
`-node`, `-mesh`, `-fx` (materiale), `-skin`, `-light`, `-camera`, `.dds`.

I comandi accettano indifferentemente `.dsb`, `.pac` (mappe) e `.gz`: il
contenitore lo risolve blocks(). Nei `.pac` la sezione si sceglie con --sec N.

Uso:
  python dsb.py info   <file> [--sec N]
  python dsb.py survey <directory>
  python dsb.py verify <directory> [--every N]           N = campionamento
  python dsb.py obj    <file> <out.obj> [--sec N]        geometria + .mtl
  python dsb.py scene  <file> <out.obj> [--sec N]        scena composta + .mtl
  python dsb.py names  <directory> [--out names.json]    dizionario CRC32->nome
"""
from __future__ import annotations

import collections
import json
import pathlib
import struct
import sys
import zlib

MAGIC = b'DSBF'
BASE = 0x10          # gli offset interni sono relativi a questo byte
OBJ_HDR = 112        # testata comune di ogni record oggetto (campo header 0x24)

# Il formato del vertice non va indovinato: ogni chunk di geometria porta una
# **dichiarazione** esplicita, un array di coppie (semantica, tipo). Gli
# attributi si susseguono nel vertice nell'ordine dichiarato, senza padding, e
# la somma delle dimensioni dei tipi da esattamente lo stride - verificato su
# 8.707 mesh su 8.707.
VTX_SEM = {0: 'pos', 1: 'nrm', 2: 'col', 3: 'uv', 6: 'tan', 7: 'binorm',
           8: 'uv2', 9: 'attr9'}
VTX_TYPE = {                       # codice -> (nome, byte, formato struct)
    0: ('float2', 8, '>2f'),
    1: ('float3', 12, '>3f'),
    2: ('float4', 16, '>4f'),
    3: ('half2', 4, '>2e'),
    4: ('half3', 6, '>3e'),
    5: ('half4', 8, '>4e'),
    6: ('ubyte4', 4, None),        # distinto dal 7, non normalizzato
    7: ('color4', 4, None),        # ubyte4; l'ultimo byte e' 0xFF -> RGBA
}

# Primitiva, byte basso del campo +0x14 del chunk. Il bit 0x100 dello stesso
# campo segnala gli **indici a 32 bit**: e' alzato esattamente nei 3 chunk del
# disco che superano i 65.535 vertici, e leggendoli a 32 bit l'indice massimo
# risulta n_vertici - 1 esatto.
PRIM = {3: 'list', 4: 'strip'}
IDX32 = 0x100

CLASS_SUFFIX = ('-node', '-mesh', '-fx', '-skin', '-light', '-camera')

# Codice di tipo a +0x0C del record oggetto. Dedotto correlando il campo con la
# classe ricavata dal suffisso del nome su tutti i 25.443 oggetti del disco:
# i conteggi combaciano (tipo 2 = 1.792 = esattamente i materiali, tipo 9 = 399
# contro 400 nomi *-light, e cosi' via).
OBJ_TYPE = {
    1:  'texture',
    2:  'material',
    4:  'effect',      # gli oggetti col suffisso -fx
    9:  'light',
    11: 'camera',
    14: 'mesh',
    16: 'skin',
    17: 'node',
}


def triangles(chunk: dict):
    """Espande gli indici di un chunk in triangoli, secondo la primitiva che il
    chunk dichiara. Gli strip usano triangoli degeneri per la cucitura e vanno
    espansi alternando il winding a ogni passo."""
    idx = chunk['indices']
    if chunk['prim'] == 'strip':
        for k in range(len(idx) - 2):
            a, b, c = idx[k], idx[k + 1], idx[k + 2]
            if a == b or b == c or a == c:
                continue                      # degenere di cucitura
            yield (a, b, c) if k % 2 == 0 else (b, a, c)
    else:
        for k in range(0, len(idx) - 2, 3):
            yield idx[k], idx[k + 1], idx[k + 2]


def blocks(path: pathlib.Path):
    """Restituisce i blocchi DSBF di un file, qualunque sia il contenitore.

    - `.dsb`  un solo blocco;
    - `.pac`  container delle mappe: `u32 n0, u32 n1` seguiti da `n0*n1 + 1`
      offset. Le sezioni sono allineate a 0x80, quindi vanno **ritagliate alla
      dimensione che il DSBF dichiara**, altrimenti la validazione fallisce sul
      padding. Il conteggio `n0*n1` regge su tutti i 167 file: la mappa e' una
      griglia di tile;
    - `.gz`   un `.pac` compresso, com'e' sul disco.
    """
    data = path.read_bytes()
    if data[:2] == b'\x1f\x8b':
        import gzip
        data = gzip.decompress(data)
    if data[:4] == MAGIC:
        return [(path.name, data)]
    n0, n1 = struct.unpack_from('>2I', data, 0)
    n = n0 * n1
    offs = struct.unpack_from(f'>{n + 1}I', data, 8)
    out = []
    for i in range(n):
        blob = data[offs[i]:offs[i + 1]]
        if blob[:4] != MAGIC:
            continue
        size = struct.unpack_from('>I', blob, 0x0C)[0]
        out.append((f'{path.stem}#{i}', blob[:size]))
    return out


def sources(root: pathlib.Path) -> list[pathlib.Path]:
    """Tutti i file che possono contenere blocchi DSBF."""
    if root.is_file():
        return [root]
    out = []
    for pat in ('*.dsb', '*.pac', '*.gz', '*.GZ'):
        out += list(root.rglob(pat))
    return sorted(set(out))


def _trs(pos, quat, scale) -> tuple:
    """Matrice 3x4 (rotazione*scala | traslazione) da posizione, quaternione
    (x, y, z, w) e scala."""
    x, y, z, w = quat
    r = (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
         2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
         2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y))
    return (r[0] * scale[0], r[1] * scale[1], r[2] * scale[2], pos[0],
            r[3] * scale[0], r[4] * scale[1], r[5] * scale[2], pos[1],
            r[6] * scale[0], r[7] * scale[1], r[8] * scale[2], pos[2])


def _mul(a, b) -> tuple:
    """Prodotto di due 3x4 (la quarta riga implicita e' 0 0 0 1)."""
    out = []
    for i in range(3):
        for j in range(3):
            out.append(sum(a[4 * i + k] * b[4 * k + j] for k in range(3)))
        out.append(sum(a[4 * i + k] * b[4 * k + 3] for k in range(3)) + a[4 * i + 3])
    return tuple(out)


def apply(m, p) -> tuple:
    return (m[0] * p[0] + m[1] * p[1] + m[2] * p[2] + m[3],
            m[4] * p[0] + m[5] * p[1] + m[6] * p[2] + m[7],
            m[8] * p[0] + m[9] * p[1] + m[10] * p[2] + m[11])


def classify(name: str) -> str:
    """Classe dedotta dal suffisso del nome. Euristica: preferire il codice di
    tipo a +0x0C, che e' autorevole."""
    for s in CLASS_SUFFIX:
        if name.endswith(s):
            return s[1:]
    if name.lower().endswith('.dds'):
        return 'texture'
    return 'altro'


class Dsb:
    def __init__(self, data: bytes, path: str = ''):
        self.path = path
        self.data = data
        if data[:4] != MAGIC:
            raise ValueError(f'{path}: magic {data[:4]!r}, atteso DSBF')
        (self.version, self.magic2, self.buf_base, self.file_size,
         self.c10, self.c14, self.buf_size, self.strtab_off,
         self.n_strings, self.c24, self.n_objects, self.c2c,
         _z0, _z1, self.f38, self.c3c) = struct.unpack_from('>HHIIIIIIIIIIIIII', data, 4)

        # tabella stringhe
        self.strings: list[str] = []
        self.str_off: list[int] = []
        o = self.strtab_off + BASE
        for i in range(self.n_strings):
            so = struct.unpack_from('>I', data, o + 4 * i)[0] + BASE
            end = data.index(b'\0', so)
            self.str_off.append(so)
            self.strings.append(data[so:end].decode('ascii', 'replace'))

        # tabella oggetti
        self.obj_off = [struct.unpack_from('>I', data, 0x80 + 4 * i)[0] + BASE
                        for i in range(self.n_objects)]

        self.by_crc = {zlib.crc32(s.encode()) & 0xffffffff: s for s in self.strings}

        bb = struct.unpack_from('>8f', data, 0x40)      # bounding box della scena
        self.bbox = (bb[0:3], bb[4:7])

    def object(self, i: int) -> dict:
        """Testata del record oggetto, 16 byte:
             +0x00 u32  indice 1-based del proprio nome nella tabella stringhe
             +0x04 u32  CRC32 del proprio nome
             +0x08 u32  indice 1-based del nome base (senza suffisso di classe),
                        0 se assente
             +0x0C u32  codice di tipo, vedi OBJ_TYPE
        """
        o = self.obj_off[i]
        name_i, crc, base_i, typ = struct.unpack_from('>4I', self.data, o)
        return {
            'off': o,
            'name': self.strings[name_i - 1] if 1 <= name_i <= len(self.strings)
                    else self.by_crc.get(crc, f'crc:{crc:08x}'),
            'crc': crc,
            'base': self.strings[base_i - 1] if 1 <= base_i <= len(self.strings) else None,
            'type': typ,
            'type_name': OBJ_TYPE.get(typ, f'tipo{typ}'),
        }

    def object_name(self, i: int) -> str:
        crc = struct.unpack_from('>I', self.data, self.obj_off[i] + 4)[0]
        return self.by_crc.get(crc, f'crc:{crc:08x}')

    # ---------------------------------------------------------------- mesh

    def meshes(self) -> list[dict]:
        """Record mesh (tipo 14). La testata comune e' di 112 byte (il campo
        header 0x24); da li' in poi c'e' la parte specifica.

            +0x20 float[4]  bounding box locale, min
            +0x30 float[4]  bounding box locale, max
            +0x44 u32       numero di chunk di geometria
            +0x50 u32[]     puntatori ai chunk

        Una mesh non e' un solo blocco di geometria: e' una **lista di chunk**,
        ciascuno col proprio vertex buffer, index buffer, dichiarazione del
        vertice e **materiale**. Sul disco quasi tutte ne hanno uno solo, ma non
        tutte: senza seguire la lista si perde silenziosamente il resto della
        mesh.
        """
        out = []
        for i in range(self.n_objects):
            o = self.object(i)
            if o['type'] != 14:
                continue
            bb = struct.unpack_from('>8f', self.data, o['off'] + 0x20)
            n = struct.unpack_from('>I', self.data, o['off'] + 0x44)[0]
            ptrs = struct.unpack_from(f'>{n}I', self.data, o['off'] + 0x50)
            out.append({'name': o['name'], 'off': o['off'],
                        'bbox': (bb[0:3], bb[4:7]),
                        'chunks': [self.chunk(p + BASE) for p in ptrs]})
        return out

    def chunk(self, c: int) -> dict:
        """Chunk di geometria.

            +0x00 u32  **indice dell'oggetto material** (8.770 su 8.770)
            +0x10 u32  numero di indici
            +0x14 u32  byte basso = primitiva (3 lista, 4 strip),
                       bit 0x100 = indici a 32 bit invece che a 16
            +0x18 u32  puntatore alla dichiarazione del vertice
            +0x20 u32  numero di attributi
            +0x24 u32  numero di vertici
            +0x28 u32  offset del vertex buffer, relativo alla regione buffer
            +0x2C u32  dimensione del vertex buffer

        L'index buffer segue il vertex buffer, allineato alla dimensione
        dell'indice. La dichiarazione e' un array di n_attr coppie u32
        (semantica, tipo).
        """
        mat = struct.unpack_from('>I', self.data, c)[0]
        ic, flags, declp, _z, nattr, vc, vboff, vbsize = \
            struct.unpack_from('>8I', self.data, c + 0x10)
        raw = struct.unpack_from(f'>{2 * nattr}I', self.data, declp + BASE)
        decl, off = [], 0
        for k in range(nattr):
            sem, typ = raw[2 * k], raw[2 * k + 1]
            name, size, fmt = VTX_TYPE.get(typ, (f'tipo{typ}', 0, None))
            decl.append({'sem': VTX_SEM.get(sem, f'sem{sem}'), 'sem_code': sem,
                         'type': name, 'type_code': typ, 'off': off,
                         'size': size, 'fmt': fmt})
            off += size
        vb = self.buf_base + vboff
        isize = 4 if flags & IDX32 else 2
        ib = -(-(vb + vbsize) // isize) * isize
        return {'off': c, 'material': mat,
                'index_count': ic, 'prim': PRIM.get(flags & 0xff, flags),
                'idx_size': isize, 'flags': flags,
                'vertex_count': vc, 'n_attr': nattr, 'decl': decl,
                'stride': vbsize // vc if vc else 0, 'decl_size': off,
                'vb': vb, 'vb_size': vbsize, 'ib': ib}

    # ----------------------------------------------------------- materiali

    def materials(self) -> dict:
        """Record `material` (tipo 2), 368 byte fissi. Indicizzato per indice
        di oggetto, che e' la chiave usata dai chunk di geometria.

            +0x20 u32       indice dell'oggetto `effect` associato
            +0x24 u32       puntatore al blocco parametri (sempre a +0x30)
            +0x28 u32       identificativo di shader / tecnica (43 valori)
            +0x3C float[4]  diffuse RGBA
            +0x58 float[3]  ambient
            +0x64 float[3]  emission
            +0x70 float[3]  specular
            +0x7C float     esponente speculare (5.0 su tutto il disco)
            +0xE4 u32[4]    **texture per stage**, 0xFFFFFFFF = nessuna

        Gli stage sono quelli che gli shader dichiarano (vedi renderer.md):
        0 colore base, 1 utility color, 2 normal map, 3 environment map.
        """
        out = {}
        for i in range(self.n_objects):
            o = self.object(i)
            if o['type'] != 2:
                continue
            fx, _p, shader = struct.unpack_from('>3I', self.data, o['off'] + 0x20)
            tex = struct.unpack_from('>4I', self.data, o['off'] + 0xE4)
            out[i] = {
                'index': i, 'name': o['name'], 'effect': fx, 'shader': shader,
                'diffuse': struct.unpack_from('>4f', self.data, o['off'] + 0x3C),
                'ambient': struct.unpack_from('>3f', self.data, o['off'] + 0x58),
                'emission': struct.unpack_from('>3f', self.data, o['off'] + 0x64),
                'specular': struct.unpack_from('>3f', self.data, o['off'] + 0x70),
                'spec_pow': struct.unpack_from('>f', self.data, o['off'] + 0x7C)[0],
                'textures': [None if t == 0xffffffff else self.object(t)['name']
                             for t in tex],
            }
        return out

    # ---------------------------------------------------------------- nodi

    def nodes(self) -> list[dict]:
        """Record node (tipo 17): la scena e' un albero.

            +0x40 float[4]  posizione
            +0x50 float[4]  quaternione di rotazione
            +0x60 float[4]  scala
            +0x70 u32       **indice dell'oggetto genitore**, 0xFFFFFFFF = radice
            +0x78 u32       **indice dell'oggetto collegato**, 0xFFFFFFFF = nessuno

        I due indici sono nella tabella degli oggetti, non CRC. Il genitore e'
        sempre un altro node; il collegato e' sempre mesh, light, skin o
        camera - mai un node. Verificato su 11.671 nodi, senza cicli.
        """
        out = []
        for i in range(self.n_objects):
            o = self.object(i)
            if o['type'] != 17:
                continue
            pos = struct.unpack_from('>4f', self.data, o['off'] + 0x40)
            rot = struct.unpack_from('>4f', self.data, o['off'] + 0x50)
            scl = struct.unpack_from('>4f', self.data, o['off'] + 0x60)
            par, _z, att, _z2 = struct.unpack_from('>4I', self.data, o['off'] + 0x70)
            out.append({'index': i, 'name': o['name'],
                        'pos': pos[:3], 'quat': rot, 'scale': scl[:3],
                        'parent': None if par == 0xffffffff else par,
                        'attached': None if att == 0xffffffff else att})
        return out

    def world(self, node: dict, by_index: dict) -> tuple:
        """Matrice di mondo del nodo: le trasformazioni dei genitori composte
        dalla radice in giu'. Restituisce 12 float, righe di una 3x4."""
        chain, n = [], node
        while n is not None:
            chain.append(n)
            n = by_index.get(n['parent']) if n['parent'] is not None else None
        m = (1., 0., 0., 0.,
             0., 1., 0., 0.,
             0., 0., 1., 0.)
        for n in reversed(chain):
            m = _mul(m, _trs(n['pos'], n['quat'], n['scale']))
        return m

    def geometry(self) -> list[dict]:
        """Vertici e indici di ogni chunk di ogni mesh, decodificati secondo la
        dichiarazione. Restituisce la lista delle mesh, ciascuna coi suoi
        chunk arricchiti di 'vertices' e 'indices'."""
        out = []
        for m in self.meshes():
            chunks = []
            for c in m['chunks']:
                code = 'I' if c['idx_size'] == 4 else 'H'
                idx = struct.unpack_from(f'>{c["index_count"]}{code}',
                                         self.data, c['ib'])
                chunks.append({**c, 'indices': list(idx),
                               'vertices': self.vertices(c)})
            out.append({**m, 'chunks': chunks})
        return out

    def vertices(self, c: dict) -> list[dict]:
        """Decodifica un vertex buffer secondo la dichiarazione del chunk."""
        stride, data = c['stride'], self.data
        verts = []
        for k in range(c['vertex_count']):
            o0 = c['vb'] + k * stride
            v = {}
            for a in c['decl']:
                p = o0 + a['off']
                if a['fmt']:
                    v[a['sem']] = struct.unpack_from(a['fmt'], data, p)
                elif a['size'] == 4:
                    v[a['sem']] = tuple(data[p:p + 4])
            verts.append(v)
        return verts

    def validate(self) -> list[str]:
        e = []
        if self.file_size != len(self.data):
            e.append(f'campo 0x0C {self.file_size} != filesize {len(self.data)}')
        if self.buf_base + self.buf_size != len(self.data):
            e.append(f'0x08+0x18 = {self.buf_base + self.buf_size} != filesize')
        if self.magic2 != 0x27:
            e.append(f'0x06 = {self.magic2:#x}, atteso 0x27')
        for c, v, exp in (('0x10', self.c10, 1), ('0x14', self.c14, 3),
                          ('0x24', self.c24, 112), ('0x2C', self.c2c, 0xffffffff),
                          ('0x3C', self.c3c, 0xcccccccc)):
            if v != exp:
                e.append(f'{c} = {v:#x}, atteso {exp:#x}')
        # le stringhe devono essere consecutive e NUL-terminate
        for i, so in enumerate(self.str_off):
            if not (0 < so < len(self.data)):
                e.append(f'stringa {i}: offset {so:#x} fuori range')
                break
            if i and self.data[so - 1] != 0:
                e.append(f'stringa {i} @{so:#x} non preceduta da NUL')
                break
            if not self.strings[i]:
                e.append(f'stringa {i} vuota')
                break
        for i, oo in enumerate(self.obj_off):
            if not (0x40 < oo < len(self.data)):
                e.append(f'oggetto {i}: offset {oo:#x} fuori range')
                break
        return e


def cmd_info(path: pathlib.Path) -> int:
    d = pick(path)
    print(f'{path.name}  {len(d.data):,} byte   exporter v{d.version:#06x}')
    print(f'  strutture {d.buf_base:#x} + buffer {d.buf_size:#x}   '
          f'strtab @ {d.strtab_off + BASE:#x}   f38 -> {d.f38 + BASE:#x}')
    print(f'  {d.n_strings} stringhe, {d.n_objects} oggetti')
    ms = d.meshes()
    mats = d.materials()
    if ms:
        print('\n  geometria:')
        for m in ms:
            for j, c in enumerate(m['chunks']):
                fmt = ' '.join(f'{a["sem"]}:{a["type"]}' for a in c['decl'])
                tag = f'{m["name"]}[{j}]' if len(m['chunks']) > 1 else m['name']
                mt = mats.get(c['material'], {}).get('name', '?')
                print(f'    {tag:<28} {c["vertex_count"]:6} vert  '
                      f'{c["index_count"]:6} idx {c["prim"]:<5} '
                      f'stride {c["stride"]:3}  mat={mt}\n{"":34}{fmt}')
    if mats:
        print('\n  materiali:')
        for m in mats.values():
            tx = ', '.join(f'{s}:{t}' for s, t in enumerate(m['textures']) if t)
            print(f'    {m["name"]:<28} shader={m["shader"]:#06x}  '
                  f'Kd=({m["diffuse"][0]:.2f},{m["diffuse"][1]:.2f},'
                  f'{m["diffuse"][2]:.2f},{m["diffuse"][3]:.2f})  {tx}')
    print('\n  oggetti:')
    for i in range(d.n_objects):
        o = d.object(i)
        print(f'    [{i}] @{o["off"]:#06x}  {o["type_name"]:<9} {o["name"]:<34} '
              f'base={o["base"]!r}')
    print('\n  stringhe:')
    byclass = collections.Counter(classify(s) for s in d.strings)
    print('    ' + ', '.join(f'{k}:{v}' for k, v in byclass.most_common()))
    for s in d.strings[:24]:
        print(f'    {zlib.crc32(s.encode()) & 0xffffffff:08x}  {s}')
    if len(d.strings) > 24:
        print(f'    ... e altre {len(d.strings) - 24}')
    errs = d.validate()
    print('\n  OK' if not errs else '\n  ERRORI:\n    ' + '\n    '.join(errs))
    return 0


def cmd_survey(root: pathlib.Path) -> int:
    files = sources(root)
    vers, classes = collections.Counter(), collections.Counter()
    nstr = nobj = nblk = 0
    bad = []
    for p in files:
        try:
            bl = blocks(p)
        except Exception as ex:                                   # noqa: BLE001
            bad.append(f'{p.name}: contenitore illeggibile: {ex}')
            continue
        for name, blob in bl:
            nblk += 1
            try:
                d = Dsb(blob, name)
            except Exception as ex:                               # noqa: BLE001
                bad.append(f'{name}: {ex}')
                continue
            for err in d.validate():
                bad.append(f'{name}: {err}')
            vers[f'{d.version:#06x}'] += 1
            nstr += d.n_strings
            nobj += d.n_objects
            for i in range(d.n_objects):
                classes[d.object(i)['type_name']] += 1
    print(f'{len(files)} file, {nblk:,} blocchi DSBF, {nstr:,} stringhe, '
          f'{nobj:,} oggetti')
    print(f'versioni exporter: {dict(vers)}')
    print('\n=== tipi di oggetto (campo +0x0C, autorevole) ===')
    for k, v in classes.most_common():
        print(f'  {k:<10} {v:7,}  ({100.0*v/nobj:.1f}%)')
    print(f'\nproblemi: {len(bad)}')
    for b in bad[:10]:
        print(f'  {b}')
    return 1 if bad else 0


def cmd_names(root: pathlib.Path) -> int:
    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv \
        else root.parent / 'dsb_names.json'
    names: dict[str, str] = {}
    for p in root.rglob('*.dsb'):
        try:
            d = Dsb(p.read_bytes(), str(p))
        except Exception:                                          # noqa: BLE001
            continue
        for s in d.strings:
            names.setdefault(f'{zlib.crc32(s.encode()) & 0xffffffff:08x}', s)
    out.write_text(json.dumps(names, indent=0, sort_keys=True), encoding='utf-8')
    print(f'{len(names):,} nomi -> {out}')
    return 0


def write_mtl(d: Dsb, out: pathlib.Path) -> pathlib.Path:
    """Scrive il .mtl accanto all'.obj. Le texture sono nominate come sul
    disco (`.dds`); i pacchetti TPKG usano la stessa chiave."""
    mtl = out.with_suffix('.mtl')
    with mtl.open('w', encoding='utf-8') as f:
        f.write(f'# materiali di {pathlib.Path(d.path).name} via tools/dsb.py\n')
        for m in d.materials().values():
            f.write(f'\nnewmtl {m["name"]}\n')
            f.write('Kd {:.4g} {:.4g} {:.4g}\n'.format(*m['diffuse'][:3]))
            f.write('Ka {:.4g} {:.4g} {:.4g}\n'.format(*m['ambient']))
            f.write('Ks {:.4g} {:.4g} {:.4g}\n'.format(*m['specular']))
            f.write('Ke {:.4g} {:.4g} {:.4g}\n'.format(*m['emission']))
            f.write(f'Ns {m["spec_pow"]:.4g}\n')
            f.write(f'd {m["diffuse"][3]:.4g}\n')
            if m['textures'][0]:
                f.write(f'map_Kd {m["textures"][0]}\n')
            if m['textures'][2]:
                f.write(f'norm {m["textures"][2]}\n')
            if m['textures'][3]:
                f.write(f'refl {m["textures"][3]}\n')
    return mtl


def pick(path: pathlib.Path) -> Dsb:
    """Il blocco DSBF da esportare. Per i `.pac` si sceglie la sezione con
    `--sec N`; senza, quella con piu' oggetti, che e' la cella da cui si vede
    di piu'."""
    bl = blocks(path)
    if len(bl) == 1:
        return Dsb(bl[0][1], str(path))
    if '--sec' in sys.argv:
        i = int(sys.argv[sys.argv.index('--sec') + 1])
    else:
        i = max(range(len(bl)),
                key=lambda k: struct.unpack_from('>I', bl[k][1], 0x28)[0])
        print(f'{len(bl)} sezioni; scelta la piu\' ricca, la {i} '
              f'(usa --sec N per un\'altra)')
    return Dsb(bl[i][1], bl[i][0])


def cmd_obj(path: pathlib.Path, out: pathlib.Path) -> int:
    d = pick(path)
    geo = d.geometry()
    mats = d.materials()
    nv = nf = 0
    with out.open('w', encoding='utf-8') as f:
        f.write(f'# da {path.name} via tools/dsb.py\n')
        f.write(f'mtllib {write_mtl(d, out).name}\n')
        base = 1
        for m in geo:
            for j, c in enumerate(m['chunks']):
                verts = c['vertices']
                if not verts:
                    continue
                tag = f'{m["name"]}.{j}' if len(m['chunks']) > 1 else m['name']
                f.write(f'\no {tag}\n')
                if c['material'] in mats:
                    f.write(f'usemtl {mats[c["material"]]["name"]}\n')
                for v in verts:
                    p = v['pos']
                    f.write(f'v {p[0]:.6g} {p[1]:.6g} {p[2]:.6g}\n')
                has_n = 'nrm' in verts[0]
                has_t = 'uv' in verts[0]
                if has_n:
                    for v in verts:
                        n = v['nrm']
                        f.write(f'vn {n[0]:.6g} {n[1]:.6g} {n[2]:.6g}\n')
                if has_t:
                    for v in verts:
                        t = v['uv']
                        f.write(f'vt {t[0]:.6g} {t[1]:.6g}\n')
                for ia, ib, ic in triangles(c):
                    a, b, cc = ia + base, ib + base, ic + base
                    if has_n and has_t:
                        f.write(f'f {a}/{a}/{a} {b}/{b}/{b} {cc}/{cc}/{cc}\n')
                    elif has_n:
                        f.write(f'f {a}//{a} {b}//{b} {cc}//{cc}\n')
                    else:
                        f.write(f'f {a} {b} {cc}\n')
                    nf += 1
                base += len(verts)
                nv += len(verts)
    print(f'{len(geo)} mesh, {nv:,} vertici, {nf:,} triangoli -> {out}')
    return 0


def cmd_scene(path: pathlib.Path, out: pathlib.Path) -> int:
    """Esporta la scena composta: ogni mesh trasformata nello spazio di mondo
    dalla catena di nodi che la porta alla radice."""
    d = pick(path)
    geo = {m['name']: m for m in d.geometry()}
    mats = d.materials()
    nodes = d.nodes()
    by_index = {n['index']: n for n in nodes}
    nv = nf = nm = 0
    with out.open('w', encoding='utf-8') as f:
        f.write(f'# scena composta da {path.name} via tools/dsb.py\n')
        f.write(f'mtllib {write_mtl(d, out).name}\n')
        base = 1
        for n in nodes:
            if n['attached'] is None:
                continue
            m = geo.get(d.object(n['attached'])['name'])
            if m is None:
                continue
            w = d.world(n, by_index)
            nm += 1
            for j, c in enumerate(m['chunks']):
                verts = c['vertices']
                if not verts:
                    continue
                f.write(f'\no {n["name"]}.{j}\n')
                if c['material'] in mats:
                    f.write(f'usemtl {mats[c["material"]]["name"]}\n')
                for v in verts:
                    p = apply(w, v['pos'])
                    f.write(f'v {p[0]:.6g} {p[1]:.6g} {p[2]:.6g}\n')
                for ia, ib, ic in triangles(c):
                    f.write(f'f {ia + base} {ib + base} {ic + base}\n')
                    nf += 1
                base += len(verts)
                nv += len(verts)
    print(f'{nm} nodi disegnabili, {nv:,} vertici, {nf:,} triangoli -> {out}')
    return 0


def cmd_verify(root: pathlib.Path) -> int:
    """Controlli sulla geometria, ciascuno con un oracolo interno al formato.

    1. somma delle dimensioni dichiarate == stride (che il chunk dichiara a
       parte, come vb_size / n_vert);
    2. ogni indice < numero di vertici;
    3. le posizioni devono RIEMPIRE il bounding box del record, non solo
       starci dentro;
    4. normale, tangente e binormale devono essere versori;
    5. le facce a voxel sono allineate agli assi: i tre vertici di ogni
       triangolo condividono un valore su x, y o z. Discrimina lista da strip.
    """
    files = sources(root)
    n = collections.Counter()
    prim_vs_mod3 = collections.Counter()
    bad = []
    every = 1
    if '--every' in sys.argv:
        every = int(sys.argv[sys.argv.index('--every') + 1])
        print(f'campionamento: 1 blocco ogni {every}')
    seen = 0
    for src in files:
        for pname, blob in blocks(src):
            seen += 1
            if (seen - 1) % every:
                continue
            n['blocchi'] += 1
            try:
                d = Dsb(blob, pname)
                geo = d.geometry()
            except Exception as ex:                               # noqa: BLE001
                bad.append(f'{pname}: {ex}')
                continue
            _verify_one(d, geo, pname, n, prim_vs_mod3, bad)
    print(f'{len(files)} file, {n["blocchi"]:,} blocchi, {n["mesh"]:,} mesh, '
          f'{n["chunk"]:,} chunk, {n["vertici"]:,} vertici, '
          f'{n["triangoli"]:,} triangoli')
    print(f'bounding box della mesh riempito esattamente: {n["bbox riempito"]:,}, '
          f'{n["bbox NON riempito"]} no')
    print(f'scena composta contro bbox dell\'header: '
          f'{n["scena nel bbox header"]:,} blocchi, '
          f'{n["scena FUORI bbox header"]} no')
    for key in ('nrm', 'tan', 'binorm'):
        t = n[f'{key} totali']
        if t:
            print(f'  {key:<7} versori: {100.0 * n[f"{key} versori"] / t:.2f}% '
                  f'su {t:,}')
    if n['facce totali']:
        print(f'  facce allineate agli assi: '
              f'{100.0 * n["facce assiali"] / n["facce totali"]:.2f}% '
              f'su {n["facce totali"]:,} triangoli')
    print('\nriferimenti incrociati:')
    for k in sorted(n):
        if k.startswith(('chunk ->', 'material ->', 'texture stage')):
            print(f'  {k:<26} {n[k]:7,}')
    print('\nprimitiva dichiarata contro divisibilita\' per 3 del conteggio indici:')
    for (prim, div3), c in sorted(prim_vs_mod3.items(), key=lambda x: str(x[0])):
        print(f'  {str(prim):<6} icount%3==0: {str(div3):<5} {c:6}')
    print(f'\nproblemi: {len(bad)}')
    for b in bad[:10]:
        print(f'  {b}')
    return 1 if bad else 0


def _verify_one(d, geo, pname, n, prim_vs_mod3, bad) -> None:
    """Applica tutti gli oracoli a un singolo blocco DSBF."""
    # 6. i riferimenti incrociati devono cadere su oggetti del tipo giusto
    types = [d.object(i)['type_name'] for i in range(d.n_objects)]
    for m in geo:
        for c in m['chunks']:
            v = c['material']
            n['chunk -> ' + (types[v] if v < len(types) else 'FUORI RANGE')] += 1
    for mat in d.materials().values():
        v = mat['effect']
        n['material -> ' + (types[v] if v < len(types) else 'FUORI RANGE')] += 1
        for s, t in enumerate(mat['textures']):
            if t is not None:
                n[f'texture stage {s}'] += 1

    # 7. la scena composta deve riempire il bounding box dell'header
    by_name = {m['name']: m for m in geo}
    nodes = d.nodes()
    by_index = {nd['index']: nd for nd in nodes}
    smn = [float('inf')] * 3
    smx = [float('-inf')] * 3
    for nd in nodes:
        if nd['attached'] is None:
            continue
        m = by_name.get(d.object(nd['attached'])['name'])
        if m is None:
            continue
        w = d.world(nd, by_index)
        for c in m['chunks']:
            for v in c['vertices']:
                q = apply(w, v['pos'])
                for j in range(3):
                    smn[j] = min(smn[j], q[j])
                    smx[j] = max(smx[j], q[j])
    lo, hi = d.bbox
    span = max(hi[j] - lo[j] for j in range(3))
    if span > 0 and smn[0] != float('inf'):
        eps = span * 0.02 + 1e-3
        if all(abs(smn[j] - lo[j]) <= eps and abs(smx[j] - hi[j]) <= eps
               for j in range(3)):
            n['scena nel bbox header'] += 1
        else:
            n['scena FUORI bbox header'] += 1
    for m in geo:
        n['mesh'] += 1
        lo, hi = m['bbox']
        mn = [float('inf')] * 3
        mx = [float('-inf')] * 3
        for c in m['chunks']:
            n['chunk'] += 1
            n['vertici'] += c['vertex_count']
            if c['decl_size'] != c['stride']:
                bad.append(f'{pname}/{m["name"]}: dichiarazione '
                           f'{c["decl_size"]} != stride {c["stride"]}')
            if c['indices'] and max(c['indices']) >= c['vertex_count']:
                bad.append(f'{pname}/{m["name"]}: indice fuori range')
            prim_vs_mod3[(c['prim'], c['index_count'] % 3 == 0)] += 1
            for v in c['vertices']:
                for j in range(3):
                    mn[j] = min(mn[j], v['pos'][j])
                    mx[j] = max(mx[j], v['pos'][j])
                for key in ('nrm', 'tan', 'binorm'):
                    u = v.get(key)
                    if u:
                        n[f'{key} totali'] += 1
                        s = u[0] * u[0] + u[1] * u[1] + u[2] * u[2]
                        if abs(s - 1.0) < 0.02:
                            n[f'{key} versori'] += 1
            tri = 0
            for ia, ib, ic in triangles(c):
                a, b, cc = (c['vertices'][x]['pos'] for x in (ia, ib, ic))
                n['facce totali'] += 1
                if any(abs(a[j] - b[j]) < 1e-3 and abs(b[j] - cc[j]) < 1e-3
                       for j in range(3)):
                    n['facce assiali'] += 1
                tri += 1
            n['triangoli'] += tri
        span = max(hi[j] - lo[j] for j in range(3))
        if span > 0:
            eps = span * 0.02 + 1e-3
            if all(abs(mn[j] - lo[j]) <= eps and abs(mx[j] - hi[j]) <= eps
                   for j in range(3)):
                n['bbox riempito'] += 1
            else:
                n['bbox NON riempito'] += 1
                bad.append(f'{pname}/{m["name"]}: bbox non riempito')


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, target = sys.argv[1], pathlib.Path(sys.argv[2])
    if cmd == 'obj':
        return cmd_obj(target, pathlib.Path(sys.argv[3]))
    if cmd == 'scene':
        return cmd_scene(target, pathlib.Path(sys.argv[3]))
    if cmd == 'info':
        return cmd_info(target)
    if cmd == 'survey':
        return cmd_survey(target)
    if cmd == 'verify':
        return cmd_verify(target)
    if cmd == 'names':
        return cmd_names(target)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
