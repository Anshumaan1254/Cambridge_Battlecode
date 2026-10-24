# Narrative game selection (6-8 wins + 3-4 losses per study team, diverse map classes, strongest opponents first) and story runner:
# writes pb_story.mjs (dump-based phase story) and tools/live/narrate.mjs (replay timeline + deaths) outputs per game to
# C:/battlecode/cache/top2_playbooks/stories/<key>/<file>.txt.   python tools/top2/playbooks/pb_select.py [--run]
import sys, os, json, subprocess, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from pbcommon import ORDER, BASE

SEL = {
    'pbg': ['00gem_fields_3fc2330b', '01starfish_47358525', '00road_of_riches_77554456', '00great_wall_7ff33f2f', '00ambush_3001d3f1',
            '01shortcut_8712e41c', '00fragment_e1ff7810', '01boss_battle_4b1716d2',
            '00contest_52dbafca', '01hooks_86848f49', '01concentrated_wealth_83e86a76', '01the_farm_7f9cccb2'],
    'ifish': ['00contest_52dbafca', '01big_world_0561a53d', '00expanse_bc3ff3f2', '01islands_ace73814', '00rushbait_v2_08bc9833',
              '00corners_8ccd80fa', '00packs_6e6a3d0d', '00monolith_a05ae120',
              '00quadrants_69638af3', '01starfish_47358525', '00road_of_riches_77554456', '01boss_battle_e8e1f817'],
    'pantheon': ['01hooks_86848f49', '01fracture_35246d93', '00quadrants_69638af3', '01boss_battle_e8e1f817', '01the_farm_7f9cccb2',
                 '00lost_world_b74302c8', '00pilgrimage_8806e3e0', '00swirl_5cd065e4',
                 '00gem_fields_3fc2330b', '00stampede_62094520', '00corners_8ccd80fa', '01shortcut_8712e41c'],
    'coo': ['01boss_battle_0a537740', '01elk_arena_7521bf78', '00great_wall_ae60b5e2', '01big_world_39dc4971', '00road_of_riches_de452e4d',
            '01shortcut_e10a1122', '01broken_curve_3119b59f', '00expanse_bb4dbd1d',
            '00gemfight_c80d2b6c', '00eight_d55c5832', '01fracture_74a08ae7', '00quadrants_86748521'],
    'cm': ['00gemfight_c80d2b6c', '00eight_d55c5832', '01fracture_4fc1aa39', '01big_world_769dd3c7', '00great_wall_78b3c219',
           '01concentrated_wealth_0eb750bf', '01the_farm_a9036fb9', '00reverse_spiral_53b13761',
           '01boss_battle_0a537740', '01starfish_2b0b9811', '01elk_arena_221310ac', '00fragment_28f9bafa'],
    'nyx': ['00interlock_424705d2', '00quadrants_b98ef586', '00lost_world_ca07a39c', '01fracture_05679ec9', '00ambush_c325017c',
            '00collision_efd4fd81', '00contest_744bba5a', '00swirl_61899d8f',
            '01starfish_9ab30d7c', '01broken_curve_a895e2b5', '00gem_fields_83048666', '01elk_arena_70b595d0'],
}


def side_of(key, f):
    for l in open(f'C:/battlecode/cache/t2/{key}/index.jsonl', encoding='utf-8'):
        r = json.loads(l)
        if f"{r['map']}_{r['matchId'][:8]}" == f:
            from pbcommon import KEYS
            me = [t for t in r['teams'] if t['teamId'].startswith(KEYS[key])][0]
            return 0 if me['side'] == 'a' else 1
    raise KeyError(f)


def run_one(key, f):
    s = side_of(key, f)
    out = f'{BASE}/stories/{key}/{f}.txt'
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return out
    env = dict(os.environ, CAMBC_CACHE='C:/Users/Anjali Gupta/AppData/Local/cambc/assets')
    a = subprocess.run(['node', 'tools/top2/playbooks/pb_story.mjs', f'C:/battlecode/cache/t2dump/{key}/{f}.json.gz', str(s)], capture_output=True, text=True, encoding='utf-8', env=env).stdout
    b = subprocess.run(['node', 'tools/live/narrate.mjs', f'C:/battlecode/cache/t2/{key}/{f}.repl26a', str(s), '100'], capture_output=True, text=True, encoding='utf-8', env=env).stdout
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fo:
        fo.write(a + '\n---- narrate.mjs\n' + b)
    return out


if __name__ == '__main__':
    if '--run' in sys.argv:
        jobs = [(k, f) for k in ORDER for f in SEL[k]]
        with cf.ThreadPoolExecutor(3) as ex:
            for o in ex.map(lambda kf: run_one(*kf), jobs):
                print(o)
