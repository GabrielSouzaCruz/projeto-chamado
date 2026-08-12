/* Service Worker - Central de Chamados (PWA)
   Estratégia: cache-first para estáticos (com validação de rede), network-first
   para navegação (HTML sempre atualizado, com fallback offline para login).
   Update: Versao True Push V2 - 2026-08-12 */

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

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const action = event.action;
  const destinoRaw = (event.notification.data && event.notification.data.url) || '/tickets/';
  const destino = new URL(destinoRaw, self.registration.scope).href;

  // Se clicou na action "Abrir Chamado" (ou no corpo da notificação sem action específica),
  // abre/foca a janela do chamado.
  if (action === 'abrir_chamado' || action === '') {
    event.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
        for (const cliente of janelas) {
          if ('focus' in cliente) {
            if (cliente.url === destino) {
              return cliente.focus();
            }
            // Janela aberta noutra rota: navega até o chamado (sem nova aba).
            try {
              cliente.navigate(destinoRaw);
            } catch (e) {
              // Navigate indisponível (janela não controlada): só foca.
            }
            return cliente.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(destino);
        }
      })
    );
  }
});

self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    console.log('Push recebido no SW:', data);
    const options = {
      body: data.body || 'Nova atualização no chamado.',
      icon: data.icon || '/static/image/pwa-192x192.png',
      badge: '/static/image/favicon.png',
      vibrate: [200, 100, 200],
      data: { url: data.url || '/' },
      tag: data.tag || 'chamado-notification',
      renotify: true,
      requireInteraction: true,
      actions: data.actions || [],
    };

    event.waitUntil(
      self.registration.showNotification(data.title || 'Sistema de Chamados', options)
    );
  } catch (e) {
    console.error('Erro ao processar push no Service Worker:', e);
  }
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
