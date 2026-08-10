// =============================================================================
// RESPONSIVIDADE E LAYOUT — base.html
// Garante que a sidebar (off-canvas no mobile / fixa no desktop) nunca volte a
// travar o scroll da página (regressão do antigo `body:has(...) { overflow:hidden }`).
// =============================================================================

describe('Responsividade e Layout (base.html)', () => {
  const caminhoDashboard = '/tickets/';

  context('Desktop (1920x1080)', () => {
    beforeEach(() => {
      cy.loginComo('tecnico');
      cy.viewport(1920, 1080);
      cy.visit(caminhoDashboard);
    });

    it('sidebar sempre visível e fixa à esquerda; conteúdo compensado', () => {
      cy.get('#sidebar').should('be.visible');
      cy.get('#sidebar').should('have.css', 'position', 'fixed');

      // O conteúdo respeita a largura da sidebar (--sidebar-width: 260px).
      cy.get('#content').should('have.css', 'margin-left', '260px');
    });

    it('o scroll da página NÃO está travado', () => {
      // Regressão crítica: o antigo `body:has(...)` impunha overflow:hidden no body.
      cy.get('body').invoke('css', 'overflow-y').should('not.eq', 'hidden');
      cy.get('html').invoke('css', 'overflow-y').should('not.eq', 'hidden');

      // Se houver conteúdo além do viewport, a página precisa rolar de verdade.
      cy.window().then((win) => {
        const scrollable = win.document.scrollingElement.scrollHeight > win.innerHeight;
        if (scrollable) {
          cy.scrollTo(0, 300);
          cy.window().its('scrollY').should('be.gt', 0);
        }
      });

      // O loader global não pode ficar cobrindo a tela após o carregamento.
      cy.get('#global-loader').should('have.class', 'd-none');
    });
  });

  context('Mobile (iPhone 12 — 390x844)', () => {
    beforeEach(() => {
      cy.loginComo('tecnico');
      cy.viewport('iphone-12');
      cy.visit(caminhoDashboard);
    });

    const posicaoDaSidebar = () =>
      cy.get('#sidebar').then(($el) => $el[0].getBoundingClientRect());

    it('sidebar começa escondida (fora da tela) e sem backdrop', () => {
      cy.get('#sidebar').should('not.have.class', 'show');
      posicaoDaSidebar().then((rect) => {
        // Off-canvas: todo o elemento fica à esquerda do viewport.
        expect(rect.right, 'lado direito da sidebar fora do viewport').to.be.lte(0);
      });
      cy.get('#sidebar-backdrop').should('not.have.class', 'show');
      cy.get('#sidebarCollapse').should('have.attr', 'aria-expanded', 'false');
    });

    it('hambúrguer abre o menu (classe .show) e clicar no backdrop fecha', () => {
      cy.get('#sidebarCollapse').should('be.visible').click();

      cy.get('#sidebar').should('have.class', 'show');
      posicaoDaSidebar().then((rect) => {
        expect(rect.left, 'sidebar visível dentro do viewport').to.be.gte(0);
      });
      cy.get('#sidebar-backdrop').should('have.class', 'show');
      cy.get('#sidebarCollapse').should('have.attr', 'aria-expanded', 'true');

      // "Tocar fora": clique no backdrop fecha o menu (off-canvas + estado ARIA).
      cy.get('#sidebar-backdrop').click({ force: true });

      cy.get('#sidebar').should('not.have.class', 'show');
      posicaoDaSidebar().then((rect) => {
        expect(rect.right).to.be.lte(0);
      });
      cy.get('#sidebar-backdrop').should('not.have.class', 'show');
      cy.get('#sidebarCollapse').should('have.attr', 'aria-expanded', 'false');
    });
  });
});
