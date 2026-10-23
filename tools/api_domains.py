"""
api_domains.py - Fase 1d: raggruppa i metodi nativi per sottosistema.

Serve a stabilire l'ordine di implementazione dell'host e a stimare il lavoro:
quanti metodi e quante chiamate pesa ogni sottosistema, e quanti metodi
restano non classificati (cioe' da capire a mano).

Legge docs/lua_signatures.json prodotto da lua_signatures.py.

Uso:  python api_domains.py [--outdir <radice_progetto>]
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

# Ordinato: vince la prima regola che matcha. Le regole piu' specifiche prima.
DOMAINS: list[tuple[str, str]] = [
    ('Dialogo/messaggi', r'Print|Message|Balloon|Select|Talk|Serif|Window|Continue'),
    ('Camera',           r'Camera|Dof|Fov|LookAt|Zoom|Viewpoint'),
    ('Audio',            r'Bgm|BGM|PlaySe|PlaySE|Sound|Volume|Voice|Jingle|Se$|Se[A-Z]'),
    # La forgia delle spade e' la meccanica-firma del gioco: sei attributi
    # (length, thick, power, penetrate, bullet, special) ciascuno con costo,
    # livello base e livello massimo. Va prima di tutto il resto per non
    # farsi rubare i metodi da 'Cost'/'Level'/'Sword'.
    ('Spada/forgia',     r'(Length|Thick|Penetrate|Bullet|Special|Power)(Cost|Level)'
                         r'|MaxCost|RestCost|Sword|Blade|Forge'),
    ('Economia/negozio', r'Money|Price|Shop|Store|Buy|Sell|Amount|LimitsHave|UseCount'
                         r'|[sSgG]etNum|Coin'),
    ('Salute/danno',     r'Hp|HP|Damage|Dead|Destroy|Life|Heal|Revive|Kill'),
    ('Progressione',     r'Book|Album|Trophy|Regist|Medal|Clear|Complete'),
    ('Animazione',       r'Animation|Anime|Motion|Pose|Frame'),
    ('Trasformazione',   r'Pos|Direction|Speed|Distance|Move|Rot|Angle|Scale|Jump|Warp|Height|Vector'),
    ('Collisione/fisica', r'Hit|Collision|Wall|Ground|Gravity|Push|Bound'),
    ('Effetti/render',   r'Effect|Efc|Particle|Fade|Color|Light|Shadow|Alpha|Blur|Filter|Draw|Visible|Texture|Flash'),
    ('Flag/stato',       r'Flag|Phase|Save|Load|GameData|Status|Param|UserInt'),
    ('Mappa',            r'Map|Area|Field|Dungeon|Room|Scene'),
    ('Input/controllo',  r'Pad|Button|Key|Input|Lock|Unlock|Trigger'),
    ('Entita/attore',    r'Node|Type|Actor|Npc|Enemy|Player|Boss|Object|Create|Delete|Spawn|Living|Item'),
    ('Tempo/flusso',     r'Time|Timer|Wait|Pause|Sleep|Update|Start|Stop|End|Reset|Init'),
    ('Risorse',          r'Package|Resource|Preload|Release|Reference'),
    ('Minigioco',        r'MiniGame|Minigame|Game'),
]
COMPILED = [(name, re.compile(pat)) for name, pat in DOMAINS]


def classify(method: str) -> str:
    for name, rx in COMPILED:
        if rx.search(method):
            return name
    return '(non classificato)'


def main() -> int:
    outdir = pathlib.Path(sys.argv[sys.argv.index('--outdir') + 1]) if '--outdir' in sys.argv \
        else pathlib.Path(__file__).parent.parent
    src = outdir / 'docs' / 'lua_signatures.json'
    if not src.exists():
        print(f'manca {src}: esegui prima lua_signatures.py')
        return 1
    data = json.loads(src.read_text(encoding='utf-8'))

    rows = []
    for host, methods in data.items():
        for m in methods:
            rows.append((classify(m['name']), host, m['name'], m['calls'],
                         m['signature'], m['ret_used']))

    dom_methods: collections.Counter[str] = collections.Counter()
    dom_calls: collections.Counter[str] = collections.Counter()
    for dom, _h, _n, calls, _s, _r in rows:
        dom_methods[dom] += 1
        dom_calls[dom] += calls

    total_m = sum(dom_methods.values())
    total_c = sum(dom_calls.values())
    print(f'{total_m} metodi, {total_c:,} chiamate, {len(dom_methods)} sottosistemi\n')
    print(f'{"sottosistema":<20} {"metodi":>7} {"chiamate":>10}  {"% chiam.":>8}')
    print('-' * 50)
    for dom, n in dom_calls.most_common():
        print(f'{dom:<20} {dom_methods[dom]:>7} {n:>10,}  {100.0*n/total_c:>7.1f}%')

    out = outdir / 'docs' / 'api_domains.md'
    with out.open('w', encoding='utf-8') as f:
        f.write('# Metodi dell\'API per sottosistema\n\n')
        f.write(f'Generato da `tools/api_domains.py`. {total_m} metodi, '
                f'{total_c:,} chiamate.\n\n')
        f.write('Classificazione per parola chiave nel nome: euristica, utile per '
                'ordinare il lavoro, non autorevole. I metodi non classificati '
                'sono quelli da esaminare a mano per primi.\n\n')
        f.write('| Sottosistema | Metodi | Chiamate | % |\n|---|---:|---:|---:|\n')
        for dom, n in dom_calls.most_common():
            f.write(f'| {dom} | {dom_methods[dom]} | {n:,} | {100.0*n/total_c:.1f}% |\n')
        for dom, _ in dom_calls.most_common():
            f.write(f'\n## {dom}\n\n')
            sel = sorted([r for r in rows if r[0] == dom], key=lambda r: -r[3])
            for _d, host, _n, calls, sig, _r in sel:
                f.write(f'- `{host}` — `{sig}`  ({calls:,}x)\n')
    print(f'\nScritto: {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
