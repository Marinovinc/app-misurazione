// Service worker: cache locale per l'offline. Nessuna rete a runtime oltre agli
// asset dell'app; l'app non ha API da chiamare (il calcolo e' client-only).
//
// Il nome della cache E' la versione: va cambiato a ogni rilascio, altrimenti il
// browser continua a servire la versione precedente e il deploy non arriva mai
// all'utente.
const CACHE = 'misura-v17';
// Percorsi **relativi**: si risolvono rispetto alla posizione di sw.js, quindi
// funzionano identici su localhost e in una sottocartella di GitHub Pages.
const ASSET = ['./', './core.js', './rileva.js', './manifest.webmanifest', './icon-512.png'];

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

// Documento e script: **rete per prima**, cache come rete di sicurezza offline.
// Cache-first sul documento significa consegnare una versione vecchia a chi ha
// gia' visitato il sito, che e' il modo piu' silenzioso di rendere invisibile un
// rilascio. Gli altri asset restano cache-first: non cambiano.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  const fresco = e.request.mode === 'navigate' || url.pathname.endsWith('.js');

  if (fresco) {
    e.respondWith(
      fetch(e.request).then(risp => {
        const copia = risp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copia));
        return risp;
      }).catch(() => caches.match(e.request).then(c => c || caches.match('./')))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(cached =>
      cached || fetch(e.request).then(risp => {
        const copia = risp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copia));
        return risp;
      }).catch(() => caches.match('./'))
    )
  );
});
