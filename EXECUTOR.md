# EXECUTOR — Guia de Execução Local

## Já feito

- Ambiente virtual Python em `.venv/`
- Dependências instaladas (`requirements.txt`)
- Migrations aplicadas
- Banco E2E em `e2e.sqlite3` (populado por `seed_e2e`)
- Node + Cypress instalados (`node_modules/`)
- Configurações Django: `config/settings.py`, `config/e2e_settings.py`, `config/test_settings.py`
- Sincronização com `origin/main` concluída (merge commit `1ed06e5`)

## Testes unitários Django

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
```

Resultado esperado: **178 OK, 0 erros, 0 falhas**

## Testes E2E (Cypress) — runner único

Use **sempre** o script `scripts/e2e.ps1`. Ele:

1. Libera a porta 8000 (mata processos residuais)
2. Roda `seed_e2e` para garantir fixtures limpas
3. Sobe `runserver` com `e2e_settings` em background
4. Aguarda `/accounts/login/` responder 200 (timeout 60 s)
5. Executa `npx.cmd cypress run` repassando argumentos extras
6. Encerra o servidor em `try/finally`
7. Devolve o exit code do Cypress

### Execução completa

```powershell
.\scripts\e2e.ps1
```

### Filtrar um spec

```powershell
.\scripts\e2e.ps1 --spec cypress/e2e/login.cy.js
```

### Resultado esperado

```
14 specs, 49 tests, 0 failures, 0 pending
```

## Já feito (tarefa mais recente)

Badge do sino via OOB no polling — commit `167ca8d`. O badge `#sino-badge` (com `hx-swap-oob="true"`) é injetado nas respostas 200 dos endpoints de polling (dashboard, fila, comentários). Resposta 204 continua sem corpo. O sino não tem `hx-trigger`, timer ou fetch próprio.

Correções pós-revisão: `e2e.ps1` usa `$ErrorActionPreference = 'Continue'`; `sino_badge.cy.js` usa polling real (intercept após visit, `cy.wait` com timeout 20 s); `ticket_detail.js` restaura scroll inicial ao fundo (`chatBox.scrollTop = chatBox.scrollHeight`) que havia sido removido no refactor `4df1ff7`.
