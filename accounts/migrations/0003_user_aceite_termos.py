from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_must_change_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='aceitou_termos',
            field=models.BooleanField(
                default=False,
                verbose_name='Aceitou os Termos de Uso e Política de Privacidade',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='data_aceite_termos',
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name='Data da aceitação dos Termos',
            ),
        ),
    ]
