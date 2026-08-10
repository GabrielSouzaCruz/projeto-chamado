// ---------------------------------------------------------------
// Comandos customizados da suíte E2E.
//
// Filosofia: TODAS as chamadas de dados (AJAX/fetch/partials) são
// interceptadas com cy.intercept. O único contato com o backend real
// é o carregamento do documento + estáticos + o login (que usa o
// usuário demo criado por `python manage.py seed_e2e`).
// ---------------------------------------------------------------

const CREDENCIAIS = {
  tecnico: {
    username: Cypress.env('E2E_TECNICO_USER'),
    password: Cypress.env('E2E_TECNICO_PASS'),
  },
  solicitante: {
    username: Cypress.env('E2E_SOLICITANTE_USER'),
    password: Cypress.env('E2E_SOLICITANTE_PASS'),
  },
};

// ---------------------------------------------------------------
// Login via UI, com cache de sessão (cy.session) para rodar rápido.
// ---------------------------------------------------------------
Cypress.Commands.add('loginComo', (perfil = 'tecnico') => {
  const creds = CREDENCIAIS[perfil];
  if (!creds) {
    throw new Error(`Perfil desconhecido: "${perfil}". Use "tecnico" ou "solicitante".`);
  }

  cy.session(perfil, () => {
    cy.visit('/accounts/login/');
    cy.get('#id_username').type(creds.username);
    cy.get('#id_password').type(creds.password, { log: false });
    cy.get('#login-form').submit();
    // Sucesso = saiu da tela de login e caiu no sistema (dashboard).
    cy.url().should('include', '/tickets/');
    cy.get('#sidebar').should('be.visible');
  });
});

// ---------------------------------------------------------------
// Intercepta TODAS as APIs de dados do chamado para não depender do
// conteúdo do banco. O response é controlado por fixtures/objetos.
// ---------------------------------------------------------------
Cypress.Commands.add('interceptarAPIsDoChamado', (id, opts = {}) => {
  const base = `**/tickets/${id}/`;

  // Partials (mini-APIs HTML consumidas via fetch pelo JS do chat)
  cy.intercept('GET', `${base}comentarios/**`, { fixture: 'comentarios-list.html' }).as('comentariosPartial');
  cy.intercept('GET', `${base}status-badge/**`, { fixture: 'status-badge.html' }).as('statusBadge');

  // Ações POST (comentar / status / assumir). `opts.comentario.delayMs`
  // permite segurar a resposta para observar o estado "A enviar...".
  const respComentario = opts.comentario || { statusCode: 200, body: { status: 'success' } };
  cy.intercept('POST', `${base}comentar/**`, respComentario).as('comentar');

  cy.intercept('POST', `${base}status/**`, { statusCode: 200, body: { status: 'success' } }).as('alterarStatus');
  cy.intercept('POST', `${base}assumir/**`, { statusCode: 200, body: { status: 'success' } }).as('assumir');
});

// ---------------------------------------------------------------
// Atalho: loga, mocka as APIs e abre o detalhe do chamado.
// ---------------------------------------------------------------
Cypress.Commands.add('abrirDetalheDoChamado', (id, opts = {}) => {
  cy.loginComo(opts.perfil || 'tecnico');
  cy.interceptarAPIsDoChamado(id, opts);
  cy.visit(`/tickets/${id}/`);
  cy.get('#form-comentario').should('be.visible');
  cy.get('#chat-input').should('be.visible');
});

// ---------------------------------------------------------------
// Helper: verifica se o container do chat está no fim do scroll.
// Usa callback com retry (assim o smooth scroll tem tempo de concluir).
// ---------------------------------------------------------------
Cypress.Commands.add('chatDeveEstarNoFim', (elemento = '#comentarios-container') => {
  cy.get(elemento).should(($el) => {
    const el = $el[0];
    const distanciaDoFim = el.scrollHeight - el.scrollTop - el.clientHeight;
    expect(distanciaDoFim, 'chat deve estar rolado até o fim').to.be.lessThan(5);
  });
});
