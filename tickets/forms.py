# tickets/forms.py

from django import forms

from .models import Ticket, Comentario, Categoria

 

class TicketForm(forms.ModelForm):

    """Formulário para criação e edição de tickets."""

    

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

                'placeholder': 'Detalhe o problema, incluindo mensagens de erro, '

                              'quando ocorre, etc.'

            }),

            'categoria': forms.Select(attrs={'class': 'form-select'}),

            'prioridade': forms.Select(attrs={'class': 'form-select'}),

        }

    

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Filtra apenas categorias ativas

        self.fields['categoria'].queryset = Categoria.objects.filter(ativa=True)

    

    def clean_anexo(self):

        anexo = self.cleaned_data.get('anexo')

        if anexo:

            # Validação do tipo de arquivo

            ext = anexo.name.split('.')[-1].lower()

            permitidos = ['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx']

            if ext not in permitidos:

                raise forms.ValidationError(

                    f'Tipo de arquivo não permitido. Use: {", ".join(permitidos)}'

                )

            # Limite de tamanho (5MB)

            if anexo.size > 5 * 1024 * 1024:

                raise forms.ValidationError('O arquivo não pode exceder 5MB.')

        return anexo

 

 

class ComentarioForm(forms.ModelForm):
    """Formulário para adicionar comentários."""

    

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

        self.usuario = kwargs.pop('usuario', None)

        super().__init__(*args, **kwargs)

        # Campo 'interno' visível apenas para técnicos

        if self.usuario and not self.usuario.is_technician:

            self.fields['interno'].widget = forms.HiddenInput()

            self.fields['interno'].initial = False

 

 

class TicketStatusForm(forms.ModelForm):

    """Formulário para alteração de status por técnicos."""

    

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

        from accounts.models import User
        # Lista de técnicos para seleção

        self.fields['tecnico_responsavel'].queryset = User.objects.filter(

            is_technician=True, is_active=True

        )