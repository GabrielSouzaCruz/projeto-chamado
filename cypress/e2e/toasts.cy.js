describe('Toasts', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
    cy.visit('/tickets/')
  })

  it('exibe toast de sucesso após ação e some em 5s', () => {
    cy.window().then(win => {
      win.mostrarNotificacao('Operação realizada com sucesso!', 'success')
    })
    cy.get('.toast-item.show').should('be.visible')
    cy.get('.toast-item.show').should('contain', 'Operação realizada com sucesso!')
    cy.wait(6500)
    cy.get('.toast-item').should('not.exist')
  })

  it('exibe toast de erro com classe correta', () => {
    cy.window().then(win => {
      win.mostrarNotificacao('Algo correu mal!', 'danger')
    })
    cy.get('.toast-item.show').should('be.visible')
    cy.get('.toast-item.show').should('have.css', 'background-color')
  })

  it('empilha múltiplos toasts simultâneos', () => {
    cy.window().then(win => {
      win.mostrarNotificacao('Primeiro', 'success')
      win.mostrarNotificacao('Segundo', 'warning')
    })
    cy.get('.toast-item.show').should('have.length', 2)
  })
})
