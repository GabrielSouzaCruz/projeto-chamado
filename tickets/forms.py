# tickets/forms.py
"""
Formulários do app tickets.

Responsáveis por:
- Validação de dados de entrada
- Renderização de widgets Bootstrap
- Regras de negócio específicas de formulário
"""

from django import forms

from accounts.models import User
from .models import Ticket, Comentario, Categoria


class TicketForm(forms.ModelForm):
    """
    Formulário para criação e edição de tickets.
    
    Validações incluídas:
    - Apenas categorias ativas são exibidas
    - Anexo: tipo e tamanho limitados (5MB)
    - Widgets Bootstrap para consistência visual
    """
    
    class Meta:
        model = Ticket
        fields = ['titulo', 'descricao', 'categoria', 'prioridade', 'anexo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descreva brevemente o problema'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Detalhe o problema, incluindo mensagens de erro, quando ocorre, etc.'
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário filtrando apenas categorias ativas.
        
        Por que filtrar aqui?
        - Evita que categorias desativadas apareçam no dropdown
        - Mantém dados históricos (tickets antigos podem ter categoria inativa)
        - Centraliza a lógica de exibição no formulário, não na view
        """
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(ativa=True)
    
    def clean_anexo(self):
        """
        Valida o arquivo de anexo: tipo e tamanho.
        
        Regras de negócio:
        - Apenas formatos comuns de documento/imagem são permitidos
        - Limite de 5MB para evitar sobrecarga no servidor/storage
        - Validação no formulário + validação no servidor (defesa em profundidade)
        """
        anexo = self.cleaned_data.get('anexo')
        
        if anexo:
            ext = anexo.name.split('.')[-1].lower()
            permitidos = ['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx']
            
            if ext not in permitidos:
                raise forms.ValidationError(
                    f'Tipo de arquivo não permitido. Use: {", ".join(permitidos)}'
                )
            
            if anexo.size > 5 * 1024 * 1024:  # 5MB em bytes
                raise forms.ValidationError('O arquivo não pode exceder 5MB.')
        
        return anexo


class ComentarioForm(forms.ModelForm):
    """
    Formulário para adicionar comentários em tickets.
    
    Recursos:
    - Campo 'interno' oculto para usuários não-técnicos (segurança)
    - Widget de texto com placeholder orientativo
    - Suporte a anexos opcionais
    """
    
    class Meta:
        model = Comentario
        fields = ['mensagem', 'interno', 'anexo']
        widgets = {
            'mensagem': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite seu comentário...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário com controle de acesso ao campo 'interno'.
        
        Regra de segurança:
        - Apenas técnicos podem marcar comentários como internos
        - Para usuários comuns, o campo é escondido e forçado como False
        - Prevenção contra manipulação via frontend: validar também no save()
        
        Args:
            usuario: Instância do usuário (passada via kwargs na view)
        """
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Esconde campo 'interno' para não-técnicos
        if self.usuario and not self.usuario.is_technician:
            self.fields['interno'].widget = forms.HiddenInput()
            self.fields['interno'].initial = False


class TicketStatusForm(forms.ModelForm):
    """
    Formulário para técnicos alterarem status, prioridade e responsável.
    
    Usado exclusivamente na view de detalhe do ticket por usuários com
    permissão de técnico. Não expõe campos sensíveis como descrição ou anexo.
    """
    
    class Meta:
        model = Ticket
        fields = ['status', 'tecnico_responsavel', 'prioridade']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tecnico_responsavel': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Inicializa o formulário filtrando apenas técnicos ativos.
        
        Por que filtrar aqui?
        - Evita que usuários inativos/ex-funcionários apareçam na seleção
        - Mantém a integridade da atribuição de tickets
        - Centraliza a lógica de filtragem no formulário
        """
        super().__init__(*args, **kwargs)
        self.fields['tecnico_responsavel'].queryset = User.objects.filter(
            is_technician=True, 
            is_active=True
        )