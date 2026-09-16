describe('Dashboard', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
    cy.visit('/tickets/')
  })

  it('renderiza hero-gradient com mensagem de boas-vindas', () => {
    cy.get('.hero-gradient').should('be.visible')
    cy.get('.hero-gradient h1').should('contain', 'Olá')
  })

  it('renderiza cards de métricas (KPIs)', () => {
    cy.get('.kpi-icon').should('have.length.gte', 3)
    cy.get('small.text-uppercase.fw-bold').should('have.length.gte', 3)
  })

  it('badges de status estão presentes', () => {
    cy.get('.badge').each(($badge) => {
      expect($badge.text().trim()).to.not.be.empty
    })
  })

  it('botão "Abrir Novo Chamado" navega corretamente', () => {
    cy.get('a[href*="/tickets/novo/"]').first().should('be.visible').click()
    cy.url().should('include', '/tickets/novo/')
  })
})
