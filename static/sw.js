/* Service Worker - Central de Chamados (PWA)
   Estratégia: cache-first para estáticos (com validação de rede), network-first
   para navegação (HTML sempre atualizado, com fallback offline para login). */

const CACHE_NAME = 'central-chamados-v3';

const PRECACHE_URLS = [
  '/',
  '/offline/',
  '/static/manifest.json',
  '/static/image/favicon.png',
  '/static/image/pwa-192x192.png',
  '/static/image/pwa-512x512.png',
  '/static/audio/notificacao.wav',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

// Toque na notificação: foca a janela aberta do PWA (ou abre uma nova) e
// navega direto para o chamado. O payload (url/ticket_id) é gravado pelo
// showNotification() no base.html.
self.addEventListener('notificationclick', (event) => {
  const dados = event.notification.data || {};
  const url = dados.url || '/tickets/';
  event.notification.close();

  event.waitUntil(
    (async () => {
      const janelas = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const cliente of janelas) {
        if ('focus' in cliente) {
          try {
            await cliente.navigate(url);
          } catch (e) {
            // Navigate indisponível (janela não controlada): só foca.
          }
          return cliente.focus();
        }
      }
      return self.clients.openWindow(url);
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  if (request.mode === 'navigate') {
    // Network-first: HTML sempre fresco; sem rede, devolve a página offline
    // pré-cacheada (em vez da página genérica do navegador).
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match('/offline/'))
    );
    return;
  }

  // Cache-first com atualização em segundo plano (stale-while-revalidate).
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === 'basic') {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
