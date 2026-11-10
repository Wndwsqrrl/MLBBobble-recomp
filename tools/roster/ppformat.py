"""MLB Bobblehead Pros roster format (player\\data\\PLAYER_DATA.CHK), as decoded so far.

File: Konami CHK container. 16-byte header ('CHK ', size 0x10, ...), one 'DAT00' block
(16-byte block header, payload 0x5BEE1 bytes), then 'CHUNKEND'.

Payload:
  0x00020  player records, 280 bytes each. The game reads them until a record with
           player id 0; all unused slots hold the same blank record. Slots 0..1299.
  0x58E00  team table: 32 blocks of 40 entries (8 bytes: player id, 0, team code, role).
           Blocks 1..30 are the MLB clubs in 2011 division order (TEAM_ORDER), 31 = AL
           All-Stars, 32 = NL All-Stars. Team code = 0x4000 + block * 0x40.
           Unused entries are 00 00 00 00 00 00 03 C5.

Player record fields (byte offset within the record, bit 0 = most significant bit):
see FIELDS. Ratings follow MLB Power Pros scales.
"""
import unicodedata

STRIDE = 280
REC0 = 0x20               # file offset of record 0
SLOTS = 1300              # record slots before the team table
TABLE = 0x58E00           # file offset of team block 1
BLOCK_ENTRIES = 40
EMPTY_ENTRY = bytes([0, 0, 0, 0, 0, 0, 0x03, 0xC5])

# role codes in the team table
ROLE_SP, ROLE_LONG, ROLE_RP, ROLE_HITTER, ROLE_SETUP, ROLE_CLOSER = 0, 1, 3, 5, 6, 7

# game team block -> MLB Stats API team id (franchise). The game's names, logos and
# leagues are built in: Houston stays an NL club and Miami shows as Florida.
TEAM_ORDER = [None,
              110, 111, 147, 139, 141,         # 1-5   BAL BOS NYY TB TOR
              145, 114, 116, 118, 142,         # 6-10  CWS CLE DET KC MIN
              108, 133, 136, 140,              # 11-14 LAA OAK SEA TEX
              144, 146, 121, 143, 120,         # 15-19 ATL FLA NYM PHI WSH
              112, 113, 117, 158, 134, 138,    # 20-25 CHC CIN HOU MIL PIT STL
              109, 115, 119, 135, 137]         # 26-30 ARI COL LAD SD SF
AL_ALLSTAR, NL_ALLSTAR = 31, 32

# name: (byte, bit, width). Bit 0 of a byte is its most significant bit.
FIELDS = {
    'id':        (0x00, 0, 16),
    'jersey':    (0x54, 5, 7),
    'position':  (0x61, 1, 4),    # scorebook number: 1 P, 2 C, 3 1B ... 9 RF
    'bats':      (0x6C, 2, 2),    # 0 R, 1 L, 2 switch
    'throws':    (0x6C, 5, 1),    # 0 R, 1 L
    'traj':      (0x6D, 1, 2),    # trajectory 1-4
    'contact':   (0x6D, 3, 4),    # 1-15
    'power':     (0x6D, 7, 8),    # 0-255
    'speed':     (0x6E, 7, 4),    # 1-15
    'arm':       (0x6F, 3, 4),    # 1-15
    'fielding':  (0x6F, 7, 4),    # 1-15 (provisional)
    'error':     (0x70, 4, 4),    # 1-15 error resistance (provisional)
    'kmh':       (0x7A, 6, 8),    # top speed, km/h
    'control':   (0x7C, 0, 8),    # 0-255
    'stamina':   (0x7D, 0, 8),    # 0-255
    'birth_year': (0x85, 2, 7),   # year - 1920
    'birth_month': (0x86, 1, 4),
    'birth_day': (0x86, 5, 5),
    'avg':       (0x88, 1, 9),    # season batting average x 1000
    'rbi':       (0x89, 5, 7),
    'hr':        (0x8B, 0, 6),
    'sb':        (0x8C, 3, 7),
    'era':       (0x8D, 5, 11),   # season ERA x 100
    'wins':      (0x90, 5, 5),
    'losses':    (0x91, 7, 5),
    'saves':     (0x93, 0, 6),
}
NAMES = {'display': (0x02, 10), 'last': (0x16, 14), 'first': (0x32, 15)}   # UTF-16BE, chars


def get(rec, name):
    byte, bit, width = FIELDS[name]
    v = int.from_bytes(rec, 'big')
    return (v >> (STRIDE * 8 - (byte * 8 + bit) - width)) & ((1 << width) - 1)


def put(rec, name, value):
    """Write a field into a bytearray record; the value is clamped to the field's range."""
    byte, bit, width = FIELDS[name]
    value = max(0, min((1 << width) - 1, int(round(value))))
    shift = STRIDE * 8 - (byte * 8 + bit) - width
    v = int.from_bytes(rec, 'big')
    v = (v & ~(((1 << width) - 1) << shift)) | (value << shift)
    rec[:] = v.to_bytes(STRIDE, 'big')


def ascii_name(s):
    """The game's font is ASCII: 'José Ramírez' -> 'Jose Ramirez'."""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()


def get_name(rec, which):
    off, n = NAMES[which]
    return bytes(rec[off:off + 2 * n]).decode('utf-16-be', 'replace').split('\0')[0]


def put_name(rec, which, s):
    off, n = NAMES[which]
    s = ascii_name(s)[:n]
    rec[off:off + 2 * n] = s.encode('utf-16-be').ljust(2 * n, b'\0')


def display_name(first, last):
    """'A. Judge' like the original roster; fall back to the last name if too long."""
    first, last = ascii_name(first), ascii_name(last)
    d = f'{first[:1]}. {last}' if first else last
    return d if len(d) <= NAMES['display'][1] else last[:NAMES['display'][1]]


def team_code(block):
    return 0x4000 + block * 0x40


def read_records(data):
    return [bytearray(data[REC0 + k * STRIDE: REC0 + (k + 1) * STRIDE]) for k in range(SLOTS)]


def read_table(data):
    """{block: [(player id, role), ...]} in file order."""
    out = {}
    for block in range(1, 33):
        base = TABLE + (block - 1) * BLOCK_ENTRIES * 8
        lst = []
        for e in range(BLOCK_ENTRIES):
            o = base + e * 8
            pid, z, code, role = (int.from_bytes(data[o + i:o + i + 2], 'big') for i in (0, 2, 4, 6))
            if pid and code == team_code(block):
                lst.append((pid, role))
        out[block] = lst
    return out


def write(base_file, records, table):
    """New PLAYER_DATA.CHK bytes: base file with records (list of bytearray, <= SLOTS) and team
    table ({block: [(player id, role)]}) replaced. Everything else is kept byte for byte."""
    data = bytearray(base_file)
    blank = bytes(data[REC0 + (SLOTS - 1) * STRIDE: REC0 + SLOTS * STRIDE])   # a blank slot
    if int.from_bytes(blank[:2], 'big') != 0:
        raise ValueError('base file: last slot is not blank')
    if len(records) > SLOTS:
        raise ValueError(f'{len(records)} players do not fit in {SLOTS} slots')
    for k in range(SLOTS):
        rec = records[k] if k < len(records) else blank
        data[REC0 + k * STRIDE: REC0 + (k + 1) * STRIDE] = rec
    for block in range(1, 33):
        entries = table.get(block, [])
        if len(entries) > BLOCK_ENTRIES:
            raise ValueError(f'team block {block}: {len(entries)} players > {BLOCK_ENTRIES}')
        base = TABLE + (block - 1) * BLOCK_ENTRIES * 8
        for e in range(BLOCK_ENTRIES):
            o = base + e * 8
            if e < len(entries):
                pid, role = entries[e]
                data[o:o + 8] = (pid.to_bytes(2, 'big') + b'\0\0' + team_code(block).to_bytes(2, 'big')
                                 + role.to_bytes(2, 'big'))
            else:
                data[o:o + 8] = EMPTY_ENTRY
    return bytes(data)
