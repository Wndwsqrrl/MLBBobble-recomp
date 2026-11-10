"""Round-trip check: reading a roster and writing it back must reproduce it byte for byte.

    python test_ppformat.py <PLAYER_DATA.CHK> [more...]
"""
import sys
import ppformat as pp

ok = True
for path in sys.argv[1:]:
    data = open(path, 'rb').read()
    recs = pp.read_records(data)
    n = next(i for i, r in enumerate(recs) if pp.get(r, 'id') == 0)
    table = pp.read_table(data)
    out = pp.write(data, recs[:n], table)
    same = out == data
    ok &= same
    sizes = ', '.join(str(len(table[b])) for b in range(1, 33))
    print(f'{"OK  " if same else "FAIL"} {path}: {n} players; team sizes {sizes}')
    if not same:
        diff = [i for i in range(len(data)) if data[i] != out[i]]
        print(f'     {len(diff)} bytes differ, first at 0x{diff[0]:X}')
    r = recs[0]
    print(f'     sample: {pp.get_name(r, "first")} {pp.get_name(r, "last")} #{pp.get(r, "jersey")} pos {pp.get(r, "position")} '
          f'born {1920 + pp.get(r, "birth_year")}-{pp.get(r, "birth_month"):02}-{pp.get(r, "birth_day"):02} '
          f'avg .{pp.get(r, "avg"):03} hr {pp.get(r, "hr")} rbi {pp.get(r, "rbi")} contact {pp.get(r, "contact")} power {pp.get(r, "power")}')
sys.exit(0 if ok else 1)
