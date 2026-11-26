"""見本：画面や動きだけを変える（音声は変えない）ときの組み込み方。コピーして使う。

これまでのやり方
・index.html の元のコードは直接書きかえず、変更は「つぎ足しのコード（パッチ）」として、
  目印の行 '/* 全体検索のシート */' の直前に入れる。パッチの頭には
  '/* ===================== ○○（版） ===================== */' の見出しを付ける。
・既存の関数は、function で宣言されたもの（render、renderHome、growHTML、recordsHTML など）なら
  {const f0=growHTML; growHTML=function(){const h=f0.apply(this,arguments); ...; return h;};} のように包んで足す。
  const で宣言されたものは包めないので、その関数を呼ぶ側を包む。
・CSS はパッチの中で <style> を足す（document.head.appendChild）。
・版の名前 APPV（例 '2026-11-27a'）を上げ、WHATSNEW（ホームの「お知らせ」）の先頭に1件足す。
  アプリは起動時に index.html?appv=... で新しい版を確かめ、上がっていたら読み込み直す。
使い方: python3 dev/examples/integrate_code.py パッチ.js 新しい版 → out/index.html"""
import re, sys, os
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
patch_js, APPV = sys.argv[1], sys.argv[2]
s = open(REPO + '/index.html', encoding='utf-8').read()
old = re.search(r"const APPV='([^']*)';", s).group(1); assert APPV > old, ('版は前より新しく', old)
js = open(patch_js, encoding='utf-8').read()
# お知らせ（ホーム）：v 版、d 日付、t 見出し、s 説明、w 場所、go 開く場所（'tab:タブid' など）
mon, day = int(APPV[5:7]), int(APPV[8:10])
wn = "  {v:'%s',d:'%d月%d日',t:'（見出し）',s:'（説明）',w:'（場所）',go:'tab:home'},\n" % (APPV, mon, day)
R = [("/* 全体検索のシート */", js + "\n/* 全体検索のシート */", 1),
     ("const WHATSNEW=[\n", "const WHATSNEW=[\n" + wn, 1),
     (f"const APPV='{old}';", f"const APPV='{APPV}';", 1)]
for a, b, n in R:
    assert s.count(a) == n, (a[:60], s.count(a)); s = s.replace(a, b)
os.makedirs('out', exist_ok=True); open('out/index.html', 'w', encoding='utf-8').write(s)
print('ok', old, '->', APPV, len(s))
