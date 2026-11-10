"""Map the save's roster region and look for a checksum (read-only).

    python save_layout.py <savedata1> <original PLAYER_DATA.CHK> <header file>
"""
import sys, os, zlib, struct, binascii
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ppformat as pp
save = open(sys.argv[1], 'rb').read()
orig = open(sys.argv[2], 'rb').read()
hdr = open(sys.argv[3], 'rb').read()
REG = 0x805C0
# 1. how far does the copied record area extend, and is the team table there too?
slots = 0
while REG + (slots + 1) * pp.STRIDE <= len(save) and save[REG + slots * pp.STRIDE: REG + (slots + 1) * pp.STRIDE] == \
        orig[pp.REC0 + slots * pp.STRIDE: pp.REC0 + (slots + 1) * pp.STRIDE]:
    slots += 1
print(f'record slots identical to the disc file from 0x{REG:X}: {slots} (of {pp.SLOTS})')
tbl = orig[pp.TABLE: pp.TABLE + 32 * 40 * 8]
print('team table copied into save:', save.find(tbl[:320]) >= 0, 'at', hex(save.find(tbl[:320])))
whole = orig[0x20: 0x20 + 0x5BEE1]
print('whole DAT00 payload verbatim in save:', save.find(whole) >= 0)
# 2. what comes right before the region?
print('16 bytes before region:', save[REG - 16:REG].hex(' '))
# 3. checksum candidates in the first 16 bytes / header file
print('save head:', save[:16].hex(' '))
print('header file:', len(hdr), 'bytes; head', hdr[:32].hex(' '))
cands = {
    'crc32(save[4:])': zlib.crc32(save[4:]) & 0xFFFFFFFF,
    'crc32(save[8:])': zlib.crc32(save[8:]) & 0xFFFFFFFF,
    'crc32(save[16:])': zlib.crc32(save[16:]) & 0xFFFFFFFF,
    'sum32(save[4:])': sum(save[4:]) & 0xFFFFFFFF,
    'sum32(save[8:])': sum(save[8:]) & 0xFFFFFFFF,
    'sum16be(save[4:])': sum(struct.unpack(f'>{(len(save) - 4) // 2}H', save[4:4 + (len(save) - 4) // 2 * 2])) & 0xFFFFFFFF,
}
words = {f'save[{o}:{o + 4}] BE': struct.unpack('>I', save[o:o + 4])[0] for o in (0, 4, 8, 12)}
words.update({f'save[{o}:{o + 4}] LE': struct.unpack('<I', save[o:o + 4])[0] for o in (0, 4, 8, 12)})
for name, v in cands.items():
    m = [w for w, x in words.items() if x == v]
    print(f'  {name:18} = 0x{v:08X}  {"MATCHES " + ", ".join(m) if m else ""}')
# hash of save inside header file?
import hashlib
for algo in ('sha1', 'md5'):
    hv = hashlib.new(algo, save).digest()
    print(f'  {algo}(save) in header file: {hdr.find(hv) >= 0}')
