"""ドライブモードの見切れを数える：横・縦・画面を回したとき・注意書きが出ているとき × いろいろな画面の大きさ × いちばん長い文など37件で、
英語（＋発音記号）と日本語が枠からはみ出さないか、上のボタンやコントロールが画面から出ないかを確かめる。
使い方: python3 dev/test/drive_fit.py [新しいindex.html|-] [ポート]（10分ほど）。「見切れ 0/37」になっていればよい。"""
import asyncio,sys,json
import os
sys.path.insert(0, os.path.dirname(__file__))
from pwh import *
INDEX=sys.argv[1] if len(sys.argv)>1 and sys.argv[1]!='-' else None
PORT=int(sys.argv[2]) if len(sys.argv)>2 else 9181
VPS=[(844,390),(740,360),(667,375),(800,360),(915,412),(568,320),(932,430)]
PICK="""(()=>{const out=[];for(const k of Object.keys(AUDIO.index)){if(!k.startsWith('e:')||k.startsWith('e:c-'))continue;let t;try{t=textOfKey(k);}catch(e){continue}if(!t||!t.en)continue;out.push({k,who:t.who||'',en:t.en||'',ja:t.ja||'',ip:!!t.ipaP,ipaP:t.ipaP?t.ipaP.id||null:null});}
 const by=f=>out.slice().sort((a,b)=>f(b)-f(a));const S=new Map();
 const add=(L,n)=>L.slice(0,n).forEach(x=>S.set(x.k,x));
 add(by(x=>x.en.length),12);add(by(x=>x.ja.length),12);add(by(x=>x.en.length+x.ja.length*2),12);add(by(x=>x.ip?x.en.length:0),12);
 // ふつうの長さも少し
 const mid=out.filter(x=>x.en.length>40&&x.en.length<70);for(let i=0;i<mid.length;i+=Math.max(1,Math.floor(mid.length/12)))S.set(mid[i].k,mid[i]);
 return [...S.values()];})()"""
SETUP="""(()=>{store.driveOK=true;openDrive();clearInterval(DV.timer);DV.timer=null;window.__u0=window.__u0||unitText;})()"""
SHOW="""(k=>{const t=textOfKey(k);unitText=()=>t;DV.sig='';dvUpdate();})"""
MEAS="""(()=>{const r=s=>document.querySelector(s);const ew=r('#drive .dv-en-wrap'),jw=r('#drive .dv-ja-wrap'),ip=r('#dvIpa');
 const ovE=ew.scrollHeight>ew.clientHeight+1,ovJ=jw.scrollHeight>jw.clientHeight+1;
 const eb=ew.getBoundingClientRect(),ib=ip.getBoundingClientRect(),en=r('#dvEn').getBoundingClientRect();
 const lastB=Math.max(en.bottom,ip.offsetParent&&ip.innerHTML?ib.bottom:0);
 const ink=lastB>eb.bottom+1;
 const top=r('#drive .dv-top').getBoundingClientRect(),dr=r('#drive').getBoundingClientRect(),ctrl=r('#drive .dv-ctrl').getBoundingClientRect();
 const outer=ctrl.bottom>dr.bottom+1||top.right>dr.right+1||r('#drive').scrollWidth>dr.width+1;
 return {ovE,ovJ,ink,outer,fe:parseFloat(getComputedStyle(r('#dvEn')).fontSize),fi:ip.innerHTML?parseFloat(getComputedStyle(ip).fontSize):0,ipShow:ip.innerHTML?getComputedStyle(ip).display!=='none':null,fj:parseFloat(getComputedStyle(r('#dvJa')).fontSize)};})()"""
async def main():
    srv=serve(site_for(INDEX),PORT)
    try:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            ctx,pg,errs=await open_page(b,PORT,(390,844),ready=True); ev=pg.evaluate
            items=await ev(PICK); print('items',len(items))
            await ev(SETUP)
            tot={};
            for scen in ['land','rotate','note','port']:
                for vp in (VPS if scen!='port' else [(360,740),(390,844),(375,667),(320,568),(412,915)]):
                    bad=0;minE=99;hid=0;ex=[]
                    for it in items:
                        if scen=='rotate':
                            await pg.set_viewport_size({'width':vp[1],'height':vp[0]}); await ev(SHOW,it['k']); await pg.set_viewport_size({'width':vp[0],'height':vp[1]}); await asyncio.sleep(0.25)
                        else:
                            await pg.set_viewport_size({'width':vp[0],'height':vp[1]})
                            await ev(f"document.getElementById('dvNote').hidden={'false' if scen=='note' else 'true'}")
                            await ev(SHOW,it['k']); await asyncio.sleep(0.05)
                        m=await ev(MEAS)
                        if m['ovE'] or m['ovJ'] or m['ink'] or m['outer']: bad+=1; ex.append((it['en'][:50],m))
                        minE=min(minE,m['fe']); hid+=1 if m['ipShow'] is False else 0
                    print(f"{scen:6s} {vp[0]}x{vp[1]}: 見切れ {bad}/{len(items)}  英語の最小 {minE}px  発音記号を隠した {hid}",flush=True)
                    for e in ex[:2]: print('    例',e)
            print('errs',[e for e in errs if 'ERR_' not in e][:3])
            await b.close()
    finally: srv.terminate()
asyncio.run(main())
