describe('Formulário de Ticket', () => {
  beforeEach(() => {
    cy.loginComo('solicitante')
    cy.visit('/tickets/novo/')
  })

  it('renderiza o wizard com 3 passos', () => {
    cy.get('#step-1').should('be.visible')
    cy.get('#step-2').should('have.class', 'd-none')
    cy.get('#step-3').should('have.class', 'd-none')
    cy.get('#step-1 #id_titulo').should('be.visible')
  })

  it('navega entre passos do wizard', () => {
    cy.get('#step-1 #id_categoria').select(1, { force: true })
    cy.get('#step-1 #id_titulo').type('Ticket de teste E2E')
    cy.get('#step-1 .btn-next').click()
    cy.get('#step-2').should('not.have.class', 'd-none')
    cy.get('#step-2 .btn-back').click()
    cy.get('#step-1').should('not.have.class', 'd-none')
  })

  it('anexo inválido exibe toast de erro', () => {
    cy.get('#step-1 #id_categoria').select(1, { force: true })
    cy.get('#step-1 #id_titulo').type('Ticket com anexo')
    cy.get('#step-1 .btn-next').click()
    cy.get('#step-2').should('not.have.class', 'd-none')
    cy.get('input[type="file"]').selectFile('cypress/fixtures/anexos/arquivo-invalido.exe', { force: true })
    cy.get('.toast-item.show').should('contain', 'Formato não permitido')
  })

  it('anexo grande exibe toast de erro', () => {
    cy.get('#step-1 #id_categoria').select(1, { force: true })
    cy.get('#step-1 #id_titulo').type('Ticket com anexo')
    cy.get('#step-1 .btn-next').click()
    cy.get('#step-2').should('not.have.class', 'd-none')
    cy.get('input[type="file"]').selectFile('cypress/fixtures/anexos/anexo-grande.png', { force: true })
    cy.get('.toast-item.show').should('contain', 'Arquivo muito grande')
  })
})
