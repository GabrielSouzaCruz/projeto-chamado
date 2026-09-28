// =============================================================================
// SCRIPTS GLOBAIS DO base.html — TAREFA 2
// Removeu-se: BFCache killer (pageshow reload), global page loader,
// anti-double-submit global, polling do sino (setInterval 5s) e Pusher global.
// =============================================================================

describe('Scripts globais do base.html', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
  })

  it('nenhum script global conflitante é renderizado', () => {
    cy.visit('/tickets/')
    cy.document().then((doc) => {
      const html = doc.documentElement.outerHTML
      expect(html, 'BFCache killer (pageshow reload)').not.to.contain('event.persisted')
      expect(html, 'polling global do sino').not.to.contain('setInterval(poll')
      expect(html, 'bloco Pusher global').not.to.contain('js.pusher.com')
      expect(doc.getElementById('global-loader'), 'global loader').to.eq(null)
    })
  })

  it('botão Voltar não recarrega: pageshow persistido não força reload', () => {
    cy.visit('/tickets/')
    cy.window().then((win) => {
      win.__memoriaVoltar = 'preservado'
    })
    // Simula o restore de BFCache (navegador dispara pageshow com persisted=true).
    cy.window().then((win) => {
      const evento = new win.Event('pageshow', { bubbles: true })
      Object.defineProperty(evento, 'persisted', { value: true })
      win.dispatchEvent(evento)
    })
    // Com o killer havia um location.reload() aqui → a memória da página se perderia.
    cy.wait(500)
    cy.window().its('__memoriaVoltar').should('eq', 'preservado')
    cy.url().should('include', '/tickets/')
  })
})
