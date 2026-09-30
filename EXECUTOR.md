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

Resultado esperado: **176 OK, 0 erros, 0 falhas**

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
13 specs, 47 tests, 0 failures, 0 pending
```

## Tarefa atual

Criar e validar `scripts/e2e.ps1` como runner único do Cypress — **concluído** (commit pendente de push).
