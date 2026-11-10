"""Write a roster's player records into a Bobblehead Pros save (the game keeps its own copy).

    python apply_to_save.py <PLAYER_DATA.CHK> <savedata1> <backup dir>

The game reads player records (names, ratings, looks) from the save and only the team
table from PLAYER_DATA.CHK, so a roster switch must update both. See ppformat.apply_to_save
for the layout. Before writing, the save is copied once into <backup dir> (an existing
backup is never overwritten). Do not run while the game is open: it rewrites the save.
"""
import os, sys, shutil
import ppformat as pp

def main():
    roster, save_path, backup_dir = sys.argv[1:4]
    chk = open(roster, 'rb').read()
    save = bytearray(open(save_path, 'rb').read())
    try:
        pp.apply_to_save(save, chk)
    except ValueError as e:
        sys.exit(f'{save_path}: {e}; not writing')
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, os.path.basename(save_path) + '.original')
    if not os.path.exists(backup):
        shutil.copy2(save_path, backup)
        print(f'backed up save to {backup}')
    tmp = save_path + '.tmp'
    open(tmp, 'wb').write(save)
    os.replace(tmp, save_path)
    print(f'wrote {pp.SLOTS} + {pp.SAVE_EXTRA} player records from {roster} into {save_path}')

if __name__ == '__main__':
    main()
