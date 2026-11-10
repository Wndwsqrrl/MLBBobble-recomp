"""Find the player-record field that stores the player's own team (uniform).

    python team_field.py <PLAYER_DATA.CHK> [more rosters...]
Search: a bit field whose value is a fixed function (identity / offset) of the club block
the player is listed under, for every club player.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
NB = pp.STRIDE * 8
def val(v, p, w): return (v >> (NB - p - w)) & ((1 << w) - 1)
for path in sys.argv[1:]:
    data = open(path, 'rb').read()
    recs = pp.read_records(data); table = pp.read_table(data)
    by_id = {pp.get(r, 'id'): int.from_bytes(r, 'big') for r in recs if pp.get(r, 'id')}
    rows = [(by_id[p], b) for b in range(1, 31) for p, _ in table[b]]
    allstar = [(by_id[p], b) for b in (31, 32) for p, _ in table[b]]
    best = []
    for w in range(5, 9):
        for p in range(16, NB - w + 1):
            diffs = collections.Counter(val(v, p, w) - b for v, b in rows)
            off, hits = diffs.most_common(1)[0]
            if hits / len(rows) > 0.9:
                best.append((hits / len(rows), w, p, off))
    best.sort(reverse=True)
    print(f'{path[-45:]}: {len(rows)} club players')
    for acc, w, p, off in best[:5]:
        as_vals = collections.Counter(val(v, p, w) for v, _ in allstar).most_common(4)
        print(f'  {acc:6.1%}  byte 0x{p // 8:02X} bit {p % 8} width {w}: value = block {off:+d}   All-Star copies -> {as_vals}')
