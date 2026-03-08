# accounts/forms.py
"""
Formulários de autenticação e gerenciamento de usuários.

Formulários disponíveis:
- LoginForm: Autenticação de usuários (Bootstrap styled)
- UserRegistrationForm: Registro de novos usuários
- ProfileUpdateForm: Atualização de perfil
- CadastroSimplificadoForm: Alternativa de registro simplificado

Nota: Este arquivo complementa accounts/views.py com formulários
customizados para as views de autenticação.
"""

import unicodedata
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
# REGISTRO
# =============================================================================

class UserRegistrationForm(UserCreationForm):
    """
    Formulário principal de registro de novos usuários.
    O 'username' foi ocultado da tela e é gerado automaticamente no backend.
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='E-mail válido é obrigatório'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nome'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Sobrenome'
    )
    
    class Meta:
        model = User
        # 'username' removido daqui para não aparecer no formulário HTML
        fields = ['email', 'first_name', 'last_name', 'departamento', 'telefone']
        widgets = {
            'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        """Valida e-mail único no sistema."""
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        
        return email
    
    def clean_password1(self):
        """Valida força da senha usando validadores do Django."""
        password = self.cleaned_data.get('password1')
        
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        
        return password

    def save(self, commit=True):
        """
        Sobrescreve o método save para gerar o username automaticamente
        baseado no nome e sobrenome do usuário.
        """
        # Cria a instância do usuário, mas não salva no banco ainda
        user = super().save(commit=False)
        
        # Pega o primeiro nome e o último sobrenome digitados
        first = self.cleaned_data.get('first_name', '').strip().lower().split(' ')[0]
        last = self.cleaned_data.get('last_name', '').strip().lower().split(' ')[-1]
        
        # Junta com ponto
        base_username = f"{first}.{last}"
        
        # Remove acentos (ex: joão.conceição -> joao.conceicao)
        base_username = ''.join(
            c for c in unicodedata.normalize('NFD', base_username) 
            if unicodedata.category(c) != 'Mn'
        )
        
        # Garante que o username será único (se existir joao.silva, vira joao.silva2)
        username = base_username
        contador = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{contador}"
            contador += 1
            
        # Atribui o username gerado de forma transparente
        user.username = username
        
        if commit:
            user.save()
            
        return user


# =============================================================================
# CADASTRO SIMPLIFICADO
# =============================================================================

class CadastroSimplificadoForm(UserCreationForm):
    """
    Formulário de cadastro simplificado (alternativa ao UserRegistrationForm).
    """
    
    email = forms.EmailField(
        required=True,
        help_text='E-mail válido é obrigatório'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nome'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Sobrenome'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'username': 'Usuário (login)',
        }
        help_texts = {
            'username': 'Máximo 30 caracteres. Apenas letras, números e @/./+/-/_',
        }
    
    def clean_username(self):
        """Valida username com mínimo 4 caracteres."""
        username = self.cleaned_data.get('username')
        if len(username) < 4:
            raise forms.ValidationError('Usuário deve ter pelo menos 4 caracteres.')
        return username
    
    def clean_email(self):
        """Valida e-mail único."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email


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