"""
lua_tables.py - Fase 1c: estrae le tabelle costanti dell'API di scripting.

Sono di due specie:

  A) definite in Lua   (es. `EventFlag = { scene_opening1 = 0, ... }`)
     -> recuperiamo nomi E valori: enum completi, gratis.

  B) iniettate dal motore (es. `actor_manager.AT_ITEM`, `soundList.SoundID.*`,
     `package_manager.IT_*`, `ObjectClass.TIMER_*`) — la tabella non esiste nel
     corpus Lua, vive nell'EBOOT.
     -> recuperiamo i nomi dei membri dai siti d'uso; i valori richiedono
        l'EBOOT (Fase 3). Per l'host questo non e' bloccante: i valori possono
        essere assegnati arbitrariamente, purche' coerenti fra Lua e motore.

Uso:  python lua_tables.py <bundle_o_dir> [--outdir <radice_progetto>]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lua_lex import tokenize, decode_lua, Token  # noqa: E402

CLOSE = {'(': ')', '[': ']', '{': '}'}

# Nomi di tipo per i namespace nativi. Puramente cosmetico: serve a produrre un
# header C++ leggibile invece di `actor_manager a0`. Modificabile a mano.
TYPE_NAME = {
    'actor_manager':        'ActorType',
    'package_manager':      'PackageId',
    'map_manager':          'MapId',
    'soundList.SoundID':    'SoundID',
    'item.Item':            'ItemId',
    'swordData.SwordData':  'SwordId',
    'GameDataFlags':        'GameDataFlag',
    'GameDataMapFlags':     'GameDataMapFlag',
    'EventFlag':            'EventFlag',
    'ObjectClass':          'ObjectClassId',
    'LIVING':               'LivingId',
}


import re

# Convenzione osservata su tutto il corpus: ogni costante enum ha un prefisso
# maiuscolo seguito da underscore -- AT_ IT_ IL_ SL_ MS_ BGM_ SE_ ATTACK_
# DUNGEON1_ ... I campi dati non la rispettano mai (accel, armHp,
# armAttackDistance), ne' i namespace di modulo (EventClass.Event).
RE_CONST = re.compile(r'^[A-Z][A-Z0-9]*_')


def is_constant_like(name: str) -> bool:
    """Distingue una costante enum da un accesso a campo (pos.x, Boss.m_info.armHp)."""
    return bool(RE_CONST.match(name)) or (name.isupper() and len(name) >= 2)


def looks_like_enum_ns(members) -> bool:
    """Scarta i namespace che sono in realta' oggetti con campi dati."""
    if not members:
        return False
    good = sum(1 for m in members if is_constant_like(m))
    return good * 2 >= len(members)


def _skip_value(toks: list[Token], i: int) -> int:
    """Avanza oltre un valore, fino alla virgola o alla graffa di chiusura di livello 0."""
    depth = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == 'OP':
            if t.value in '([{':
                depth += 1
            elif t.value in ')]}':
                if depth == 0:
                    return i
                depth -= 1
            elif t.value == ',' and depth == 0:
                return i
        i += 1
    return i


def parse_table(toks: list[Token], i: int):
    """toks[i] == '{'  ->  (dict, indice_dopo_la_graffa_chiusa)"""
    assert toks[i].value == '{'
    i += 1
    out: dict[str, object] = {}
    while i < len(toks):
        t = toks[i]
        if t.kind == 'OP' and t.value == '}':
            return out, i + 1
        if t.kind == 'OP' and t.value == ',':
            i += 1
            continue

        # chiave = valore
        if (t.kind in ('NAME', 'KEYWORD') and i + 1 < len(toks)
                and toks[i + 1].kind == 'OP' and toks[i + 1].value == '='):
            key = t.value
            j = i + 2
            v = toks[j] if j < len(toks) else None
            if v is None:
                break
            if v.kind == 'OP' and v.value == '{':
                sub, j = parse_table(toks, j)
                out[key] = sub
            elif v.kind == 'NUMBER':
                out[key] = v.value
                j += 1
            elif v.kind == 'STRING':
                out[key] = v.value
                j += 1
            elif (v.kind == 'OP' and v.value == '-' and j + 1 < len(toks)
                  and toks[j + 1].kind == 'NUMBER'):
                out[key] = '-' + toks[j + 1].value
                j += 2
            else:
                out[key] = None          # espressione: valore non costante
                j = _skip_value(toks, j)
            i = j
            continue

        i = _skip_value(toks, i)
        if i < len(toks) and toks[i].kind == 'OP' and toks[i].value == ',':
            i += 1
    return out, i


def find_lua_tables(toks: list[Token]) -> dict[str, dict]:
    """Assegnazioni di tabella a livello di istruzione.

    Copre sia `NAME = { ... }` sia i target puntati `A.B = { ... }` /
    `A.B.C = { ... }`: senza questi ultimi si perdono tabelle come
    `item.Item` o `Boss.m_info`, che finirebbero classificate come native.
    """
    out: dict[str, dict] = {}
    n = len(toks)
    i = 0
    while i + 2 < n:
        if toks[i].kind != 'NAME':
            i += 1
            continue
        # non deve essere una chiave dentro un'altra tabella
        prev = toks[i - 1] if i else None
        if prev and prev.kind == 'OP' and prev.value in (',', '{'):
            i += 1
            continue
        # target eventualmente puntato
        chain = [toks[i].value]
        j = i
        while (j + 2 < n and toks[j + 1].kind == 'OP' and toks[j + 1].value == '.'
               and toks[j + 2].kind == 'NAME'):
            chain.append(toks[j + 2].value)
            j += 2
        if (j + 2 < n
                and toks[j + 1].kind == 'OP' and toks[j + 1].value == '='
                and toks[j + 2].kind == 'OP' and toks[j + 2].value == '{'):
            tbl, k = parse_table(toks, j + 2)
            if tbl:
                # innesta la catena:  a.b.c = {...}  ->  {a: {b: {c: {...}}}}
                node = out.setdefault(chain[0], {})
                for part in chain[1:-1]:
                    nxt = node.get(part)
                    if not isinstance(nxt, dict):
                        nxt = {}
                        node[part] = nxt
                    node = nxt
                if len(chain) == 1:
                    node.update(tbl)
                else:
                    tgt = node.get(chain[-1])
                    if isinstance(tgt, dict):
                        tgt.update(tbl)
                    else:
                        node[chain[-1]] = tbl
            i = k
            continue
        i = j + 1
    return out


def harvest_refs(toks: list[Token]) -> collections.Counter:
    """Tutte le catene puntate usate come valore (non seguite da '(')."""
    refs: collections.Counter[str] = collections.Counter()
    i, n = 0, len(toks)
    while i < n:
        if toks[i].kind != 'NAME':
            i += 1
            continue
        prev = toks[i - 1] if i else None
        if prev and prev.kind == 'KEYWORD' and prev.value == 'function':
            i += 1
            continue
        chain = [toks[i].value]
        j = i
        while (j + 2 < n and toks[j + 1].kind == 'OP' and toks[j + 1].value == '.'
               and toks[j + 2].kind == 'NAME'):
            chain.append(toks[j + 2].value)
            j += 2
        nxt = toks[j + 1] if j + 1 < n else None
        is_call = nxt and nxt.kind == 'OP' and nxt.value in ('(', ':')
        if len(chain) >= 2 and not is_call:
            refs['.'.join(chain)] += 1
        i = j + 1
    return refs


def flatten(prefix: str, tbl: dict, out: dict) -> None:
    for k, v in tbl.items():
        path = f'{prefix}.{k}'
        if isinstance(v, dict):
            flatten(path, v, out)
        else:
            out[path] = v


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = pathlib.Path(sys.argv[1])
    outdir = pathlib.Path(sys.argv[sys.argv.index('--outdir') + 1]) if '--outdir' in sys.argv \
        else pathlib.Path(__file__).parent.parent

    files = [root] if root.is_file() else \
        [p for p in root.rglob('*') if p.suffix.lower() in ('.eu', '.lua')]

    lua_tables: dict[str, dict] = {}
    refs: collections.Counter[str] = collections.Counter()
    for p in files:
        toks = tokenize(decode_lua(p.read_bytes()))
        for name, tbl in find_lua_tables(toks).items():
            lua_tables.setdefault(name, {}).update(tbl)
        refs.update(harvest_refs(toks))

    flat: dict[str, object] = {}
    for name, tbl in lua_tables.items():
        flatten(name, tbl, flat)

    # raggruppa i riferimenti per namespace (tutto tranne l'ultimo componente)
    ns_members: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for path, cnt in refs.items():
        ns, _, leaf = path.rpartition('.')
        ns_members[ns][leaf] += cnt

    # classifica prima le tabelle definite in Lua: serve a riconoscere gli enum
    # che non seguono la convenzione di nome (EventFlag ha membri minuscoli, ma
    # e' definita in Lua con valori interi -> e' un enum a tutti gli effetti).
    ui_tables, enum_tables, data_tables = {}, {}, {}
    for name, tbl in lua_tables.items():
        leaves = {}
        flatten(name, tbl, leaves)
        if any(k.endswith(('.TexturePackageName', '.ScenePackageName')) for k in leaves):
            ui_tables[name] = leaves
        elif leaves and all(v is not None and str(v).lstrip('-').isdigit()
                            for v in leaves.values()):
            enum_tables[name] = leaves
        else:
            data_tables[name] = leaves

    native, resolved, rejected = {}, {}, {}
    for ns, members in ns_members.items():
        root_name = ns.split('.')[0]
        is_lua_enum = ns in enum_tables or root_name in enum_tables
        if not (is_lua_enum or looks_like_enum_ns(members)):
            rejected[ns] = members            # pos.x, Boss.m_info.armHp, ...
            continue
        known = sum(1 for m in members if f'{ns}.{m}' in flat)
        if root_name in lua_tables and known >= len(members) / 2:
            resolved[ns] = members
        else:
            native[ns] = members

    def score(d, ns):
        return -sum(d[ns].values())

    print(f'Tabelle definite in Lua : {len(lua_tables)}'
          f'  ({len(flat):,} costanti foglia)')
    print(f'  descrittori UI        : {len(ui_tables)}')
    print(f'  enum (tutti interi)   : {len(enum_tables)}')
    print(f'  tabelle dati          : {len(data_tables)}')
    print(f'Namespace enum risolti  : {len(resolved)}')
    print(f'Namespace enum NATIVI   : {len(native)}   (valori solo dall\'EBOOT)')
    print(f'Scartati (campi, non enum): {len(rejected)}'
          f'  es. {", ".join(sorted(rejected)[:5])}')
    print()
    print('=== enum risolti (nomi + valori dal Lua) ===')
    for ns in sorted(resolved, key=lambda n: score(resolved, n))[:12]:
        print(f'  {TYPE_NAME.get(ns, ns):<22} {len(resolved[ns]):4} membri usati, '
              f'{sum(resolved[ns].values()):5} riferimenti')
    print()
    print('=== enum NATIVI (solo nomi, dai siti d\'uso) ===')
    for ns in sorted(native, key=lambda n: score(native, n))[:15]:
        print(f'  {TYPE_NAME.get(ns, ns):<22} {len(native[ns]):4} membri, '
              f'{sum(native[ns].values()):5} riferimenti   <- {ns}')

    # ---- header C++ degli enum
    hdr = outdir / 'generated' / 'script_enums.h'
    hdr.parent.mkdir(parents=True, exist_ok=True)
    with hdr.open('w', encoding='utf-8') as f:
        f.write('// Generato da tools/lua_tables.py - NON modificare a mano.\n')
        f.write('// Tabelle costanti dell\'API di scripting.\n//\n')
        f.write('// I valori degli enum NATIVI non sono noti dal Lua (le tabelle\n')
        f.write('// vivono nell\'EBOOT). Sono numerati progressivamente qui: va bene\n')
        f.write('// finche\' host e Lua usano la stessa numerazione, ma vanno\n')
        f.write('// riconciliati con l\'EBOOT prima di leggere dati salvati originali.\n\n')
        f.write('#pragma once\n\n')
        for ns in sorted(resolved, key=lambda n: score(resolved, n)):
            tn = TYPE_NAME.get(ns, ns.replace('.', '_'))
            f.write(f'// {ns} - valori dal Lua\nenum class {tn} : int {{\n')
            for m in sorted(resolved[ns], key=lambda x: int(flat.get(f'{ns}.{x}', 0))):
                f.write(f'    {m} = {flat.get(f"{ns}.{m}", 0)},\n')
            f.write('};\n\n')
        for ns in sorted(native, key=lambda n: score(native, n)):
            tn = TYPE_NAME.get(ns, ns.replace('.', '_'))
            f.write(f'// {ns} - NATIVO, {len(native[ns])} membri, valori da verificare\n')
            f.write(f'enum class {tn} : int {{\n')
            for i, m in enumerate(sorted(native[ns])):
                f.write(f'    {m} = {i},\n')
            f.write('};\n\n')

    # ---- output
    docs = outdir / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    (docs / 'lua_tables.json').write_text(json.dumps({
        'lua_defined': flat,
        'resolved': {k: dict(v) for k, v in resolved.items()},
        'native': {k: dict(v) for k, v in native.items()},
        'ui_tables': {k: sorted(v) for k, v in ui_tables.items()},
        'enum_tables': list(enum_tables),
        'rejected_namespaces': {k: dict(v) for k, v in rejected.items()},
    }, indent=1, ensure_ascii=False), encoding='utf-8')

    with (docs / 'lua_tables.md').open('w', encoding='utf-8') as f:
        f.write('# Tabelle costanti dell\'API di scripting\n\n')
        f.write(f'Generato da `tools/lua_tables.py`. {len(flat):,} costanti '
                f'definite in Lua; {len(native)} namespace nativi.\n\n')
        f.write('## Enum risolti (valori noti dal Lua)\n\n')
        for ns in sorted(resolved, key=lambda n: score(resolved, n)):
            f.write(f'### `{ns}` — {len(resolved[ns])} membri usati\n\n')
            for m, c in resolved[ns].most_common():
                val = flat.get(f'{ns}.{m}', '?')
                f.write(f'- `{m}` = `{val}`  ({c} rif.)\n')
            f.write('\n')
        f.write('\n## Enum nativi (valori da recuperare dall\'EBOOT)\n\n')
        f.write('I nomi sono completi rispetto all\'uso negli script; i valori '
                'sono liberi purché coerenti fra host e Lua.\n\n')
        for ns in sorted(native, key=lambda n: score(native, n)):
            if sum(native[ns].values()) < 2:
                continue
            tn = TYPE_NAME.get(ns, ns)
            f.write(f'### `{tn}` — {len(native[ns])} membri  (namespace Lua `{ns}`)\n\n')
            for m, c in native[ns].most_common():
                f.write(f'- `{m}`  ({c} rif.)\n')
            f.write('\n')

        f.write('\n## Descrittori UI definiti in Lua\n\n')
        f.write(f'{len(ui_tables)} schermate descritte dichiarativamente in Lua, '
                'ciascuna con i pacchetti texture/scena che referenzia. '
                'L\'intero layer di interfaccia è dato, non codice.\n\n')
        f.write('| Schermata | Chiavi | TexturePackageName |\n|---|---|---|\n')
        for name in sorted(ui_tables, key=lambda n: -len(ui_tables[n])):
            leaves = ui_tables[name]
            tex = next((v for k, v in leaves.items()
                        if k.endswith('.TexturePackageName')), '—')
            f.write(f'| `{name}` | {len(leaves)} | `{tex}` |\n')

    print(f'\nScritti:\n  {docs / "lua_tables.md"}\n  {docs / "lua_tables.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
