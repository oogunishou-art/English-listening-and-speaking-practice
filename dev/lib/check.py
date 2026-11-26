"""英語の音声の点検：音声認識（sherpa-onnx の NeMo CTC）で、原稿どおりに聞こえるかを点数にする。
これまでの基準：点数 0.95 以上・文の途中に 0.3 秒以上の不自然な間がない（句読点の数まで）・長さが自然。
だめなものは seed・noise を変えて数本読み直し、いちばん良いものを使う（前より良くならなければ差しかえない）。

  from check import recognize, score
  hs = recognize([(a, sr), ...])            # まとめて認識（速い）
  score('How was your weekend?', hs[0])     # 0〜1
  短い語（1〜3語）は with_pre(a, sr) で「The next word is」を前に付けて認識し、'word is' より後ろを使う

疑問文の文末の上げ下げ（Yes/No 疑問文は上げ、疑問詞の疑問文・A or B? は下げる）も、qtype() と reshape() で直せる。"""
import os, re, difflib, unicodedata, numpy as np
T = os.environ.get('GE_TOOLS', '/tmp/getools')
M = f'{T}/sherpa-onnx-nemo-ctc-en-conformer-small'
_R = None

def rec():
    global _R
    if _R is None:
        import sherpa_onnx
        _R = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=M + '/model.onnx', tokens=M + '/tokens.txt', num_threads=2, decoding_method='greedy_search')
    return _R

def _16k(a, sr):
    import librosa
    a = np.asarray(a, np.float32)
    return librosa.resample(a, orig_sr=sr, target_sr=16000) if sr != 16000 else a

def recognize(batch):
    """batch: [(音声, サンプリング周波数)] → 聞き取った文字列（小文字）のリスト"""
    R = rec(); ss = []
    for a, sr in batch:
        a = _16k(a, sr); a = np.concatenate([np.zeros(4000, np.float32), a / (np.max(np.abs(a)) + 1e-9) * 0.5, np.zeros(4000, np.float32)])
        s = R.create_stream(); s.accept_waveform(16000, a); ss.append(s)
    R.decode_streams(ss)
    return [s.result.text.strip().lower() for s in ss]

_PRE = None
def with_pre(a, sr):
    """短い語の前に「The next word is」を付ける（認識が安定する）。結果は 'word is' より後ろを使う"""
    global _PRE
    if _PRE is None:
        from tts import en
        p, psr = en('The next word is,'); _PRE = _16k(p, psr)
    a = _16k(a, sr); a = a / (np.max(np.abs(a)) + 1e-9) * np.max(np.abs(_PRE))
    return np.concatenate([_PRE, np.zeros(2400, np.float32), a]), 16000

def norm(t):
    t = unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode().replace('-', ' ').replace('’', "'")
    return re.sub(r"[^a-z' ]", ' ', t).split()

def score(text, heard):
    tw, hw = norm(text), norm(heard)
    if ''.join(tw).replace("'", '') == ''.join(hw).replace("'", ''): return 1.0
    return difflib.SequenceMatcher(None, ''.join(tw), ''.join(hw)).ratio()

# ---- 疑問文の文末の上げ下げ ----
WH = r"(what|what's|where|where's|when|why|who|who's|whom|whose|which|how|how's)"
AUX = r"(do|does|did|is|are|was|were|am|can|could|will|would|shall|should|may|might|must|have|has|had|isn't|aren't|wasn't|weren't|don't|doesn't|didn't|can't|couldn't|won't|wouldn't|shouldn't|haven't|hasn't|hadn't|you|got|want|need)"

def qtype(t):
    """文末の疑問文の種類：'yn'（上げる）・'wh' 'choice' 'whabout'（下げる）・'tag'（付加疑問）・'other'・None（疑問文でない）"""
    from tts import straight
    t = straight(t).strip(); s = re.split(r'(?<!\bMr\.)(?<!\bMs\.)(?<!\bDr\.)(?<=[.!?])\s+', t)[-1]
    if not s.endswith('?'): return None
    w = re.sub(r'^(?:(oh|so|and|but|well|hey|okay|ok|um|uh|right|really|sorry|excuse me|hi|hello|then|now|wait),\s*)+', '', s, flags=re.I).lower()
    m = None
    for mm in re.finditer(r'(?:^|[,—–;:]\s*)(?=' + WH + r'\b|' + AUX + r'\b)', w): m = mm
    if m and m.start() > 0: w = w[m.end():]
    if re.search(r",\s*(isn't|aren't|wasn't|weren't|don't|doesn't|didn't|can't|won't|is|are|was|do|does|did|can|will|right|okay)\s*\w*\?$", w): return 'tag'
    if re.match(WH + r"\b", w): return 'whabout' if re.match(r"how about\b|what about\b", w) else 'wh'
    if re.search(r"\bor\b", w) and re.match(AUX + r"\b", w): return 'choice'
    if re.match(AUX + r"\b", w): return 'yn'
    return 'other'

def reshape(x, sr, mode, amount=None):
    """文末の声の高さだけを変える（Praat の PSOLA。声・速さ・発音はそのまま）。mode='rise' 上げる／'fall' 下げる"""
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(np.asarray(x, np.float64), sr)
    p = snd.to_pitch(time_step=0.01, pitch_floor=65, pitch_ceiling=420)
    f = p.selected_array['frequency']; t = p.xs(); v = f > 0; t, f = t[v], f[v]
    if len(t) < 6: return None
    segs = []; s0 = 0
    for i in range(1, len(t) + 1):
        if i == len(t) or t[i] - t[i - 1] > 0.05: segs.append((s0, i - 1)); s0 = i
    a, b = segs[-1]; k = len(segs) - 1
    while t[b] - t[a] < 0.18 and k > 0: k -= 1; a = segs[k][0]
    t0, t1 = max(t[a], t[b] - 0.55), t[b]
    st = lambda hz: 12 * np.log2(hz / 100.0); hz = lambda s: 100.0 * 2 ** (s / 12)
    med = np.median(st(f)); before = f[(t >= t0 - 0.06) & (t <= t0)]
    p0 = st(np.median(before)) if len(before) else st(f[np.searchsorted(t, t0)])
    if mode == 'rise': p0 = min(p0, med); p1 = max(p0 + (amount or 6.0), med + 3.5)
    else: p1 = min(p0 - (amount or 5.0), med - 4.0)
    man = call(snd, 'To Manipulation', 0.01, 65, 420); tier = call(man, 'Extract pitch tier')
    call(tier, 'Remove points between', t0, t1 + 0.2)
    n = max(4, int((t1 - t0) / 0.02))
    for i in range(n + 1):
        u = i / n; e = u ** 1.4 if mode == 'rise' else u ** 0.8
        call(tier, 'Add point', t0 + (t1 - t0) * u, hz(p0 + (p1 - p0) * e))
    call(tier, 'Add point', t1 + 0.15, hz(p1)); call([tier, man], 'Replace pitch tier')
    return call(man, 'Get resynthesis (overlap-add)').values[0].astype(np.float32)
