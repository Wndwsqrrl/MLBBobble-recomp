"""Test the hypothesized Power Pros rating layout on well-known players."""
import sys, os, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roster_lib import *

NB = 280 * 8
def val(rec, byte, bit, w):
    p = byte * 8 + bit
    return (rec >> (NB - p - w)) & ((1 << w) - 1)

HIT = [('traj', 0x6D, 1, 2), ('con', 0x6D, 3, 4), ('pow', 0x6D, 7, 8), ('spd', 0x6E, 7, 4),
       ('arm', 0x6F, 3, 4), ('fld', 0x6F, 7, 4), ('err', 0x70, 3, 4)]
PIT = [('kmh', 0x7A, 6, 8), ('ctl', 0x7B, 6, 8), ('sta', 0x7C, 6, 8)]

players = load_roster(sys.argv[1])
names = ['Ichiro Suzuki', 'Albert Pujols', 'Adam Dunn', 'Juan Pierre', 'Yadier Molina', 'Prince Fielder',
         'Carl Crawford', 'Joe Mauer', 'Jose Bautista', 'Michael Bourn', 'Brett Gardner', 'Mark Reynolds',
         'Roy Halladay', 'Mariano Rivera', 'Stephen Strasburg', 'Tim Wakefield', 'Aroldis Chapman',
         'Cliff Lee', 'Jamie Moyer', 'Felix Hernandez', 'Jonathan Papelbon', 'Carlos Marmol']
for n in names:
    for pl in players.values():
        if (pl['first'] + ' ' + pl['last']) == n and any(1 <= t <= 30 for t, _ in pl['teams']):
            rec = int.from_bytes(pl['rec'], 'big')
            h = '  '.join(f'{k}={val(rec, b, i, w):3}' for k, b, i, w in HIT)
            p = '  '.join(f'{k}={val(rec, b, i, w):3}' for k, b, i, w in PIT)
            print(f'{n:18} {h} || {p}')
            break
