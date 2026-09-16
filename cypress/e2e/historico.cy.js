describe('Histórico', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
    cy.visit('/tickets/historico/')
  })

  it('seção de filtros é visível', () => {
    cy.get('.filtros-section, form[method="get"]').should('be.visible')
  })

  it('filtros respondem em mobile (375px)', () => {
    cy.viewport(375, 812)
    cy.get('.filtros-section, form[method="get"]').should('be.visible')
    cy.get('select[multiple]').should('be.visible')
  })

  it('select múltiplo aceita mais de uma seleção', () => {
    cy.get('select[multiple]').first().then(($sel) => {
      const options = $sel.find('option')
      if (options.length >= 2) {
        cy.wrap($sel).select([options.eq(0).val(), options.eq(1).val()])
        cy.wrap($sel).invoke('val').should('have.length', 2)
      }
    })
  })

  it('tabela tem cabeçalho e corpo', () => {
    cy.get('table thead').should('be.visible')
    cy.get('table tbody').should('exist')
  })
})
