describe('Offcanvas de Notificações', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
    cy.visit('/tickets/')
  })

  it('sino abre o offcanvas', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#drawerNotificacoes').should('have.class', 'show')
  })

  it('offcanvas tem estrutura correta', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#drawerNotificacoes .offcanvas-header').should('contain.text', 'Notificações')
    cy.get('#drawerNotificacoes .offcanvas-body').should('exist')
  })

  it('clicar no sino esconde o badge', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#sino-badge').should('have.class', 'd-none')
  })

  it('offcanvas tem botão de fechar', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#drawerNotificacoes .btn-close').should('exist')
    cy.get('#drawerNotificacoes .btn-close').click()
    cy.get('#drawerNotificacoes').should('not.have.class', 'show')
  })
})
