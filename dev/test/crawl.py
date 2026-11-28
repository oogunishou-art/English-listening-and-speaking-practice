"""全タブのボタンを自動で押して（2段まで）、エラー・横のはみ出し・ほかのタブが開けなくなる不具合を洗い出す（総点検用）。
使い方:
  python3 dev/test/crawl.py [--index 新しいindex.html] [--store 記録.json] [--vp 360x740] [--tabs home,listen] [--depth 2]
  記録の入った状態で試すときは、先に python3 dev/test/make_store.py /tmp/store_rich.json を作って --store に渡す。
  1回押すごとに：エラー（ページのエラー・console.error）、横のはみ出し、全タブを開き直してエラーが出ないかを確かめ、NG を出す。
  押す前に毎回、再生を止めて音声の Blob を捨て、記録を最初の状態に戻す（ヘッドレスのブラウザは Blob の置き場が小さいため）。
  ERR_BLOB_OUT_OF_MEMORY・ERR_FAILED はヘッドレスでだけ出る雑音なので数えない。全部で20〜30分ほど。メモリを3GBほど使うので2つ同時には動かさない。"""
import asyncio, sys, json, time, argparse, os
sys.path.insert(0, os.path.dirname(__file__))
from pwh import *
ap = argparse.ArgumentParser(); ap.add_argument('--index'); ap.add_argument('--store'); ap.add_argument('--vp', default='390x844'); ap.add_argument('--tabs')
ap.add_argument('--port', type=int, default=9113); ap.add_argument('--depth', type=int, default=2)
o = ap.parse_args(); VP = tuple(map(int, o.vp.split('x')))
SKIP = {'retry', 'hics', 'nimport', 'nexport', 'bkimp', 'install', 'hgcal'}   # ファイル・外のページ・ダウンロードを開くもの
COLLECT = """(()=>{const out=[],seen={};document.getElementById('view').querySelectorAll('[data-act]').forEach(e=>{if(e.disabled)return;const r=e.getBoundingClientRect();if(!r.width||!r.height)return;
 const a=e.dataset.act,g=e.dataset.arg||'',k=a+'|'+g;if(seen[k])return;seen[k]=1;out.push({a,g,p:e.dataset.prog||'',key:e.dataset.key||'',f:e.dataset.for||''});});return out;})()"""
CLICK = """(([a,g,p,key,f])=>{const L=[...document.querySelectorAll('#view [data-act="'+a+'"]')].filter(e=>(e.dataset.arg||'')===g&&(e.dataset.prog||'')===p&&(e.dataset.key||'')===key&&(e.dataset.for||'')===f&&!e.disabled);
 if(!L.length)return 'nf';L[0].scrollIntoView({block:'center'});L[0].click();return 'ok';})"""
RESET = """(snap=>{try{pausePL();endProg();PL.token=(typeof PL.token==='number'?PL.token:0)+1000;sxDropPend&&sxDropPend();if(PL.S){try{URL.revokeObjectURL(PL.S.url)}catch(e){}PL.S=null;PL.ri=-1;}el.removeAttribute('src');el.load();}catch(e){}
 try{if(STY.on)stClose();}catch(e){}try{if(DV.on)closeDrive();}catch(e){}
 document.querySelectorAll('dialog[open]').forEach(d=>{try{d.close()}catch(e){}});
 const s=JSON.parse(snap);for(const k of Object.keys(store))delete store[k];Object.assign(store,s);save();})"""
ALLTABS = """(()=>{const t0=tab,bad=[];for(const t of TABS){try{tab=t.id;render()}catch(e){bad.push(t.id+': '+e.message)}}try{tab=t0;render()}catch(e){}return bad})()"""
async def main():
    srv = serve(site_for(o.index), o.port); store = json.load(open(o.store)) if o.store else None; res = []; tot = 0
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            ctx, pg, errs = await open_page(b, o.port, VP, store=store); ev = pg.evaluate
            tabs = o.tabs.split(',') if o.tabs else await ev('TABS.map(t=>t.id)')
            snap = await ev('JSON.stringify(store)')
            async def check(label):
                await asyncio.sleep(0.25)
                ov = await ev('document.documentElement.scrollWidth>innerWidth+1'); bad = await ev(ALLTABS); e = real_errors(errs)
                if e or ov or bad: res.append((label, e[:3], 'はみ出し' if ov else '', bad)); print('NG', res[-1], flush=True)
                errs.clear()
            async def root(t):
                await ev(RESET, snap)
                try: await ev(f"go('{t}');window.scrollTo(0,0)")
                except Exception as x:
                    print('ROOT FAIL', t, str(x)[:300], flush=True); await pg.reload(); await pg.wait_for_function('typeof render==="function"'); await asyncio.sleep(2); await ev(RESET, snap); await ev(f"go('{t}')")
                await asyncio.sleep(0.2)
            for t in tabs:
                t0 = time.time(); await root(t); base = await ev(COLLECT); await check(f'{t}:open')
                basek = {(c['a'], c['g']) for c in base}; cnt = {}; L1 = []
                for c in base:
                    if c['a'] in SKIP: continue
                    cnt[c['a']] = cnt.get(c['a'], 0) + 1
                    if cnt[c['a']] <= 3: L1.append(c)   # 同じボタンの並び（一覧の行など）は3つまで
                n = 0
                for c in L1:
                    args = [c['a'], c['g'], c['p'], c['key'], c['f']]
                    await root(t); await ev(CLICK, args); n += 1; await check(f"{t}>{c['a']}({c['g']})")
                    if o.depth < 2: continue
                    new = [x for x in await ev(COLLECT) if (x['a'], x['g']) not in basek and x['a'] not in SKIP]; cnt2 = {}; L2 = []
                    for x in new:
                        cnt2[x['a']] = cnt2.get(x['a'], 0) + 1
                        if cnt2[x['a']] <= 2: L2.append(x)
                    for x in L2[:25]:
                        await root(t); await ev(CLICK, args); await asyncio.sleep(0.15)
                        await ev(CLICK, [x['a'], x['g'], x['p'], x['key'], x['f']]); n += 1
                        await check(f"{t}>{c['a']}({c['g']})>{x['a']}({x['g']})")
                tot += n; print(f'{t}: {n}回押した {time.time()-t0:.0f}秒 NG {len(res)}', flush=True)
            await b.close()
    finally: srv.terminate()
    print('合計', tot, '回押した。NG', len(res))
    for r in res: print('NG', r)
asyncio.run(main())
