# tickets/admin.py

from django.contrib import admin

from django.utils.html import format_html

from .models import Ticket, Comentario, Categoria

 

@admin.register(Categoria)

class CategoriaAdmin(admin.ModelAdmin):

    list_display = ['nome', 'icone', 'ativa', 'total_tickets']

    list_editable = ['ativa']

    search_fields = ['nome']

    

    def total_tickets(self, obj):

        return obj.ticket_set.count()

    total_tickets.short_description = 'Total de Tickets'

 

 

class ComentarioInline(admin.TabularInline):

    model = Comentario

    extra = 0

    readonly_fields = ['autor', 'mensagem', 'criado_em']

    fields = ['autor', 'mensagem', 'interno', 'criado_em']

@admin.register(Ticket)

class TicketAdmin(admin.ModelAdmin):

    list_display = ['id', 'titulo', 'solicitante', 'tecnico_responsavel', 

                    'status_colored', 'prioridade_colored', 'criado_em']

    list_filter = ['status', 'prioridade', 'categoria', 'tecnico_responsavel']

    search_fields = ['titulo', 'descricao', 'solicitante__username']

    readonly_fields = ['criado_em', 'atualizado_em', 'resolvido_em']

    inlines = [ComentarioInline]

    

    fieldsets = (

        ('Informações do Chamado', {

            'fields': ('titulo', 'descricao', 'anexo')

        }),

        ('Classificação', {

            'fields': ('categoria', 'prioridade', 'status')

        }),

        ('Responsáveis', {

            'fields': ('solicitante', 'tecnico_responsavel')

        }),

        ('Datas', {

            'fields': ('criado_em', 'atualizado_em', 'resolvido_em'),

            'classes': ('collapse',)

        }),

    )

    

    actions = ['marcar_resolvido', 'atribuir_a_mim']

    

    def status_colored(self, obj):

        colors = {

            'aberto': 'orange',

            'em_andamento': 'blue',

            'aguardando': 'gray',

            'resolvido': 'green',

            'fechado': 'black',

        }

        return format_html(

            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),

            obj.get_status_display()

        )

    status_colored.short_description = 'Status'

    

    def prioridade_colored(self, obj):

        colors = {

            'baixa': 'gray',

            'media': 'blue',

            'alta': 'orange',

            'critica': 'red',

        }

        return format_html(

            '<span style="color: {}; font-weight: bold;">{}</span>',

            colors.get(obj.prioridade, 'gray'),

            obj.get_prioridade_display()

        )

    prioridade_colored.short_description = 'Prioridade'

    

    def marcar_resolvido(self, request, queryset):

        count = queryset.update(status='resolvido')

        self.message_user(request, f'{count} ticket(s) marcado(s) como resolvido.')

    marcar_resolvido.short_description = 'Marcar como resolvido'

    

    def atribuir_a_mim(self, request, queryset):

        count = queryset.update(tecnico_responsavel=request.user)

        self.message_user(request, f'{count} ticket(s) atribuído(s) a você.')

    atribuir_a_mim.short_description = 'Atribuir a mim'

 

 

@admin.register(Comentario)

class ComentarioAdmin(admin.ModelAdmin):

    list_display = ['ticket', 'autor', 'interno', 'criado_em']

    list_filter = ['interno', 'criado_em']

    search_fields = ['mensagem', 'ticket__titulo', 'autor__username']