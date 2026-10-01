// =============================================================================
// VENDOR LOCAL — sem CDN
// Garante que nenhum recurso externo (CDN) é solicitado e que Bootstrap,
// FontAwesome e Inter estão funcionando a partir de static/vendor/.
// =============================================================================

const CDN_PATTERNS = [
  { pattern: '*cdn*',         alias: 'block_cdn'         },
  { pattern: '*googleapis*',  alias: 'block_googleapis'  },
  { pattern: '*gstatic*',     alias: 'block_gstatic'     },
  { pattern: '*jsdelivr*',    alias: 'block_jsdelivr'     },
  { pattern: '*cdnjs*',       alias: 'block_cdnjs'        },
  { pattern: '*unpkg*',       alias: 'block_unpkg'        },
]

describe('Vendor local — sem CDN', () => {
  beforeEach(() => {
    cy.loginComo('tecnico')
  })

  it('nenhuma requisição a CDN externa é feita ao carregar a página', () => {
    const cdnChamados = []

    CDN_PATTERNS.forEach(({ pattern }) => {
      cy.intercept(pattern, (req) => {
        cdnChamados.push(req.url)
        req.destroy()
      })
    })

    cy.visit('/tickets/')

    cy.then(() => {
      expect(cdnChamados, `CDNs chamados: ${JSON.stringify(cdnChamados)}`).to.have.length(0)
    })
  })

  it('ícone FontAwesome tem font-family "Font Awesome 6 Free" e largura > 0', () => {
    cy.visit('/tickets/')
    cy.get('i.fas').first().should('be.visible').then(($el) => {
      cy.window().then((win) => {
        const pseudoStyle = win.getComputedStyle($el[0], '::before')
        expect(pseudoStyle.fontFamily, 'font-family do ::before').to.include('Font Awesome 6 Free')
        expect($el[0].offsetWidth, 'largura do ícone').to.be.greaterThan(0)
      })
    })
  })

  it('elemento Bootstrap (.btn) tem estilos aplicados (display inline e padding > 0)', () => {
    cy.visit('/tickets/')
    cy.get('.btn').first().should('be.visible').then(($el) => {
      cy.window().then((win) => {
        const style = win.getComputedStyle($el[0])
        expect(style.display, 'display do .btn').to.match(/inline/)
        expect(parseFloat(style.paddingTop), 'padding-top do .btn').to.be.greaterThan(0)
      })
    })
  })

  it('body usa a fonte Inter', () => {
    cy.visit('/tickets/')
    cy.get('body').then(($body) => {
      cy.window().then((win) => {
        const style = win.getComputedStyle($body[0])
        expect(style.fontFamily, 'font-family do body').to.include('Inter')
      })
    })
  })
})
