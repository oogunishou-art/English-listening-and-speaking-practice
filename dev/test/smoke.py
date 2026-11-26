"""全部のタブを、スマホ縦（390×844）・横（844×390）・幅の狭いスマホ（360×740）で開いて、
エラーと横のはみ出しがないかを確かめる。画面の写真も撮る（自分で見て確かめる用）。

使い方:
  python3 dev/test/smoke.py                         # リポジトリの index.html をそのまま確かめる
  python3 dev/test/smoke.py --index 新しいindex.html  # 新しい index.html を、リポジトリの音声ファイルといっしょに確かめる
  オプション: --shots 写真の置き場所（決めなければ /tmp/ge-shots）  --port 9100
  --js 'go("rec");store.rec.sub="sum";render()'  … 全タブのあとに、その画面も写す（何回でも指定できる）

コンソールで使える主なもの：go('タブid')、render()、store（記録）、save()、A.ready（音声の準備ができたか）、TABS"""
import argparse, asyncio, os, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ap = argparse.ArgumentParser(); ap.add_argument('--index'); ap.add_argument('--shots', default='/tmp/ge-shots'); ap.add_argument('--port', type=int, default=9100)
ap.add_argument('--js', action='append', default=[])
o = ap.parse_args(); os.makedirs(o.shots, exist_ok=True)

site = REPO
if o.index:   # リポジトリのファイルをハードリンクで並べ、index.html だけ差しかえたテスト用フォルダ
    site = tempfile.mkdtemp(prefix='ge-site-')
    for f in os.listdir(REPO):
        p = os.path.join(REPO, f)
        if os.path.isfile(p) and f != 'index.html':
            try: os.link(p, os.path.join(site, f))
            except OSError: os.symlink(p, os.path.join(site, f))
    import shutil; shutil.copy(o.index, os.path.join(site, 'index.html'))
    d = os.path.dirname(os.path.abspath(o.index))   # 新しい index.html の横にある新しい音声・字形のファイルも並べる
    for f in os.listdir(d):
        if (f.startswith('geadd-') or f.startswith('pdf-fonts-')) and f.endswith('.bin') and not os.path.exists(os.path.join(site, f)):
            os.symlink(os.path.join(d, f), os.path.join(site, f))
srv = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), 'srv.py'), site, str(o.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

async def main():
    bad = 0
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        for vp in [{'width': 390, 'height': 844}, {'width': 844, 'height': 390}, {'width': 360, 'height': 740}]:
            ctx = await b.new_context(service_workers='block', viewport=vp); pg = await ctx.new_page(); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(f'http://127.0.0.1:{o.port}/index.html'); await pg.wait_for_function('typeof render==="function"&&typeof TABS!=="undefined"', timeout=60000)
            ev = pg.evaluate
            for _ in range(240):
                if await ev('typeof A!=="undefined"&&A.ready'): break
                await asyncio.sleep(0.5)
            tabs = await ev('TABS.map(t=>t.id)'); over = []
            for t in tabs:
                await ev(f"go('{t}')"); await asyncio.sleep(0.3)
                if await ev('document.documentElement.scrollWidth>innerWidth+1'): over.append(t)
                await pg.screenshot(path=f"{o.shots}/{vp['width']}x{vp['height']}_{t}.png", full_page=True)
            for i, js in enumerate(o.js):
                await ev(js); await asyncio.sleep(0.5)
                if await ev('document.documentElement.scrollWidth>innerWidth+1'): over.append(f'js{i+1}')
                await pg.screenshot(path=f"{o.shots}/{vp['width']}x{vp['height']}_js{i+1}.png", full_page=True)
            ok = not errs and not over; bad += 0 if ok else 1
            print(('OK ' if ok else 'NG ') + f"{vp['width']}x{vp['height']} タブ{len(tabs)}つ", 'はみ出し:', over or 'なし', 'エラー:', errs[:3] or 'なし')
            await ctx.close()
        await b.close()
    print('写真:', o.shots)
    return bad

try: r = asyncio.run(main())
finally: srv.terminate()
sys.exit(1 if r else 0)
