"""
Row Level Security (RLS) para tabelas sensiveis.

ATENCAO: Esta migration requer privilegios de SUPERUSER no PostgreSQL.
No Neon, execute manualmente como superuser ou via migration hook.

So executa em PostgreSQL — ignorada em SQLite (testes).

Tabelas protegidas:
  - accounts_user: usuario so ve seu proprio registro
  - tickets_ticket: solicitante so ve seus tickets; tecnico ve tickets atribuidos
  - tickets_comentario: autor so ve seus comentarios
"""
from django.db import migrations


def forwards_rlps(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    sql = """
ALTER TABLE accounts_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts_user FORCE ROW LEVEL SECURITY;
CREATE POLICY user_isolation ON accounts_user
    USING (id = current_setting('app.current_user_id')::int);

ALTER TABLE tickets_ticket ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets_ticket FORCE ROW LEVEL SECURITY;
CREATE POLICY ticket_solicitante_isolation ON tickets_ticket
    USING (solicitante_id = current_setting('app.current_user_id')::int);
CREATE POLICY ticket_tecnico_access ON tickets_ticket
    USING (tecnico_responsavel_id = current_setting('app.current_user_id')::int);
CREATE POLICY ticket_staff_bypass ON tickets_ticket
    USING (current_setting('app.current_user_is_staff', true)::boolean = true);

ALTER TABLE tickets_comentario ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets_comentario FORCE ROW LEVEL SECURITY;
CREATE POLICY comentario_autor_isolation ON tickets_comentario
    USING (autor_id = current_setting('app.current_user_id')::int);
CREATE POLICY comentario_staff_bypass ON tickets_comentario
    USING (current_setting('app.current_user_is_staff', true)::boolean = true);
"""
    schema_editor.execute(sql)


def reverse_rlps(apps, schema_editor):
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
        ('tickets', '0007_pushsubscription'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards_rlps, reverse_rlps),
    ]
