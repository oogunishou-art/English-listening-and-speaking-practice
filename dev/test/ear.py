"""イヤホンのボタン（次へ＝覚えた・前へ・一時停止）と声のお知らせを、実際に音声を流して確かめる。
使い方: python3 dev/test/ear.py [新しいindex.html]
  S1 猶予を過ぎた「次へ」：いまの項目を覚えた（段階+2）にして次へ
  S2 自然に次へ進んだ直後（猶予内）の「次へ」：前の項目を覚えたにし、いまの項目を頭から
  S3 1.2秒以内の連打は無視
  S4 猶予内の「前へ」：ひとつ前に戻り、直前の「覚えた」を取り消す
  S5 猶予を過ぎた「前へ」：いまの項目を「もう一度」（段階0・苦手）
  S6 一時停止（無音を流す）と再開
  S7 声のお知らせ ok・again・goal・badge・pr・rank・week が、つなげた音声に入っていて鳴るか"""
import asyncio, sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from pwh import *
INDEX = sys.argv[1] if len(sys.argv) > 1 else None; PORT = 9112
ST = """(()=>{const S_=PL.S,r=S_&&S_.recs[PL.ri];return {ri:PL.ri,uid:r&&r.unit&&(r.unit.id||r.unit.kind),t:+el.currentTime.toFixed(2),rs:r&&+r.start.toFixed(2),playing:PL.playing,det:PL.det?PL.det.q.map(x=>x.st.key).join(','):'',soft:PL.soft}})()"""
async def main():
    srv = serve(site_for(INDEX), PORT)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            ctx, pg, errs = await open_page(b, PORT); ev = pg.evaluate
            async def st(lbl=''): s = await ev(ST); print(' ', lbl, s); return s
            srs = lambda id: ev(f"JSON.stringify(store.srs['{id}']||null)+' 苦手='+(store.weak['{id}']||0)")
            await ev("go('listen');if(!LT.units.length)LT.rebuild(false);startProg(LT)"); await asyncio.sleep(6.5); s0 = await st('はじめ'); id0 = s0['uid']
            print('S1 猶予を過ぎた「次へ」'); await ev("btnLearn(1)"); await asyncio.sleep(0.3); await st('押した直後'); print('  段階', id0, await srs(id0))
            await asyncio.sleep(2.5); id1 = (await st('2.5秒後'))['uid']
            print('S2 自然に進んだ直後の「次へ」'); await ev("sxGo(PL.S.recs[PL.ri].end-0.8)"); await asyncio.sleep(2.0); id2 = (await st('自然に次へ'))['uid']
            await ev("btnLearn(1)"); await asyncio.sleep(0.3); await st('猶予内の次へ'); print('  前', id1, await srs(id1)); print('  いま', id2, await srs(id2))
            print('S3 連打'); await ev("btnLearn(1)"); await asyncio.sleep(0.2); print('  0.5秒後にもう一度→無視', id2, await srs(id2))
            await asyncio.sleep(1.2); await ev("btnLearn(1)"); await asyncio.sleep(0.3); await st('1.4秒後'); print('  ', id2, await srs(id2))
            await asyncio.sleep(6)
            print('S4 猶予内の「前へ」'); cur = (await st('前'))['uid']; await ev("btnLearn(1)"); await asyncio.sleep(1.5); print('  覚えた', cur, await srs(cur))
            await ev("btnLearn(-1)"); await asyncio.sleep(0.4); await st('前へ'); print('  取り消し', cur, await srs(cur))
            print('S5 猶予を過ぎた「前へ」'); await asyncio.sleep(6); cur = (await st('前'))['uid']; await ev("btnLearn(-1)"); await asyncio.sleep(0.3); print('  もう一度', cur, await srs(cur))
            print('S6 一時停止と再開'); await asyncio.sleep(3); await st('前'); await ev("pauseUser()"); await asyncio.sleep(1.5); await st('一時停止'); await ev("resumePL()"); await asyncio.sleep(0.5); await st('再開')
            print('S7 声のお知らせ  つなげた音声に入っているもの:', await ev("Object.keys(PL.S.cue).join(',')"))
            for n in ['ok', 'again', 'goal', 'badge', 'pr', 'rank', 'week']:
                await asyncio.sleep(1)
                r = await ev(f"(()=>{{PL.cues=[cueKey('{n}')];sxCues(PL.S.recs[PL.ri].start);return PL.det?PL.det.q.map(x=>x.st.key).join(','):'（鳴らない）'}})()")
                print('  ', n, '->', r); await asyncio.sleep(3)
            print('エラー', real_errors(errs)[:5]); await b.close()
    finally: srv.terminate()
asyncio.run(main())
