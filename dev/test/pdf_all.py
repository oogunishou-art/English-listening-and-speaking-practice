"""テキスト（PDF）を、種類 × 用紙（A4・スマホ）× 表・確認テストなどで作って /tmp/ge-pdf に保存し、
字形がなくて「?」になった文字と、確認テストが出ていない種類を数える。使い方: python3 dev/test/pdf_all.py [新しいindex.html] [記録.json]
  そのあと pdftotext / pdftoppm -r 80 -f 1 -l 1 -png で中身と見た目を確かめる。"""
import asyncio, sys, json, base64, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from pwh import *
INDEX = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None; STORE = sys.argv[2] if len(sys.argv) > 2 else None
OUT = '/tmp/ge-pdf'; os.makedirs(OUT, exist_ok=True); PORT = 9115
KINDS = ['word', 'idiom', 'base', 'talk', 'gram', 'poly', 'jba', 'para', 'stack', 'red', 'mp', 'pr', 'long', 'nat']
TESTK = ['word', 'idiom', 'base', 'jba', 'gram', 'para', 'stack', 'poly', 'talk', 'nat', 'red']   # PDFTESTK と同じ
async def main():
    srv = serve(site_for(INDEX), PORT)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx, pg, errs = await open_page(b, PORT, store=json.load(open(STORE)) if STORE else None, ready=False); ev = pg.evaluate
            await ev("""(()=>{window.__miss={};const g0=PdfDoc.prototype.glyphs;PdfDoc.prototype.glyphs=function(str,fk){const r=g0.call(this,str,fk);
              for(const x of r){if(x.g===(PDFF.fonts[x.k].cmap.get(63)||0)&&x.ch!=='?')__miss[x.ch]=(__miss[x.ch]||0)+1;}return r;};})()""")
            C = [dict(kind=k, paper=pp, lim=0) for k in KINDS for pp in ('a4', 'phone')]
            C += [dict(kind=k, paper=pp, lay='table', lim=300) for k in ['word', 'idiom', 'base', 'jba'] for pp in ('a4', 'phone')]
            C += [dict(kind=k, paper='a4', test='je', lim=60) for k in TESTK] + [dict(kind=k, paper='phone', test='ej', lim=60) for k in TESTK]
            C += [dict(kind='word', paper='a4', big=True, rec=False, chk=False, lim=200), dict(kind='idiom', paper='a4', sort='weak', flt='weak', lim=100)]
            for i, c in enumerate(C):
                r = await ev("""(async c=>{const o=Object.assign({},store.pdf,{lv:0,cat:'all',flt:'all',sort:'seq',lay:'card',test:'none',big:false,rec:true,chk:true,ipa:true,ex:true,note:true},c);
                  let R;try{R=await pdfMake(o);}catch(e){return {err:String(e&&e.message||e)}}
                  const buf=new Uint8Array(await R.blob.arrayBuffer());let s='';for(let i=0;i<buf.length;i+=32768)s+=String.fromCharCode.apply(null,buf.subarray(i,i+32768));
                  return {pages:R.pages,n:R.n,size:R.size,b64:btoa(s)};})""", c)
                if 'err' in r: print('エラー', c, r['err']); continue
                fn = f"{OUT}/{i:02d}_{c['kind']}_{c['paper']}_{c.get('lay','card')}_{c.get('test','none')}.pdf"; open(fn, 'wb').write(base64.b64decode(r['b64']))
                note = ''
                if c.get('test'):
                    txt = subprocess.run(['pdftotext', fn, '-'], capture_output=True, text=True).stdout
                    note = '確認テストあり' if '確認テスト（' in txt else '★確認テストが出ていない'
                print(f"{i:02d} {c} {r['pages']}ページ {r['n']}件 {r['size']//1024}KB {note}", flush=True)
            print('字形がなく「?」になった文字:', await ev('JSON.stringify(__miss)'))
            print('エラー', real_errors(errs)[:5]); await b.close()
    finally: srv.terminate()
asyncio.run(main())
