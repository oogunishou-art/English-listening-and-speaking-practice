"""音声合成。英語は Piper の音声モデル（ONNX）に音素を直接わたして読ませ、日本語は VOICEVOX で読ませる。
先に bash dev/setup.sh で道具をそろえておく（置き場所 GE_TOOLS、決めなければ /tmp/getools）。

英語の声（アプリで使っているもの）
  e: 'ryan'（あなた役の男性。設定なし）
  f: 'libritts' spk=60（女性。読み直すときは noise=0.333, noise_w=0.4 が安定）
  b: 'britf'（イギリス英語の女性）
  会話の相手役は libritts のいろいろな話者（例：同僚 4、ジムの女性 162、上司 90。若い男性・女性は場面ごとに選ぶ）
日本語の声：VOICEVOX 冥鳴ひまり（スタイル14）、速さ 1.1、前後の無音 0.05 秒

使い方の例
  a, sr = en('How was your weekend?')                 # 男性
  a, sr = en('How was your weekend?', 'libritts', 60)  # 女性
  a, sr = word('refund')                               # 1語だけの読み（前置きの文の中で読ませて切り出す）
  a, sr = ja('週末はどうだった？')
  save_wav('x.wav', a, sr)"""
import os, re, json, subprocess, io
import numpy as np, onnxruntime as ort
T = os.environ.get('GE_TOOLS', '/tmp/getools')
VOICES = {'ryan': f'{T}/voices/en-us-ryan-high.onnx', 'libritts': f'{T}/voices/en-us-libritts-high.onnx',
          'britf': f'{T}/voices/en-gb-southern_english_female-low.onnx'}
LANG = {'ryan': 'en-us', 'libritts': 'en-us', 'britf': 'en-gb-x-rp'}
# espeak-ng が文の中でまちがえる読みを、音素の段階で直す
FIX = [(re.compile(r'([ɛɪ])kskjˈuːs(?= m)'), r'\1kskjˈuːz'),          # Excuse me の excuse は z の音
       (re.compile(r'(?:^|(?<=\s))jˈuːzd t(?=[əʊuː])'), 'jˈuːst t')]   # 「〜したものだ」の used to は s の音
ABBR = re.compile(r'\b(Mr|Mrs|Ms|Dr|St|No)\.$')
_S = {}

def straight(s): return s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')

def model(v):
    if v not in _S:
        o = ort.SessionOptions(); o.intra_op_num_threads = 2
        _S[v] = (ort.InferenceSession(VOICES[v], o, providers=['CPUExecutionProvider']), json.load(open(VOICES[v] + '.json')))
    return _S[v]

def phonemize(texts, lang='en-us'):
    inp = ''.join(json.dumps({'text': straight(t)}) + '\n' for t in texts)
    r = subprocess.run([f'{T}/piper/piper_phonemize', '-l', lang, '--espeak_data', f'{T}/piper/espeak-ng-data', '-j'],
                       input=inp.encode(), capture_output=True, env={'LD_LIBRARY_PATH': f'{T}/piper'}, check=True)
    return [''.join(json.loads(l)['phonemes']) for l in r.stdout.decode().splitlines() if l.strip()]

def fix(ipa):
    for pat, rep in FIX: ipa = pat.sub(rep, ipa)
    return ipa

def sentences(text):
    parts, cur = [], ''
    for tok in re.split(r'(?<=[.?!])\s+', text.strip()):
        cur = (cur + ' ' + tok).strip() if cur else tok
        if ABBR.search(cur): continue
        parts.append(cur); cur = ''
    if cur: parts.append(cur)
    return parts

def ids_of(ipa, cfg):
    m = cfg['phoneme_id_map']; ids = [m['^'][0], m['_'][0]]
    for ch in ipa:
        if ch not in m: continue   # Piper と同じく、モデルにない記号は飛ばす
        ids += [m[ch][0], m['_'][0]]
    return ids + [m['$'][0]]

def synth(ipa, voice='ryan', spk=None, noise=None, length=None, noise_w=None, seed=0):
    """音素（IPA）を1つ読ませる。seed・noise・noise_w を変えると読み方のゆらぎが変わる（読み直しに使う）"""
    sess, cfg = model(voice); inf = cfg['inference']
    ids = np.array([ids_of(ipa, cfg)], dtype=np.int64)
    scales = np.array([inf['noise_scale'] if noise is None else noise, inf['length_scale'] if length is None else length,
                       inf['noise_w'] if noise_w is None else noise_w], dtype=np.float32)
    feed = {'input': ids, 'input_lengths': np.array([ids.shape[1]], dtype=np.int64), 'scales': scales}
    if cfg.get('num_speakers', 1) > 1: feed['sid'] = np.array([spk or 0], dtype=np.int64)
    np.random.seed(seed)
    a = sess.run(None, feed)[0].squeeze()
    return a.astype(np.float32), cfg['audio']['sample_rate']

def en(text, voice='ryan', spk=None, noise=None, noise_w=None, length=None, seed=0):
    """英文を読ませる。文ごとに読み、0.2 秒の間をはさむ（piper コマンドと同じ）"""
    ss = sentences(straight(text)); ph = [fix(p) for p in phonemize(ss, LANG[voice])]
    assert len(ph) == len(ss), (text, ph)
    chunks = []; sr = 22050
    for i, p in enumerate(ph):
        a, sr = synth(p, voice=voice, spk=spk, noise=noise, noise_w=noise_w, length=length, seed=seed)
        a = a / max(0.01, float(np.max(np.abs(a)))) * 0.95
        if i: chunks.append(np.zeros(int(sr * 0.2), np.float32))
        chunks.append(a)
    return np.clip(np.concatenate(chunks), -1, 1), sr

def _gap(a, sr, lo, hi, th_ratio=0.03):
    fr = int(sr * 0.005); n = len(a) // fr; r = np.sqrt((a[:n * fr].reshape(n, fr) ** 2).mean(1)); sil = r < r.max() * th_ratio
    i0, i1 = int(lo * sr / fr), min(n, int(hi * sr / fr)); best = None; i = i0
    while i < i1:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if best is None or (j - i) > (best[1] - best[0]): best = (i, j)
            i = j
        else: i += 1
    return best, fr

def word(w, voice='ryan', spk=None, **kw):
    """1語だけの読み。「The next word is. refund.」と前置きと区切って読ませ、間の無音で切り出す
    （1語だけを読ませると不自然になりやすい）。2語以上の言い方（熟語など）は en() でそのまま読ませる"""
    pre = phonemize(['The next word is'], LANG[voice])[0]
    ipa = fix(phonemize([straight(w)], LANG[voice])[0])
    a, sr = synth(pre + '. ' + ipa.rstrip('.?!') + '.', voice=voice, spk=spk, **kw)
    best, fr = _gap(a, sr, 0.45, len(a) / sr - 0.2)
    if best is None or (best[1] - best[0]) * fr / sr < 0.05: return en(w, voice, spk)
    return a[max(0, best[1] * fr - int(0.02 * sr)):], sr

_VV = None
def _vv():
    global _VV
    if _VV is None:
        import glob
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        lib = glob.glob(f'{T}/voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1*')[0]
        syn = Synthesizer(Onnxruntime.load_once(filename=lib), OpenJtalk(f'{T}/open_jtalk_dic_utf_8-1.11'), cpu_num_threads=2)
        with VoiceModelFile.open(f'{T}/vvm/1.vvm') as m: syn.load_voice_model(m)
        _VV = syn
    return _VV

def ja(text, speed=1.1, style=14):
    """日本語を読ませる。読みまちがえる語（例：市場→いちば、方→かた）は、text をかなに書きかえて読ませる"""
    import soundfile as sf
    syn = _vv(); q = syn.create_audio_query(text, style)
    q.speed_scale = speed; q.pre_phoneme_length = 0.05; q.post_phoneme_length = 0.05
    a, sr = sf.read(io.BytesIO(syn.synthesis(q, style)), dtype='float32')
    return a, sr

def ja_reading(text, style=14):
    """VOICEVOX の読み（カタカナ）。読みまちがいの点検に"""
    q = _vv().create_audio_query(text, style)
    return ''.join(m.text for ph in q.accent_phrases for m in ph.moras)

from audio import save_wav  # noqa: E402  （ここからも使えるように）
