"""音声の MP3 化と、追加の音声ファイル（geadd-*.bin）づくり。既存の音声ファイルは変えない。

音声ファイル（.bin）の形：'GEPK0001' + 8バイトの 0 + MP3 を順に並べたもの（1ファイル 10MB まで）。
index.html の AUDIO：
  AUDIO.packs = [{file, size, sha}]（sha は SHA-256。アプリが読み込み時に確かめる）
  AUDIO.index = {キー: [パック番号, 先頭からの位置, バイト数, 長さ(ミリ秒)]}
キーの頭：e 英語・男性（Ryan）／f 英語・女性（LibriTTS 60）または会話の相手役／b 英語・イギリス英語の女性／
          j 日本語（VOICEVOX 冥鳴ひまり）／t 会話の場面名（日本語）／m・v・w 会話の役ごとの別の声
同じキーを新しいパックに入れなおすと、そのキーは新しい音声に差しかわる（古いパックはそのまま残す）。"""
import json, os, hashlib, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio import read_wav, trim, fade, normalize, encode, verify
MAGIC = b'GEPK0001' + b'\0' * 8; PACK_MAX = 10 * 1024 * 1024

def span(s, name):
    """index.html の文字列 s から const NAME={...} を取り出す。返り値：(中身, 始まり, 終わり)"""
    i = s.index(f'const {name}=') + len(f'const {name}=')
    obj, end = json.JSONDecoder().raw_decode(s[i:]); return obj, i, i + end

def put(s, name, obj, a, b, **kw):
    """span で取り出した場所に、中身を書き戻す"""
    return s[:a] + json.dumps(obj, ensure_ascii=kw.get('ascii', False), separators=(',', ':')) + s[b:]

def encode_all(jobs, mp3dir):
    """jobs: [(キー, WAVのパス, 名前)]。同じ名前は1回だけ MP3 にする。返り値 {名前: 長さ(ミリ秒)}"""
    os.makedirs(mp3dir, exist_ok=True); ms = {}
    for k, wav, name in jobs:
        if name in ms: continue
        mp, mj = f'{mp3dir}/{name}.mp3', f'{mp3dir}/{name}.json'
        if os.path.exists(mp) and os.path.exists(mj):
            j = json.load(open(mj))
            if j.get('src') == wav and j.get('mt') == os.path.getmtime(wav): ms[name] = j['ms']; continue
        sr, x = read_wav(wav); y = fade(normalize(trim(x, sr), sr), sr)
        encode(y, sr, mp); v = verify(mp, len(y) / sr); assert v, ('検証エラー', k, wav)
        json.dump({'ms': v, 'src': wav, 'mt': os.path.getmtime(wav)}, open(mj, 'w')); ms[name] = v
    return ms

def build_packs(A, jobs, ms, mp3dir, outdir, tag):
    """jobs の順に MP3 を詰めて geadd-{tag}-N-sha8.bin を作り、A['index'] と A['packs'] を更新する。
    tag はその版の名前（例 '20261127a'）。outdir の中身は作り直す"""
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.startswith('geadd-') and f.endswith('.bin'): os.remove(outdir + '/' + f)
    base = len(A['packs']); packs = []; st = {'cur': bytearray(MAGIC), 'pend': {}, 'placed': {}}
    def flush():
        cur = st['cur']
        if len(cur) <= len(MAGIC): return
        h = hashlib.sha256(cur).hexdigest(); fn = f'geadd-{tag}-{len(packs)+1}-{h[:8]}.bin'
        open(f'{outdir}/{fn}', 'wb').write(cur); packs.append({'file': fn, 'size': len(cur), 'sha': h})
        for kk, v in st['pend'].items(): A['index'][kk] = [base + len(packs) - 1] + v
        st['cur'] = bytearray(MAGIC); st['pend'] = {}; st['placed'] = {}
    for k, wav, name in jobs:
        b = open(f'{mp3dir}/{name}.mp3', 'rb').read()
        if name in st['placed']: st['pend'][k] = [st['placed'][name], len(b), ms[name]]; continue
        if len(st['cur']) + len(b) > PACK_MAX: flush()
        st['placed'][name] = len(st['cur']); st['pend'][k] = [len(st['cur']), len(b), ms[name]]; st['cur'] += b
    flush(); A['packs'] += packs
    return packs

def clip(repo, A, key):
    """いまアプリに入っている音声（MP3 のバイト列）を取り出す。聞きくらべや点検に"""
    p, off, n, _ = A['index'][key]
    with open(os.path.join(repo, A['packs'][p]['file']), 'rb') as f: f.seek(off); return f.read(n)
