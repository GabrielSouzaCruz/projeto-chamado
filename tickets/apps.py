# tickets/apps.py
"""
Configuração do app tickets.

Responsável por:
- Registrar o app no Django
- Configurar nome verbose para o admin
- Carregar signals quando o app estiver pronto
"""

from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """
    Configuração principal do app de Chamados.
    
    Esta classe é carregada automaticamente pelo Django quando o app
    é incluído em INSTALLED_APPS. O método ready() é executado uma
    vez, após o carregamento inicial do projeto.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'
    verbose_name = 'Chamados'
    
    def ready(self):
        """
        Executa quando o app está pronto para uso.
        
        Por que importar signals aqui?
        - Django só registra receivers após o import do módulo
        - Se não importar, os signals (pre_save, post_save) não funcionam
        - Este é o local oficial recomendado pela documentação Django
        
        O que é carregado:
        - tickets.signals: contém receivers para salvar status antigo
          antes de atualizar tickets (usado para detectar mudanças)
        """
        import tickets.signals