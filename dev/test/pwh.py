"""点検テストの共通部品：テスト用サイトを作ってサーバーを立て、ページを開く（smoke.py 以外の点検テストで使う）。
  site_for(index)  … index.html だけ差しかえたテスト用フォルダ（None ならリポジトリそのまま）
  serve(site,port) … dev/test/srv.py（Range 対応）でサーバーを立てる
  open_page(browser,port,vp,store) … ページを開いて音声の準備（A.ready）まで待つ。store を渡すと記録を入れた状態で開く
    （記録は sessionStorage の印で1回だけ localStorage に入れる。ふつうに入れるとアプリの読み込み時に保存し直されて消える）"""
import asyncio, json, os, subprocess, sys, time, tempfile, shutil
from playwright.async_api import async_playwright
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def site_for(index=None):
    if not index: return REPO
    site = tempfile.mkdtemp(prefix='ge-site-')
    for f in os.listdir(REPO):
        p = os.path.join(REPO, f)
        if os.path.isfile(p) and f != 'index.html': os.symlink(p, os.path.join(site, f))
    shutil.copy(index, os.path.join(site, 'index.html'))
    d = os.path.dirname(os.path.abspath(index))
    for f in os.listdir(d):
        if (f.startswith('geadd-') or f.startswith('pdf-fonts-')) and f.endswith('.bin') and not os.path.exists(os.path.join(site, f)):
            os.symlink(os.path.join(d, f), os.path.join(site, f))
    return site
def serve(site, port):
    p = subprocess.Popen([sys.executable, os.path.join(REPO, 'dev/test/srv.py'), site, str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1); return p
async def open_page(b, port, vp=(390, 844), store=None, ready=True):
    ctx = await b.new_context(service_workers='block', viewport={'width': vp[0], 'height': vp[1]}, accept_downloads=True)
    if store is not None:
        await ctx.add_init_script("""(s=>{try{if(!sessionStorage.getItem('__seeded')){localStorage.setItem('genEnglish.v1',s);sessionStorage.setItem('__seeded','1');}}catch(e){}})(%s)""" % json.dumps(json.dumps(store)))
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append('console.' + m.type + ': ' + m.text) if m.type == 'error' else None)
    pg.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
    await pg.goto(f'http://127.0.0.1:{port}/index.html')
    await pg.wait_for_function('typeof render==="function"&&typeof TABS!=="undefined"', timeout=60000)
    if ready:
        for _ in range(240):
            if await pg.evaluate('typeof A!=="undefined"&&A.ready'): break
            await asyncio.sleep(0.5)
    return ctx, pg, errs
def real_errors(errs):
    """ヘッドレスのブラウザだけで出る雑音（外のフォント・音声の Blob の読み直し）を除く"""
    return [e for e in errs if 'ERR_' not in e]
