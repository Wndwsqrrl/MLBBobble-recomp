"""Decode the Bobblehead Pros team-roster table (8-byte entries after the player records)."""
import sys, collections
STRIDE, BASE = 280, 0x20

def load(path):
    b = open(path, 'rb').read()
    names = {}
    for k in range(818):
        r = b[BASE + k * STRIDE: BASE + (k + 1) * STRIDE]
        s = lambda o, n: r[o:o + 2 * n].decode('utf-16-be', 'replace').split('\0')[0]
        names[int.from_bytes(r[0:2], 'big')] = (s(0x32, 15) + ' ' + s(0x16, 14)).strip()
    end = 0x20 + 0x5BEE1
    # scan for entries: (pid 1..818, 0, team code with 0x4000 bit, role < 16)
    ents = []
    for o in range(BASE + 818 * STRIDE, end - 7, 2):
        pid, z, team, role = (int.from_bytes(b[o + i:o + i + 2], 'big') for i in (0, 2, 4, 6))
        if 1 <= pid <= 818 and z == 0 and (team & 0xC000) == 0x4000 and role < 16:
            ents.append((o, pid, team, role))
    return b, names, ents

for label, path in (('BASE', sys.argv[1]), ('OCT11', sys.argv[2])):
    b, names, ents = load(path)
    teams = collections.OrderedDict()
    for o, pid, team, role in ents:
        teams.setdefault(team, []).append((o, pid, role))
    print(f'===== {label}: {len(ents)} roster entries, {len(teams)} team codes')
    if label == 'BASE':
        first_off = ents[0][0]
        print(f'  table first entry at 0x{first_off:X}')
    for team, lst in teams.items():
        offs = [o for o, _, _ in lst]
        roles = collections.Counter(r for _, _, r in lst)
        sample = ', '.join(names[p].split(' ')[-1] for _, p, _ in lst[:6])
        print(f'  team 0x{team:04X} (idx {(team & 0x3FFF) >> 6:2}, low6 {team & 0x3F}): {len(lst):2} players '
              f'@0x{offs[0]:X}-0x{offs[-1]:X} roles {dict(sorted(roles.items()))} | {sample}')
    if label == 'BASE':
        base_teams = {t: [p for _, p, _ in l] for t, l in teams.items()}
        base_names = names
    else:
        print('===== changes BASE -> OCT11 (by team, by name):')
        for t, l in teams.items():
            new = set(names[p] for _, p, _ in l)
            old = set(base_names[p] for p in base_teams.get(t, []))
            add, rem = sorted(new - old), sorted(old - new)
            if add or rem:
                print(f'  0x{t:04X}: +{len(add)} -{len(rem)}  in: {", ".join(add[:5])}{" ..." if len(add) > 5 else ""}  out: {", ".join(rem[:5])}{" ..." if len(rem) > 5 else ""}')
