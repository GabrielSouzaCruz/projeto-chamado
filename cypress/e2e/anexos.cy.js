// =============================================================================
// ANEXOS — Validação do input file e preview (ticket_detail.html)
// Cobre: extensão inválida, arquivo > 2 MB, preview de PDF e de imagem.
// Os arquivos de teste ficam em cypress/fixtures/anexos/.
// =============================================================================

describe('Anexos — Validação e Preview', () => {
  beforeEach(() => {
    cy.abrirDetalheDoChamado(1);
  });

  const selecionarAnexo = (caminho) =>
    cy.get('#chat-file').selectFile(`cypress/fixtures/anexos/${caminho}`, { force: true });

  it('extensão inválida (.exe) mostra toast de erro e limpa o input', () => {
    selecionarAnexo('arquivo-invalido.exe');

    cy.get('.toast-item').should('contain.text', 'Formato não permitido');
    cy.get('#chat-file').should('have.value', '');
    cy.get('#chat-anexo-preview').should('not.be.visible');
    cy.get('#chat-file-name').should('not.contain.text', '.exe');
  });

  it('arquivo maior que 2 MB mostra toast de erro e limpa o input', () => {
    selecionarAnexo('anexo-grande.png'); // 2.500.000 bytes

    cy.get('.toast-item').should('contain.text', 'Arquivo muito grande');
    cy.get('#chat-file').should('have.value', '');
    cy.get('#chat-anexo-preview').should('not.be.visible');
  });

  it('PDF válido: preview visível com nome e tamanho; "Remover" limpa', () => {
    selecionarAnexo('anexo-valido.pdf');

    cy.get('#chat-anexo-preview').should('be.visible');
    cy.get('#chat-anexo-nome').should('have.text', 'anexo-valido.pdf');
    cy.get('#chat-anexo-tamanho').should('contain.text', 'KB');
    cy.get('#chat-file-name').should('contain.text', 'anexo-valido.pdf');

    cy.get('#chat-anexo-remover').click();
    cy.get('#chat-anexo-preview').should('not.be.visible');
    cy.get('#chat-file').should('have.value', '');
  });

  it('imagem válida: thumbnail no preview e envio com anexo limpa tudo', () => {
    selecionarAnexo('imagem-valida.png');

    cy.get('#chat-anexo-preview').should('be.visible');
    cy.get('#chat-anexo-thumb img').should('be.visible'); // FileReader (assíncrono)

    cy.get('#chat-input').type('Segue a imagem do erro{enter}');
    cy.wait('@comentar').its('response.statusCode').should('eq', 200);

    cy.get('#chat-anexo-preview').should('not.be.visible');
    cy.get('#chat-input').should('have.value', '');
    cy.chatDeveEstarNoFim();
  });
});
