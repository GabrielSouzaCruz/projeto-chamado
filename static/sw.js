/* Service Worker - Central de Chamados (PWA)
   Sem handlers de install/fetch: este SW só recebe push e notificationclick.
   O activate apaga os caches de versões anteriores — por isso o CACHE_NAME
   muda a cada release, para forçar a atualização do worker.
   Update: Push Only - 2026-09-28 */

const CACHE_NAME = 'central-chamados-v6';

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
  if (navigator.clearAppBadge) {
    navigator.clearAppBadge();
  }
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
      vibrate: [200, 100, 200],
      data: { url: data.url || '/' },
      tag: data.tag || 'chamado-notification',
      renotify: data.renotify === true,
      actions: data.actions || [],
    };

    const title = data.title || 'Sistema de Chamados';

    const showNotificationPromise = self.registration.showNotification(title, options)
      .then(() => {
        if (data.unread_count && navigator.setAppBadge) {
          navigator.setAppBadge(data.unread_count);
        }
      })
      .catch((err) => {
        // Fallback gracioso: Brave/Windows abortam o banner se bloquearem o
        // download do icon/badge em background. Remove as imagens e tenta uma
        // notificação "texto-only" limpa, garantindo que o banner aparece.
        console.warn('Falha ao mostrar notificação rica. Tentando modo texto-only...', err);
        delete options.icon;
        delete options.badge;
        delete options.image;
        return self.registration.showNotification(title, options);
      });

    event.waitUntil(showNotificationPromise);
  } catch (e) {
    console.error('Erro ao processar push no Service Worker:', e);
  }
});
