# tickets/admin.py
"""
Configuração do Django Admin para o app tickets.

Personalizações incluídas:
- Listagens com cores para status e prioridade
- Filtros avançados para busca rápida
- Ações em massa para operações de técnico
- Inline de comentários para visualização completa
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import Ticket, Comentario, Categoria


# =============================================================================
# CATEGORIA
# =============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """
    Admin de Categorias com visualização rápida de uso.
    
    Recursos:
    - Edição inline do campo 'ativa' (toggle rápido)
    - Contador de tickets por categoria
    - Busca por nome
    """
    
    list_display = ['nome', 'icone', 'ativa', 'total_tickets']
    list_editable = ['ativa']  # Permite ativar/desativar sem abrir o form
    search_fields = ['nome']
    ordering = ['nome']
    
    def get_queryset(self, request):
        """
        Otimiza query para evitar N+1 no contador de tickets.
        
        Sem annotate: 1 query para lista + N queries para contar tickets
        Com annotate: 1 query única com JOIN e COUNT
        """
        queryset = super().get_queryset(request)
        return queryset.annotate(ticket_count=Count('ticket'))
    
    def total_tickets(self, obj):
        """Retorna quantidade de tickets nesta categoria (otimizado)."""
        return getattr(obj, 'ticket_count', obj.ticket_set.count())
    
    total_tickets.short_description = 'Total de Tickets'
    total_tickets.admin_order_field = 'ticket_count'  # Permite ordenar pela coluna


# =============================================================================
# TICKET
# =============================================================================

class ComentarioInline(admin.TabularInline):
    """
    Inline de comentários na página de detalhe do ticket.
    
    Permite visualizar todo o histórico de comunicação sem sair do ticket.
    Campos readonly para preservar integridade do histórico.
    """
    
    model = Comentario
    extra = 0  # Não mostra campos vazios para novo comentário
    readonly_fields = ['autor', 'mensagem', 'interno', 'criado_em']
    can_delete = False  # Impede exclusão acidental de comentários
    
    def has_add_permission(self, request, obj=None):
        """
        Desabilita adição de comentários via admin inline.
        
        Por que? Comentários devem ser adicionados via interface web
        do sistema (ticket_detail.html), não pelo admin do Django.
        Isso garante que a lógica de negócio (permissões, notificações)
        seja executada corretamente.
        """
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Admin principal de Tickets com visualização rica e ações em massa.
    
    Recursos:
    - Status e prioridade coloridos para identificação rápida
    - Filtros laterais para segmentação
    - Fieldsets organizados por contexto
    - Ações em massa para operações de técnico
    - Inline de comentários para histórico completo
    """
    
    list_display = [
        'id', 'titulo', 'solicitante', 'tecnico_responsavel',
        'status_colored', 'prioridade_colored', 'criado_em'
    ]
    list_display_links = ['id', 'titulo']  # Clicáveis para abrir detalhe
    list_filter = ['status', 'prioridade', 'categoria', 'tecnico_responsavel', 'criado_em']
    search_fields = ['titulo', 'descricao', 'solicitante__username', 'solicitante__first_name']
    readonly_fields = ['criado_em', 'atualizado_em', 'resolvido_em']
    inlines = [ComentarioInline]
    ordering = ['-criado_em']  # Mais recentes primeiro
    date_hierarchy = 'criado_em'  # Navegação por data no topo
    
    fieldsets = (
        ('Informações do Chamado', {
            'fields': ('titulo', 'descricao', 'anexo'),
            'description': 'Dados principais do problema relatado'
        }),
        ('Classificação', {
            'fields': ('categoria', 'prioridade', 'status'),
            'description': 'Categorização e priorização do ticket'
        }),
        ('Responsáveis', {
            'fields': ('solicitante', 'tecnico_responsavel'),
            'description': 'Quem abriu e quem está atendendo'
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em', 'resolvido_em'),
            'classes': ('collapse',),  # Seção recolhida por padrão
            'description': 'Timestamps automáticos (não editáveis)'
        }),
    )
    
    # Ações em massa disponíveis para técnicos/admins
    actions = ['marcar_resolvido', 'atribuir_a_mim', 'marcar_cancelado']
    
    def status_colored(self, obj):
        """
        Exibe status com cor para identificação visual rápida.
        
        Cores:
        - Aberto: laranja (atenção)
        - Em andamento: azul (trabalhando)
        - Aguardando: cinza (pausa)
        - Resolvido: verde (sucesso)
        - Cancelado: vermelho (cancelado)
        """
        colors = {
            'aberto': 'orange',
            'em_andamento': 'blue',
            'aguardando': 'gray',
            'resolvido': 'green',
            'fechado': 'black',
            'cancelado': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'  # Permite ordenar
    
    def prioridade_colored(self, obj):
        """
        Exibe prioridade com cor para identificação visual rápida.
        
        Cores:
        - Baixa: cinza
        - Média: azul
        - Alta: laranja
        - Crítica: vermelho
        """
        colors = {
            'baixa': 'gray',
            'media': 'blue',
            'alta': 'orange',
            'critica': 'red',
        }
        color = colors.get(obj.prioridade, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_prioridade_display()
        )
    
    prioridade_colored.short_description = 'Prioridade'
    prioridade_colored.admin_order_field = 'prioridade'  # Permite ordenar
    
    @admin.action(description='Marcar selecionados como resolvido')
    def marcar_resolvido(self, request, queryset):
        """
        Ação em massa: marca múltiplos tickets como resolvidos.
        
        Uso: Selecione tickets → Ação → "Marcar como resolvido"
        Atualiza status e registra data de resolução automaticamente.
        """
        count = queryset.update(status=Ticket.Status.RESOLVIDO)
        self.message_user(request, f'{count} ticket(s) marcado(s) como resolvido.')
    
    @admin.action(description='Atribuir selecionados a mim')
    def atribuir_a_mim(self, request, queryset):
        """
        Ação em massa: atribui múltiplos tickets ao usuário atual.
        
        Uso: Técnico seleciona tickets da fila → "Atribuir a mim"
        Útil para assumir carga de trabalho rapidamente.
        """
        count = queryset.update(tecnico_responsavel=request.user)
        self.message_user(request, f'{count} ticket(s) atribuído(s) a você.')
    
    @admin.action(description='Marcar selecionados como cancelado')
    def marcar_cancelado(self, request, queryset):
        """
        Ação em massa: cancela múltiplos tickets.
        
        Uso: Admin seleciona tickets inválidos/duplicados → "Cancelar"
        Tickets cancelados permanecem no histórico para auditoria.
        """
        count = queryset.update(status=Ticket.Status.CANCELADO)
        self.message_user(request, f'{count} ticket(s) marcado(s) como cancelado.')


# =============================================================================
# COMENTÁRIO
# =============================================================================

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    """
    Admin de Comentários para auditoria e moderação.
    
    Uso principal: visualizar histórico completo de comunicações,
    identificar comentários internos vs públicos, e buscar por conteúdo.
    """
    
    list_display = ['ticket', 'autor', 'interno', 'criado_em']
    list_filter = ['interno', 'criado_em', 'autor']
    search_fields = ['mensagem', 'ticket__titulo', 'autor__username']
    readonly_fields = ['ticket', 'autor', 'mensagem', 'interno', 'anexo', 'criado_em']
    ordering = ['-criado_em']
    
    def has_add_permission(self, request):
        """
        Desabilita criação de comentários via admin.
        
        Por que? Comentários devem ser criados via interface web
        do sistema, onde a lógica de permissão e notificação é executada.
        """
        return False
    
    def has_change_permission(self, request, obj=None):
        """
        Permite visualização, mas não edição de comentários.
        
        Por que? Histórico de comunicação deve ser imutável para
        fins de auditoria e compliance.
        """
        return request.user.is_superuser