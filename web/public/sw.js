const CACHE = 'growora-v091-shell';
const SHELL = ['/', '/index.html'];
self.addEventListener('install', (e) => e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));
self.addEventListener('fetch', (e) => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).catch(()=>caches.match('/index.html'))));
});
