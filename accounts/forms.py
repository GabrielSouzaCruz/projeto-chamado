# accounts/forms.py
"""
Formulários de autenticação e gerenciamento de usuários.

Formulários disponíveis:
- LoginForm: Autenticação de usuários (Bootstrap styled)
- ProfileUpdateForm: Atualização de perfil

Nota: Este arquivo complementa accounts/views.py com formulários
customizados para as views de autenticação.

Nota: O formulário de registro público (UserRegistrationForm) foi removido
junto com a rota register/ — contas são criadas apenas pelo admin.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User


# =============================================================================
# LOGIN
# =============================================================================

class LoginForm(AuthenticationForm):
    """
    Formulário de login customizado com widgets Bootstrap.
    """
    
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Ex: joao.silva',
            'autofocus': True,
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite sua senha',
            'autocomplete': 'current-password'
        })
    )


# =============================================================================
# PERFIL
# =============================================================================

class ProfileUpdateForm(forms.ModelForm):
    """
    Formulário para atualização de perfil do usuário logado.
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'departamento', 'telefone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        """Valida e-mail único, exceto o próprio e-mail do usuário."""
        email = self.cleaned_data.get('email')
        
        # Exclui o usuário atual da busca
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        
        return email