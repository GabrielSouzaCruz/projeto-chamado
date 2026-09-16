describe('PWA', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('manifest.json está acessível e válido', () => {
    cy.request('/static/manifest.json').then((response) => {
      expect(response.status).to.eq(200)
      const manifest = response.body
      expect(manifest).to.have.property('name')
      expect(manifest).to.have.property('icons')
      expect(manifest.icons).to.have.length.gte(2)
    })
  })

  it('ícone 512×512 maskable está declarado', () => {
    cy.request('/static/manifest.json').then((response) => {
      const maskable = response.body.icons.find(i => i.purpose === 'maskable')
      expect(maskable).to.exist
      expect(maskable.sizes).to.eq('512x512')
    })
  })

  it('link rel=manifest está no <head>', () => {
    cy.get('link[rel="manifest"]').should('exist')
  })

  it('meta theme-color está presente', () => {
    cy.get('meta[name="theme-color"]').should('exist')
  })
})
