"""Find which bit fields of a Bobblehead Pros player record hold which facts/ratings."""
import sys, os, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *

players = load_roster(sys.argv[1])
people, bat, pit, app = load_lahman(sys.argv[2])
m, _ = match(players, people, app)

POS_COLS = [('P', 'G_p'), ('C', 'G_c'), ('1B', 'G_1b'), ('2B', 'G_2b'), ('3B', 'G_3b'), ('SS', 'G_ss'),
            ('LF', 'G_lf'), ('CF', 'G_cf'), ('RF', 'G_rf'), ('DH', 'G_dh')]
def f(x, k):
    try: return float(x.get(k) or 0)
    except ValueError: return 0.0

rows = []
for pid, lid in m.items():
    pl, pe = players[pid], people[lid]
    roles = [r for t, r in pl['teams'] if 1 <= t <= 30]
    is_p = roles[0] != 5
    # primary position from 2010+2011 appearances
    g = collections.Counter()
    for a in app.get(lid, []):
        if int(a['yearID']) in (2010, 2011):
            for name, col in POS_COLS: g[name] += f(a, col)
    pos = g.most_common(1)[0][0] if g else '?'
    b10 = [x for x in bat.get(lid, []) if x['yearID'] == '2010']
    p10 = [x for x in pit.get(lid, []) if x['yearID'] == '2010']
    S = lambda lst, k: sum(f(x, k) for x in lst)
    AB, H, HR, BB, SO, SB, D, T = (S(b10, k) for k in ('AB', 'H', 'HR', 'BB', 'SO', 'SB', '2B', '3B'))
    PA = AB + BB + S(b10, 'HBP') + S(b10, 'SF')
    IPo, PK, PBB, ER, GS, PG = (S(p10, k) for k in ('IPouts', 'SO', 'BB', 'ER', 'GS', 'G'))
    row = dict(pid=pid, rec=int.from_bytes(pl['rec'], 'big'), is_p=is_p, pos=pos,
               bats=pe['bats'], throws=pe['throws'], born=float(pe['birthYear'] or 0),
               height=f(pe, 'height'), weight=f(pe, 'weight'))
    if not is_p and PA >= 150:
        row.update(AVG=H / AB, ISO=(H + D + 2 * T + 3 * HR - H) / AB if AB else 0, HRr=HR / PA,
                   SBr=SB / PA, BBr=BB / PA, SOr=SO / PA, PA=PA)
    if is_p and IPo >= 60:
        ip = IPo / 3
        row.update(K9=PK * 9 / ip, BB9=PBB * 9 / ip, ERA=ER * 9 / ip, IPGS=(ip / GS) if GS >= 5 else None, IP=ip)
    rows.append(row)

NB = 280 * 8
LO = 0x50 * 8
def fields():
    for width in range(1, 9):
        for pos in range(LO, NB - width + 1):
            yield width, pos
def val(rec, width, pos):
    return (rec >> (NB - pos - width)) & ((1 << width) - 1)

def rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = (i + j) / 2
        i = j + 1
    return r
def spearman(x, y):
    rx, ry = rank(x), rank(y); n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx)); sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return sxy / (sx * sy) if sx and sy else 0.0

def label_fit(sub, key, max_vals=8):
    """Fields whose value predicts a categorical label best (accuracy with majority label per value)."""
    best = []
    labels = [r[key] for r in sub]
    for width, pos in fields():
        if width > 4: continue
        vals = [val(r['rec'], width, pos) for r in sub]
        if len(set(vals)) < 2 or len(set(vals)) > max_vals: continue
        tab = collections.defaultdict(collections.Counter)
        for v, l in zip(vals, labels): tab[v][l] += 1
        acc = sum(c.most_common(1)[0][1] for c in tab.values()) / len(sub)
        best.append((acc, width, pos, {v: c.most_common(1)[0][0] for v, c in sorted(tab.items())}))
    best.sort(key=lambda t: (-t[0], t[1]))
    return best[:3]

def corr_fit(sub, key, top=3):
    sub = [r for r in sub if r.get(key) is not None]
    y = [r[key] for r in sub]
    best = []
    for width, pos in fields():
        if width < 3: continue
        x = [val(r['rec'], width, pos) for r in sub]
        if len(set(x)) < 4: continue
        best.append((spearman(x, y), width, pos))
    best.sort(key=lambda t: -abs(t[0]))
    # drop overlapping duplicates (same field seen at other widths): keep strongest per start byte region
    out, used = [], []
    for rho, w, p in best:
        if any(abs(p - q) < 8 for q in used): continue
        out.append((rho, w, p)); used.append(p)
        if len(out) == top: break
    return len(sub), out

def show_field(w, p): return f'byte 0x{p // 8:02X} bit {p % 8} width {w}'

hit = [r for r in rows if not r['is_p']]; pitch = [r for r in rows if r['is_p']]
print(f'matched rows: {len(rows)} ({len(hit)} hitters, {len(pitch)} pitchers)')
print('\n== categorical (accuracy of best field) ==')
for name, sub, key in (('bats (all)', rows, 'bats'), ('throws (all)', rows, 'throws'), ('position (hitters)', hit, 'pos')):
    for acc, w, p, mp in label_fit(sub, key):
        print(f'  {name:18} {acc:6.1%}  {show_field(w, p)}  values->{mp}')
print('\n== numeric (Spearman rho, top fields) ==')
for name, sub, key in (('birth year', rows, 'born'), ('height', rows, 'height'), ('weight', rows, 'weight'),
                       ('AVG', hit, 'AVG'), ('ISO', hit, 'ISO'), ('HR rate', hit, 'HRr'), ('SB rate', hit, 'SBr'),
                       ('BB rate', hit, 'BBr'), ('SO rate', hit, 'SOr'),
                       ('K/9', pitch, 'K9'), ('BB/9', pitch, 'BB9'), ('ERA', pitch, 'ERA'), ('IP per start', pitch, 'IPGS')):
    n, out = corr_fit(sub, key)
    print(f'  {name:13} n={n:3}  ' + '  |  '.join(f'{rho:+.2f} {show_field(w, p)}' for rho, w, p in out))
