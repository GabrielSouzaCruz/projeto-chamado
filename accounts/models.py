# accounts/models.py
"""
Modelo de usuário customizado do sistema.

Este módulo define o modelo User que estende AbstractUser do Django,
adicionando campos específicos para o sistema de chamados:
- is_technician: Identifica técnicos de TI (controle de acesso)
- departamento: Organização por área da empresa
- telefone: Contato para comunicação

Por que AbstractUser e não AbstractBaseUser?
- AbstractUser já traz campos padrão (username, email, password, etc.)
- Menos código para manter
- Suficiente para sistemas internos/empresariais
- Se precisar de campos muito customizados, considere AbstractBaseUser

Importante: AUTH_USER_MODEL deve ser definido ANTES das migrations!
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modelo de usuário customizado para o sistema de chamados.
    
    Campos herdados do AbstractUser:
    - username, email, password (autenticação)
    - first_name, last_name (identificação)
    - is_active, is_staff, is_superuser (permissões)
    - date_joined, last_login (auditoria)
    
    Campos adicionais:
    - is_technician: Controle de acesso a funcionalidades de técnico
    - departamento: Organização interna
    - telefone: Contato direto
    """
    
    # =========================================================================
    # CAMPOS CUSTOMIZADOS
    # =========================================================================
    
    is_technician = models.BooleanField(
        default=False,
        verbose_name='É Técnico de TI',
        help_text='Marque se este usuário é um técnico de suporte'
    )
    """
    ⚠️ SEGURANÇA: Este campo controla acesso a funcionalidades críticas:
    - Ver todos os tickets (não apenas os próprios)
    - Assumir tickets da fila
    - Alterar status de tickets
    - Ver comentários internos
    - Acessar Fila Admin
    
    Como usar em views:
    if request.user.is_technician:
        # Acesso permitido
        pass
    
    Como usar em templates:
    {% if user.is_technician %}
        <!-- Conteúdo para técnicos -->
    {% endif %}
    """
    
    departamento = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Departamento'
    )
    """
    Campo opcional para organização interna.
    Exemplos: 'TI', 'RH', 'Financeiro', 'Operações'
    
    Uso: Filtrar tickets por departamento do solicitante,
    identificar padrões de demanda por área.
    """
    
    telefone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name='Telefone'
    )
    """
    Campo opcional para contato direto.
    Formato livre (permite ramais, celulares, etc.)
    
    Uso: Técnicos podem contatar solicitante para
    esclarecimentos rápidos sobre o ticket.
    """
    
    # =========================================================================
    # META CONFIGURATION
    # =========================================================================
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['username']  # Ordenação padrão nas listagens
    
    # =========================================================================
    # REPRESENTAÇÃO EM STRING
    # =========================================================================
    
    def __str__(self):
        """
        Retorna nome completo se disponível, caso contrário username.
        
        Exemplos:
        - 'João Silva' (se first_name + last_name preenchidos)
        - 'joao.silva' (se nome completo vazio)
        
        Usado em:
        - Admin do Django
        - Dropdowns de seleção
        - Logs e mensagens
        """
        return f'{self.get_full_name() or self.username}'
    
    # =========================================================================
    # PROPRIEDADES E MÉTODOS AUXILIARES
    # =========================================================================
    
    @property
    def nome_completo(self):
        """
        Retorna nome completo formatado para exibição.
        
        Alias para get_full_name() com fallback para username.
        Útil em templates onde se quer consistência de nomenclatura.
        
        Exemplo no template:
        {{ user.nome_completo }}
        
        Por que ter esta propriedade se já existe get_full_name()?
        - get_full_name() pode retornar string vazia
        - nome_completo sempre retorna algo (fallback para username)
        - Nome mais intuitivo para desenvolvedores brasileiros
        """
        return self.get_full_name() or self.username
    
    # =========================================================================
    # MÉTODOS DE PERMISSÃO (OPCIONAIS - PARA FUTURO)
    # =========================================================================
    
    def pode_assumir_tickets(self):
        """
        Verifica se usuário pode assumir tickets da fila.
        
        Retorna:
            bool: True se for técnico e ativo
        """
        return self.is_technician and self.is_active
    
    def pode_ver_todos_tickets(self):
        """
        Verifica se usuário pode ver todos os tickets (não apenas os próprios).
        
        Retorna:
            bool: True se for técnico ou superuser
        """
        return self.is_technician or self.is_superuser
    
    def pode_acessar_fila_admin(self):
        """
        Verifica se usuário pode acessar a Fila Admin.
        
        Retorna:
            bool: True se for superuser (admin do Django)
        """
        return self.is_superuser