"""Shared helpers: parse Bobblehead Pros PLAYER_DATA.CHK and join players to Lahman."""
import csv, os, unicodedata, collections

STRIDE, BASE, NPLAYERS = 280, 0x20, 818
TEAMS = ['', 'BAL', 'BOS', 'NYA', 'TBA', 'TOR', 'CHA', 'CLE', 'DET', 'KCA', 'MIN', 'LAA', 'OAK', 'SEA', 'TEX',
         'ATL', 'FLO', 'NYN', 'PHI', 'WAS', 'CHN', 'CIN', 'HOU', 'MIL', 'PIT', 'SLN', 'ARI', 'COL', 'LAN', 'SDN', 'SFN',
         'AL-ALLSTAR', 'NL-ALLSTAR']

def load_roster(path):
    b = open(path, 'rb').read()
    players = {}
    for k in range(NPLAYERS):
        r = b[BASE + k * STRIDE: BASE + (k + 1) * STRIDE]
        s = lambda o, n: r[o:o + 2 * n].decode('utf-16-be', 'replace').split('\0')[0]
        pid = int.from_bytes(r[0:2], 'big')
        players[pid] = dict(pid=pid, slot=k, disp=s(0x02, 10), last=s(0x16, 14), first=s(0x32, 15), rec=r, teams=[])
    end = 0x20 + 0x5BEE1
    for o in range(BASE + NPLAYERS * STRIDE, end - 7, 2):
        pid, z, team, role = (int.from_bytes(b[o + i:o + i + 2], 'big') for i in (0, 2, 4, 6))
        if 1 <= pid <= NPLAYERS and z == 0 and (team & 0xC000) == 0x4000 and role < 16:
            players[pid]['teams'].append(((team & 0x3FFF) >> 6, role))
    return players

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ''.join(c for c in s if c.isalnum())

def load_lahman(core):
    rd = lambda f: list(csv.DictReader(open(os.path.join(core, f), encoding='utf-8-sig', newline='')))
    people = {p['playerID']: p for p in rd('People.csv')}
    bat = collections.defaultdict(list); pit = collections.defaultdict(list); app = collections.defaultdict(list)
    for x in rd('Batting.csv'):
        if 2008 <= int(x['yearID']) <= 2011: bat[x['playerID']].append(x)
    for x in rd('Pitching.csv'):
        if 2008 <= int(x['yearID']) <= 2011: pit[x['playerID']].append(x)
    for x in rd('Appearances.csv'):
        if 2009 <= int(x['yearID']) <= 2011: app[x['playerID']].append(x)
    return people, bat, pit, app

def match(players, people, app):
    """Return {pid: lahman playerID} for MLB-team players (team idx 1..30)."""
    by_name = collections.defaultdict(list)
    for pidL, p in people.items():
        by_name[(norm(p['nameFirst'] or ''), norm(p['nameLast'] or ''))].append(pidL)
        by_name[('', norm(p['nameLast'] or ''))].append(pidL)
    out, miss = {}, []
    for pid, pl in players.items():
        mlb = [t for t, _ in pl['teams'] if 1 <= t <= 30]
        if not mlb: continue
        team = TEAMS[mlb[0]]
        cands = by_name.get((norm(pl['first']), norm(pl['last'])), [])
        def played_for(x, years=(2011, 2010)):
            return any(a['teamID'] == team and int(a['yearID']) in years for a in app.get(x, []))
        good = [x for x in cands if played_for(x)]
        if len(good) != 1:   # fall back: last name + team in 2011/2010
            good2 = [x for x in by_name.get(('', norm(pl['last'])), []) if played_for(x)]
            if len(good) == 0 and len(good2) == 1: good = good2
        if len(good) == 1: out[pid] = good[0]
        else: miss.append((pl['first'], pl['last'], team, len(good)))
    return out, miss
