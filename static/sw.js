/* CargoBridge AI — Service Worker */

const CACHE_NAME = 'cargobridge-v3';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/js/pwa.js',
  '/static/manifest.json',
  '/static/app_icon.png',
  '/static/favicon.png',
  '/static/ui-assets/index-CAB9GrOd.js',
  '/static/ui-assets/index-Cf-YFq8p.css'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Network-first for API calls and dynamic routes (HTML)
  if (event.request.mode === 'navigate' || url.pathname.startsWith('/api/') || !url.pathname.match(/\.(css|js|png|jpg|jpeg|gif|svg|woff2?|json)$/i)) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          if (event.request.mode === 'navigate') {
             return new Response('Offline. Please check your connection.', {
               status: 503,
               headers: { 'Content-Type': 'text/plain' }
             });
          }
          return new Response('{"error":"offline"}', {
            headers: { 'Content-Type': 'application/json' },
          });
        });
      })
    );
    return;
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (!response || response.status !== 200 || response.type !== 'basic') return response;
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      });
    })
  );
});
