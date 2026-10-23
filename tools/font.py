"""
font.py - il font di interfaccia: atlante, tabella dei caratteri, larghezze.

E' il primo pezzo di host che **esegue davvero uno script del gioco** invece di
imitarlo. `UserInterface/Font/Font.lua.eu` non e' un file di dati travestito da
Lua: e' Lua, e lo si carica con la VM (`lupa`), esattamente come fara' l'host.
Se la tesi del progetto - riusare gli script verbatim - vale da qualche parte,
vale prima di tutto qui.

Il descrittore dichiara tutto:

    TexturePackageName = "UserInterface/Font/Font_eng"   pacchetto TPKG
    TextureName        = "Font_eng.dds"                  texture dentro
    TableName          = "UserInterface/Font/Font.bin"   mappa dei caratteri
    TextureFontWidth   = 32     lato della cella nell'atlante
    TextureFontHeight  = 32
    FontWidth          = 20.0   corpo effettivo del glifo
    FontHeight         = 26.0
    Space              = 2.0    spaziatura fra caratteri
    CharacterWidth     = { {"Ａ", 18.0}, ... }   avanzamenti, per carattere

I nomi dei pacchetti sono **percorsi relativi alla cartella `data/`, senza
estensione**: `UserInterface/Font/Font_eng` -> `data/UserInterface/Font/
Font_eng.ps3.tpk`. E' la convenzione del package manager del gioco
(`gPackageManager`), e vale per tutti i riferimenti negli script.

`Font.bin` e' un array di **UTF-16BE**, un code point per glifo, nell'ordine in
cui i glifi stanno nell'atlante. Comincia con gli hiragana in ordine
あいうえお, poi i katakana, poi il resto: 688 glifi per la versione europea.
Non c'e' intestazione - la dimensione del file diviso due da' il numero di
glifi, ed e' l'unica interpretazione che non lascia byte spaiati.

Il testo del gioco e' scritto a **larghezza piena**: `Ｓｎａｐｓｈｏｔ
　ｆａｉｌｅｄ．`, non `Snapshot failed.`. La tabella `CharacterWidth` elenca
infatti Ａ-Ｚ e ａ-ｚ in forma full-width, ed e' il motivo per cui il font e'
proporzionale pur avendo una griglia fissa: la cella e' sempre 32, ma
l'avanzamento no.

Uso:
  python font.py info <Font.lua.eu>
  python font.py atlas <Font.lua.eu> <out.png>      l'atlante con la griglia
  python font.py draw <Font.lua.eu> "testo" <out.png>
"""
from __future__ import annotations

import pathlib
import sys

import tpk

CELL_COLS = None            # dedotto dalla larghezza dell'atlante


def data_root(path: pathlib.Path) -> pathlib.Path:
    """Risale da un file qualsiasi fino alla cartella `data/`, che e' la radice
    dei percorsi usati dagli script."""
    for p in [path] + list(path.parents):
        if p.name == 'data':
            return p
    raise SystemExit(f'{path}: non sono dentro una cartella data/')


def full_width(text: str) -> str:
    """Il gioco scrive a larghezza piena. Comodita': si passa `Hello` e si
    ottengono i caratteri che il font conosce davvero."""
    out = []
    for ch in text:
        o = ord(ch)
        if ch == ' ':
            out.append('　')
        elif 0x21 <= o <= 0x7e:
            out.append(chr(o - 0x21 + 0xff01))
        else:
            out.append(ch)
    return ''.join(out)


class Font:
    def __init__(self, lua_path: pathlib.Path):
        from lupa import LuaRuntime

        self.root = data_root(lua_path)
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(lua_path.read_text(encoding='utf-8'))
        d = lua.globals().Font
        if d is None:
            raise SystemExit(f'{lua_path}: nessuna tabella Font')

        self.cell = (int(d.TextureFontWidth), int(d.TextureFontHeight))
        self.size = (float(d.FontWidth), float(d.FontHeight))
        self.space = float(d.Space)
        self.width = {}
        for entry in d.CharacterWidth.values():
            ch, w = entry[1], float(entry[2])
            if ch:
                self.width[ch] = w

        table = self.root / str(d.TableName)
        raw = table.read_bytes()
        self.codes = [int.from_bytes(raw[i:i + 2], 'big')
                      for i in range(0, len(raw), 2)]
        self.index = {chr(c): i for i, c in enumerate(self.codes)}

        pkg = self.root / f'{d.TexturePackageName}.ps3.tpk'
        pack = tpk.Tpk(pkg.read_bytes(), str(pkg))
        want = str(d.TextureName).lower()
        entry = next((e for e in pack.entries if e.name.lower() == want),
                     pack.entries[0])
        self.image = pack.image(entry).convert('RGBA')
        self.cols = self.image.width // self.cell[0]
        self.package, self.texture = str(d.TexturePackageName), entry.name

    # -- glifi

    def cell_box(self, ch: str):
        i = self.index.get(ch)
        if i is None:
            return None
        cw, chh = self.cell
        return ((i % self.cols) * cw, (i // self.cols) * chh,
                (i % self.cols) * cw + cw, (i // self.cols) * chh + chh)

    def advance(self, ch: str) -> float:
        return self.width.get(ch, self.size[0]) + self.space

    def measure(self, text: str) -> tuple[float, float]:
        return (sum(self.advance(c) for c in text), self.size[1])

    def render(self, text: str, scale: float = 1.0, color=None):
        """Disegna una riga. L'atlante e' bianco su trasparente, quindi il
        colore si applica moltiplicando."""
        from PIL import Image

        w, h = self.measure(text)
        cw, chh = self.cell
        img = Image.new('RGBA', (max(int(w * scale) + 1, 1),
                                 int(chh * scale)), (0, 0, 0, 0))
        x = 0.0
        for ch in text:
            box = self.cell_box(ch)
            if box is not None:
                g = self.image.crop(box)
                if scale != 1.0:
                    g = g.resize((int(cw * scale), int(chh * scale)),
                                 Image.LANCZOS)
                img.alpha_composite(g, (int(x * scale), 0))
            x += self.advance(ch)
        if color:
            tint = Image.new('RGBA', img.size, tuple(color))
            r, g_, b, a = img.split()
            tint.putalpha(a)
            img = tint
        return img


def cmd_info(path: pathlib.Path) -> int:
    f = Font(path)
    print(f'{path.name}')
    print(f'  atlante {f.package} / {f.texture}  {f.image.width}x'
          f'{f.image.height}, celle {f.cell[0]}x{f.cell[1]} -> {f.cols} colonne')
    print(f'  corpo {f.size[0]}x{f.size[1]}, spaziatura {f.space}')
    print(f'  {len(f.codes)} glifi nella tabella, {len(f.width)} larghezze '
          f'dichiarate')
    groups = {'hiragana': (0x3040, 0x309f), 'katakana': (0x30a0, 0x30ff),
              'latino full-width': (0xff01, 0xff5e), 'CJK': (0x4e00, 0x9fff),
              'ASCII': (0x20, 0x7e)}
    for name, (lo, hi) in groups.items():
        n = sum(1 for c in f.codes if lo <= c <= hi)
        if n:
            print(f'    {name:<18} {n}')
    rest = [c for c in f.codes
            if not any(lo <= c <= hi for lo, hi in groups.values())]
    if rest:
        print(f'    altro              {len(rest)}: '
              + ' '.join(chr(c) for c in rest[:12]))
    print(f'  primi glifi: {"".join(chr(c) for c in f.codes[:24])}')
    return 0


def cmd_atlas(path: pathlib.Path, out: pathlib.Path) -> int:
    f = Font(path)
    f.image.convert('RGB').save(out)
    print(f'{f.image.width}x{f.image.height} -> {out}')
    return 0


def cmd_draw(path: pathlib.Path, text: str, out: pathlib.Path) -> int:
    from PIL import Image

    f = Font(path)
    lines = [full_width(t) for t in text.split('\\n')]
    imgs = [f.render(t, scale=2.0) for t in lines]
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs)
    sheet = Image.new('RGBA', (w, h), (24, 26, 34, 255))
    y = 0
    for i in imgs:
        sheet.alpha_composite(i, (0, y))
        y += i.height
    sheet.convert('RGB').save(out)
    missing = {c for t in lines for c in t if f.cell_box(c) is None}
    print(f'{len(lines)} righe -> {out}'
          + (f'; glifi assenti: {"".join(sorted(missing))}' if missing else ''))
    return 0


def main() -> int:
    # La console di Windows e' cp1252 e questo strumento stampa hiragana.
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, target = sys.argv[1], pathlib.Path(sys.argv[2])
    if cmd == 'info':
        return cmd_info(target)
    if cmd == 'atlas':
        return cmd_atlas(target, pathlib.Path(sys.argv[3]))
    if cmd == 'draw':
        return cmd_draw(target, sys.argv[3], pathlib.Path(sys.argv[4]))
    print(__doc__)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
