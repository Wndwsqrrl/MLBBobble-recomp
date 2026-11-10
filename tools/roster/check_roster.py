"""Sanity-check a built roster folder.

    python check_roster.py out/2026 [name ...]
"""
import os, sys, collections
import ppformat as pp

folder = sys.argv[1]
data = open(os.path.join(folder, 'PLAYER_DATA.CHK'), 'rb').read()
recs = pp.read_records(data)
n = next(i for i, r in enumerate(recs) if pp.get(r, 'id') == 0)
table = pp.read_table(data)
problems = []
if pp.write(data, recs[:n], table) != data: problems.append('does not round-trip')
ids = [pp.get(r, 'id') for r in recs[:n]]
if ids != list(range(1, n + 1)): problems.append('player ids are not 1..N in slot order')
for b in range(1, 33):
    want = 25 if b <= 30 else 34
    if len(table[b]) != want: problems.append(f'team block {b}: {len(table[b])} players (want {want})')
    if len({p for p, _ in table[b]}) != len(table[b]): problems.append(f'team block {b}: duplicate player')
club = collections.Counter(p for b in range(1, 31) for p, _ in table[b])
dup = [p for p, c in club.items() if c > 1]
if dup: problems.append(f'{len(dup)} players on more than one club')
for b in range(1, 31):
    roles = collections.Counter(r for _, r in table[b])
    if roles[pp.ROLE_SP] != 5 or roles[pp.ROLE_HITTER] != 13: problems.append(f'block {b}: roles {dict(roles)}')
for r in recs[:n]:
    if pp.get(r, 'position') == 1: continue      # pitchers keep the template's batting ratings (traj 0 etc.)
    for k, (lo, hi) in dict(contact=(1, 15), speed=(1, 15), traj=(1, 4)).items():
        if not lo <= pp.get(r, k) <= hi: problems.append(f'{pp.get_name(r, "last")}: {k} {pp.get(r, k)}'); break
print(f'{n} players, team sizes ' + ' '.join(str(len(table[b])) for b in range(1, 33)))
print('problems: ' + ('; '.join(problems[:12]) if problems else 'none'))
want = [w.lower() for w in sys.argv[2:]]
team_of = {p: b for b in range(1, 31) for p, _ in table[b]}
for r in recs[:n]:
    full = f'{pp.get_name(r, "first")} {pp.get_name(r, "last")}'
    if any(w == full.lower() for w in want) and pp.get(r, 'id') in team_of:
        g = lambda k: pp.get(r, k)
        line = (f'{full:20} [{pp.get_name(r, "display")}] #{g("jersey"):<2} pos {g("position")} '
                f'{"RLS"[g("bats")]}/{"RL"[g("throws")]} born {1920 + g("birth_year")} block {team_of[g("id")]:2} | ')
        if g('position') == 1:
            line += (f'{g("kmh")} km/h ({g("kmh") / 1.609:.0f} mph) control {g("control")} stamina {g("stamina")} | '
                     f'{g("wins")}-{g("losses")} ERA {g("era") / 100:.2f} SV {g("saves")}')
        else:
            line += (f'traj {g("traj")} contact {g("contact")} power {g("power")} speed {g("speed")} arm {g("arm")} | '
                     f'.{g("avg"):03} {g("hr")} HR {g("rbi")} RBI {g("sb")} SB')
        print('  ' + line)
sys.exit(1 if problems else 0)
