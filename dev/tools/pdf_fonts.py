"""PDF 教材（テキスト・座学）用の字形ファイル pdf-fonts-*.bin の点検と作り直し。
PDF は端末の中で作り、字形はこのファイルから必要な文字だけを埋めこむ。ここにない文字は PDF に出ない。
新しい教材で、いままで使っていなかった漢字・記号を入れたら、check で確かめ、足りなければ build する。

  python3 dev/tools/pdf_fonts.py check [index.html]
  python3 dev/tools/pdf_fonts.py build [index.html]   → リポジトリに新しい pdf-fonts-<sha8>.bin を作り、
                                                        渡した index.html の const PDFFONT={file,size} を書きかえる
ファイルの形：'GEPF' + JSON の長さ(4バイト) + JSON（jp/jpb/ipa/ipab ごとの位置・文字→字形番号）+ TTF 4つ
字形：日本語・英字＝Noto Sans CJK JP（Regular/Bold、PDF に埋めこむため TrueType の輪郭に変換）、発音記号＝DejaVu Sans
build には fonttools と、/usr/share/fonts の Noto Sans CJK・DejaVu Sans が要る（なければ apt-get install fonts-noto-cjk fonts-dejavu-core）"""
import hashlib, json, os, re, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
cmd = sys.argv[1]; IDX = sys.argv[2] if len(sys.argv) > 2 else REPO + '/index.html'
s = open(IDX, encoding='utf-8').read()
m = re.search(r"const PDFFONT=\{file:'([^']+)',size:(\d+)\}", s); cur = m.group(1)

def used_chars(s):
    i = s.index('const AUDIO='); j = s.index('\n', i)
    return {c for c in s[:i] + s[j:] if ord(c) > 0x7e and not (0xd800 <= ord(c) <= 0xdfff)}

def header(path):
    b = open(path, 'rb').read(); assert b[:4] == b'GEPF'; n = int.from_bytes(b[4:8], 'little'); return json.loads(b[8:8 + n])

EXTRA = '□■☆★✓✔●○◎△▲▼▶◀・…「」『』（）【】〜ー―－：；！？％＋／＝×÷①②③④⑤⑥⑦⑧⑨⑩→←↑↓、。ＡＢＣＤ０１２３４５６７８９'
LAT = ''.join(chr(c) for c in list(range(0x20, 0x7f)) + list(range(0xa0, 0x180)) + list(range(0x250, 0x370)) +
              [0x3b8, 0x3b2, 0x2013, 0x2014, 0x2019, 0x201c, 0x201d, 0x2026, 0x2192, 0x1d7b, 0x1d4a])

if cmd == 'check':
    h = header(os.path.join(REPO, cur)); have = {int(k) for f in h.values() for k in f['cmap']}
    i = s.index('const DATA=') + 11; D, _ = json.JSONDecoder().raw_decode(s, i)
    skip = lambda c: c.isspace() or ord(c) in (0xfe0f, 0x200b, 0x200d)
    data = {c for c in json.dumps(D, ensure_ascii=False) if ord(c) > 0x7e}
    miss = sorted(c for c in data if ord(c) not in have and not skip(c))
    ui = sorted(c for c in used_chars(s) - data if ord(c) not in have and not skip(c))
    print('字形ファイル', cur)
    print('教材（DATA）で足りない文字', len(miss), ''.join(miss[:200]) or '')
    print('（参考）画面の文字で足りないもの', len(ui), ''.join(ui[:200]), '… PDF に出す見出しなどに使うときだけ問題')
    sys.exit(1 if miss else 0)

if cmd == 'build':
    from fontTools.ttLib import TTCollection, TTFont, newTable
    from fontTools import subset
    from fontTools.pens.cu2quPen import Cu2QuPen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    import tempfile
    tmp = tempfile.mkdtemp()
    jp_text = ''.join(sorted(used_chars(s) | set(EXTRA) | set(chr(c) for c in range(0x20, 0x7f))))
    def otf2ttf(font):
        go = font.getGlyphOrder(); gs = font.getGlyphSet(); glyf = newTable('glyf'); glyf.glyphOrder = go; glyf.glyphs = {}
        for name in go:
            pen = TTGlyphPen(gs); gs[name].draw(Cu2QuPen(pen, 1.0, reverse_direction=True)); glyf[name] = pen.glyph()
        font['glyf'] = glyf; font['loca'] = newTable('loca'); maxp = font['maxp']; maxp.tableVersion = 0x00010000
        for a in ('maxZones', 'maxTwilightPoints', 'maxStorage', 'maxFunctionDefs', 'maxInstructionDefs', 'maxStackElements', 'maxSizeOfInstructions', 'maxComponentElements'): setattr(maxp, a, 0)
        maxp.maxZones = 1; maxp.maxComponentDepth = 0
        for t in ('CFF ', 'VORG'):
            if t in font: del font[t]
        font['head'].glyphDataFormat = 0; font.sfntVersion = '\x00\x01\x00\x00'; font['post'].formatType = 3.0
        return font
    def sub(font, text):
        o = subset.Options(); o.layout_features = []; o.hinting = False; o.desubroutinize = True; o.name_IDs = [0, 1, 2, 3, 4, 5, 6]; o.notdef_outline = True; o.glyph_names = False
        o.drop_tables += ['GSUB', 'GPOS', 'GDEF', 'BASE', 'vhea', 'vmtx', 'VORG', 'DSIG', 'kern', 'hdmx', 'LTSH', 'VDMX', 'gasp']
        ss = subset.Subsetter(o); ss.populate(text=text); ss.subset(font); return font
    meta = {}; blobs = {}
    def save(font, key):
        p = f'{tmp}/{key}.ttf'; font.save(p); f = TTFont(p)
        cm = f.getBestCmap(); go = f.getGlyphOrder(); gid = {n: i for i, n in enumerate(go)}; hh = f['hhea']; os2 = f['OS/2']; hd = f['head']
        meta[key] = dict(upm=hd.unitsPerEm, asc=hh.ascent, desc=hh.descent, cap=getattr(os2, 'sCapHeight', 700) or 700,
                         bbox=[hd.xMin, hd.yMin, hd.xMax, hd.yMax], cmap={str(c): gid[n] for c, n in cm.items()}, n=len(go))
        blobs[key] = open(p, 'rb').read()
    for w, key in (('Regular', 'jp'), ('Bold', 'jpb')):
        save(otf2ttf(sub(TTCollection(f'/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc').fonts[0], jp_text)), key)
    for fn, key in (('DejaVuSans.ttf', 'ipa'), ('DejaVuSans-Bold.ttf', 'ipab')):
        save(sub(TTFont('/usr/share/fonts/truetype/dejavu/' + fn), LAT), key)
    NAMES = {'jp': 'NotoSansCJKjp-Regular', 'jpb': 'NotoSansCJKjp-Bold', 'ipa': 'DejaVuSans', 'ipab': 'DejaVuSans-Bold'}
    off = 0; hdr = {}
    for k in ('jp', 'jpb', 'ipa', 'ipab'):
        mm = dict(meta[k]); mm.update(off=off, len=len(blobs[k]), name=NAMES[k]); hdr[k] = mm; off += len(blobs[k])
    js = json.dumps(hdr, separators=(',', ':')).encode()
    data = b'GEPF' + len(js).to_bytes(4, 'little') + js + b''.join(blobs[k] for k in ('jp', 'jpb', 'ipa', 'ipab'))
    fn = f'pdf-fonts-{hashlib.sha256(data).hexdigest()[:8]}.bin'; open(os.path.join(REPO, fn), 'wb').write(data)
    s = s.replace(m.group(0), f"const PDFFONT={{file:'{fn}',size:{len(data)}}}"); open(IDX, 'w', encoding='utf-8').write(s)
    print('作りました', fn, len(data), 'バイト（前の', cur, 'は消さずに残す）。', IDX, 'の PDFFONT を書きかえました')
