"""Fit real-stat -> Bobblehead Pros rating curves on the 2011 Opening Day roster and score them."""
import sys, os, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *
players = load_roster(sys.argv[1]); core = sys.argv[2]
people, bat, pit, app = load_lahman(core)
m, _ = match(players, people, app)
f = lambda x, k: float(x.get(k) or 0) if (x.get(k) or '').replace('.', '', 1).isdigit() else 0.0
NB = 280 * 8
def val(rec, byte, bit, w): p = byte * 8 + bit; return (rec >> (NB - p - w)) & ((1 << w) - 1)

FIELDS = dict(traj=(0x6D, 1, 2), con=(0x6D, 3, 4), pow=(0x6D, 7, 8), spd=(0x6E, 7, 4),
              kmh=(0x7A, 6, 8), ctl=(0x7C, 0, 8), sta=(0x7D, 0, 8))

def lines(lid, table, years, weights):
    """Weighted multi-year totals (most recent first)."""
    tot = collections.Counter()
    for y, wgt in zip(years, weights):
        for x in table.get(lid, []):
            if x['yearID'] == str(y):
                for k in x:
                    if k not in ('playerID', 'yearID', 'stint', 'teamID', 'lgID'): tot[k] += wgt * f(x, k)
    return tot

VARIANTS = {'2010 only': ((2010,), (1.0,)), '2010+2009 (2:1)': ((2010, 2009), (2.0, 1.0)),
            '3yr 3:2:1': ((2010, 2009, 2008), (3.0, 2.0, 1.0))}

def hitter_feats(t):
    AB, H, HR, BB, SO, SB, CS, D, T = (t[k] for k in ('AB', 'H', 'HR', 'BB', 'SO', 'SB', 'CS', '2B', '3B'))
    PA = AB + BB + t['HBP'] + t['SF']
    if PA < 200: return None
    return dict(AVG=H / AB, ISO=(D + 2 * T + 3 * HR) / AB, HRr=HR / PA, SOr=SO / PA, BBr=BB / PA,
                SPD=(SB + CS) / PA, T3=T / PA, PA=PA)
def pitcher_feats(t):
    ip = t['IPouts'] / 3
    if ip < 40: return None
    return dict(BB9=t['BB'] * 9 / ip, K9=t['SO'] * 9 / ip, IPG=ip / max(t['G'], 1), ST=t['GS'] / max(t['G'], 1))

def lstsq(X, y):
    """Ordinary least squares via normal equations (small k)."""
    k = len(X[0]); A = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * yy for r, yy in zip(X, y)) for i in range(k)]
    for i in range(k):  # Gauss-Jordan
        piv = max(range(i, k), key=lambda r: abs(A[r][i])); A[i], A[piv] = A[piv], A[i]; b[i], b[piv] = b[piv], b[i]
        for r in range(k):
            if r != i and A[i][i]:
                fct = A[r][i] / A[i][i]
                A[r] = [a - fct * c for a, c in zip(A[r], A[i])]; b[r] -= fct * b[i]
    return [b[i] / A[i][i] if A[i][i] else 0 for i in range(k)]

def score(pred, act, lo, hi, step):
    p = [min(hi, max(lo, round(v))) for v in pred]
    ex = sum(1 for a, b in zip(p, act) if a == b) / len(act)
    near = sum(1 for a, b in zip(p, act) if abs(a - b) <= step) / len(act)
    mae = sum(abs(a - b) for a, b in zip(p, act)) / len(act)
    return ex, near, mae

def quantile_map(xs, ys):
    """Rank-preserving map: i-th smallest predictor -> i-th smallest actual rating."""
    order = sorted(range(len(xs)), key=lambda i: xs[i]); ys_sorted = sorted(ys)
    out = [0] * len(xs)
    for r, i in enumerate(order): out[i] = ys_sorted[r]
    return out

RATINGS = [  # name, hitter?, features, (lo, hi, near-step)
    ('con', True, ['AVG', 'SOr'], (1, 15, 1)),
    ('pow', True, ['ISO', 'HRr'], (0, 255, 15)),
    ('spd', True, ['SPD', 'T3'], (1, 15, 1)),
    ('traj', True, ['HRr', 'ISO'], (1, 4, 0)),
    ('ctl', False, ['BB9', 'K9'], (0, 255, 10)),
    ('sta', False, ['IPG', 'ST'], (0, 255, 15)),
]
for vname, (years, weights) in VARIANTS.items():
    print(f'===== stats used: {vname}')
    data = []
    for pid, lid in m.items():
        pl = players[pid]; rec = int.from_bytes(pl['rec'], 'big')
        role = [r for t, r in pl['teams'] if 1 <= t <= 30][0]
        if role == 5: feats = hitter_feats(lines(lid, bat, years, weights))
        else: feats = pitcher_feats(lines(lid, pit, years, weights))
        if feats: data.append((role == 5, rec, feats))
    for name, hitter, feat, (lo, hi, step) in RATINGS:
        rows = [(rec, fe) for h, rec, fe in data if h == hitter]
        y = [val(rec, *FIELDS[name]) for rec, _ in rows]
        X = [[1.0] + [fe[k] for k in feat] for _, fe in rows]
        w = lstsq(X, y)
        lin = [sum(a * b for a, b in zip(w, x)) for x in X]
        e1 = score(lin, y, lo, hi, step)
        q = quantile_map(lin, y)
        e2 = score(q, y, lo, hi, step)
        coef = ' + '.join(f'{c:.3g}*{k}' for c, k in zip(w[1:], feat))
        print(f'  {name:4} n={len(rows):3} range {min(y)}-{max(y)} | linear  exact {e1[0]:5.1%}  within {step}: {e1[1]:5.1%}  MAE {e1[2]:5.2f}'
              f' | rank-match exact {e2[0]:5.1%} within {step}: {e2[1]:5.1%} MAE {e2[2]:5.2f} | {name} = {w[0]:.3g} + {coef}')
