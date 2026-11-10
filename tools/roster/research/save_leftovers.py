"""Find 2011 player records that survive in a save outside the main player block (read-only).

    python save_leftovers.py <savedata1> <original PLAYER_DATA.CHK>
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
save = open(sys.argv[1], 'rb').read()
orig = pp.read_records(open(sys.argv[2], 'rb').read())
MAIN_LO, MAIN_HI = 0x805C0, 0x805C0 + pp.SLOTS * pp.STRIDE
# locate any 2011 record by its first 0x50 bytes (id + names), anywhere in the save
hits = []
for k, r in enumerate(orig[:818]):
    key = bytes(r[2:0x50])                      # names, without the id
    i = save.find(key)
    while i >= 0:
        hits.append((i - 2, k, pp.get_name(r, 'first') + ' ' + pp.get_name(r, 'last')))
        i = save.find(key, i + 1)
outside = sorted(h for h in hits if not MAIN_LO <= h[0] < MAIN_HI)
print(f'2011 records still in the save: {len(hits)}; outside the main block: {len(outside)}')
if outside:
    offs = [h[0] for h in outside]
    print(f'  span 0x{offs[0]:X} - 0x{offs[-1]:X}')
    gaps = collections.Counter(b - a for a, b in zip(offs, offs[1:]))
    print('  spacing between them:', gaps.most_common(4))
    for o, k, n in outside[:12]:
        print(f'  0x{o:X}  id-field {int.from_bytes(save[o:o + 2], "big"):4}  {n}')
