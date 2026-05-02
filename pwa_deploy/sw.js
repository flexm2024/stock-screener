const CACHE = 'screener-v3';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./index.html'])));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = e.request.url;

  if (url.includes('/results/')) {
    // results JSON: 캐시 완전 bypass — 항상 네트워크에서 직접
    return;
  }

  // 나머지: 캐시 우선, 없으면 네트워크
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
