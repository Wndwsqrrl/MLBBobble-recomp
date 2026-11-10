"""Is the save's first word a CRC32 / Adler32 / byte sum over some leading range? (read-only)"""
import sys, zlib, struct
save = open(sys.argv[1], 'rb').read()
targets = {}
for o in (0, 4, 8, 12):
    targets[struct.unpack('>I', save[o:o + 4])[0]] = f'save[{o}] BE'
    targets[struct.unpack('<I', save[o:o + 4])[0]] = f'save[{o}] LE'
found = []
for start in (4, 8, 16):
    crc, adl, s = 0, 1, 0
    for pos in range(start, len(save), 4):
        chunk = save[pos:pos + 4]
        crc = zlib.crc32(chunk, crc); adl = zlib.adler32(chunk, adl); s = (s + sum(chunk)) & 0xFFFFFFFF
        end = pos + 4
        for name, v in (('crc32', crc & 0xFFFFFFFF), ('crc32^ff', (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF), ('adler32', adl), ('sum32', s)):
            if v in targets:
                found.append(f'{name}(save[{start}:{end:#x}]) == {targets[v]}')
print('\n'.join(found[:20]) if found else 'no leading-range CRC32/Adler32/sum matches the first words')
