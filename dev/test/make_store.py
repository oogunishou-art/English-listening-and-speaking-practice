"""点検用の「2か月ほど使った人」の記録を作る（store_rich.json）。使い方: python3 dev/test/make_store.py [出力先]"""
import json, random, datetime, os, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
s = open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()
i = s.index('const DATA=') + 11; D, _ = json.JSONDecoder().raw_decode(s, i)
ph = [p['id'] for p in D['phrases']]; w = [p['id'] for p in D['phrases4']]; idm = [p['id'] for p in D['phrases5']]; dl = [d['id'] for d in D['dialogs']]
random.seed(1); today = datetime.date.today(); iso = lambda d: d.isoformat()
srs, plays = {}, {}
for arr, n in [(ph, 600), (w, 1500), (idm, 300), (dl, 80)]:
    for x in random.sample(arr, n):
        srs[x] = {'b': random.choice([0, 1, 1, 2, 2, 3, 3, 4, 4, 5]), 'd': iso(today + datetime.timedelta(days=random.randint(-5, 20))), 'n': random.randint(1, 8),
                  'a': random.choice([0, 0, 0, 1, 2]), 't': iso(today - datetime.timedelta(days=random.randint(0, 40)))}
        plays[x] = random.randint(1, 12)
log, playLog, vol, srsLog = {}, {}, {}, {}
for k in range(1, 70):
    d = iso(today - datetime.timedelta(days=k))
    if k in (3, 9, 10, 25): continue
    sec = random.randint(300, 4000); log[d] = sec; playLog[d] = random.randint(20, 300)
    vol[d] = {'p': playLog[d], 'v': playLog[d] * 3, 'n': random.randint(0, 30), 't': {'base': sec * .4, 'word': sec * .3, 'idiom': sec * .1, 'talk': sec * .2}}
    srsLog[d] = {'new': random.randint(0, 30), 'rev': random.randint(0, 40), 'ok': random.randint(0, 10), 'again': random.randint(0, 5), 'okb': random.randint(0, 12), 'known': random.randint(0, 6)}
st = {'srs': srs, 'plays': plays, 'log': log, 'srsLog': srsLog, 'vol': vol,
      'habit': {'goal': 20, 'voice': True, 'rest': {}, 'goalDays': {k: 1 for k in list(log)[:40]}, 'badges': {}, 'playLog': playLog, 'remind': '07:30', 'remindDays': 'daily', 'weekSeen': '', 'bInit': True},
      'fav': {x: True for x in ph[:15] + w[:10] + dl[:3]}, 'folders': [{'id': 'f1', 'name': 'よく使う', 'items': ph[20:30]}],
      'notes': [{'id': 'n1', 'ja': 'テスト', 'en': 'This is a test.', 'memo': '', 't': iso(today)}], 'weak': {x: 2 for x in w[:20]},
      'wset': {'n': 25, 'log': {iso(today - datetime.timedelta(days=k)): random.randint(0, 4) for k in range(1, 20)}, 'mins': 3, 'talk': '3', 'items': [], 'idx': 0, 'done': True, 'cnt': 1, 'p0': {}, 'prev': []},
      'study': {'mode': 'read', 'auto': False, 'slow': False, 'big': False, 'log': {iso(today - datetime.timedelta(days=k)): random.randint(60, 900) for k in range(1, 10)}, 'seen': {x: 1 for x in w[:200]}, 'tot': 5000, 'cur': None, 'mg': 2},
      'okLog': [], 'settings': {'btnLearn': True}}
out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/store_rich.json'
json.dump(st, open(out, 'w')); print('作りました', out)
