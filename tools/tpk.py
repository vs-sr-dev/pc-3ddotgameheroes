"""
tpk.py - parser del formato TPKG (texture package) di 3D Dot Game Heroes.

Formato ricostruito per intero e validato su tutti i 763 pacchetti del disco
(4.033 texture). Tutto big-endian.

  header, 0x20 byte
    0x00  char[4]  'TPKG'
    0x04  char[4]  'ps3\\0'
    0x08  u16      versione (4 su tutto il disco)
    0x0A  u16      numero di texture
    0x0C  u32      offset dell'area dati       (0x0C + 0x10 == dimensione file)
    0x10  u32      dimensione dell'area dati
    0x14  u32      fine della tabella dei mip
    0x18  u32[2]   zero

  entry, 0x20 byte ciascuna, a partire da 0x20
    +0x00 u32      offset assoluto del nome (stringa NUL-terminated)
    +0x04 u32      dimensione totale della texture (somma dei mip)
    +0x08 u32      offset del dato, relativo all'area dati
    +0x0C u32      formato pixel: 9=DXT1, 10=DXT3, 11=DXT5
    +0x10 u16      larghezza
    +0x12 u16      altezza
    +0x14 u8       numero di livelli mip
    +0x15 u8[3]    zero
    +0x18 u32      ignoto, varia per entry (666 valori distinti; indice?)
    +0x1C u32      timestamp Unix di build, uguale per tutte le entry del
                   pacchetto (441 distinti, tutti fra agosto 2009 e marzo 2010)

  segue: tabella dei nomi, poi la tabella dei mip (u32 con la dimensione di
  ogni livello, in ordine, per ogni texture), allineata a 4 byte dopo i nomi;
  poi padding fino all'area dati.

Note sul formato pixel
  - il codice non e' ricavabile dalla dimensione: DXT3 e DXT5 occupano
    entrambi 16 byte per blocco 4x4. Va letto da +0x0C.
  - DXT3 domina nettamente (3.867 texture contro 46 DXT5, 116 DXT1): l'alfa
    esplicita a 4 bit tiene i bordi netti richiesti dall'estetica a voxel,
    dove l'alfa interpolata di DXT5 sfrangerebbe.

Uso:
  python tpk.py info   <file.tpk>
  python tpk.py survey <directory>              censimento e validazione
  python tpk.py export <file.tpk> <outdir>      scrive .dds e .png
  python tpk.py sheet  <file.tpk> <out.png>     provino a contatto
"""
from __future__ import annotations

import collections
import datetime
import io
import math
import pathlib
import struct
import sys

MAGIC = b'TPKG'

# codice a +0x0C -> (nome, fourCC DDS, byte per blocco 4x4)
FORMATS: dict[int, tuple[str, bytes, int]] = {
    9:  ('DXT1', b'DXT1', 8),
    10: ('DXT3', b'DXT3', 16),
    11: ('DXT5', b'DXT5', 16),
}


class Entry:
    __slots__ = ('name', 'size', 'data_off', 'pixfmt', 'w', 'h',
                 'n_mips', 'unk18', 'stamp', 'mips', 'faces')

    @property
    def fmt_name(self) -> str:
        return FORMATS.get(self.pixfmt, (f'fmt{self.pixfmt}?', b'', 0))[0]

    def __repr__(self) -> str:
        return (f'{self.name} {self.w}x{self.h} {self.fmt_name} '
                f'{self.size}B {len(self.mips)}mip')


class Tpk:
    def __init__(self, data: bytes, path: str = ''):
        self.path = path
        self.data = data
        if data[:4] != MAGIC:
            raise ValueError(f'{path}: magic {data[:4]!r}, atteso TPKG')
        self.platform = data[4:8].rstrip(b'\0').decode('ascii', 'replace')
        (self.version, self.count, self.data_off, self.data_size,
         self.miptable_end) = struct.unpack_from('>HHIII', data, 8)

        self.entries: list[Entry] = []
        names_end = 0
        for i in range(self.count):
            o = 0x20 + i * 0x20
            e = Entry()
            (name_off, e.size, e.data_off, e.pixfmt, e.w, e.h,
             e.n_mips, e.unk18, e.stamp) = struct.unpack_from('>IIIIHHB3xII', data, o)
            end = data.index(b'\0', name_off)
            e.name = data[name_off:end].decode('ascii', 'replace')
            names_end = max(names_end, end + 1)
            e.mips = []
            self.entries.append(e)

        # tabella dei mip: subito dopo i nomi, allineata a 4
        self.miptable_off = (names_end + 3) & ~3
        o = self.miptable_off
        for e in self.entries:
            e.mips = list(struct.unpack_from(f'>{e.n_mips}I', data, o))
            o += 4 * e.n_mips
            # Le cubemap memorizzano 6 facce consecutive, ciascuna con la
            # propria catena di mip, ma la tabella elenca i mip una volta sola.
            # Non e' stato trovato un flag esplicito: il numero di facce si
            # ricava dal rapporto fra size e somma dei mip.
            tot = sum(e.mips)
            e.faces = e.size // tot if tot and e.size % tot == 0 else 1

    def validate(self) -> list[str]:
        errs = []
        if self.data_off + self.data_size != len(self.data):
            errs.append(f'data_off+data_size={self.data_off + self.data_size} '
                        f'!= filesize {len(self.data)}')
        end = self.miptable_off + 4 * sum(e.n_mips for e in self.entries)
        if end != self.miptable_end:
            errs.append(f'fine miptable calcolata {end} != dichiarata {self.miptable_end}')
        for e in self.entries:
            if sum(e.mips) * e.faces != e.size:
                errs.append(f'{e.name}: somma mip {sum(e.mips)} x {e.faces} facce '
                            f'!= size {e.size}')
            if e.data_off + e.size > self.data_size:
                errs.append(f'{e.name}: dato oltre l\'area dati')
            info = FORMATS.get(e.pixfmt)
            if info and e.mips:
                blocks = math.ceil(e.w / 4) * math.ceil(e.h / 4)
                if blocks and e.mips[0] != blocks * info[2]:
                    errs.append(f'{e.name}: mip0 {e.mips[0]} != {blocks}blocchi'
                                f'x{info[2]}B ({info[0]})')
        return errs

    def blob(self, e: Entry) -> bytes:
        s = self.data_off + e.data_off
        return self.data[s:s + e.size]

    def dds(self, e: Entry) -> bytes:
        info = FORMATS.get(e.pixfmt)
        if not info:
            raise ValueError(f'{e.name}: formato {e.pixfmt} sconosciuto')
        return (dds_header(e.w, e.h, len(e.mips), info[1], e.mips[0], e.faces)
                + self.blob(e))

    def image(self, e: Entry):
        from PIL import Image
        return Image.open(io.BytesIO(self.dds(e)))


def dds_header(w: int, h: int, mips: int, fourcc: bytes, linear: int,
               faces: int = 1) -> bytes:
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000
    caps = 0x1000 | (0x400008 if mips > 1 else 0)
    caps2 = 0
    if faces == 6:                       # DDSCAPS2_CUBEMAP + le sei facce
        caps |= 0x8
        caps2 = 0x200 | 0x400 | 0x800 | 0x1000 | 0x2000 | 0x4000 | 0x8000
    return (b'DDS ' + struct.pack('<II', 124, flags)
            + struct.pack('<IIII', h, w, linear, 0)
            + struct.pack('<I', mips) + b'\0' * 44
            + struct.pack('<II', 32, 0x4) + fourcc + b'\0' * 20
            + struct.pack('<IIIII', caps, caps2, 0, 0, 0))


def cmd_info(path: pathlib.Path) -> int:
    t = Tpk(path.read_bytes(), str(path))
    stamps = sorted({e.stamp for e in t.entries})
    when = ', '.join(
        datetime.datetime.fromtimestamp(s, datetime.UTC).strftime('%Y-%m-%d %H:%M')
        for s in stamps[:3])
    print(f'{path.name}  v{t.version} [{t.platform}]  {t.count} texture')
    print(f'  dati @ {t.data_off} + {t.data_size} = {len(t.data)}   '
          f'miptable {t.miptable_off}..{t.miptable_end}   build {when}')
    for e in t.entries:
        cube = '  CUBEMAP' if e.faces == 6 else ''
        print(f'    {e.name:<30} {e.w:>4}x{e.h:<4} {e.fmt_name:<5} '
              f'{len(e.mips):>2} mip{cube}  off={e.data_off:<9} size={e.size:<9} '
              f'mips={e.mips[:6]}{"..." if len(e.mips) > 6 else ""}')
    errs = t.validate()
    print('  OK' if not errs else '  ERRORI:\n    ' + '\n    '.join(errs))
    return 0


def cmd_survey(root: pathlib.Path) -> int:
    files = sorted(root.rglob('*.tpk'))
    fmts, dims, versions, stamps = (collections.Counter() for _ in range(4))
    nmips = collections.Counter()
    bad, ntex, nbytes = [], 0, 0
    for p in files:
        try:
            t = Tpk(p.read_bytes(), str(p))
        except Exception as ex:                                   # noqa: BLE001
            bad.append(f'{p.name}: {ex}')
            continue
        versions[t.version] += 1
        for err in t.validate():
            bad.append(f'{p.name}: {err}')
        for e in t.entries:
            ntex += 1
            nbytes += e.size
            fmts[e.fmt_name] += 1
            dims[(e.w, e.h)] += 1
            nmips[len(e.mips)] += 1
            stamps[e.stamp] += 1

    print(f'{len(files)} pacchetti, {ntex:,} texture, {nbytes/1024/1024:.1f} MB di pixel')
    print(f'versioni header: {dict(versions)}')
    print('\n=== formati ===')
    for f, n in fmts.most_common():
        print(f'  {f:<8} {n:6,}  ({100.0*n/ntex:.1f}%)')
    print('\n=== dimensioni piu\' comuni ===')
    for (w, h), n in dims.most_common(8):
        print(f'  {w:>5} x {h:<5} {n:6,}')
    print('\n=== numero di mip ===')
    print('  ' + ', '.join(f'{k}:{v:,}' for k, v in sorted(nmips.items())))
    ds = [datetime.datetime.fromtimestamp(s, datetime.UTC) for s in stamps]
    print(f'\n=== build stamp: {len(stamps)} distinti, '
          f'da {min(ds):%Y-%m-%d} a {max(ds):%Y-%m-%d} ===')
    print(f'\nproblemi: {len(bad)}')
    for b in bad[:10]:
        print(f'  {b}')
    return 1 if bad else 0


def cmd_export(path: pathlib.Path, outdir: pathlib.Path) -> int:
    t = Tpk(path.read_bytes(), str(path))
    outdir.mkdir(parents=True, exist_ok=True)
    npng = 0
    for e in t.entries:
        try:
            dds = t.dds(e)
        except ValueError as ex:
            print(f'  salto: {ex}')
            continue
        stem = pathlib.Path(e.name).stem
        (outdir / f'{stem}.dds').write_bytes(dds)
        try:
            t.image(e).convert('RGBA').save(outdir / f'{stem}.png')
            npng += 1
        except Exception as ex:                                   # noqa: BLE001
            print(f'  {e.name}: DDS ok, PNG fallito ({ex})')
    print(f'{len(t.entries)} texture -> {outdir}  ({npng} PNG)')
    return 0


def cmd_sheet(path: pathlib.Path, outpng: pathlib.Path, cell: int = 128) -> int:
    from PIL import Image, ImageDraw
    t = Tpk(path.read_bytes(), str(path))
    ims = []
    for e in t.entries:
        try:
            im = t.image(e).convert('RGBA')
        except Exception:                                         # noqa: BLE001
            continue
        # fondo a scacchi per rendere visibile l'alfa
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        for y in range(0, im.height, 8):
            for x in range(0, im.width, 8):
                if (x // 8 + y // 8) % 2:
                    bg.paste((190, 190, 190, 255), (x, y, min(x+8, im.width),
                                                    min(y+8, im.height)))
        ims.append((e, Image.alpha_composite(bg, im).convert('RGB')))
    if not ims:
        print('nessuna texture decodificabile')
        return 1
    cols = min(6, len(ims))
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new('RGB', (cols * cell, rows * (cell + 12)), (25, 25, 25))
    dr = ImageDraw.Draw(sheet)
    for i, (e, im) in enumerate(ims):
        im.thumbnail((cell, cell), Image.NEAREST)
        x, y = (i % cols) * cell, (i // cols) * (cell + 12)
        sheet.paste(im, (x + (cell - im.width) // 2, y + 12))
        dr.text((x + 2, y + 1), f'{e.name[:20]} {e.w}x{e.h} {e.fmt_name}',
                fill=(255, 220, 0))
    sheet.save(outpng)
    print(f'{len(ims)} texture -> {outpng}')
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, target = sys.argv[1], pathlib.Path(sys.argv[2])
    if cmd == 'info':
        return cmd_info(target)
    if cmd == 'survey':
        return cmd_survey(target)
    if cmd == 'export':
        return cmd_export(target, pathlib.Path(sys.argv[3]))
    if cmd == 'sheet':
        return cmd_sheet(target, pathlib.Path(sys.argv[3]))
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
