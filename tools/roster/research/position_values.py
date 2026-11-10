"""Value scale of the 3-bit per-position fielding grades (main vs secondary vs none)."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
data = open(sys.argv[1], 'rb').read()
recs = pp.read_records(data); table = pp.read_table(data)
role = {p: r for b in range(1, 31) for p, r in table[b]}
NB = pp.STRIDE * 8
APT = [('P', 0x61, 5), ('C', 0x62, 0), ('1B', 0x62, 3), ('2B', 0x62, 6), ('3B', 0x63, 1), ('SS', 0x63, 4),
       ('LF', 0x64, 0), ('CF', 0x64, 3), ('RF', 0x64, 6)]
def apt(r, byte, bit):
    v = int.from_bytes(r, 'big'); p = byte * 8 + bit
    return (v >> (NB - p - 3)) & 7
main_v, other_v, pit = collections.Counter(), collections.Counter(), collections.Counter()
nsec = collections.Counter()
for r in recs[:818]:
    pid = pp.get(r, 'id')
    if pid not in role: continue
    main = pp.get(r, 'position')
    vals = [apt(r, b, i) for _, b, i in APT]
    if role[pid] != pp.ROLE_HITTER:
        pit[tuple(vals)] += 1; continue
    main_v[vals[main - 1]] += 1
    others = [v for k, v in enumerate(vals) if k != main - 1]
    for v in others: other_v[v] += 1
    nsec[sum(1 for v in others if v)] += 1
print('hitters, grade at their main position:', sorted(main_v.items()))
print('hitters, grades at other positions   :', sorted(other_v.items()))
print('hitters, number of secondary positions:', sorted(nsec.items()))
print('pitchers, most common grade vectors (P C 1B 2B 3B SS LF CF RF):', pit.most_common(3))
for name in ('Derek Jeter', 'Ben Zobrist', 'Albert Pujols', 'Joe Mauer', 'Ichiro Suzuki', 'Chone Figgins', 'Michael Young'):
    for r in recs[:750]:
        if f'{pp.get_name(r, "first")} {pp.get_name(r, "last")}' == name:
            print(f'  {name:15} main {pp.get(r, "position")}  ' + ' '.join(f'{n}={apt(r, b, i)}' for n, b, i in APT))
            break

