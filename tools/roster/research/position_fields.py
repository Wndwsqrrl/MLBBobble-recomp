"""Find per-position fielding fields: compare record bits with games played at each position.

    python position_fields.py <original PLAYER_DATA.CHK> <lahman core dir>
"""
import sys, os, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import load_roster, load_lahman, match
players = load_roster(sys.argv[1]); people, bat, pit, app = load_lahman(sys.argv[2])
m, _ = match(players, people, app)
NB = 280 * 8
def val(v, p, w): return (v >> (NB - p - w)) & ((1 << w) - 1)
POS = [('C', 'G_c'), ('1B', 'G_1b'), ('2B', 'G_2b'), ('3B', 'G_3b'), ('SS', 'G_ss'), ('LF', 'G_lf'), ('CF', 'G_cf'), ('RF', 'G_rf')]
rows = []
for pid, lid in m.items():
    pl = players[pid]
    if [r for t, r in pl['teams'] if 1 <= t <= 30][0] != 5: continue
    g = collections.Counter()
    for a in app.get(lid, []):
        if a['yearID'] in ('2009', '2010'):
            for name, col in POS: g[name] += float(a.get(col) or 0)
    if sum(g.values()) < 30: continue
    rows.append((int.from_bytes(pl['rec'], 'big'), g))
print('hitters with >= 30 games in the field (2009-10):', len(rows))
EXCL = set(range(0x6C * 8, 0x71 * 8)) | set(range(0x85 * 8, 0x95 * 8)) | set(range(0x52 * 8 + 5, 0x55 * 8 + 4))
for name, _ in POS:
    played = [1 if g[name] >= 15 else 0 for _, g in rows]
    best = []
    for w in (1, 2, 3, 4):
        for p in range(0x50 * 8, 0xC0 * 8 - w + 1):
            if any(q in EXCL for q in range(p, p + w)): continue
            vals = [val(v, p, w) for v, _ in rows]
            if len(set(vals)) < 2: continue
            # accuracy of 'value > 0 means plays this position'
            acc = sum(1 for x, y in zip(vals, played) if (x > 0) == bool(y)) / len(rows)
            best.append((acc, w, p, collections.Counter(vals).most_common(3)))
    best.sort(key=lambda t: (-t[0], t[1]))
    print(f'{name:3} played by {sum(played):3}: ' + ' | '.join(f'{a:.1%} 0x{p // 8:02X}.{p % 8} w{w} {c}' for a, w, p, c in best[:3]))
