"""Fetch MLB The Show player ratings (Live series cards) from the game's public site.

    python fetch_show.py 26             -> cache/show26_live.json

Pages through https://mlbNN.theshow.com/apis/items.json?type=mlb_card with a pause
between requests and keeps only "Live" series cards (each player's current
ratings). The ratings are Sony's; they are cached locally (cache/ is git-ignored)
and never committed. Turn off a VPN if the site answers 403 Forbidden.
"""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
KEEP = ['name', 'team', 'team_short_name', 'display_position', 'display_secondary_positions', 'jersey_number',
        'age', 'bat_hand', 'throw_hand', 'is_hitter', 'ovr', 'contact_left', 'contact_right', 'power_left',
        'power_right', 'plate_vision', 'plate_discipline', 'batting_clutch', 'speed', 'base_stealing',
        'baserunning_aggression', 'arm_strength', 'arm_accuracy', 'fielding_ability', 'reaction_left',
        'reaction_right', 'blocking', 'stamina', 'pitch_velocity', 'pitch_control', 'pitch_movement',
        'pitching_clutch', 'bb_per_bf', 'hr_per_bf', 'k_per_bf_left', 'k_per_bf_right', 'hits_per_bf_left',
        'hits_per_bf_right', 'pitches']


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'bobblehead-roster-tool'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f'{url}: {e}')
            time.sleep(2 ** attempt)


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else '26'
    base = f'https://mlb{game}.theshow.com/apis/items.json?type=mlb_card&page='
    os.makedirs(CACHE, exist_ok=True)
    first = get(base + '1')
    pages = first['total_pages']
    live = []
    for pg in range(1, pages + 1):
        data = first if pg == 1 else get(base + str(pg))
        for c in data['items']:
            if c.get('series') == 'Live':
                live.append({k: c.get(k) for k in KEEP})
        if pg % 20 == 0:
            print(f'  page {pg}/{pages}: {len(live)} live cards')
        time.sleep(0.5)
    path = os.path.join(CACHE, f'show{game}_live.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(live, f, ensure_ascii=False)
    print(f'wrote {path}: {len(live)} live cards from {pages} pages')


if __name__ == '__main__':
    main()
