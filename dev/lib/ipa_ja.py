"""音声に使った発音（espeak-ng 形式の音素）を、日本の英和辞典ふうの発音記号に直す。
・アメリカ英語。アクセント（強く読む母音）は母音の上に ´、第2アクセントは ` をつける（例：accept → /əksépt/、information → /ìnfərméiʃən/）
・表記は学習用英和辞典に合わせる：ɛ→e、ɚ→ər、ɜː→əːr、oʊ→ou、eɪ→ei、ɹ→r、弱い i（ᵻ）→ɪ、弱い a（ɐ）→ə、たたき音 ɾ→t
・単語は「何音節目を強く読むか」も返す"""
import unicodedata
ACUTE, GRAVE = '́', '̀'
VOW = ['ɛə', 'aɪ', 'aʊ', 'eɪ', 'oʊ', 'ɔɪ', 'iː', 'uː', 'ɑː', 'ɔː', 'ɜː', 'oː', 'i', 'ɪ', 'ɛ', 'æ', 'ʌ', 'ə', 'ɚ', 'ʊ', 'ɐ', 'ᵻ', 'ɑ', 'ɔ', 'u']
CON = ['tʃ', 'dʒ', 'p', 'b', 't', 'd', 'k', 'ɡ', 'f', 'v', 'θ', 'ð', 's', 'z', 'ʃ', 'ʒ', 'h', 'm', 'n', 'ŋ', 'l', 'ɹ', 'w', 'j', 'ɾ']
VMAP = {'ɛə': 'eə', 'aɪ': 'ai', 'aʊ': 'au', 'eɪ': 'ei', 'oʊ': 'ou', 'ɔɪ': 'ɔi', 'iː': 'iː', 'uː': 'uː', 'ɑː': 'ɑ', 'ɔː': 'ɔː', 'ɜː': 'əːr', 'oː': 'ɔː',
        'i': 'i', 'ɪ': 'ɪ', 'ɛ': 'e', 'æ': 'æ', 'ʌ': 'ʌ', 'ə': 'ə', 'ɚ': 'ər', 'ʊ': 'ʊ', 'ɐ': 'ə', 'ᵻ': 'ɪ', 'ɑ': 'ɑ', 'ɔ': 'ɔ', 'u': 'u'}
CMAP = {'ɹ': 'r', 'ɡ': 'g', 'ɾ': 't'}

def tokens(ph):
    out, i = [], 0
    while i < len(ph):
        c = ph[i]
        if c in 'ˈˌ ,': out.append(('S', c)); i += 1; continue
        for t in VOW:
            if ph.startswith(t, i): out.append(('V', t)); i += len(t); break
        else:
            for t in CON:
                if ph.startswith(t, i): out.append(('C', t)); i += len(t); break
            else: raise ValueError(f'不明な記号 {c!r} in {ph}')
    return out

def convert(ph):
    """返り値：(表示用の発音記号, 音節数, 強く読む音節の番号 or None)"""
    tk = tokens(ph); res = []; pend = None; nsyl = 0; prim = None
    i = 0
    while i < len(tk):
        k, t = tk[i]
        if k == 'S':
            if t in 'ˈˌ': pend = t
            else: res.append(t)
            i += 1; continue
        if k == 'C':
            res.append(CMAP.get(t, t)); i += 1; continue
        # 母音
        nxt = tk[i + 1] if i + 1 < len(tk) else None
        after = tk[i + 2] if i + 2 < len(tk) else None
        j = i + 2
        while j < len(tk) and tk[j] in (('S', 'ˈ'), ('S', 'ˌ')): j += 1     # アクセント記号は飛ばして見る
        after = tk[j] if j < len(tk) else None
        r_follows = nxt == ('C', 'ɹ') and not (after and after[0] == 'V')   # 後ろが r で、その後に母音が続かない
        v = VMAP[t]
        if t in ('ɜː', 'ɚ') and nxt == ('C', 'ɹ'): i += 1                   # ɜː・ɚ のあとの r は1つだけ
        elif r_follows and t in ('ɪ', 'ɛ', 'ʊ'): v = {'ɪ': 'iər', 'ɛ': 'eər', 'ʊ': 'uər'}[t]; i += 1
        elif r_follows and t in ('ɑː', 'ɑ'): v = 'ɑːr'; i += 1
        elif r_follows and t in ('oː', 'ɔː'): v = 'ɔːr'; i += 1
        elif t in ('aɪ', 'aʊ') and nxt == ('V', 'ɚ'): v = v + 'ər'; i += 1; nsyl += 1   # fire, hour（2音節）
        nsyl += 1
        if pend == 'ˈ': v = v[0] + ACUTE + v[1:]; prim = nsyl - (1 if v.endswith('ər') and t in ('aɪ', 'aʊ') else 0)
        elif pend == 'ˌ': v = v[0] + GRAVE + v[1:]
        pend = None
        res.append(v); i += 1
    s = ''.join(res)
    return unicodedata.normalize('NFD', s), nsyl, prim

def display(ph):
    """表示用：「, 」で区切られた読み（there is, there are）は ／ でつなぐ"""
    parts = [p.strip() for p in ph.split(',')]
    outs = [convert(p) for p in parts]
    return ' ／ '.join(o[0] for o in outs), outs

def for_text(text, single=None, keep_comma=False):
    """英語（単語・熟語・文）から、アプリの表示用の発音記号を作る。
    返り値：(ipa, acc)。acc は1語の単語のときだけ [強く読む音節の番号, 音節数]（アプリの「アクセント」表示に使う。ないときは None）
    「there is, there are」のように読みを並べる見出し語だけ keep_comma=True（／ でつなぐ）"""
    import re
    from tts import phonemize, fix, straight, sentences
    def clean(t):
        if keep_comma: t = re.sub(r'\s*[–—]\s*', ', ', t)
        t = re.sub(r'[.?!;:"“”…—–()]', ' ', t)
        if not keep_comma: t = t.replace(',', ' ')
        return re.sub(r'\s+', ' ', t).strip()
    ss = [clean(x) for x in sentences(straight(text))]; ss = [x for x in ss if x]
    ph = ' '.join(fix(x) for x in phonemize(ss))   # 文ごとに読み（アプリの音声と同じ）
    ph = ph.replace('ʔn̩', 'tən').replace('ʔ', 't').replace('n̩', 'ən').replace('l̩', 'əl')
    if single is None: single = ' ' not in ph and ',' not in ph
    d, outs = display(ph); acc = None
    if single and outs[0][2]:
        nsyl = outs[0][1]
        if re.search('(au|ai)ər', d.replace(ACUTE, '').replace(GRAVE, '')) and not re.search(r'(wer|yer|ier|ia)', text): nsyl -= 1
        acc = [outs[0][2], nsyl]
    return d, acc
