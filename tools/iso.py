"""
iso.py - estrattore ufficiale: legge il disco via UDF e produce extract/.

Perche' UDF e non ISO9660. Il disco ha entrambi i filesystem, ma i nomi
ISO9660 sono **troncati a 31 caratteri** e maiuscolizzati: `d_1_1_1.ps3.pac.gz`
diventa `D_1_1_1_PS3_PAC.GZ`. I nomi contano - in `format_pac.md` la cella
della griglia e' codificata nel nome della mesh, e i riferimenti fra materiale
e texture sono per nome. Quindi si estrae sempre via UDF.

Perche' un lettore scritto a mano. `pycdlib` rifiuta questo disco
(`UDF File Set Tag identifier not 256`) e ha ragione a modo suo: i Blu-ray PS3
usano UDF 2.50 con **partizione di metadati**, la seconda mappa di partizione
del Logical Volume Descriptor. Gli inode non stanno nella partizione fisica ma
dentro un file di metadati che la ricopre. Ignorarlo porta a leggere un File
Entry dove ci si aspetta il File Set Descriptor - esattamente l'errore di
pycdlib. Sono ~150 righe, e valgono l'indipendenza da una dipendenza esterna.

Catena dei descrittori, per chi dovesse rimetterci mano:

  settore 256      Anchor Volume Descriptor Pointer (tag 2) -> estensione VDS
  VDS              Partition Descriptor (tag 5)  -> settore d'inizio partizione
                   Logical Volume Descriptor (6) -> block size, ICB del FSD,
                                                    tabella delle partizioni
  mappa tipo 2     '*UDF Metadata Partition' -> LBA del file di metadati
  File Entry (261) del file di metadati, tipo 250 -> le sue estensioni *sono*
                   i blocchi della partizione di metadati
  File Set Desc.   (tag 256) -> ICB della directory radice
  File Entry       (261) o Extended File Entry (266) -> estensioni del dato
  directory        sequenza di File Identifier Descriptor (tag 257)

I *dati* dei file stanno nella partizione fisica; solo gli inode stanno nella
partizione di metadati. Da qui il campo `part` dei long_ad, che va rispettato.

Uso:
  python iso.py index                   riscrive tools/iso_index.tsv (nomi UDF)
  python iso.py sets                    cosa dichiara il manifesto, con i totali
  python iso.py manifest                calcola tools/manifest.tsv (sha256)
  python iso.py extract [set ...]       estrae in extract/ (default: tutti)
  python iso.py verify [set ...]        confronta extract/ col manifesto
  python iso.py magic <glob> [n]        primi byte dei file che corrispondono

Opzioni: --iso <file>  --out <dir>  --force (riestrai anche se gia' presente)

Il manifesto e' l'impronta del disco supportato, non contenuto del gioco: e'
versionabile e sta nel repository. `extract/` no - vedi la politica BYOA.
"""
from __future__ import annotations

import fnmatch
import gzip
import hashlib
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ISO = ROOT / '3D Dot Game Heroes (Europe).iso'
OUT = ROOT / 'extract'
INDEX = ROOT / 'tools' / 'iso_index.tsv'
MANIFEST = ROOT / 'tools' / 'manifest.tsv'

SECTOR = 2048

# I set dichiarati: nome -> (glob sui percorsi UDF, a cosa serve).
# `extract` senza argomenti li estrae tutti; questo elenco *e'* la definizione
# di cosa vuol dire "extract/ completo".
SETS: dict[str, tuple[tuple[str, ...], str]] = {
    'script':    (('*.lua', '*.lua.eu'),      'script di gioco, Lua sorgente'),
    'texture':   (('*.tpk',),                 'TPKG, texture'),
    'model':     (('*.dsb',),                 'DSBF, scene e modelli'),
    'map':       (('*_PAC.GZ', '*.pac.gz'),   'mappe, container di blocchi DSBF'),
    'collision': (('*.DPK', '*.dpk'),         'collisione'),
    'align':     (('*MAP_ALIGNMENT/*.DAT',),  'griglia logica e grafo del mondo'),
    'voxel':     (('*.edt', '*.EDT', '*.sav', '*.SAV'),
                                              'dati dell editor dei personaggi'),
    'shader':    (('*.spk', '*.pkg'),         'programmi Cg (solo per i simboli)'),
    'image':     (('*.png', '*.dds', '*.PNG', '*.DDS'), 'immagini sciolte'),
    'audio':     (('*.wav', '*.WAV'),         'suoni e musica'),
    'movie':     (('*.bik', '*.BIK'),         'filmati Bink'),
    'boot':      (('*/EBOOT.BIN', '*/PARAM.SFO'),
                                              'eseguibile e metadati (Fase 3)'),
    'font':      (('*/Font/Font.bin',),       'metriche del font di interfaccia'),
    'devtool':   (('*.exe',),                 'utility Windows lasciate sul disco'),
}

# Non dichiarati apposta: PS3UPDAT.PUP (il firmware, 256 MB), TROPHY.TRP,
# LICDIR/LIC.DAT, PS3LOGO.DAT, PS3_DISC.SFB - infrastruttura di piattaforma,
# nulla che riguardi il gioco - e IconData/Thumbs.db, che e' una cache di
# miniature di Windows finita sul master per distrazione.

# Passi derivati: dopo l'estrazione, da un file se ne ricava un altro.
# Sono parte del manifesto perche' senza di essi extract/ non e' completo.
DERIVED = {
    'map': ('pac', 'decompressione gzip -> extract/pac/*.pac'),
}


# --------------------------------------------------------------------------
# lettore UDF

class Node:
    __slots__ = ('path', 'size', 'extents', 'is_dir')

    def __init__(self, path: str, size: int, extents: list, is_dir: bool):
        self.path = path
        self.size = size
        self.extents = extents      # [(settore fisico, byte)]
        self.is_dir = is_dir

    @property
    def lba(self) -> int:
        return self.extents[0][0] if self.extents else 0


class Udf:
    """Lettore UDF di sola lettura, quel tanto che basta per elencare ed
    estrarre. Non gestisce ne' file sparsi ne' compressione: su un disco di
    gioco stampato non esistono."""

    def __init__(self, path: pathlib.Path):
        self.f = open(path, 'rb')
        self.parts: dict[int, list] = {}     # ref -> [(base fisica, blocchi)]
        self._read_volume()

    # -- primitive

    def _sect(self, n: int, count: int = 1) -> bytes:
        self.f.seek(n * SECTOR)
        return self.f.read(SECTOR * count)

    def _map(self, part: int, lba: int) -> int:
        """Blocco logico di una partizione -> settore fisico."""
        for base, length in self.parts[part]:
            if lba < length:
                return base + lba
            lba -= length
        raise ValueError(f'blocco {lba} fuori dalla partizione {part}')

    def _read_part(self, part: int, lba: int, size: int) -> bytes:
        """Legge `size` byte a partire da un blocco logico, seguendo le
        estensioni della partizione se ne attraversa il confine."""
        out = bytearray()
        while len(out) < size:
            phys = self._map(part, lba + len(out) // SECTOR)
            need = size - len(out)
            out += self._sect(phys, (need + SECTOR - 1) // SECTOR)[:need]
        return bytes(out)

    # -- descrittori

    def _read_volume(self) -> None:
        anchor = self._sect(256)
        if struct.unpack_from('<H', anchor, 0)[0] != 2:
            raise ValueError('nessun Anchor Volume Descriptor Pointer a 256')
        vds_len, vds_loc = struct.unpack_from('<II', anchor, 16)

        pd_start = lvd = None
        vds = self._sect(vds_loc, vds_len // SECTOR)
        for o in range(0, vds_len, SECTOR):
            tag = struct.unpack_from('<H', vds, o)[0]
            if tag == 5:
                pd_start = struct.unpack_from('<I', vds, o + 188)[0]
            elif tag == 6:
                lvd = vds[o:o + SECTOR]
        if pd_start is None or lvd is None:
            raise ValueError('Partition o Logical Volume Descriptor mancanti')

        if struct.unpack_from('<I', lvd, 212)[0] != SECTOR:
            raise ValueError('blocco logico diverso da 2048, non gestito')

        # La partizione fisica e' sempre il riferimento 0; la tabella delle
        # mappe segue a 440 e ne dichiara altre, virtuali.
        self.parts[0] = [(pd_start, 1 << 62)]
        n_maps = struct.unpack_from('<I', lvd, 268)[0]
        o = 440
        for ref in range(n_maps):
            kind, length = lvd[o], lvd[o + 1]
            if kind == 2 and lvd[o + 5:o + 28] == b'*UDF Metadata Partition':
                meta_lba = struct.unpack_from('<I', lvd, o + 40)[0]
                self.parts[ref] = self._metadata_extents(pd_start, meta_lba)
            o += length

        fsd_lba, fsd_part = struct.unpack_from('<IH', lvd, 252)
        fsd = self._read_part(fsd_part, fsd_lba, SECTOR)
        if struct.unpack_from('<H', fsd, 0)[0] != 256:
            raise ValueError('il File Set Descriptor non e\' dove dice il LVD')
        self.root = struct.unpack_from('<IH', fsd, 404)  # (lba, partizione)

    def _metadata_extents(self, pd_start: int, meta_lba: int) -> list:
        """Le estensioni del file di metadati (tipo 250) *sono* i blocchi
        della partizione di metadati."""
        fe = self._sect(pd_start + meta_lba)
        if struct.unpack_from('<H', fe, 0)[0] not in (261, 266):
            raise ValueError('file di metadati: File Entry non riconosciuto')
        return [(pd_start + lba, n // SECTOR)
                for lba, n, part in self._alloc(fe, 0)]

    def _alloc(self, fe: bytes, part: int):
        """Estensioni dichiarate da un File Entry, come (lba, byte, partizione).
        Il tipo di descrittore sta nei flag dell'ICB tag."""
        tag = struct.unpack_from('<H', fe, 0)[0]
        base = 216 if tag == 266 else 176
        l_ea, l_ad = struct.unpack_from('<II', fe, base - 8)
        kind = struct.unpack_from('<H', fe, 16 + 18)[0] & 7
        o, end = base + l_ea, base + l_ea + l_ad
        if kind == 3:                       # dato immediato, dentro il File Entry
            return [(-1, l_ad, o)]          # (-1, byte, offset nel File Entry)
        step = 8 if kind == 0 else 16
        out = []
        while o + step <= end:
            n, lba = struct.unpack_from('<II', fe, o)
            p = struct.unpack_from('<H', fe, o + 8)[0] if kind == 1 else part
            length, etype = n & 0x3FFFFFFF, n >> 30
            if etype == 3:                  # continuazione: non usata qui
                raise ValueError('estensione di continuazione, non gestita')
            if length and etype in (0, 1):  # allocata (registrata o meno)
                out.append((lba, length, p))
            o += step
        return out

    # -- albero

    def _entry(self, lba: int, part: int) -> tuple[bytes, int, int, list]:
        fe = self._read_part(part, lba, SECTOR)
        tag = struct.unpack_from('<H', fe, 0)[0]
        if tag not in (261, 266):
            raise ValueError(f'File Entry inatteso: tag {tag}')
        ftype = fe[16 + 11]
        size = struct.unpack_from('<Q', fe, 56)[0]
        return fe, ftype, size, self._alloc(fe, part)

    def _fids(self, fe: bytes, size: int, extents: list, part: int):
        """I File Identifier Descriptor di una directory."""
        data = bytearray()
        for lba, n, p in extents:
            data += fe[p:p + n] if lba == -1 else self._read_part(p, lba, n)
        data = bytes(data[:size])
        o = 0
        while o + 38 <= len(data):
            if struct.unpack_from('<H', data, o)[0] != 257:
                break
            chars, l_fi = data[o + 18], data[o + 19]
            child_lba, child_part = struct.unpack_from('<IH', data, o + 24)
            l_iu = struct.unpack_from('<H', data, o + 36)[0]
            raw = data[o + 38 + l_iu:o + 38 + l_iu + l_fi]
            o = (o + 38 + l_iu + l_fi + 3) & ~3
            if chars & 0x08 or not l_fi:        # voce genitore
                continue
            name = (raw[1:].decode('utf-16-be') if raw[0] == 16
                    else raw[1:].decode('latin-1'))
            yield name, bool(chars & 0x02), child_lba, child_part

    def walk(self) -> list[Node]:
        """Tutti i file del disco, in ordine di percorso."""
        out: list[Node] = []
        stack = [('', self.root[0], self.root[1])]
        while stack:
            prefix, lba, part = stack.pop()
            fe, ftype, size, extents = self._entry(lba, part)
            for name, is_dir, clba, cpart in self._fids(fe, size, extents, part):
                path = f'{prefix}/{name}' if prefix else name
                if is_dir:
                    stack.append((path, clba, cpart))
                    continue
                _, _, csize, cext = self._entry(clba, cpart)
                phys = [(self._map(p, l), n) for l, n, p in cext]
                out.append(Node(path, csize, phys, False))
        out.sort(key=lambda n: n.path)
        return out

    def chunks(self, node: Node, limit: int = 0, size: int = 1 << 22):
        """Il contenuto di un file, a blocchi: i filmati Bink arrivano a 1,2 GB
        e non ha senso tenerli in memoria per copiarli o farne l'hash."""
        want = min(limit, node.size) if limit else node.size
        done = 0
        for phys, n in node.extents:
            if done >= want:
                return
            self.f.seek(phys * SECTOR)
            left = min(n, want - done)
            while left > 0:
                b = self.f.read(min(size, left))
                if not b:
                    raise ValueError(f'{node.path}: file troncato')
                left -= len(b)
                done += len(b)
                yield b

    def read(self, node: Node, limit: int = 0) -> bytes:
        return b''.join(self.chunks(node, limit))

    def sha(self, node: Node) -> str:
        h = hashlib.sha256()
        for b in self.chunks(node):
            h.update(b)
        return h.hexdigest()


# --------------------------------------------------------------------------
# indice e manifesto

def load_index() -> list[Node]:
    if not INDEX.exists():
        raise SystemExit(f'indice mancante: {INDEX} - esegui prima: iso.py index')
    out = []
    for line in INDEX.read_text(encoding='utf-8').splitlines()[1:]:
        path, lba, size = line.split('\t')
        out.append(Node(path, int(size), [(int(lba), int(size))], False))
    return out


def match(node: Node, globs) -> bool:
    return any(fnmatch.fnmatch(node.path, g) for g in globs)


def select(names: list[str]) -> tuple[list[str], list[Node]]:
    """I nodi appartenenti ai set richiesti (tutti, se la lista e' vuota)."""
    unknown = [n for n in names if n not in SETS]
    if unknown:
        raise SystemExit(f'set sconosciuti: {", ".join(unknown)}\n'
                         f'disponibili: {", ".join(SETS)}')
    wanted = names or list(SETS)
    index = load_index()
    globs = tuple(g for n in wanted for g in SETS[n][0])
    return wanted, [n for n in index if match(n, globs)]


def dest(node: Node, out: pathlib.Path) -> pathlib.Path:
    return out / node.path


def human(n: int) -> str:
    for unit in ('B', 'kB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.1f} {unit}' if unit != 'B' else f'{n} B'
        n /= 1024
    return ''


def sha_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        while (b := fh.read(1 << 22)):
            h.update(b)
    return h.hexdigest()


# --------------------------------------------------------------------------
# comandi

def cmd_index(iso: pathlib.Path) -> int:
    udf = Udf(iso)
    nodes = udf.walk()
    with INDEX.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write('path\tlba\tsize\n')
        for n in nodes:
            if len(n.extents) > 1:
                print(f'  ! {n.path}: {len(n.extents)} estensioni, '
                      f'l\'indice ne registra una sola')
            fh.write(f'{n.path}\t{n.lba}\t{n.size}\n')
    total = sum(n.size for n in nodes)
    print(f'{len(nodes)} file, {human(total)} -> {INDEX}')
    return 0


def cmd_sets(iso: pathlib.Path) -> int:
    index = load_index()
    claimed = set()
    print(f'{"set":<11} {"file":>6} {"byte":>10}  descrizione')
    for name, (globs, desc) in SETS.items():
        hit = [n for n in index if match(n, globs)]
        claimed.update(id(n) for n in hit)
        print(f'{name:<11} {len(hit):>6} {human(sum(n.size for n in hit)):>10}  {desc}')
        if name in DERIVED:
            print(f'{"":<11} {"":>6} {"":>10}  + derivato: {DERIVED[name][1]}')
    rest = [n for n in index if id(n) not in claimed]
    print(f'\ndichiarati {len(index) - len(rest)} file su {len(index)}; '
          f'{len(rest)} non dichiarati')
    for n in sorted(rest, key=lambda n: -n.size)[:12]:
        print(f'  - {n.path}  ({human(n.size)})')
    if len(rest) > 12:
        print(f'  ... e altri {len(rest) - 12}')
    return 0


def cmd_manifest(iso: pathlib.Path, names: list[str]) -> int:
    wanted, nodes = select(names)
    udf = Udf(iso)
    rows, total = [], 0
    for i, n in enumerate(nodes):
        rows.append((n.path, n.size, udf.sha(n)))
        total += n.size
        if i % 50 == 0:
            print(f'  {i}/{len(nodes)}  {human(total)}...', end='\r')
    with MANIFEST.open('w', encoding='utf-8', newline='\n') as fh:
        fh.write('# PC-3Ddot - impronta del disco supportato.\n'
                 '# 3D Dot Game Heroes (Europe), BLES-00875.\n'
                 f'# {len(rows)} file, {total} byte. Percorsi UDF.\n'
                 'path\tsize\tsha256\n')
        for path, size, digest in rows:
            fh.write(f'{path}\t{size}\t{digest}\n')
    print(f'{len(rows)} file, {human(total)} -> {MANIFEST}')
    return 0


def load_manifest() -> dict[str, tuple[int, str]]:
    if not MANIFEST.exists():
        raise SystemExit(f'manifesto mancante: {MANIFEST} - '
                         f'esegui prima: iso.py manifest')
    out = {}
    for line in MANIFEST.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or line.startswith('path\t'):
            continue
        path, size, digest = line.split('\t')
        out[path] = (int(size), digest)
    return out


def cmd_extract(iso: pathlib.Path, out: pathlib.Path, names: list[str],
                force: bool) -> int:
    wanted, nodes = select(names)
    man = load_manifest() if MANIFEST.exists() else {}
    udf = Udf(iso)
    written = skipped = 0
    total = 0
    for n in nodes:
        path = dest(n, out)
        if path.exists() and path.stat().st_size == n.size and not force:
            skipped += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with path.open('wb') as fh:
            for b in udf.chunks(n):
                h.update(b)
                fh.write(b)
        if n.path in man and h.hexdigest() != man[n.path][1]:
            print(f'  ! {n.path}: hash diverso dal manifesto')
        written += 1
        total += n.size
    print(f'estratti {written} file ({human(total)}), {skipped} gia\' presenti')

    for name in wanted:
        if name in DERIVED:
            written += derive(out, name)
    return 0


def derive(out: pathlib.Path, name: str) -> int:
    """Passi derivati. Per ora solo le mappe: i .pac.gz vanno decompressi,
    perche' tutto il resto della catena legge il .pac in chiaro."""
    sub, _ = DERIVED[name]
    dst_dir = out / sub
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    # Solo i nomi UDF: `D_1_1_1.ps3.pac.gz` -> `d_1_1_1.ps3.pac`. Chi avesse
    # ancora i nomi troncati di 7-Zip (`D_1_1_1_PS3_PAC.GZ`) non e' conforme al
    # manifesto e va riestratto - accettarli qui genera solo doppioni.
    for src in sorted(out.rglob('*.pac.gz')):
        dst = dst_dir / f'{src.name.split(".")[0].lower()}.ps3.pac'
        if dst.exists():
            continue
        dst.write_bytes(gzip.decompress(src.read_bytes()))
        n += 1
    if n:
        print(f'  derivati {n} .pac in {dst_dir}')
    return n


def cmd_verify(out: pathlib.Path, names: list[str], deep: bool) -> int:
    man = load_manifest()
    wanted, nodes = select(names)
    missing, wrong, ok = [], [], 0
    for n in nodes:
        path = dest(n, out)
        if not path.exists():
            missing.append(n.path)
            continue
        size, digest = man.get(n.path, (n.size, None))
        if path.stat().st_size != size:
            wrong.append((n.path, 'dimensione'))
        elif deep and digest and sha_file(path) != digest:
            wrong.append((n.path, 'sha256'))
        else:
            ok += 1
    print(f'set: {", ".join(wanted)}')
    print(f'  {ok} file corrispondono' + ('' if deep else ' (solo dimensione;'
          ' usa --deep per lo sha256)'))
    for path in missing[:20]:
        print(f'  mancante  {path}')
    if len(missing) > 20:
        print(f'  ... e altri {len(missing) - 20} mancanti')
    for path, why in wrong[:20]:
        print(f'  diverso   {path}  ({why})')
    if not missing and not wrong:
        print('  nessun problema')
    return 1 if (missing or wrong) else 0


def cmd_magic(iso: pathlib.Path, glob: str, take: int) -> int:
    nodes = [n for n in load_index() if fnmatch.fnmatch(n.path, glob)]
    if take:
        nodes = nodes[:take]
    udf = Udf(iso)
    for n in nodes:
        b = udf.read(n, 32)
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in b)
        print(f'{n.path}  ({n.size:,} B)')
        print(f'    {b.hex(" ")}')
        print(f'    |{asc}|')
    return 0


def main() -> int:
    argv = sys.argv[1:]
    iso, out, force, deep = ISO, OUT, False, False
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--iso':
            iso = pathlib.Path(argv[i + 1]); i += 2
        elif a == '--out':
            out = pathlib.Path(argv[i + 1]); i += 2
        elif a == '--force':
            force = True; i += 1
        elif a == '--deep':
            deep = True; i += 1
        else:
            rest.append(a); i += 1

    if not rest:
        print(__doc__)
        return 1
    cmd, args = rest[0], rest[1:]

    if cmd in ('index', 'manifest', 'magic', 'extract') and not iso.exists():
        raise SystemExit(f'ISO non trovata: {iso}')

    if cmd == 'index':
        return cmd_index(iso)
    if cmd == 'sets':
        return cmd_sets(iso)
    if cmd == 'manifest':
        return cmd_manifest(iso, args)
    if cmd == 'extract':
        return cmd_extract(iso, out, args, force)
    if cmd == 'verify':
        return cmd_verify(out, args, deep)
    if cmd == 'magic':
        return cmd_magic(iso, args[0] if args else '*',
                         int(args[1]) if len(args) > 1 else 5)
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
