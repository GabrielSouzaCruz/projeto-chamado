# accounts/admin.py
"""
Configuração do Django Admin para o modelo de usuário customizado.

Este módulo registra o modelo User no admin do Django com personalizações:
- Campos customizados visíveis (is_technician, departamento, telefone)
- Filtros para segmentação rápida de usuários
- Fieldsets organizados para melhor UX no admin

Importante: UserAdmin já traz configurações padrão para:
- username, password (com hash automático)
- Permissões (groups, user_permissions)
- Status (is_active, is_staff, is_superuser)
- Datas (date_joined, last_login)

Nós apenas estendemos com campos específicos do sistema de chamados.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin customizado para o modelo User com campos adicionais.
    
    Herda de UserAdmin para manter:
    - Hash automático de senhas
    - Interface padrão de permissões do Django
    - Filtros e buscas padrão
    
    Adiciona:
    - is_technician: Identifica técnicos de TI
    - departamento: Organização por área
    - telefone: Contato direto
    
    ⚠️ IMPORTANTE - is_technician vs is_staff:
    - is_technician: Acesso a funcionalidades do sistema de chamados
    - is_staff: Acesso ao /admin/ do Django
    - Um usuário pode ter um, ambos, ou nenhum
    
    Exemplos de uso no admin:
    - Filtrar por is_technician=True para ver todos os técnicos
    - Ativar/desativar técnicos em massa
    - Buscar por departamento para organização
    """
    
    # =========================================================================
    # LISTA DE USUÁRIOS (list_display)
    # =========================================================================
    
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_technician',  # ← Campo customizado
        'is_staff',       # ← Acesso ao admin Django
        'is_active',      # ← Usuário ativo/inativo
    ]
    """
    Colunas exibidas na listagem de usuários.
    
    Por que estas colunas?
    - username: Identificador único
    - email: Contato principal
    - first_name, last_name: Nome completo
    - is_technician: Quem pode atender tickets
    - is_staff: Quem acessa o admin Django
    - is_active: Quem pode logar no sistema
    
    ⚠️ Evite adicionar muitas colunas (performance)
    Cada coluna extra = mais dados carregados = lista mais lenta
    """
    
    # =========================================================================
    # FILTROS LATERAIS (list_filter)
    # =========================================================================
    
    list_filter = [
        'is_technician',  # Filtrar técnicos vs não-técnicos
        'is_staff',       # Filtrar staff vs não-staff
        'is_active',      # Filtrar ativos vs inativos
        'groups',         # Filtrar por grupos de permissão
    ]
    """
    Filtros exibidos na barra lateral do admin.
    
    Uso prático:
    1. Clique em "is_technician" → "Yes" → Vê apenas técnicos
    2. Clique em "is_active" → "No" → Vê usuários inativos
    3. Clique em "groups" → Seleciona grupo → Filtra por grupo
    
    ⚠️ list_filter usa lookup exato, não busca textual
    Para busca textual, use search_fields
    """
    
    # =========================================================================
    # CAMPOS DE EDIÇÃO (fieldsets)
    # =========================================================================
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {
            'fields': ('is_technician', 'departamento', 'telefone'),
            'description': 'Campos específicos do sistema de chamados'
        }),
    )
    """
    Campos exibidos ao EDITAR um usuário existente.
    
    Estrutura:
    - UserAdmin.fieldsets: Campos padrão do Django (username, senha, permissões, etc.)
    - + Nosso tuple: Adiciona nova seção com campos customizados
    
    Seções padrão do UserAdmin (herdadas):
    1. 'Personal info': first_name, last_name, email
    2. 'Permissions': groups, user_permissions
    3. 'Important dates': last_login, date_joined
    
    Nossa seção adicional:
    4. 'Informações Adicionais': is_technician, departamento, telefone
    
    ⚠️ A ordem importa! Nossa seção aparece POR ÚLTIMO
    """
    
    # =========================================================================
    # CAMPOS DE CRIAÇÃO (add_fieldsets)
    # =========================================================================
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('is_technician', 'departamento', 'telefone'),
            'description': 'Campos específicos do sistema de chamados'
        }),
    )
    """
    Campos exibidos ao CRIAR um novo usuário.
    
    Diferença para fieldsets:
    - add_fieldsets: Usado na criação (não tem senha ainda)
    - fieldsets: Usado na edição (já tem senha, pode mudar)
    
    Por que separar?
    - Na criação, Django pede password1 + password2
    - Na edição, Django mostra campo de senha opcional (não obriga mudar)
    
    ⚠️ Se não definir add_fieldsets, Django usa fieldsets para ambos
    Mas é melhor definir explicitamente para clareza
    """
    
    # =========================================================================
    # BUSCA (search_fields)
    # =========================================================================
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    """
    Campos pesquisáveis na barra de busca do admin.
    
    Uso:
    - Digite "joao" → Busca em username, email, first_name, last_name
    - Busca é case-insensitive e parcial (icontains)
    
    ⚠️ Não inclua campos não-textuais aqui:
    - is_technician: Booleano (use list_filter)
    - departamento: CharField (pode incluir se quiser buscar por texto)
    """
    
    # =========================================================================
    # ORDENAÇÃO (ordering)
    # =========================================================================
    
    ordering = ['username']
    """
    Ordenação padrão da listagem de usuários.
    
    Opções comuns:
    - ['username']: Ordena alfabeticamente por username
    - ['-date_joined']: Mais recentes primeiro
    - ['last_name', 'first_name']: Por nome completo
    
    ⚠️ A ordenação pode ser sobrescrita pelo usuário clicando nos headers
    """