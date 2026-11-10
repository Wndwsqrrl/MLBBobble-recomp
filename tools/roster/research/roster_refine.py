"""Refine fielding/error and control/stamina field alignment with a narrow scan."""
import sys, os, csv, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *
players = load_roster(sys.argv[1]); core = sys.argv[2]
people, bat, pit, app = load_lahman(core)
fld = collections.defaultdict(list)
for x in csv.DictReader(open(os.path.join(core, 'Fielding.csv'), encoding='utf-8-sig', newline='')):
    if x['yearID'] in ('2008', '2009', '2010'): fld[x['playerID']].append(x)
m, _ = match(players, people, app)
f = lambda x, k: float(x.get(k) or 0) if (x.get(k) or '').replace('.', '', 1).isdigit() else 0.0
NB = 280 * 8
def val(rec, p, w): return (rec >> (NB - p - w)) & ((1 << w) - 1)
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r
def rho(x, y):
    rx, ry = rank(x), rank(y); n = len(x); mx, my = sum(rx) / n, sum(ry) / n
    a = sum((p - mx) * (q - my) for p, q in zip(rx, ry)); b = math.sqrt(sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry))
    return a / b if b else 0
H, P = [], []
for pid, lid in m.items():
    pl = players[pid]; rec = int.from_bytes(pl['rec'], 'big')
    role = [r for t, r in pl['teams'] if 1 <= t <= 30][0]
    S = lambda lst, k: sum(f(x, k) for x in lst)
    fl = [x for x in fld.get(lid, []) if x['POS'] != 'P']
    if role == 5:
        PO, A, E, G = (S(fl, k) for k in ('PO', 'A', 'E', 'G'))
        if PO + A + E > 80: H.append((rec, dict(FPCT=(PO + A) / (PO + A + E), E_G=E / max(G, 1))))
    else:
        pt = [x for x in pit.get(lid, []) if x['yearID'] in ('2009', '2010')]
        IPo = S(pt, 'IPouts')
        if IPo >= 120:
            ip = IPo / 3; G = S(pt, 'G'); GS = S(pt, 'GS')
            P.append((rec, dict(BB9=S(pt, 'BB') * 9 / ip, IPperG=ip / max(G, 1), STARTER=GS / max(G, 1), role=role)))
def scan(rows, key, lo_byte, hi_byte, widths, top=6):
    y = [s[key] for _, s in rows]
    res = []
    for w in widths:
        for p in range(lo_byte * 8, hi_byte * 8):
            x = [val(r, p, w) for r, _ in rows]
            if len(set(x)) < 3: continue
            res.append((rho(x, y), p, w, min(x), max(x), len(set(x))))
    res.sort(key=lambda t: -abs(t[0]))
    print(f'{key:8} n={len(rows)}: ' + ' | '.join(f'{r:+.2f} 0x{p // 8:02X}.{p % 8} w{w} [{a}-{b}] {d}v' for r, p, w, a, b, d in res[:top]))
print('-- hitters: fielding/error between 0x6F and 0x72')
scan(H, 'FPCT', 0x6F, 0x72, (3, 4, 5))
scan(H, 'E_G', 0x6F, 0x72, (3, 4, 5))
print('-- pitchers: control/stamina between 0x7B and 0x7E')
scan(P, 'BB9', 0x7B, 0x7E, (6, 7, 8))
scan(P, 'IPperG', 0x7B, 0x7E, (6, 7, 8))
scan(P, 'STARTER', 0x7B, 0x7E, (6, 7, 8))
