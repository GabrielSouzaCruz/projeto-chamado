// =============================================================================
// CHAT — Interações e Fluidez (ticket_detail.html + ticket_detail.js)
// Foco: envio via Enter, estado "A enviar...", Shift+Enter, limpeza do campo
// e rolagem automática ao fim. TODAS as chamadas AJAX são interceptadas.
// =============================================================================

describe('Chat — Interações e Fluidez', () => {
  beforeEach(() => {
    cy.abrirDetalheDoChamado(1);
  });

  it('Enter envia a mensagem, limpa o campo e re-renderiza o chat', () => {
    cy.get('#chat-input').type('Problema com o acesso ao sistema{enter}');

    cy.wait('@comentar').its('response.statusCode').should('eq', 200);
    // Envio bem-sucedido dispara o refresh do HTML dos comentários (mini-API).
    cy.wait('@comentariosPartial');

    cy.get('#chat-input').should('have.value', '');
    cy.chatDeveEstarNoFim();
  });

  it('botão de envio desabilita e mostra spinner "A enviar..." durante a requisição', () => {
    // Segura a resposta por 900ms para observarmos o estado intermediário.
    cy.intercept('POST', '**/tickets/1/comentar/**', {
      delayMs: 900,
      statusCode: 200,
      body: { status: 'success' },
    }).as('comentar');

    cy.get('#chat-input').type('Mensagem com spinner{enter}');

    cy.get('.chat-send').should('be.disabled');
    cy.get('.chat-send').should('have.attr', 'aria-busy', 'true');
    cy.get('.chat-send').should('contain.text', 'A enviar');
    cy.get('.chat-send .spinner-border').should('be.visible');

    cy.wait('@comentar');

    cy.get('.chat-send').should('not.be.disabled');
    cy.get('.chat-send').should('not.have.attr', 'aria-busy', 'true');
    cy.get('.chat-send').should('contain.text', 'Enviar');
  });

  it('Shift+Enter quebra a linha em vez de enviar o formulário', () => {
    // Se o formulário fosse enviado, este handler lança erro e falha o teste.
    cy.intercept('POST', '**/tickets/1/comentar/**', (req) => {
      throw new Error('O formulário NÃO deveria ser enviado com Shift+Enter');
    }).as('comentar');

    cy.get('#chat-input').type('linha um{shift}{enter}linha dois');

    cy.get('#chat-input').should('have.value', 'linha um\nlinha dois');
    cy.get('#chat-input').should('have.focus'); // foco mantido, sem submit
    cy.get('.chat-send').should('not.be.disabled');
  });

  it('após o envio o container rola suavemente até a última mensagem', () => {
    // O load inicial já posiciona o chat no fim (scroll instantâneo).
    cy.chatDeveEstarNoFim();

    cy.get('#chat-input').type('Última mensagem da conversa{enter}');
    cy.wait('@comentar');
    cy.wait('@comentariosPartial');

    cy.chatDeveEstarNoFim();
  });
});
