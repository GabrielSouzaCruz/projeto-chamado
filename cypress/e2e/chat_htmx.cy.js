// =============================================================================
// CHAT HTMX — envio via hx-post (sem reload) e polling pausado com aba oculta.
// Aqui o POST e o GET de comentários passam pelo backend real (e2e_settings):
// o intercept só observa (alias), para que o swap do container seja o real.
// =============================================================================

const TICKET_ID = 1;

describe('Chat HTMX — envio e polling', () => {
  beforeEach(() => {
    cy.loginComo('tecnico');
  });

  it('envia comentário via htmx sem recarregar a página', () => {
    cy.intercept('POST', `**/tickets/${TICKET_ID}/comentar/**`).as('enviarComentario');

    cy.visit(`/tickets/${TICKET_ID}/`);
    cy.get('#form-comentario').should('be.visible');

    // Marcador na window: se a página recarregar, ele some.
    cy.window().then((w) => {
      w.__marcador = 'presente';
    });

    const texto = `Comentário htmx ${Date.now()}`;
    cy.get('#chat-input').type(`${texto}{enter}`);

    cy.wait('@enviarComentario');

    cy.get('#comentarios-container').should('contain.text', texto);
    cy.get('#chat-input').should('have.value', '');
    cy.window().its('__marcador').should('eq', 'presente');
  });

  it('não faz polling de comentários com a aba oculta', () => {
    // O relógio precisa ser instalado antes do visit para controlar os
    // timers do htmx (hx-trigger="every 15s").
    cy.clock();
    cy.visit(`/tickets/${TICKET_ID}/`);
    cy.get('#comentarios-container').should('exist');

    cy.document().then((doc) => {
      Object.defineProperty(doc, 'hidden', { configurable: true, get: () => true });
      Object.defineProperty(doc, 'visibilityState', { configurable: true, get: () => 'hidden' });
    });

    cy.intercept('GET', `**/tickets/${TICKET_ID}/comentarios/**`).as('pollingComentarios');

    cy.tick(16000);

    cy.get('@pollingComentarios.all').should('have.length', 0);
  });
});
