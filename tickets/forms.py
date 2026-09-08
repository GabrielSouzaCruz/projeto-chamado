# tickets/forms.py
import magic
from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User
from .models import Ticket, Comentario, Categoria

TAMANHO_MAXIMO = 2 * 1024 * 1024  # 2MB

MIME_PERMITIDOS = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'image/bmp',
    'application/pdf',
}

def validar_arquivo(arquivo):
    """Valida extensao, tamanho e magic bytes do anexo."""
    if arquivo:
        # Tamanho
        if arquivo.size > TAMANHO_MAXIMO:
            raise ValidationError('O arquivo nao pode exceder 2MB.')

        # Magic bytes (verifica o conteudo real, nao so a extensao)
        chunk = arquivo.read(2048)
        arquivo.seek(0)
        mime = magic.from_buffer(chunk, mime=True)
        if mime not in MIME_PERMITIDOS:
            raise ValidationError(
                f'Tipo de arquivo nao permitido ({mime}). '
                'Envie apenas imagens (JPG, PNG, GIF, WEBP) ou PDF.'
            )
    return arquivo

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['titulo', 'descricao', 'categoria', 'prioridade', 'anexo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título do problema'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Detalhe o problema...'}),
            'categoria': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'prioridade': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'anexo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,application/pdf'}), # Bootstrap class
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(ativa=True)
        self.fields['categoria'].empty_label = "Selecione uma categoria"

    def clean_anexo(self):
        return validar_arquivo(self.cleaned_data.get('anexo'))

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['mensagem', 'interno', 'anexo']
        widgets = {
            'mensagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Digite seu comentário...'}),
            'anexo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,application/pdf'}), # Bootstrap class
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Lógica de campo interno
        if self.usuario and not self.usuario.is_technician:
            self.fields['interno'].widget = forms.HiddenInput()
            self.fields['interno'].initial = False
        else:
            # Se for técnico, adiciona classe de checkbox do bootstrap
            self.fields['interno'].widget.attrs.update({'class': 'form-check-input'})

    def clean_anexo(self):
        return validar_arquivo(self.cleaned_data.get('anexo'))

class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['status', 'tecnico_responsavel', 'prioridade']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tecnico_responsavel': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico_responsavel'].queryset = User.objects.filter(
            is_technician=True, 
            is_active=True
        )
        self.fields['tecnico_responsavel'].empty_label = "Aguardando Técnico"