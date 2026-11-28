"""戻るボタン（Android の戻る操作）を確かめる：タブを2つ進んで戻る、設定・検索・ドライブモード・座学モードを戻るで閉じる、
ボタンで閉じたあとの戻るで前のタブに戻る。使い方: python3 dev/test/nav.py [新しいindex.html]（各行の「→」が期待する結果）"""
import asyncio, sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from pwh import *
INDEX = sys.argv[1] if len(sys.argv) > 1 else None; PORT = 9117
async def main():
    srv = serve(site_for(INDEX), PORT)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            ctx, pg, errs = await open_page(b, PORT); ev = pg.evaluate
            async def state(lbl): print(f'{lbl:34s}', await ev("JSON.stringify({tab,dlg:[...document.querySelectorAll('dialog[open]')].map(d=>d.id),dv:DV.on,st:STY.on})"))
            async def back(): await ev('history.back()'); await asyncio.sleep(0.5)
            async def click(sel): await pg.click(sel); await asyncio.sleep(0.4)
            await click('#nav button[data-tab=listen]'); await click('#nav button[data-tab=word]'); await state('聞き流し→単語')
            await back(); await state('戻る → listen'); await back(); await state('戻る → 最初のタブ（記録なしは intro）')
            await click('#nav button[data-tab=talk]'); await click('#openSettings'); await state('会話で設定を開く')
            await back(); await state('戻る → 設定が閉じて talk')
            await click('#openSettings'); await ev("document.getElementById('settings').close()"); await asyncio.sleep(0.6); await state('設定をボタンで閉じる')
            await back(); await state('戻る → 最初のタブ（記録なしは intro）')
            await click('#nav button[data-tab=more]'); await ev("openDrive()"); await asyncio.sleep(0.5); await state('ドライブモード')
            await back(); await state('戻る → 閉じて more')
            await ev("go('pdf')"); await asyncio.sleep(0.4); await ev("stNew();stOpen()"); await asyncio.sleep(0.5); await state('座学モード')
            await back(); await state('戻る → 閉じて pdf')
            await ev("stOpen()"); await asyncio.sleep(0.5); await ev("stClose()"); await asyncio.sleep(0.6); await state('座学をボタンで閉じる')
            await back(); await state('戻る → more')
            await click('#openSearch'); await back(); await state('検索を開いて戻る → 閉じる')
            print('エラー', real_errors(errs)[:5]); await b.close()
    finally: srv.terminate()
asyncio.run(main())
