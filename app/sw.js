// Family Finance — Service Worker
// Caches app shell for offline access. API calls always go to network.

const CACHE_NAME = 'family-finance-v35';  // bump this whenever index.html changes

// Cache '/' (the actual root response), not '/index.html' which Cloudflare
// redirects — serving a redirect response from a SW causes ERR_FAILED on mobile.
const SHELL = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// Install: cache the app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: serve shell from cache; everything else from network
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Always fetch Supabase API calls from network
  if (url.hostname.includes('supabase.co')) return;

  // CDN scripts — network first, cache as fallback
  if (url.hostname.includes('jsdelivr') || url.hostname.includes('cdn')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // Navigation requests (PWA launch, page refresh) — network first, cached '/' as fallback.
  // Must be network-first to avoid serving a cached redirect response, which
  // causes "response served by SW has redirections" / ERR_FAILED on mobile.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => caches.match('/'))
    );
    return;
  }

  // Other app shell assets — cache first
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
