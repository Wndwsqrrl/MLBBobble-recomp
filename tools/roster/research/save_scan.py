"""Look for player records inside a Bobblehead Pros save file (read-only).

    python save_scan.py <savedata1> <original PLAYER_DATA.CHK> <oct2011 PLAYER_DATA.CHK>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
save = open(sys.argv[1], 'rb').read()
print(f'save: {len(save):,} bytes, head {save[:16].hex(" ")}')
for label, path in (('original', sys.argv[2]), ('oct2011', sys.argv[3])):
    recs = pp.read_records(open(path, 'rb').read())
    n = next(i for i, r in enumerate(recs) if pp.get(r, 'id') == 0)
    # where does each record of this roster appear verbatim in the save?
    hits = []
    for k in (0, 1, 100, 500, 800, n - 1):
        hits.append((k, save.find(bytes(recs[k]))))
    full = sum(1 for k in range(n) if save.find(bytes(recs[k])) >= 0)
    print(f'{label:9}: {full}/{n} records found verbatim; sample offsets ' + ', '.join(f'#{k}@0x{o:X}' if o >= 0 else f'#{k}:-' for k, o in hits))
for name in ('Crawford', 'Konerko', 'Pierzynski'):
    b = name.encode('utf-16-be'); offs, i = [], save.find(b)
    while i >= 0 and len(offs) < 6: offs.append(i); i = save.find(b, i + 1)
    print(f'"{name}" UTF-16BE at ' + ', '.join(f'0x{o:X}' for o in offs))
