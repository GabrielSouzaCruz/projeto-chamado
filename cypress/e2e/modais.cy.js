// =============================================================================
// MODAIS — Cancelar Chamado + tecla Esc
// Valida o atalho global de Vanilla JS em base.html: Esc fecha o modal via
// Bootstrap API, remove o backdrop, desbloqueia o body e devolve o foco.
// =============================================================================

describe('Modais — Cancelar Chamado e tecla Esc', () => {
  beforeEach(() => {
    // Técnico é superusuário no seed => o botão "Cancelar Chamado" é renderizado.
    cy.abrirDetalheDoChamado(1);

    // No Electron headless o transitionend não dispara. Como o Bootstrap 5
    // decide animar pela classe .fade (não pelo CSS), remover o .fade de todos
    // os modais faz o hide() rodar de forma síncrona e o .show sair na hora.
    cy.get('.modal').invoke('removeClass', 'fade');
  });

  it('abre pelo botão com backdrop e conteúdo correto', () => {
    cy.get('[data-bs-target="#modalCancelarTicket"]').should('be.visible').click();

    cy.get('#modalCancelarTicket').should('have.class', 'show');
    cy.get('#modalCancelarTicket h4').should('have.text', 'Cancelar Chamado?');
    cy.get('.modal-backdrop').should('exist');
    cy.get('body').should('have.class', 'modal-open');
  });

  it('tecla Esc fecha o modal, remove o backdrop e devolve o foco ao gatilho', () => {
    cy.get('[data-bs-target="#modalCancelarTicket"]').click();
    cy.get('#modalCancelarTicket').should('have.class', 'show');

    // Tecla Esc: atalho global (base.html) fecha via bootstrap.Modal.getInstance().hide().
    cy.get('body').type('{esc}');

    cy.get('#modalCancelarTicket').should('not.have.class', 'show');
    cy.get('.modal-backdrop').should('not.exist');
    cy.get('body').should('not.have.class', 'modal-open');

    // Foco devolvido ao elemento que abriu o modal (o botão "Cancelar Chamado").
    cy.focused().should('have.attr', 'data-bs-target', '#modalCancelarTicket');
  });

  it('botão "Voltar" (data-bs-dismiss) também fecha sem navegar', () => {
    cy.get('[data-bs-target="#modalCancelarTicket"]').click();
    cy.get('#modalCancelarTicket').should('have.class', 'show');

    cy.get('#modalCancelarTicket').contains('button', 'Voltar').click();

    cy.get('#modalCancelarTicket').should('not.have.class', 'show');
    cy.get('.modal-backdrop').should('not.exist');
  });
});
