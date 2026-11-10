"""Which names does each roster's team block show if its player ids are looked up in another roster?

    python id_crossmap.py <table from PLAYER_DATA.CHK> <names from PLAYER_DATA.CHK> [block]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
tab = pp.read_table(open(sys.argv[1], 'rb').read())
recs = pp.read_records(open(sys.argv[2], 'rb').read())
by_id = {pp.get(r, 'id'): r for r in recs if pp.get(r, 'id')}
block = int(sys.argv[3]) if len(sys.argv) > 3 else 6
names = [f"{pp.get_name(by_id[p], 'first')} {pp.get_name(by_id[p], 'last')}" if p in by_id else f'<id {p}>'
         for p, _ in tab[block]]
print(f'block {block}: ' + ', '.join(names))
