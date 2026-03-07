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
    
    Representa um ticket aberto por um solicitante, com status,
    prioridade, categoria e possível técnico responsável.
    """
    
    class Status(models.TextChoices):
        """Estados possíveis do ciclo de vida do ticket."""
        ABERTO = 'aberto', 'Aberto'
        EM_ANDAMENTO = 'em_andamento', 'Em Andamento'
        AGUARDANDO = 'aguardando', 'Aguardando Resposta'
        RESOLVIDO = 'resolvido', 'Resolvido'
        FECHADO = 'fechado', 'Fechado'
        CANCELADO = 'cancelado', 'Cancelado'
    
    class Prioridade(models.TextChoices):
        """Níveis de urgência para priorização da fila."""
        BAIXA = 'baixa', 'Baixa'
        MEDIA = 'media', 'Média'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'
    
    # === Dados do Ticket ===
    titulo = models.CharField(max_length=200, verbose_name='Título')
    descricao = models.TextField(verbose_name='Descrição do Problema')
    
    # === Relacionamentos ===
    # CASCADE: se o usuário for deletado, seus tickets também são (histórico preservado via logs)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_solicitados',  # Permite: user.tickets_solicitados.all()
        verbose_name='Solicitante'
    )
    
    # SET_NULL: se o técnico for deletado, o ticket permanece sem responsável (não é perdido)
    tecnico_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_atendidos',  # Permite: tecnico.tickets_atendidos.all()
        verbose_name='Técnico Responsável'
    )
    
    # SET_NULL: categoria pode ser removida sem afetar tickets históricos
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Categoria'
    )
    
    # === Metadados ===
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ABERTO,
        verbose_name='Status'
    )
    
    prioridade = models.CharField(
        max_length=20,
        choices=Prioridade.choices,
        default=Prioridade.MEDIA,
        verbose_name='Prioridade'
    )
    
    anexo = models.FileField(
        upload_to='tickets/anexos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Anexo'
    )
    
    # === Timestamps ===
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    resolvido_em = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Resolvido em'
    )
    
    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-criado_em']  # Mais recentes primeiro
    
    def __str__(self):
        return f'#{self.pk} - {self.titulo}'
    
    def save(self, *args, **kwargs):
        """
        Override do save para registrar automaticamente a data de resolução.
        
        Quando o status muda para RESOLVIDO e resolvido_em ainda é None,
        preenchemos com o timestamp atual. Isso garante métricas precisas
        de tempo de resolução sem depender de lógica externa.
        """
        if self.status == self.Status.RESOLVIDO and not self.resolvido_em:
            self.resolvido_em = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def status_css_class(self):
        """
        Retorna classe CSS Bootstrap para estilização visual do status.
        
        Usado nos templates para badges coloridas:
        - Aberto: amarelo (bg-warning)
        - Em andamento: azul (bg-info)
        - Resolvido: verde (bg-success)
        - Cancelado: vermelho (bg-danger)
        """
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
        """
        Retorna classe CSS customizada para estilização da prioridade.
        
        As classes são definidas em base.html:
        - badge-priority-baixa: cinza
        - badge-priority-media: azul claro
        - badge-priority-alta: laranja
        - badge-priority-critica: vermelho
        """
        classes = {
            self.Prioridade.BAIXA: 'badge-priority-baixa',
            self.Prioridade.MEDIA: 'badge-priority-media',
            self.Prioridade.ALTA: 'badge-priority-alta',
            self.Prioridade.CRITICA: 'badge-priority-critica',
        }
        return classes.get(self.prioridade, 'badge-priority-baixa')
    
    def cancelar(self):
        """
        Método auxiliar para cancelar o ticket com validação embutida.
        
        Uso: ticket.cancelar() em vez de manipular status diretamente.
        Facilita testes e mantém a lógica de negócio centralizada.
        """
        self.status = self.Status.CANCELADO
        self.save()
    
    def assumir(self, tecnico):
        """
        Método auxiliar para técnico assumir o ticket.
        
        - Atribui o técnico responsável
        - Se estiver ABERTO, muda automaticamente para EM_ANDAMENTO
        - Facilita a lógica nas views sem repetir código
        
        Args:
            tecnico: Instância do usuário técnico
        """
        self.tecnico_responsavel = tecnico
        if self.status == self.Status.ABERTO:
            self.status = self.Status.EM_ANDAMENTO
        self.save()


class Comentario(models.Model):
    """
    Comentários em tickets para comunicação entre solicitante e técnico.
    
    Recursos:
    - Comentários públicos (visíveis a todos) ou internos (só técnicos)
    - Anexos opcionais para evidências
    - Timestamp automático de criação
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,  # Comentário não faz sentido sem ticket
        related_name='comentarios',  # Permite: ticket.comentarios.all()
        verbose_name='Ticket'
    )
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Autor'
    )
    
    mensagem = models.TextField(verbose_name='Mensagem')
    
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
        ordering = ['criado_em']  # Mais antigos primeiro (linha do tempo)
    
    def __str__(self):
        return f'Comentário de {self.autor} em {self.ticket}'