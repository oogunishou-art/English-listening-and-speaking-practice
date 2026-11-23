/* 一般英会話リスニング：電波がなくてもアプリを開けるようにする（ページ・アイコン・マニフェストだけを保存。音声はアプリ側で保存済み） */
const SHELL = 'geshell-v1';
const ASSET = 'geasset-v1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.searchParams.has('appv')) return;              // 新しい版の確認はそのまま通す
  if (/\/(icon-[\w-]+\.png|apple-touch-icon\.png|manifest\.webmanifest)$/.test(url.pathname)) {   // アイコン・マニフェスト：保存したものを先に使い、裏で新しくする
    e.respondWith((async () => {
      const c = await caches.open(ASSET);
      const hit = await c.match(req);
      const net = fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => null);
      return hit || (await net) || Response.error();
    })());
    return;
  }
  const isPage = req.mode === 'navigate' || /\/(index\.html)?$/.test(url.pathname);
  if (!isPage) return;                                   // 音声ファイルなどは触らない
  e.respondWith((async () => {
    const cache = await caches.open(SHELL);
    const key = new URL('./index.html', self.registration.scope).href;
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 5000);
      const res = await fetch(req, { signal: ctrl.signal, cache: 'no-store' });
      clearTimeout(t);
      if (res.ok) await cache.put(key, res.clone());
      return res;
    } catch (err) {
      const hit = await cache.match(key);
      if (hit) return hit;
      throw err;
    }
  })());
});
