"""
lua_lex.py - tokenizer Lua 5.x minimale ma corretto.

Serve alle analisi del corpus di script: i regex non reggono argomenti
annidati, letterali stringa contenenti parentesi e commenti lunghi.

Token = (kind, value, line) con kind in:
  NAME NUMBER STRING KEYWORD OP
"""
from __future__ import annotations

KEYWORDS = frozenset("""
and break do else elseif end false for function if in local nil not or
repeat return then true until while
""".split())

# ordinati per lunghezza decrescente: il matching e' greedy
OPERATORS = (
    '...', '..', '==', '~=', '<=', '>=',
    '+', '-', '*', '/', '%', '^', '#', '<', '>', '=',
    '(', ')', '{', '}', '[', ']', ';', ':', ',', '.',
)

_DIGITS = '0123456789'
_HEX = '0123456789abcdefABCDEF'


def decode_lua(data: bytes) -> str:
    """Decodifica un sorgente Lua del gioco, che ha encoding MISTO.

    Il corpus mescola UTF-8 e Shift-JIS anche dentro lo stesso file
    (`all.lua.eu`: ~11.800 righe UTF-8 e ~1.500 Shift-JIS). Decodificare tutto
    come UTF-8 corrompe le stringhe di dialogo giapponesi.

    Lo split su '\\n' e' sicuro: in Shift-JIS il secondo byte di una coppia non
    vale mai 0x0A, quindi il byte 0x0A e' sempre un vero fine riga.
    """
    out = []
    for line in data.split(b'\n'):
        try:
            out.append(line.decode('utf-8'))
        except UnicodeDecodeError:
            try:
                out.append(line.decode('cp932'))       # Shift-JIS Microsoft
            except UnicodeDecodeError:
                out.append(line.decode('utf-8', errors='replace'))
    return '\n'.join(out)


class Token:
    __slots__ = ('kind', 'value', 'line')

    def __init__(self, kind: str, value: str, line: int):
        self.kind = kind
        self.value = value
        self.line = line

    def __repr__(self):
        return f'{self.kind}({self.value!r})@{self.line}'


def _long_bracket(src: str, i: int):
    """Se src[i:] apre un long bracket [=*[ restituisce (livello, indice_dopo_apertura)."""
    if src[i] != '[':
        return None
    j = i + 1
    level = 0
    while j < len(src) and src[j] == '=':
        level += 1
        j += 1
    if j < len(src) and src[j] == '[':
        return level, j + 1
    return None


def tokenize(src: str) -> list[Token]:
    toks: list[Token] = []
    i, n, line = 0, len(src), 1

    while i < n:
        c = src[i]

        if c == '\n':
            line += 1
            i += 1
            continue
        if c in ' \t\r':
            i += 1
            continue

        # commenti
        if src.startswith('--', i):
            lb = _long_bracket(src, i + 2)
            if lb:
                level, start = lb
                close = ']' + '=' * level + ']'
                end = src.find(close, start)
                end = n if end < 0 else end + len(close)
                line += src.count('\n', i, end)
                i = end
            else:
                end = src.find('\n', i)
                i = n if end < 0 else end
            continue

        # stringa lunga
        lb = _long_bracket(src, i)
        if lb:
            level, start = lb
            close = ']' + '=' * level + ']'
            end = src.find(close, start)
            end = n if end < 0 else end
            toks.append(Token('STRING', src[start:end], line))
            line += src.count('\n', i, end)
            i = end + len(close)
            continue

        # stringa breve
        if c in '"\'':
            j = i + 1
            buf = []
            while j < n and src[j] != c:
                if src[j] == '\\' and j + 1 < n:
                    buf.append(src[j:j + 2])
                    j += 2
                else:
                    if src[j] == '\n':
                        line += 1
                    buf.append(src[j])
                    j += 1
            toks.append(Token('STRING', ''.join(buf), line))
            i = j + 1
            continue

        # numero
        if c in _DIGITS or (c == '.' and i + 1 < n and src[i + 1] in _DIGITS):
            j = i
            if src.startswith(('0x', '0X'), i):
                j = i + 2
                while j < n and src[j] in _HEX:
                    j += 1
            else:
                seen_e = False
                while j < n:
                    d = src[j]
                    if d in _DIGITS or d == '.':
                        j += 1
                    elif d in 'eE' and not seen_e:
                        seen_e = True
                        j += 1
                        if j < n and src[j] in '+-':
                            j += 1
                    else:
                        break
            toks.append(Token('NUMBER', src[i:j], line))
            i = j
            continue

        # identificatore / parola chiave
        if c.isalpha() or c == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            word = src[i:j]
            toks.append(Token('KEYWORD' if word in KEYWORDS else 'NAME', word, line))
            i = j
            continue

        # operatore
        for op in OPERATORS:
            if src.startswith(op, i):
                toks.append(Token('OP', op, line))
                i += len(op)
                break
        else:
            i += 1  # carattere ignoto (es. byte UTF-8 orfano): salta

    return toks
