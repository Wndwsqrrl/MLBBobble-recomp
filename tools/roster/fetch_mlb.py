"""Fetch a season's MLB rosters, player bios and stats from the public MLB Stats API.

    python fetch_mlb.py 2026                -> cache/mlb_2026.json
    python fetch_mlb.py 2011 2011-03-31     -> cache/mlb_2011_2011-03-31.json

Rosters are the active rosters on the last day of that regular season (the same
point in the year as the game's own end-of-season roster update), or on the date
given as the second argument (e.g. opening day). Also fetches
both All-Star Game squads. Uses only the Python standard library. The data is
MLB's; it is cached locally (cache/ is git-ignored) and never committed.
"""
import json, os, sys, time, urllib.request, urllib.parse

API = 'https://statsapi.mlb.com/api/v1'
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')


def get(path, **params):
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'User-Agent': 'bobblehead-roster-tool'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # transient network errors: retry with backoff
            if attempt == 3:
                raise RuntimeError(f'{url}: {e}')
            time.sleep(2 ** attempt)


def last_regular_season_day(season):
    s = get('/seasons/' + str(season), sportId=1)['seasons'][0]
    return s['regularSeasonEndDate']


def all_star_rosters(season):
    sched = get('/schedule', sportId=1, season=season, gameType='A')
    games = [g for d in sched.get('dates', []) for g in d['games']]
    if not games:
        return {}
    box = get(f"/game/{games[0]['gamePk']}/boxscore")
    out = {}
    for side in ('away', 'home'):
        t = box['teams'][side]
        league = 'AL' if 'American' in t['team']['name'] else 'NL'
        out[league] = [p['person']['id'] for p in t['players'].values()]
    return out


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 else time.localtime().tm_year
    os.makedirs(CACHE, exist_ok=True)
    date = sys.argv[2] if len(sys.argv) > 2 else last_regular_season_day(season)
    print(f'season {season}: rosters as of {date}')
    teams = sorted(get('/teams', sportId=1, season=season)['teams'], key=lambda t: t['id'])
    rosters, ids = {}, set()
    for t in teams:
        r = get(f"/teams/{t['id']}/roster", rosterType='active', date=date)
        rosters[t['id']] = [dict(id=p['person']['id'], jersey=p.get('jerseyNumber', ''),
                                 pos=p['position']['abbreviation']) for p in r['roster']]
        ids.update(p['id'] for p in rosters[t['id']])
        print(f"  {t['abbreviation']:4} {len(rosters[t['id']]):2} players")
    asg = all_star_rosters(season)
    for v in asg.values():
        ids.update(v)
    print(f"  All-Star squads: " + ', '.join(f'{k} {len(v)}' for k, v in asg.items()))

    people = {}
    idl = sorted(ids)
    hydrate = f'stats(group=[hitting,pitching],type=[season],season={season})'
    for i in range(0, len(idl), 50):
        chunk = idl[i:i + 50]
        res = get('/people', personIds=','.join(map(str, chunk)), hydrate=hydrate)
        for p in res['people']:
            stats = {}
            for block in p.get('stats', []):
                splits = block.get('splits', [])
                if splits:
                    # one total per group (a traded player has team splits + a total; take the total)
                    tot = [s for s in splits if 'team' not in s] or splits
                    stats[block['group']['displayName']] = tot[0]['stat']
            people[p['id']] = dict(
                id=p['id'], first=p.get('useName') or p.get('firstName', ''), last=p.get('useLastName') or p.get('lastName', ''),
                full=p.get('fullName', ''), bats=p.get('batSide', {}).get('code', 'R'),
                throws=p.get('pitchHand', {}).get('code', 'R'), birth=p.get('birthDate', ''),
                pos=p.get('primaryPosition', {}).get('abbreviation', ''), debut=p.get('mlbDebutDate', ''),
                height=p.get('height', ''), weight=p.get('weight', 0), stats=stats)
        time.sleep(0.2)
    out = dict(season=season, date=date,
               teams=[dict(id=t['id'], abbr=t['abbreviation'], name=t['name'], club=t.get('clubName', t['teamName']),
                           league=t['league']['name'], division=t.get('division', {}).get('name', ''))
                      for t in teams],
               rosters=rosters, allstars=asg, people=people)
    path = os.path.join(CACHE, f'mlb_{season}.json' if len(sys.argv) <= 2 else f'mlb_{season}_{date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    print(f'wrote {path}: {len(people)} players')


if __name__ == '__main__':
    main()
