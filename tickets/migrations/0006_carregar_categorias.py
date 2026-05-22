from django.db import migrations

def carregar_categorias_iniciais(apps, schema_editor):
    Categoria = apps.get_model('tickets', 'Categoria')
    categorias = [
        {'nome': 'Infraestrutura', 'descricao': 'Problemas com rede, servidores ou hardware.'},
        {'nome': 'Software', 'descricao': 'Erros em sistemas, acessos ou aplicativos.'},
        {'nome': 'RH/Pessoal', 'descricao': 'Dúvidas sobre benefícios ou folha.'},
    ]
    
    for cat in categorias:
        Categoria.objects.get_or_create(nome=cat['nome'], defaults={'descricao': cat['descricao']})

class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_alter_ticket_status'), # Ajuste para a sua migração anterior
    ]

    operations = [
        migrations.RunPython(carregar_categorias_iniciais),
    ]