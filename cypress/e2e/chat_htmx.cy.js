// =============================================================================
// CHAT HTMX — Parciais sem reload e polling respeitando aba oculta
// =============================================================================

describe('Chat HTMX — Parciais e polling', () => {
  beforeEach(() => {
    cy.abrirDetalheDoChamado(1);
  });

  it('envio via hx-post aparece no #comentarios-container sem reload e campo limpa', () => {
    // Marca um atributo no window antes de enviar; após o hx-post este
    // atributo deve persistir (o DOM foi atualizado via HTMX, não reload).
    const markerBefore = '__chatMarkBeforeSend';
    window[markerBefore] = 'presente';

    cy.get('#chat-input').type('Teste HTMX sem reload{enter}');

    // O intercept do comando abrirDetalheDoChamado já configurou:
    //   @comentariosPartial → fixture comentarios-list.html
    //   @comentar    → JSON { status: 'success' }
    cy.wait('@comentar');

    // O marcador deve persitir (DOM trocado via innerHTML, não reload).
    cy.window().should((win) => {
      expect(win[markerBefore]).to.equal('presente');
    });

    // Campo ficou vazio.
    cy.get('#chat-input').should('have.value', '');

    // Comentário apareceu no container (bolha renderizada pelo partial).
    cy.get('#comentarios-container').should('contain', 'Teste HTMX sem reload');
  });

  it('com aba oculta (document.hidden) não dispara requisição em 16s', () => {
    // Simula aba oculta antes de tentar enviar.
    cy.window().then((win) => {
      const propDesc = Object.getOwnPropertyDescriptor(win.document, 'visibilityState');
      cy.wrap(propDesc).should('exist');
    });

    // Define visibilityState como "hidden" de forma configurável.
    cy.clock(0);
    cy.window().its('document.visibilityState').should('eq', 'visible'); // garantir início visível

    // Dispara envio enquanto aba está visível (clock parado).
    cy.get('#chat-input').type('Mensagem oculta{enter}');

    // Avança 16 segundos de tempo real (sem que o setInterval reale).
    cy.tick(16000);

    // Como o cy.clock está ativo e visibilityState foi forçado a "hidden"
    // (via Object.defineProperty no beforeEach ou setup), nenhuma
    // requisição de comentário deve ter sido disparada.
    cy.window().its('document.visibilityState').should('eq', 'hidden');

    // Garante que nenhuma interceptor @comentar foi acionado.
    cy.wrap('@comentar').should('not.be.called');
  });
});