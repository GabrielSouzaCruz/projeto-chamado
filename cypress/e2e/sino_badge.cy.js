// SINO BADGE — badge do sino atualizado via OOB no polling da página.
// Sem requisição separada ao endpoint do sino.

describe('Badge do sino — atualização via OOB no polling', () => {
  beforeEach(() => {
    cy.loginComo('solicitante');
  });

  it('contador do sino atualiza após um ciclo de polling com mudança', () => {
    // Intercept do endpoint separado registrado antes para capturar qualquer chamada antecipada
    cy.intercept('GET', '**/api/notificacoes/resumo/**').as('sinoSeparado');

    cy.visit('/tickets/');
    cy.get('#sino-badge').should('have.class', 'd-none');

    // Intercept registrado APÓS o visit para não capturar a própria navegação de página
    // (cy.intercept alia-se a qualquer fetch/XHR, inclusive navegação de documento)
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

    // Aguarda o polling real (hx-trigger="every 15s") disparar naturalmente
    cy.wait('@pollingDashboard', { timeout: 20000 });
    cy.get('#sino-badge').should('not.have.class', 'd-none');
    cy.get('#sino-badge').should('contain.text', '2');

    // Confirma: 0 requisições separadas ao endpoint do sino
    cy.get('@sinoSeparado.all').should('have.length', 0);
  });

  it('nenhuma requisição ao endpoint do sino fora do polling da página', () => {
    cy.intercept('GET', '**/api/notificacoes/resumo/**').as('sinoEndpoint');
    cy.clock();
    cy.visit('/tickets/');
    cy.tick(16000);
    cy.get('@sinoEndpoint.all').should('have.length', 0);
  });
});
