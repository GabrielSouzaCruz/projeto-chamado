# AGENTS.md

## REGRA PERMANENTE — leia antes de tudo.

Ao terminar QUALQUER tarefa, sua resposta final deve ser SOMENTE este bloco, com exatamente estas 5 linhas, nada antes nem depois:

STATUS: OK | FALHOU | PARCIAL
O QUE FOI FEITO: <1-2 frases>
ARQUIVOS ALTERADOS: <caminhos separados por vírgula>
TESTADO?: sim/não + comando e resultado (ex: "sim, manage.py test → 118 OK")
PENDÊNCIAS: <itens ou "nenhuma">

Proibido: listas explicativas, trechos de código, cabeçalhos, emojis, descrição teste a teste. Se algo precisa de decisão, vai em PENDÊNCIAS em uma linha.

Exemplo correto:

STATUS: OK
O QUE FOI FEITO: Middleware força troca de senha; AJAX recebe 403 JSON.
ARQUIVOS ALTERADOS: accounts/middleware.py, config/settings.py, accounts/tests.py
TESTADO?: sim, manage.py test --settings=config.test_settings → 118 OK
PENDÊNCIAS: nenhuma

## Comando de teste

- `python manage.py test --settings=config.test_settings`

## Regras do repositório

- Não alterar `requirements.txt` sem pedido explícito.
