const CACHE_NAME = 'agenda-beauty-v1';
const ASSETS = [
    '/',
    '/admin',
    '/static/style.css',
    '/static/icon-192.svg',
    '/static/manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    // Para peticiones de API (datos dinámicos), siempre ir al servidor
    const url = new URL(event.request.url);
    if (event.request.method !== 'GET' ||
        url.pathname.startsWith('/horarios') ||
        url.pathname.startsWith('/reservas') ||
        url.pathname.startsWith('/crear') ||
        url.pathname.startsWith('/eliminar') ||
        url.pathname.startsWith('/agregar') ||
        url.pathname.startsWith('/borrar') ||
        url.pathname.startsWith('/bloquear') ||
        url.pathname.startsWith('/desbloquear')) {
        return;
    }

    // Para assets estáticos, intentar cache primero, luego red
    event.respondWith(
        caches.match(event.request)
            .then(cached => cached || fetch(event.request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
            )
    );
});
