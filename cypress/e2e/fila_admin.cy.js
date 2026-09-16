describe('Fila Admin', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
    cy.visit('/tickets/fila-admin/')
  })

  it('botão Filtrar tem altura mínima de 44px (WCAG touch target)', () => {
    cy.get('.btn-filtrar').then(($btn) => {
      const height = $btn[0].getBoundingClientRect().height
      expect(height).to.be.gte(44)
    })
  })

  it('botão limpar reseta os filtros', () => {
    cy.get('select').first().then(($sel) => {
      cy.wrap($sel).select(1)
    })
    cy.get('.btn-action-circle[title*="impar"], .btn-action-circle[title*="Limpar"]').click()
    cy.get('select').first().should('have.value', 'todos')
  })

  it('botões de ação têm área de toque 44×44px', () => {
    cy.get('.btn-action-circle').each(($btn) => {
      const rect = $btn[0].getBoundingClientRect()
      expect(rect.width).to.be.gte(44)
      expect(rect.height).to.be.gte(44)
    })
  })

  it('tabela renderiza chamados com colunas corretas', () => {
    cy.get('table thead th').should('have.length.gte', 4)
    cy.get('table tbody tr').should('have.length.gte', 1)
  })
})
