"""Find exact stat fields (value == real 2010 number) in Bobblehead Pros player records."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *

players = load_roster(sys.argv[1])
people, bat, pit, app = load_lahman(sys.argv[2])
m, _ = match(players, people, app)
def f(x, k):
    try: return float(x.get(k) or 0)
    except ValueError: return 0.0

NB = 280 * 8; LO = 0x50 * 8
def val(rec, w, p): return (rec >> (NB - p - w)) & ((1 << w) - 1)

hit, pitch = [], []
for pid, lid in m.items():
    pl = players[pid]; rec = int.from_bytes(pl['rec'], 'big')
    roles = [r for t, r in pl['teams'] if 1 <= t <= 30]
    b10 = [x for x in bat.get(lid, []) if x['yearID'] == '2010']
    p10 = [x for x in pit.get(lid, []) if x['yearID'] == '2010']
    S = lambda lst, k: sum(f(x, k) for x in lst)
    if roles[0] == 5 and b10 and S(b10, 'AB') > 0:
        AB, H = S(b10, 'AB'), S(b10, 'H')
        hit.append((rec, dict(G=S(b10, 'G'), AB=AB, R=S(b10, 'R'), H=H, D=S(b10, '2B'), T=S(b10, '3B'), HR=S(b10, 'HR'),
                              RBI=S(b10, 'RBI'), SB=S(b10, 'SB'), BB=S(b10, 'BB'), SO=S(b10, 'SO'),
                              AVG1000=round(H / AB * 1000))))
    if roles[0] != 5 and p10 and S(p10, 'IPouts') > 0:
        ip = S(p10, 'IPouts') / 3
        pitch.append((rec, dict(W=S(p10, 'W'), L=S(p10, 'L'), G=S(p10, 'G'), GS=S(p10, 'GS'), SV=S(p10, 'SV'),
                                SO=S(p10, 'SO'), BB=S(p10, 'BB'), IPouts=S(p10, 'IPouts'), IP=int(ip),
                                ERA100=round(S(p10, 'ER') * 9 / ip * 100), H=S(p10, 'H'), HR=S(p10, 'HR'))))

def search(rows, label):
    print(f'== {label}: {len(rows)} players with 2010 stats')
    for stat in rows[0][1]:
        best = None
        for w in range(4, 14):
            for p in range(LO, NB - w + 1):
                hits = sum(1 for rec, s in rows if val(rec, w, p) == int(s[stat]))
                if best is None or hits > best[0]: best = (hits, w, p)
        hits, w, p = best
        print(f'  {stat:8} {hits / len(rows):6.1%} exact  byte 0x{p // 8:02X} bit {p % 8} width {w}')
search(hit, 'HITTERS')
search(pitch, 'PITCHERS')
