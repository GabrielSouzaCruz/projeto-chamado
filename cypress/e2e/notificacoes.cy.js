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

  it('abrir a gaveta busca o resumo e substitui o "Carregando..."', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#drawerNotificacoes').should('have.class', 'show')
    // Sem polling: a lista só carrega quando a gaveta abre. O spinner inicial
    // é trocado pelo conteúdo (itens) ou pelo estado vazio.
    cy.get('#notificacoes-lista').should(($el) => {
      expect($el.text()).not.to.contain('Carregando notificações...')
    })
    cy.get('#notificacoes-lista').find('a.d-block, .fa-bell-slash').should('exist')
  })

  it('offcanvas tem botão de fechar', () => {
    cy.get('#sino-notificacoes').click()
    cy.get('#drawerNotificacoes .btn-close').should('exist')
    cy.get('#drawerNotificacoes .btn-close').click()
    cy.get('#drawerNotificacoes').should('not.have.class', 'show')
  })
})
