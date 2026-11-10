"""Build an MLB Bobblehead Pros roster for a real season.

    python build_season.py --base "<game>\\data\\xbox360_us\\player\\data\\PLAYER_DATA.CHK"
                           --mlb cache/mlb_2026.json [--show cache/show26_live.json]
                           --name "2026 End of season" --out out/2026

Writes <out>/PLAYER_DATA.CHK, SEASON_PLAYER_DATA.CHK (copied unchanged from the base
game folder), roster.txt and report.txt; import the folder from the launcher
(Setup -> Pros roster -> Import... -> Roster folder).

The base file must be your own disc roster (2011 Opening Day). It is used as the
format template, as the answer key for the rating scales, and to borrow a similar
player's look (appearance, pitch types and the other undecoded fields) for each new
player.

Ratings, on the game's own Power Pros scales:
  * stats-based: the formulas the 2011 roster was built with (reproduced from it:
    contact, power, trajectory, stamina, control) applied to this season's stats;
  * The Show-based: each The Show rating converted by matching its rank among this
    season's players to the same rank in the 2011 roster's distribution;
  * final = blend, weighted by how many PA / IP the stats rest on. report.txt lists
    every player where the two sources disagree a lot.
"""
import argparse, bisect, collections, json, os, shutil, statistics
import ppformat as pp

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--mlb', required=True)
ap.add_argument('--show')
ap.add_argument('--name', required=True)
ap.add_argument('--out', required=True)
args = ap.parse_args()

base = open(args.base, 'rb').read()
base_recs = pp.read_records(base)
NBASE = next(i for i, r in enumerate(base_recs) if pp.get(r, 'id') == 0)
base_table = pp.read_table(base)
mlb = json.load(open(args.mlb, encoding='utf-8'))
show = json.load(open(args.show, encoding='utf-8')) if args.show else []
people = {int(k): v for k, v in mlb['people'].items()}

# ---------------------------------------------------------------- 2011 answer key
base_role = {}
for block in range(1, 31):
    for pid, role in base_table[block]:
        base_role[pid] = role
key_hit = [r for r in base_recs[:NBASE] if base_role.get(pp.get(r, 'id')) == pp.ROLE_HITTER]
key_pit = [r for r in base_recs[:NBASE] if base_role.get(pp.get(r, 'id'), 5) != pp.ROLE_HITTER]
key_sp = [r for r in base_recs[:NBASE] if base_role.get(pp.get(r, 'id')) == pp.ROLE_SP]
key_rp = [r for r in base_recs[:NBASE] if base_role.get(pp.get(r, 'id')) in (1, 2, 3, 6, 7)]
DIST = {  # sorted 2011 values per rating (the target scale)
    'contact': sorted(pp.get(r, 'contact') for r in key_hit), 'power': sorted(pp.get(r, 'power') for r in key_hit),
    'speed': sorted(pp.get(r, 'speed') for r in key_hit), 'arm': sorted(pp.get(r, 'arm') for r in key_hit),
    'fielding': sorted(pp.get(r, 'fielding') for r in key_hit), 'error': sorted(pp.get(r, 'error') for r in key_hit),
    'traj': sorted(pp.get(r, 'traj') for r in key_hit), 'kmh': sorted(pp.get(r, 'kmh') for r in key_pit),
    'control': sorted(pp.get(r, 'control') for r in key_pit),
    'stamina_sp': sorted(pp.get(r, 'stamina') for r in key_sp), 'stamina_rp': sorted(pp.get(r, 'stamina') for r in key_rp),
}
# A 0 in the 2011 file is a placeholder (one pitcher has control 0; the next lowest is 83),
# not a real rating: keep zeros out of the target scales.
DIST = {k: [x for x in v if x > 0] for k, v in DIST.items()}
RANGE = dict(contact=(1, 15), power=(0, 255), speed=(1, 15), arm=(1, 15), fielding=(1, 15), error=(1, 15),
             traj=(1, 4), kmh=(110, 170), control=(0, 255), stamina=(0, 255))

def num(x, default=0.0):
    try: return float(x)
    except (TypeError, ValueError): return default

# ---------------------------------------------------------------- stats-based ratings
def stat_hitter(st):
    """Formulas reproduced from the 2011 roster (fit on 2010 stats; see research/roster_fit.py)."""
    ab, h, hr = num(st.get('atBats')), num(st.get('hits')), num(st.get('homeRuns'))
    pa = num(st.get('plateAppearances')) or ab
    if ab < 1 or pa < 1: return None, 0
    d, t = num(st.get('doubles')), num(st.get('triples'))
    so, sb, cs = num(st.get('strikeOuts')), num(st.get('stolenBases')), num(st.get('caughtStealing'))
    avg, iso = h / ab, (d + 2 * t + 3 * hr) / ab
    r = dict(contact=-6.56 + 55.1 * avg - 2.0 * so / pa,
             power=89.2 + 315 * iso + 372 * hr / pa,
             speed=7.21 + 59.1 * (sb + cs) / pa + 72.6 * t / pa,
             traj=0.495 + 15.4 * hr / pa + 6.09 * iso)
    return r, pa

def stat_pitcher(st):
    ip = num(st.get('inningsPitched'))
    outs = int(ip) * 3 + round((ip - int(ip)) * 10)
    if outs < 3: return None, 0
    ip = outs / 3; g = max(num(st.get('gamesPitched')) or num(st.get('gamesPlayed')), 1)
    bb9, k9 = num(st.get('baseOnBalls')) * 9 / ip, num(st.get('strikeOuts')) * 9 / ip
    start = num(st.get('gamesStarted')) / g
    return dict(control=164 - 9.98 * bb9 + 1.6 * k9, stamina=10.7 + 25.1 * ip / g - 9.13 * start), ip

# ---------------------------------------------------------------- The Show: match cards to players
def norm(s): return ''.join(c for c in pp.ascii_name(s).lower() if c.isalnum())
cards = collections.defaultdict(list)
for c in show:
    cards[norm(c['name'])].append(c)
team_abbr = {t['id']: t['abbr'] for t in mlb['teams']}
SHOW_TEAM = {'AZ': 'ARI', 'ATH': 'OAK', 'CWS': 'CWS', 'WSH': 'WSH', 'KC': 'KC', 'SD': 'SD', 'SF': 'SF', 'TB': 'TB'}
player_team, any_jersey, any_pos = {}, {}, {}
for tid, lst in mlb['rosters'].items():
    for e in lst:
        player_team[e['id']] = int(tid); any_jersey[e['id']] = e['jersey']; any_pos[e['id']] = e['pos']

def card_for(p):
    lst = cards.get(norm(p['full'])) or cards.get(norm(p['first'] + ' ' + p['last'])) or []
    if len(lst) <= 1: return lst[0] if lst else None
    abbr = team_abbr.get(player_team.get(p['id']))
    same = [c for c in lst if c['team_short_name'] in (abbr, SHOW_TEAM.get(abbr, abbr))]
    if len(same) == 1: return same[0]
    same = [c for c in (same or lst) if c['bat_hand'] == p['bats'] and c['throw_hand'] == p['throws']]
    return same[0] if len(same) == 1 else None

def show_hitter(c):
    """The Show ratings for a hitter; a rating The Show leaves at 0 (missing data) is dropped."""
    if not c or not c.get('is_hitter'): return None
    L, R = lambda k: num(c.get(k + '_left')), lambda k: num(c.get(k + '_right'))
    r = dict(contact=0.3 * L('contact') + 0.7 * R('contact'), power=0.3 * L('power') + 0.7 * R('power'),
             speed=0.8 * num(c['speed']) + 0.2 * num(c['base_stealing']), arm=num(c['arm_strength']),
             fielding=0.6 * num(c['fielding_ability']) + 0.4 * (num(c['reaction_left']) + num(c['reaction_right'])) / 2,
             error=0.5 * num(c['fielding_ability']) + 0.5 * num(c['arm_accuracy']))
    return {k: v for k, v in r.items() if v > 0} or None

def show_pitcher(c):
    if not c or c.get('is_hitter'): return None
    pitches = (c.get('pitches') or {}).get('pitches', []) if isinstance(c.get('pitches'), dict) else (c.get('pitches') or [])
    fast = [num(p.get('speed')) for p in pitches if 'Fastball' in (p.get('name') or '') or 'Sinker' in (p.get('name') or '')
            or 'Cutter' in (p.get('name') or '')]
    mph = max(fast) if fast else (max(num(p.get('speed')) for p in pitches) if pitches else 0)
    r = dict(control=num(c['pitch_control']), stamina=num(c['stamina']), velocity=num(c['pitch_velocity']), mph=mph)
    return {k: v for k, v in r.items() if v > 0} or None

# ---------------------------------------------------------------- choose 25 per club
def stat_of(p, group): return p['stats'].get(group, {})

clubs = {}
for block in range(1, 31):
    roster = [people[e['id']] for e in mlb['rosters'][str(pp.TEAM_ORDER[block])] if e['id'] in people]
    jersey = {e['id']: e['jersey'] for e in mlb['rosters'][str(pp.TEAM_ORDER[block])]}
    pos_of = {e['id']: e['pos'] for e in mlb['rosters'][str(pp.TEAM_ORDER[block])]}
    pit = [p for p in roster if pos_of[p['id']] == 'P']
    hit = [p for p in roster if pos_of[p['id']] != 'P']
    ipf = lambda p: num(stat_of(p, 'pitching').get('inningsPitched'))
    gs = lambda p: num(stat_of(p, 'pitching').get('gamesStarted'))
    sp = sorted(pit, key=lambda p: (-gs(p), -ipf(p)))[:5]
    rest = [p for p in pit if p not in sp]
    closer = max(rest, key=lambda p: num(stat_of(p, 'pitching').get('saves')), default=None)
    rest = [p for p in rest if p is not closer]
    setup = max(rest, key=lambda p: num(stat_of(p, 'pitching').get('holds')), default=None)
    rest = [p for p in rest if p is not setup]
    rp = sorted(rest, key=lambda p: -ipf(p))[:12 - len(sp) - 2]
    pa = lambda p: num(stat_of(p, 'hitting').get('plateAppearances'))
    catchers = sorted([p for p in hit if pos_of[p['id']] == 'C'], key=lambda p: -pa(p))[:2]
    others = sorted([p for p in hit if p not in catchers], key=lambda p: -pa(p))
    hitters = (catchers + others)[:13]
    hitters.sort(key=lambda p: ('C 1B 2B 3B SS LF CF RF DH TWP OF IF'.split() + [pos_of[p['id']]]).index(pos_of[p['id']]))
    entries = ([(p, pp.ROLE_SP) for p in sp] + [(p, pp.ROLE_RP) for p in rp]
               + ([(setup, pp.ROLE_SETUP)] if setup else []) + ([(closer, pp.ROLE_CLOSER)] if closer else [])
               + [(p, pp.ROLE_HITTER) for p in hitters])
    clubs[block] = dict(entries=entries, jersey=jersey, pos=pos_of)

# All-Star squads: the real game's players, padded to 34 with the league's best remaining player
league_of = {t['id']: ('AL' if 'American' in t['league'] else 'NL') for t in mlb['teams']}
allstars = {}
for block, lg in ((pp.AL_ALLSTAR, 'AL'), (pp.NL_ALLSTAR, 'NL')):
    ids = [i for i in mlb['allstars'].get(lg, []) if i in people][:34]
    pool = [e for b in range(1, 31) for e in clubs[b]['entries'] if league_of.get(pp.TEAM_ORDER[b]) == lg]
    def ovr(p):
        c = card_for(p); return num(c['ovr']) if c else 0
    for p, _ in sorted(pool, key=lambda e: -ovr(e[0])):
        if len(ids) >= 34: break
        if p['id'] not in ids: ids.append(p['id'])
    allstars[block] = ids

# ---------------------------------------------------------------- ratings
chosen = {}   # mlb id -> (person, role, block)
for block in range(1, 31):
    for p, role in clubs[block]['entries']:
        chosen.setdefault(p['id'], (p, role, block))
for block in (pp.AL_ALLSTAR, pp.NL_ALLSTAR):
    for i in allstars[block]:
        if i not in chosen:
            p = people[i]; is_p = p['pos'] == 'P'
            chosen[i] = (p, pp.ROLE_RP if is_p else pp.ROLE_HITTER, player_team.get(i))

def quantile_to(dist_key, values):
    """Map raw values to the 2011 distribution by rank (ties share a rank)."""
    dist = DIST[dist_key]; order = sorted(values)
    out = {}
    for v in set(values):
        lo = bisect.bisect_left(order, v); hi = bisect.bisect_right(order, v) - 1
        q = ((lo + hi) / 2) / max(1, len(order) - 1)
        out[v] = dist[min(len(dist) - 1, int(round(q * (len(dist) - 1))))]
    return out

hit_ids = [i for i, (p, role, _) in chosen.items() if role == pp.ROLE_HITTER]
pit_ids = [i for i, (p, role, _) in chosen.items() if role != pp.ROLE_HITTER]
S_hit = {i: stat_hitter(stat_of(chosen[i][0], 'hitting')) for i in hit_ids}
S_pit = {i: stat_pitcher(stat_of(chosen[i][0], 'pitching')) for i in pit_ids}
C_hit = {i: show_hitter(card_for(chosen[i][0])) for i in hit_ids}
C_pit = {i: show_pitcher(card_for(chosen[i][0])) for i in pit_ids}

show_scaled = collections.defaultdict(dict)
def scale(ids, src_of, key, dist_key, dest):
    have = [i for i in ids if src_of[i] and key in src_of[i]]
    if not have: return
    m = quantile_to(dist_key, [src_of[i][key] for i in have])
    for i in have: show_scaled[i][dest] = m[src_of[i][key]]
for k in ('contact', 'power', 'speed', 'arm', 'fielding', 'error'):
    scale(hit_ids, C_hit, k, k, k)
scale(hit_ids, C_hit, 'power', 'traj', 'traj')
scale(pit_ids, C_pit, 'control', 'control', 'control')
scale([i for i in pit_ids if chosen[i][1] == pp.ROLE_SP], C_pit, 'stamina', 'stamina_sp', 'stamina')
scale([i for i in pit_ids if chosen[i][1] != pp.ROLE_SP], C_pit, 'stamina', 'stamina_rp', 'stamina')
scale(pit_ids, C_pit, 'velocity', 'kmh', 'kmh')
for i in pit_ids:                       # a real fastball speed beats the rank-matched rating
    if C_pit[i] and C_pit[i].get('mph', 0) >= 70:
        show_scaled[i]['kmh'] = round(C_pit[i]['mph'] * 1.609)

final, notes = {}, []
SPREAD = dict(contact=3, power=40, traj=2, control=35, stamina=40, speed=4)
for i in hit_ids + pit_ids:
    is_hit = i in S_hit
    s, n = (S_hit if is_hit else S_pit)[i]
    w = (n / (n + 250.0)) if is_hit else (n / (n + 60.0))
    sh = show_scaled.get(i, {})
    keys = ('contact', 'power', 'speed', 'traj', 'arm', 'fielding', 'error') if is_hit else ('control', 'stamina', 'kmh')
    r = {}
    for k in keys:
        sv = s.get(k) if s else None
        cv = sh.get(k)
        if k in ('speed',) and cv is not None: sv = None          # stolen-base data reproduces speed poorly
        if sv is not None and cv is not None: v = w * sv + (1 - w) * cv
        elif sv is not None: v = w * sv + (1 - w) * statistics.median(DIST['stamina_sp' if k == 'stamina' and chosen[i][1] == pp.ROLE_SP else ('stamina_rp' if k == 'stamina' else k)])
        elif cv is not None: v = cv
        else: v = statistics.median(DIST['stamina_sp' if k == 'stamina' and chosen[i][1] == pp.ROLE_SP else ('stamina_rp' if k == 'stamina' else k)])
        lo, hi = RANGE[k]
        r[k] = max(lo, min(hi, round(v)))
        # Only flag players with real playing time: small samples are expected to disagree.
        enough = n >= (250 if is_hit else 40)
        if enough and sv is not None and cv is not None and k in SPREAD and abs(sv - cv) >= SPREAD[k]:
            p = chosen[i][0]
            notes.append((abs(sv - cv) / SPREAD[k], f"{p['full']:24} {team_abbr.get(player_team.get(i), '?'):4} {k:8} "
                          f"stats {sv:6.0f}  The Show {cv:6.0f}  -> {r[k]:4}   ({int(n)} {'PA' if is_hit else 'IP'})"))
    final[i] = r

# ---------------------------------------------------------------- records
# The game has no DH position: the 2011 roster lists pure DHs (Ortiz, Thome) at first base.
POSNUM = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9, 'DH': 3, 'OF': 8, 'IF': 6, 'TWP': 3}
base_people = {}  # 2011 template candidates: (is_pitcher, bats, throws) -> [rec]
for r in base_recs[:NBASE]:
    role = base_role.get(pp.get(r, 'id'))
    if role is None: continue
    if role != pp.ROLE_HITTER and pp.get(r, 'kmh') < 130: continue      # no knuckleball templates
    base_people.setdefault((role != pp.ROLE_HITTER, pp.get(r, 'bats'), pp.get(r, 'throws')), []).append(r)

def template(is_pitcher, bats, throws, pos, seed):
    lst = (base_people.get((is_pitcher, bats, throws)) or base_people.get((is_pitcher, 0, throws))
           or base_people[(is_pitcher, 0, 0)])
    if not is_pitcher:
        same = [r for r in lst if pp.get(r, 'position') == pos]
        lst = same or lst
    return lst[seed % len(lst)]

BATS = {'R': 0, 'L': 1, 'S': 2, 'B': 2}
block_of_team = {tid: b for b, tid in enumerate(pp.TEAM_ORDER) if tid}

def secondary_positions(i):
    c = card_for(chosen[i][0])
    raw = (c or {}).get('display_secondary_positions') or ''
    out = []
    for s in raw.replace('/', ',').split(','):
        s = s.strip().upper()
        if s == 'OF': out += ['LF', 'CF', 'RF']
        elif s == 'IF': out += ['2B', '3B', 'SS']
        elif s in pp.APT_POSITIONS: out.append(s)
    return out

def make_record(pid, i, role):
    p = chosen[i][0]; is_p = role != pp.ROLE_HITTER
    pos = POSNUM.get(any_pos.get(i) or p['pos'], 1 if is_p else 8)
    if is_p: pos = 1
    rec = bytearray(template(is_p, BATS.get(p['bats'], 0), 1 if p['throws'] == 'L' else 0, pos, i))
    pp.put(rec, 'id', pid)
    pp.put_name(rec, 'display', pp.display_name(p['first'], p['last']))
    pp.put_name(rec, 'last', p['last']); pp.put_name(rec, 'first', p['first'])
    j = (any_jersey.get(i) or '').strip()
    if j.isdigit(): pp.put(rec, 'jersey', int(j))
    pp.put(rec, 'position', pos)
    # uniform: the club the player is listed with (All-Star copies wear their own club's too)
    club = next((b for b in range(1, 31) if any(e[0]['id'] == i for e in clubs[b]['entries'])), None)
    club = club or block_of_team.get(player_team.get(i))
    if club: pp.put(rec, 'team', club)
    main = pp.APT_POSITIONS[pos - 1]
    for k, v in pp.fielding_grades(main, [] if is_p else secondary_positions(i)).items():
        pp.put(rec, 'apt_' + k, v)
    pp.put(rec, 'bats', BATS.get(p['bats'], 0)); pp.put(rec, 'throws', 1 if p['throws'] == 'L' else 0)
    if p['birth']:
        y, mo, d = (int(x) for x in p['birth'].split('-'))
        pp.put(rec, 'birth_year', y - 1920); pp.put(rec, 'birth_month', mo); pp.put(rec, 'birth_day', d)
    for k, v in final[i].items(): pp.put(rec, k, v)
    hs, ps = stat_of(p, 'hitting'), stat_of(p, 'pitching')
    ab = num(hs.get('atBats'))
    pp.put(rec, 'avg', round(num(hs.get('hits')) / ab * 1000) if ab else 0)
    pp.put(rec, 'hr', num(hs.get('homeRuns'))); pp.put(rec, 'rbi', num(hs.get('rbi'))); pp.put(rec, 'sb', num(hs.get('stolenBases')))
    if is_p:
        pp.put(rec, 'era', round(num(ps.get('era'), 0) * 100)); pp.put(rec, 'wins', num(ps.get('wins')))
        pp.put(rec, 'losses', num(ps.get('losses'))); pp.put(rec, 'saves', num(ps.get('saves')))
    return rec

# order like the original: by MLB debut, then name; All-Star copies after everyone else
order = sorted(chosen, key=lambda i: (chosen[i][0].get('debut') or '9999', pp.ascii_name(chosen[i][0]['last']),
                                      pp.ascii_name(chosen[i][0]['first'])))
club_ids = {p['id'] for b in range(1, 31) for p, _ in clubs[b]['entries']}
records, pid_of = [], {}
for i in order:
    if i not in club_ids:
        continue          # All-Star-only player: gets just the All-Star copy below
    pid = len(records) + 1; pid_of[i] = pid
    records.append(make_record(pid, i, chosen[i][1]))
table = {b: [(pid_of[p['id']], role) for p, role in clubs[b]['entries']] for b in range(1, 31)}
for block in (pp.AL_ALLSTAR, pp.NL_ALLSTAR):
    ent = []
    for i in allstars[block]:
        role = chosen[i][1]
        pid = len(records) + 1
        rec = make_record(pid, i, role)
        records.append(rec)
        ent.append((pid, role))
    table[block] = ent

out = pp.write(base, records, table)
os.makedirs(args.out, exist_ok=True)
open(os.path.join(args.out, 'PLAYER_DATA.CHK'), 'wb').write(out)
base_dir = os.path.dirname(os.path.abspath(args.base))
season_src = os.path.join(base_dir, 'SEASON_PLAYER_DATA.CHK')              # e.g. a roster library folder
if not os.path.exists(season_src):                                          # the game folder layout
    season_src = os.path.join(os.path.dirname(base_dir), 'season_data', 'SEASON_PLAYER_DATA.CHK')
shutil.copyfile(season_src, os.path.join(args.out, 'SEASON_PLAYER_DATA.CHK'))
open(os.path.join(args.out, 'roster.txt'), 'w').write(f'name={args.name}\r\n')

matched = sum(1 for i in chosen if card_for(chosen[i][0]))
with open(os.path.join(args.out, 'report.txt'), 'w', encoding='utf-8') as f:
    f.write(f'{args.name}: {len(records)} player records ({len(records) - 68} club players + 68 All-Star copies)\n')
    f.write(f'The Show cards matched: {matched} of {len(chosen)} players\n\n')
    f.write('Largest disagreements between stats-based and The Show-based ratings (Power Pros scale):\n')
    for _, line in sorted(notes, reverse=True):
        f.write('  ' + line + '\n')
print(f'wrote {args.out}: {len(records)} records, The Show matched {matched}/{len(chosen)}, {len(notes)} disagreements flagged')
