// Service worker: cache locale per l'offline. Nessuna rete a runtime oltre al
// Flask locale; le POST /api NON vengono mai messe in cache (dati, non asset).
const CACHE = 'misura-v1';
const ASSET = ['/', '/manifest.webmanifest', '/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSET)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(chiavi => Promise.all(chiavi.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api')) return; // rete diretta
  e.respondWith(
    caches.match(e.request).then(cached =>
      cached || fetch(e.request).then(risp => {
        const copia = risp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copia));
        return risp;
      }).catch(() => caches.match('/'))
    )
  );
});
