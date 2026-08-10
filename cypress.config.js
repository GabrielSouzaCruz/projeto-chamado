const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    // Servidor Django em execução: python manage.py runserver
    baseUrl: 'http://127.0.0.1:8000',

    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',

    // Padrão: Desktop. Os specs de mobile trocam via cy.viewport('iphone-12').
    viewportWidth: 1920,
    viewportHeight: 1080,

    defaultCommandTimeout: 10000,
    requestTimeout: 10000,

    // Reexecuta testes "flaky" 1x no modo headless (CI); no modo interativo, 0.
    retries: {
      runMode: 1,
      openMode: 0,
    },

    video: false,
    screenshotOnRunFailure: true,

    env: {
      // Credenciais criadas por: python manage.py seed_e2e
      E2E_TECNICO_USER: 'qa_tecnico',
      E2E_TECNICO_PASS: 'qa-senha-123',
      E2E_SOLICITANTE_USER: 'qa_solicitante',
      E2E_SOLICITANTE_PASS: 'qa-senha-123',
    },
  },
});
