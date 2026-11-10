"""Pin down rating field boundaries: top candidate fields per metric with value ranges."""
import sys, os, csv, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *

players = load_roster(sys.argv[1])
core = sys.argv[2]
people, bat, pit, app = load_lahman(core)
fld = collections.defaultdict(list)
for x in csv.DictReader(open(os.path.join(core, 'Fielding.csv'), encoding='utf-8-sig', newline='')):
    if x['yearID'] in ('2009', '2010'): fld[x['playerID']].append(x)
m, _ = match(players, people, app)
def f(x, k):
    try: return float(x.get(k) or 0)
    except ValueError: return 0.0
NB = 280 * 8; LO = 0x50 * 8
def val(rec, w, p): return (rec >> (NB - p - w)) & ((1 << w) - 1)

# fields already identified as stats/identity: exclude from rating search
EXCLUDE = [(0x6C * 8 + 2, 2), (0x6C * 8 + 5, 1), (0x61 * 8 + 1, 4), (0x85 * 8 + 2, 7), (0x88 * 8 + 1, 9), (0x8B * 8, 6),
           (0x89 * 8 + 5, 7), (0x8C * 8 + 3, 7), (0x90 * 8 + 5, 5), (0x91 * 8 + 7, 5), (0x93 * 8, 6), (0x8D * 8 + 5, 11)]
used = set()
for p, w in EXCLUDE: used.update(range(p, p + w))

rows = []
for pid, lid in m.items():
    pl = players[pid]
    roles = [r for t, r in pl['teams'] if 1 <= t <= 30]
    S = lambda lst, k: sum(f(x, k) for x in lst)
    yrs = lambda d: [x for x in d.get(lid, []) if x['yearID'] in ('2009', '2010')]
    b, pt, fl = yrs(bat), yrs(pit), [x for x in fld.get(lid, []) if x['POS'] != 'P']
    row = dict(rec=int.from_bytes(pl['rec'], 'big'), is_p=roles[0] != 5)
    AB, H, HR, BB, SO, SB, CS, D, T = (S(b, k) for k in ('AB', 'H', 'HR', 'BB', 'SO', 'SB', 'CS', '2B', '3B'))
    PA = AB + BB + S(b, 'HBP') + S(b, 'SF')
    if not row['is_p'] and PA >= 250:
        row.update(AVG=H / AB, ISO=(D + 2 * T + 3 * HR) / AB, HRr=HR / PA, SBr=SB / PA, SBA=(SB + CS) / PA,
                   T3=T / PA, BBr=BB / PA, SOr=SO / PA)
        PO, A, E, G = (S(fl, k) for k in ('PO', 'A', 'E', 'G'))
        if PO + A + E > 50 and G > 30:
            row.update(ERR=E / (PO + A + E), RNG=(PO + A) / G)
        of = [x for x in fl if x['POS'] == 'OF']
        if of and S(of, 'G') > 40: row.update(OFA=S(of, 'A') / S(of, 'G'))
    IPo = S(pt, 'IPouts')
    if row['is_p'] and IPo >= 120:
        ip = IPo / 3; GS = S(pt, 'GS')
        row.update(K9=S(pt, 'SO') * 9 / ip, BB9=S(pt, 'BB') * 9 / ip, H9=S(pt, 'H') * 9 / ip, HR9=S(pt, 'HR') * 9 / ip,
                   IPGS=ip / GS if GS >= 8 else None, START=GS / max(1, S(pt, 'G')))
    rows.append(row)

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
    a = sum((p - mx) * (q - my) for p, q in zip(rx, ry))
    b = math.sqrt(sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry))
    return a / b if b else 0

def scan(key, hitters, top=6):
    sub = [r for r in rows if r['is_p'] != hitters and r.get(key) is not None]
    y = [r[key] for r in sub]
    res = []
    for w in range(3, 9):
        for p in range(LO, NB - w + 1):
            if any(q in used for q in range(p, p + w)): continue
            x = [val(r['rec'], w, p) for r in sub]
            d = len(set(x))
            if d < 4: continue
            res.append((rho(x, y), w, p, min(x), max(x), d))
    res.sort(key=lambda t: -abs(t[0]))
    out, seen = [], []
    for t in res:
        if any(abs(t[2] - s) < 4 for s in seen): continue
        out.append(t); seen.append(t[2])
        if len(out) == top: break
    print(f'{key:5} n={len(sub):3} ' + ' | '.join(f'{r:+.2f} 0x{p // 8:02X}.{p % 8} w{w} [{lo}-{hi}] {d}v' for r, w, p, lo, hi, d in out))

print('HITTERS')
for k in ('AVG', 'ISO', 'HRr', 'SBr', 'SBA', 'T3', 'BBr', 'SOr', 'ERR', 'RNG', 'OFA'): scan(k, True)
print('PITCHERS')
for k in ('K9', 'BB9', 'H9', 'HR9', 'IPGS', 'START'): scan(k, False)
