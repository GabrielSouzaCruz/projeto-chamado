import './commands';

// ---------------------------------------------------------------
// Erros de terceiros (redes externas / APIs do navegador) NÃO podem
// derrubar a suíte. Apenas erros do NOSSO código devem falhar o teste.
// ---------------------------------------------------------------
Cypress.on('uncaught:exception', (err) => {
  const ignoraveis = /pusher|Notification|serviceWorker|WebSocket|Audio|ResizeObserver/i;
  if (ignoraveis.test(err.message)) {
    return false; // impede o Cypress de falhar o teste
  }
  return true;
});

beforeEach(() => {
  // -------------------------------------------------------------
  // Isolamento de rede: o tempo real (Pusher) nunca deve depender
  // de um backend/canal real. Servimos um stub da lib no lugar do
  // script externo para que os handlers da página não quebrem.
  // -------------------------------------------------------------
  cy.intercept('GET', '**/js.pusher.com/**', {
    statusCode: 200,
    contentType: 'application/javascript',
    body: 'window.Pusher = class { constructor() { this.connection = { state: "connected" }; } subscribe() { return { bind() {}, unbind() {} }; } disconnect() {} connect() {} };',
  });

  // Service Worker (PWA): bloqueado para não registrar cache em background
  // nem interferir no comportamento de rede dos testes.
  cy.intercept('GET', '**/sw.js', { statusCode: 200, contentType: 'application/javascript', body: '' });
});
