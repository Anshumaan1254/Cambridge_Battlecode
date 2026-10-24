import json
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl'):
    j = json.loads(l)
    print(j['map'], j['file'], j['W'], j['H'], 'spawnA', j['spawnA'][:3], len(j['spawnA']), 'spawnB', j['spawnB'][:3], 'altars', j['altars'], 'keys', [k for k in j.keys()])
    break
n = sum(1 for _ in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl'))
print(n)
