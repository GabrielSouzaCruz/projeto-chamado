// SINO BADGE — badge do sino atualizado via OOB no polling da página.
// Sem requisição separada ao endpoint do sino.

describe('Badge do sino — atualização via OOB no polling', () => {
  beforeEach(() => {
    cy.loginComo('solicitante');
  });

  it('contador do sino atualiza após um ciclo de polling com mudança', () => {
    // Intercepta a requisição de polling do dashboard e injeta o badge OOB
    cy.intercept({ method: 'GET', pathname: '/tickets/' }, (req) => {
      if (req.headers['hx-request'] === 'true') {
        req.reply({
          statusCode: 200,
          headers: { 'Content-Type': 'text/html; charset=utf-8' },
          body:
            '<span class="d-none versao-atual" data-v="nova-versao"></span>' +
            '<span id="sino-badge" hx-swap-oob="true" class="badge" ' +
            'aria-label="Notificações não lidas: 2" role="status">2</span>',
        });
      }
    }).as('pollingDashboard');

    cy.visit('/tickets/');
    cy.get('#sino-badge').should('have.class', 'd-none');

    // Dispara manualmente a requisição HTMX (simula o que o timer de 15s faria)
    cy.window().then((win) => {
      win.htmx.ajax('GET', '/tickets/?versao=desatualizado', {
        target: '#dashboard-live',
        swap: 'innerHTML',
      });
    });

    cy.wait('@pollingDashboard');
    cy.get('#sino-badge').should('not.have.class', 'd-none');
    cy.get('#sino-badge').should('contain.text', '2');
  });

  it('nenhuma requisição ao endpoint do sino fora do polling da página', () => {
    cy.intercept('GET', '**/api/notificacoes/resumo/**').as('sinoEndpoint');
    cy.clock();
    cy.visit('/tickets/');
    cy.tick(16000);
    cy.get('@sinoEndpoint.all').should('have.length', 0);
  });
});
