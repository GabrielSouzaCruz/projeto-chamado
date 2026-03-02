# tickets/apps.py

from django.apps import AppConfig

 

class TicketsConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'

    name = 'tickets'

    verbose_name = 'Chamados'

    

    def ready(self):

        # Importa signals para registrá-los

        import tickets.signals