"""Describe the second player list after the main block in a save (read-only)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
save = open(sys.argv[1], 'rb').read()
orig = open(sys.argv[2], 'rb').read()
orecs = pp.read_records(orig)
X = 0x805C0 + pp.SLOTS * pp.STRIDE
k = 0
while True:
    r = bytearray(save[X + k * pp.STRIDE: X + (k + 1) * pp.STRIDE])
    if len(r) < pp.STRIDE: break
    pid = pp.get(r, 'id'); nm = pp.get_name(r, 'last')
    same = [j for j in range(818) if bytes(orecs[j]) == bytes(r)]
    if k < 3 or not nm or k % 5 == 0 or not same:
        print(f'  extra slot {k:3} @0x{X + k * pp.STRIDE:X}: id {pid:4} {pp.get_name(r, "first")} {nm}'
              f'  {"== disc record #" + str(same[0]) if same else "(not a disc record)"}')
    if not nm:
        print(f'  -> list ends after {k} records; next bytes: {save[X + k * pp.STRIDE: X + k * pp.STRIDE + 24].hex(" ")}')
        break
    k += 1
print(f'save: main block 0x805C0-0x{X:X}, extra list 0x{X:X}-0x{X + k * pp.STRIDE:X} ({k} records), file end 0x{len(save):X}')
