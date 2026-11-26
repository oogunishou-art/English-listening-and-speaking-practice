"""見本：教材（フレーズ）を音声つきで足すときの組み込み方。コピーして、教材の種類に合わせて直して使う。
先に bash dev/setup.sh。

使い方: python3 dev/examples/integrate_audio.py 新しいフレーズ.json 新しい版（例 2026-11-27a） [作業フォルダ]
  新しいフレーズ.json：[{"id":"greet-99","cat":"greet","lv":1,"en":"...","ja":"...","note":"...","grp":"scene"}, ...]
  → 作業フォルダ/out/index.html と out/geadd-<版>-N-<sha8>.bin
  テスト：python3 dev/test/smoke.py --index 作業フォルダ/out/index.html
  公開：out の geadd-*.bin をリポジトリにコピー → index.html をコピー → commit・push（.bin を先に。push は1回でよい）

音声のキー：e:<id> 英語・男性 ／ f:<id> 英語・女性 ／ j:<id> 日本語
（単語 phrases4・熟語 phrases5 は例文も e:<id>x f:<id>x j:<id>x、会話は e:<id>-<行> f:… j:<id>-<行> t:<id> など。
 アプリ側でどのキーを使うかは index.html の dlgKey・mixUnit・unitInfo などを見る）"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'lib'))
from packlib import encode_all, build_packs, span, put
from tts import en, ja, save_wav
from check import recognize, score
from ipa_ja import for_text
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
src, APPV = sys.argv[1], sys.argv[2]; W = os.path.abspath(sys.argv[3] if len(sys.argv) > 3 else 'work'); TAG = APPV.replace('-', '')
os.makedirs(W + '/wav', exist_ok=True)
s = open(REPO + '/index.html', encoding='utf-8').read()
old = re.search(r"const APPV='([^']*)';", s).group(1); assert APPV > old, ('版は前より新しく', old)
new = json.load(open(src, encoding='utf-8'))
D, d0, d1 = span(s, 'DATA'); have = {p['id'] for p in D['phrases']}; cats = {c['id'] for c in D['cats']}
for p in new:
    assert p['id'] not in have and p['cat'] in cats, p['id']
    p['ipa'] = for_text(p['en'])[0]
    D['phrases'].append(p)
s = put(s, 'DATA', D, d0, d1)

# 音声：英語は seed を変えて最大4本読み、音声認識で原稿どおりに聞こえたものを使う
jobs = []
for p in new:
    for px, V in (('e', dict(voice='ryan')), ('f', dict(voice='libritts', spk=60, noise=0.333, noise_w=0.4))):
        best = None
        for seed in range(4):
            a, sr = en(p['en'], seed=seed, **V); sc = score(p['en'], recognize([(a, sr)])[0])
            if best is None or sc > best[0]: best = (sc, a, sr)
            if sc >= 0.95: break
        assert best[0] >= 0.8, ('聞き取れない', px, p['en'], best[0])
        if best[0] < 0.95: print('※ 点数が低い', px, p['id'], best[0])
        f = f"{W}/wav/{px}_{p['id']}.wav"; save_wav(f, best[1], best[2]); jobs.append((f"{px}:{p['id']}", f, f"{TAG}_{px}_{p['id']}"))
    a, sr = ja(p['ja']); f = f"{W}/wav/j_{p['id']}.wav"; save_wav(f, a, sr); jobs.append((f"j:{p['id']}", f, f"{TAG}_j_{p['id']}"))

A, a0, a1 = span(s, 'AUDIO')
ms = encode_all(jobs, W + '/mp3'); packs = build_packs(A, jobs, ms, W + '/mp3', W + '/out', TAG)
s = put(s, 'AUDIO', A, a0, a1, ascii=True)
mon, day = int(APPV[5:7]), int(APPV[8:10])
wn = "  {v:'%s',d:'%d月%d日',t:'フレーズを%d個追加しました',s:'（説明）',w:'聞き流し',go:'tab:listen'},\n" % (APPV, mon, day, len(new))
for a, b in (("const WHATSNEW=[\n", "const WHATSNEW=[\n" + wn), (f"const APPV='{old}';", f"const APPV='{APPV}';")):
    assert s.count(a) == 1, a; s = s.replace(a, b)
open(W + '/out/index.html', 'w', encoding='utf-8').write(s)
print('ok', len(new), 'フレーズ', [(p['file'], p['size']) for p in packs])
