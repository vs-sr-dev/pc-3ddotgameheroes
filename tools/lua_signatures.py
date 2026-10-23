"""
lua_signatures.py - Fase 1b: inferisce le firme dei metodi nativi dai call site.

Per ogni metodo `ricevitore:Metodo(...)` chiamato dal corpus Lua ricava:
  - numero di chiamate e file coinvolti
  - arita' osservata (istogramma) -> parametri obbligatori vs opzionali
  - tipo di ogni posizione (letterale numerico/stringa/booleano, riferimento a
    enum con relativo namespace, variabile, risultato di chiamata, espressione)
  - se il valore di ritorno viene consumato

Produce:
  docs/lua_signatures.md    report leggibile
  docs/lua_signatures.json  dati grezzi
  generated/script_api.h    stub C++ dell'interfaccia da implementare

Uso:  python lua_signatures.py <dir_corpus> [--outdir <radice_progetto>]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lua_lex import tokenize, decode_lua, Token  # noqa: E402
from lua_tables import TYPE_NAME, is_constant_like  # noqa: E402

# token che, se precedono una chiamata, indicano che il valore di ritorno serve
VALUE_CONTEXT = frozenset((
    '=', '(', ',', '==', '~=', '<', '>', '<=', '>=',
    '..', '+', '-', '*', '/', '%', '^', '#', '{', '[',
))
VALUE_KEYWORDS = frozenset(('return', 'and', 'or', 'not', 'if', 'elseif', 'while', 'until'))

# ricevitori che denotano la stessa classe host
RECEIVER_ALIAS = {
    'event': 'Event',
    'object': 'Object',
    'gpackagemanager': 'PackageManager',
    'g_mapmanager': 'MapManager',
}


def norm_receiver(chain: str) -> str:
    last = chain.rsplit('.', 1)[-1]
    return RECEIVER_ALIAS.get(last.lower(), last)


def split_args(toks: list[Token]) -> list[list[Token]]:
    """Divide la lista di token degli argomenti sulle virgole di primo livello."""
    if not toks:
        return []
    out, cur, depth = [], [], 0
    for t in toks:
        if t.kind == 'OP':
            if t.value in '([{':
                depth += 1
            elif t.value in ')]}':
                depth -= 1
            elif t.value == ',' and depth == 0:
                out.append(cur)
                cur = []
                continue
        cur.append(t)
    out.append(cur)
    return out


def classify(toks: list[Token]) -> tuple[str, str | None, str | None]:
    """-> (tipo, namespace_enum, valore_campione)"""
    if not toks:
        return 'empty', None, None

    if len(toks) == 1:
        t = toks[0]
        if t.kind == 'STRING':
            return 'string', None, t.value
        if t.kind == 'NUMBER':
            return 'number', None, t.value
        if t.kind == 'KEYWORD' and t.value in ('true', 'false'):
            return 'bool', None, t.value
        if t.kind == 'KEYWORD' and t.value == 'nil':
            return 'nil', None, None
        if t.kind == 'NAME':
            return 'var', None, t.value

    # numero negativo
    if (len(toks) == 2 and toks[0].kind == 'OP' and toks[0].value == '-'
            and toks[1].kind == 'NUMBER'):
        return 'number', None, '-' + toks[1].value

    # catena puntata senza chiamate: riferimento a costante/enum
    if (len(toks) >= 3
            and all(t.kind == 'NAME' or (t.kind == 'OP' and t.value == '.') for t in toks)
            and toks[0].kind == 'NAME' and toks[-1].kind == 'NAME'):
        path = ''.join(t.value for t in toks)
        return 'enum', path.rsplit('.', 1)[0], path

    if any(t.kind == 'OP' and t.value == '(' for t in toks):
        return 'call', None, None
    if toks[0].kind == 'OP' and toks[0].value == '{':
        return 'table', None, None
    return 'expr', None, None


class MethodInfo:
    def __init__(self, name: str):
        self.name = name
        self.calls = 0
        self.ret_used = 0
        self.files: set[str] = set()
        self.receivers: collections.Counter[str] = collections.Counter()
        self.arity: collections.Counter[int] = collections.Counter()
        self.pos_types: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        self.pos_enums: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        self.pos_samples: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)


def build_module_map(src: str, fallback: str) -> callable:
    """Nel bundle all.lua.eu i moduli sono delimitati da '-- Start <percorso>'.
    Restituisce una funzione linea -> nome modulo."""
    marks: list[tuple[int, str]] = []
    for n, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s.startswith('--') and s[2:].lstrip().startswith('Start '):
            marks.append((n, s[2:].lstrip()[6:].strip()))
    if not marks:
        return lambda _line: fallback

    import bisect
    starts = [m[0] for m in marks]
    names = [m[1] for m in marks]

    def resolve(line: int) -> str:
        i = bisect.bisect_right(starts, line) - 1
        return names[i] if i >= 0 else fallback

    return resolve


def scan(tokens: list[Token], modname: callable, methods: dict[str, MethodInfo]) -> None:
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t.kind != 'NAME':
            i += 1
            continue

        # catena puntata del ricevitore
        start = i
        j = i
        chain = [t.value]
        while (j + 2 < n and tokens[j + 1].kind == 'OP' and tokens[j + 1].value == '.'
               and tokens[j + 2].kind == 'NAME'):
            chain.append(tokens[j + 2].value)
            j += 2

        # deve seguire  ':' NAME '('
        if not (j + 3 < n
                and tokens[j + 1].kind == 'OP' and tokens[j + 1].value == ':'
                and tokens[j + 2].kind == 'NAME'
                and tokens[j + 3].kind == 'OP' and tokens[j + 3].value == '('):
            i += 1
            continue

        meth = tokens[j + 2].value
        # e non deve essere una *definizione*  (function X:m(...))
        if start > 0 and tokens[start - 1].kind == 'KEYWORD' and tokens[start - 1].value == 'function':
            i = j + 3
            continue

        # ritaglia gli argomenti bilanciando le parentesi
        k = j + 4
        depth = 1
        args_toks: list[Token] = []
        while k < n and depth > 0:
            tk = tokens[k]
            if tk.kind == 'OP':
                if tk.value in '([{':
                    depth += 1
                elif tk.value in ')]}':
                    depth -= 1
                    if depth == 0:
                        break
            args_toks.append(tk)
            k += 1

        # il ritorno serve?
        ret_used = False
        if start > 0:
            p = tokens[start - 1]
            if (p.kind == 'OP' and p.value in VALUE_CONTEXT) or \
               (p.kind == 'KEYWORD' and p.value in VALUE_KEYWORDS):
                ret_used = True

        mi = methods.setdefault(meth, MethodInfo(meth))
        mi.calls += 1
        mi.files.add(modname(t.line))
        mi.receivers[norm_receiver('.'.join(chain))] += 1
        if ret_used:
            mi.ret_used += 1

        args = split_args(args_toks)
        mi.arity[len(args)] += 1
        for pos, a in enumerate(args):
            kind, ns, sample = classify(a)
            mi.pos_types[pos][kind] += 1
            if ns:
                mi.pos_enums[pos][ns] += 1
            if sample is not None and kind in ('string', 'number', 'enum', 'bool'):
                mi.pos_samples[pos][sample] += 1

        i = k + 1


# ---------------------------------------------------------------- tipizzazione

def cpp_type(mi: MethodInfo, pos: int) -> str:
    types = mi.pos_types[pos]
    enums = mi.pos_enums[pos]
    concrete = {k: v for k, v in types.items() if k in ('string', 'number', 'bool', 'enum')}

    if not concrete:
        return 'ScriptValue'
    if enums:
        ns, _ = enums.most_common(1)[0]
        if ns in TYPE_NAME:
            return TYPE_NAME[ns]
        # non ogni catena puntata e' un enum: Boss.m_info.armHp e' un campo dati.
        # Accetta solo se i membri osservati seguono la convenzione PREFISSO_.
        leaves = [s.rsplit('.', 1)[-1] for s in mi.pos_samples[pos]]
        if leaves and sum(map(is_constant_like, leaves)) * 2 >= len(leaves):
            return ns.rsplit('.', 1)[-1]
        return 'ScriptValue'
    dom = max(concrete, key=concrete.get)
    if dom == 'string':
        return 'const char*'
    if dom == 'bool':
        return 'bool'
    if dom == 'number':
        vals = mi.pos_samples[pos]
        if any('.' in v or 'e' in v.lower() for v in vals):
            return 'float'
        return 'int'
    return 'ScriptValue'


def signature(mi: MethodInfo) -> str:
    lo, hi = min(mi.arity), max(mi.arity)
    params = []
    for pos in range(hi):
        t = cpp_type(mi, pos)
        opt = ' /*opt*/' if pos >= lo else ''
        params.append(f'{t} a{pos}{opt}')
    ret = 'ScriptValue' if mi.ret_used else 'void'
    return f'{ret} {mi.name}({", ".join(params)})'


# ---------------------------------------------------------------------- output

def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = pathlib.Path(sys.argv[1])
    outdir = pathlib.Path(sys.argv[sys.argv.index('--outdir') + 1]) if '--outdir' in sys.argv \
        else pathlib.Path(__file__).parent.parent

    # accetta un singolo file (es. all.lua.eu, che e' un soprainsieme dei file
    # sciolti: analizzarli insieme conterebbe due volte gli stessi call site)
    files = [root] if root.is_file() else \
        [p for p in root.rglob('*') if p.suffix.lower() in ('.eu', '.lua')]
    methods: dict[str, MethodInfo] = {}
    defined: set[str] = set()

    for p in files:
        src = decode_lua(p.read_bytes())
        toks = tokenize(src)
        for i in range(len(toks) - 3):
            if (toks[i].kind == 'KEYWORD' and toks[i].value == 'function'
                    and toks[i + 2].kind == 'OP' and toks[i + 2].value == ':'):
                defined.add(toks[i + 3].value)
        scan(toks, build_module_map(src, p.name), methods)

    native = {k: v for k, v in methods.items() if k not in defined}
    by_recv: dict[str, list[MethodInfo]] = collections.defaultdict(list)
    for mi in native.values():
        by_recv[mi.receivers.most_common(1)[0][0]].append(mi)

    total_calls = sum(m.calls for m in native.values())
    print(f'File analizzati : {len(files)}')
    print(f'Metodi nativi   : {len(native)}   call site: {total_calls:,}')
    print(f'Classi host     : {len(by_recv)}')
    print()
    for recv in sorted(by_recv, key=lambda r: -sum(m.calls for m in by_recv[r])):
        ms = by_recv[recv]
        print(f'  {recv:<16} {len(ms):3} metodi, {sum(m.calls for m in ms):6,} chiamate')

    # --- report markdown
    doc = outdir / 'docs' / 'lua_signatures.md'
    doc.parent.mkdir(parents=True, exist_ok=True)
    with doc.open('w', encoding='utf-8') as f:
        f.write('# Firme inferite dell\'API di scripting\n\n')
        f.write(f'Generato da `tools/lua_signatures.py` su {len(files)} file Lua.\n')
        f.write(f'{len(native)} metodi nativi, {total_calls:,} call site.\n\n')
        f.write('Tipi dedotti dai letterali osservati: `enum` = riferimento a tabella '
                'costante Lua, `ScriptValue` = solo variabili/espressioni, tipo non '
                'determinabile staticamente. `/*opt*/` = posizione assente in almeno '
                'una chiamata.\n\n')
        for recv in sorted(by_recv, key=lambda r: -sum(m.calls for m in by_recv[r])):
            ms = sorted(by_recv[recv], key=lambda m: -m.calls)
            f.write(f'\n## {recv} — {len(ms)} metodi, {sum(m.calls for m in ms):,} chiamate\n\n')
            for mi in ms:
                pct = 100.0 * mi.ret_used / mi.calls
                f.write(f'### `{signature(mi)}`\n\n')
                f.write(f'- {mi.calls:,} chiamate in {len(mi.files)} moduli; '
                        f'ritorno usato {mi.ret_used}/{mi.calls} ({pct:.0f}%)\n')
                ar = ', '.join(f'{k}({v})' for k, v in sorted(mi.arity.items()))
                f.write(f'- arità: {ar}\n')
                if len(mi.receivers) > 1:
                    rc = ', '.join(f'{r}({c})' for r, c in mi.receivers.most_common())
                    f.write(f'- ricevitori: {rc}\n')
                for pos in range(max(mi.arity)):
                    tc = ', '.join(f'{k}({v})' for k, v in mi.pos_types[pos].most_common())
                    line = f'- `a{pos}`: {tc}'
                    ex = [v for v, _ in mi.pos_samples[pos].most_common(3)]
                    if ex:
                        line += '  — es. ' + ', '.join(f'`{e}`' for e in ex)
                    f.write(line + '\n')
                f.write('\n')

    # --- json
    js = outdir / 'docs' / 'lua_signatures.json'
    payload = {
        recv: [{
            'name': mi.name,
            'signature': signature(mi),
            'calls': mi.calls,
            'ret_used': mi.ret_used,
            'arity': dict(mi.arity),
            'receivers': dict(mi.receivers),
            'params': [{
                'types': dict(mi.pos_types[p]),
                'enums': dict(mi.pos_enums[p]),
                'samples': dict(mi.pos_samples[p].most_common(5)),
                'cpp': cpp_type(mi, p),
            } for p in range(max(mi.arity))],
        } for mi in sorted(by_recv[recv], key=lambda m: -m.calls)]
        for recv in by_recv
    }
    js.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding='utf-8')

    # --- header C++
    hdr = outdir / 'generated' / 'script_api.h'
    hdr.parent.mkdir(parents=True, exist_ok=True)
    with hdr.open('w', encoding='utf-8') as f:
        f.write('// Generato da tools/lua_signatures.py - NON modificare a mano.\n')
        f.write('// Interfaccia di scripting inferita dai call site del corpus Lua\n')
        f.write(f'// originale ({total_calls:,} call site, {len(native)} metodi).\n')
        f.write('//\n// I tipi sono dedotti staticamente: verificare i casi ScriptValue\n')
        f.write('// contro l\'EBOOT prima di considerarli definitivi.\n\n')
        f.write('#pragma once\n#include "script_value.h"\n\n')
        for recv in sorted(by_recv, key=lambda r: -sum(m.calls for m in by_recv[r])):
            ms = sorted(by_recv[recv], key=lambda m: -m.calls)
            f.write(f'// {sum(m.calls for m in ms):,} call site\n')
            f.write(f'class I{recv} {{\npublic:\n    virtual ~I{recv}() = default;\n\n')
            for mi in ms:
                f.write(f'    // {mi.calls:,}x\n    virtual {signature(mi)} = 0;\n')
            f.write('};\n\n')

    print(f'\nScritti:\n  {doc}\n  {js}\n  {hdr}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
