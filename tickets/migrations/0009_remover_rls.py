"""
Remove o RLS criado pela migration 0008 (row_level_security).

A 0008 criava policies baseadas em current_setting('app.current_user_id'),
uma variavel que NUNCA e definida pela aplicacao — no Postgres a variavel
inexistente fazia toda consulta falhar ou retornar vazio, ou seja, um RLS
falso/broken. Este commit remove as policies e desativa o RLS.

So executa em PostgreSQL — ignorada em SQLite (testes).
Reverse e intencionalmente vazio (noop): nao recriamos o RLS quebrado.
"""
from django.db import migrations


def remover_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    sql = """
DROP POLICY IF EXISTS ticket_staff_bypass ON tickets_ticket;
DROP POLICY IF EXISTS ticket_tecnico_access ON tickets_ticket;
DROP POLICY IF EXISTS ticket_solicitante_isolation ON tickets_ticket;
ALTER TABLE tickets_ticket DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS comentario_staff_bypass ON tickets_comentario;
DROP POLICY IF EXISTS comentario_autor_isolation ON tickets_comentario;
ALTER TABLE tickets_comentario DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_isolation ON accounts_user;
ALTER TABLE accounts_user DISABLE ROW LEVEL SECURITY;
"""
    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_row_level_security'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remover_rls, migrations.RunPython.noop),
    ]
