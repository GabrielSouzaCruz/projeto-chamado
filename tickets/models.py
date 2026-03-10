# tickets/models.py
"""
Modelos do sistema de chamados.

Estrutura:
- Categoria: Classificação dos tickets
- Ticket: Chamado principal
- Comentario: Interações nos tickets
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    """
    Categoria para classificação dos chamados.
    
    Usada para organizar tickets por tipo de problema
    (Hardware, Software, Rede, etc.) e facilitar filtros.
    """
    nome = models.CharField(max_length=100, verbose_name='Nome')
    icone = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name='Ícone (classe FontAwesome)',
        help_text='Ex: fa-desktop, fa-network-wired, fa-print'
    )
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativa = models.BooleanField(default=True, verbose_name='Ativa')
    
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome


class Ticket(models.Model):
    """
    Modelo principal de chamado de suporte.
    """
    
    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Aberto'
        EM_ANDAMENTO = 'em_andamento', 'Em Andamento'
        AGUARDANDO = 'aguardando', 'Aguardando Resposta'
        RESOLVIDO = 'resolvido', 'Resolvido'
        FECHADO = 'fechado', 'Fechado'
        CANCELADO = 'cancelado', 'Cancelado'
    
    class Prioridade(models.TextChoices):
        BAIXA = 'baixa', 'Baixa'
        MEDIA = 'media', 'Média'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'
    
    titulo = models.CharField(max_length=200, verbose_name='Título')
    descricao = models.TextField(verbose_name='Descrição do Problema')
    
    # Relacionamentos
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_solicitados',
        verbose_name='Solicitante'
    )
    
    tecnico_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_atendidos',
        verbose_name='Técnico Responsável'
    )
    
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Categoria'
    )
    
    # Metadados com db_index=True para performance em filtros e buscas
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTO,
        verbose_name='Status',
        db_index=True  # 🔥 Otimiza filtros de Status na Fila Admin
    )
    
    prioridade = models.CharField(
        max_length=20,
        choices=Prioridade.choices,
        default=Prioridade.MEDIA,
        verbose_name='Prioridade',
        db_index=True  # 🔥 Otimiza filtros de Prioridade e Ordenação
    )
    
    anexo = models.FileField(
        upload_to='tickets/anexos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Anexo'
    )
    
    # Timestamps
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em', db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    resolvido_em = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Resolvido em'
    )
    
    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f'#{self.pk} - {self.titulo}'
    
    def save(self, *args, **kwargs):
        if self.status == self.Status.RESOLVIDO and not self.resolvido_em:
            self.resolvido_em = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def status_css_class(self):
        classes = {
            self.Status.ABERTO: 'bg-warning text-dark',
            self.Status.EM_ANDAMENTO: 'bg-info text-white',
            self.Status.AGUARDANDO: 'bg-secondary text-white',
            self.Status.RESOLVIDO: 'bg-success text-white',
            self.Status.FECHADO: 'bg-dark text-white',
            self.Status.CANCELADO: 'bg-danger text-white',
        }
        return classes.get(self.status, 'bg-secondary text-white')
    
    @property
    def prioridade_css_class(self):
        classes = {
            self.Prioridade.BAIXA: 'badge-priority-baixa',
            self.Prioridade.MEDIA: 'badge-priority-normal',
            self.Prioridade.ALTA: 'badge-priority-alta',
            self.Prioridade.CRITICA: 'badge-priority-critica',
        }
        return classes.get(self.prioridade, 'badge-priority-baixa')
    
    def cancelar(self):
        self.status = self.Status.CANCELADO
        self.save()
    
    def assumir(self, tecnico):
        self.tecnico_responsavel = tecnico
        if self.status == self.Status.ABERTO:
            self.status = self.Status.EM_ANDAMENTO
        self.save()


class Comentario(models.Model):
    """
    Comentários em tickets.
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name='Ticket'
    )
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Autor'
    )
    
    # 🔥 GRAU AQUI: null=True, blank=True para permitir envio só com anexo (sem dar erro)
    mensagem = models.TextField(
        verbose_name='Mensagem', 
        null=True, 
        blank=True
    )
    
    interno = models.BooleanField(
        default=False,
        verbose_name='Comentário Interno',
        help_text='Se marcado, visível apenas para técnicos'
    )
    
    anexo = models.FileField(
        upload_to='tickets/comentarios/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Anexo'
    )
    
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    
    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ['criado_em']
    
    def __str__(self):
        return f'Comentário de {self.autor} em {self.ticket}'