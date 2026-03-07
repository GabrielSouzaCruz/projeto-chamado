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
    
    Herda de AuthenticationForm para:
    - Validação automática de username/password
    - Integração com Django auth system
    - Proteção contra brute-force (via Django)
    
    Widgets customizados:
    - Campos com classe Bootstrap (form-control)
    - Placeholders orientativos
    - Autofocus no username
    """
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite seu nome de usuário',
            'autofocus': True,
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
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
    
    ⚠️ SEGURANÇA:
    - Registro é ABERTO (qualquer um pode criar conta)
    - Para produção com controle, considere:
      1. is_active=False até aprovação do admin
      2. Verificação por e-mail com token
      3. Whitelist de domínios corporativos
    
    Validações incluídas:
    - Username único (herdado do Django)
    - E-mail único (clean_email)
    - Senhas conferem (herdado do Django)
    - Validação de força da senha (Django validators)
    - Username mínimo 4 caracteres
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
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'username'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'autocomplete': 'new-password'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'autocomplete': 'new-password'
            }),
        }
        labels = {
            'username': 'Usuário (login)',
        }
        help_texts = {
            'username': 'Máximo 30 caracteres. Apenas letras, números e @/./+/-/_',
            'password1': 'Mínimo 8 caracteres. Não use senhas óbvias.',
        }
    
    def clean_username(self):
        """
        Valida username: mínimo 4 caracteres.
        
        Validações herdadas do Django (não precisa reimplementar):
        - Username único
        - Caracteres válidos (alphanumeric + @/./+/-/_)
        - Máximo 30 caracteres
        
        Adicionamos apenas:
        - Mínimo 4 caracteres (evita usernames muito curtos)
        """
        username = self.cleaned_data.get('username')
        
        if len(username) < 4:
            raise forms.ValidationError('Usuário deve ter pelo menos 4 caracteres.')
        
        return username
    
    def clean_email(self):
        """
        Valida e-mail único no sistema.
        
        Por que validar aqui?
        - Evita múltiplos usuários com mesmo e-mail
        - Importante para recuperação de senha futura
        - Previne duplicação acidental
        
        ⚠️ Race condition:
        Em alta concorrência, dois registros simultâneos podem passar
        aqui. Para produção crítica, adicione unique constraint no banco.
        """
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        
        return email
    
    def clean_password1(self):
        """
        Valida força da senha usando validadores do Django.
        
        Validações (configuradas em settings.py):
        - Mínimo 8 caracteres
        - Não similar a username/email
        - Não é senha comum (lista de senhas proibidas)
        - Não é apenas numérica
        
        Por que validar aqui?
        - Feedback imediato no formulário
        - Mensagens de erro amigáveis
        - Segue políticas de senha da organização
        """
        password = self.cleaned_data.get('password1')
        
        try:
            validate_password(password)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        
        return password


class CadastroSimplificadoForm(UserCreationForm):
    """
    Formulário de cadastro simplificado (alternativa ao UserRegistrationForm).
    
    Diferenças para UserRegistrationForm:
    - Menos campos obrigatórios
    - Mais rápido de preencher
    - Ideal para registro rápido interno
    
    ⚠️ ATENÇÃO:
    Este formulário é MANTIDO para compatibilidade, mas recomenda-se
    usar UserRegistrationForm para consistência com o sistema.
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
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        labels = {
            'username': 'Usuário (login)',
        }
        help_texts = {
            'username': 'Máximo 30 caracteres. Apenas letras, números e @/./+/-/_',
            'password1': 'Mínimo 8 caracteres. Não use senhas óbvias.',
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
    
    Campos editáveis:
    - first_name, last_name: Identificação
    - email: Contato (único, validado)
    - departamento: Organização interna
    - telefone: Contato direto
    
    Campos NÃO editáveis:
    - username: Identificador único (mudança requer admin)
    - is_technician: Permissão (apenas admin)
    - password: Usar formulário separado (alterar_senha)
    
    Segurança:
    - Valida e-mail único (exceto o próprio)
    - Apenas dados do usuário logado são atualizados
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
        """
        Valida e-mail único, exceto o próprio e-mail do usuário.
        
        Por que permitir o próprio e-mail?
        - Usuário pode salvar perfil sem mudar e-mail
        - Evita erro "este e-mail já está cadastrado" para o próprio
        
        Como funciona:
        - Busca e-mail em outros usuários (exclui o atual)
        - Se encontrar, retorna erro
        - Se não encontrar, permite salvar
        """
        email = self.cleaned_data.get('email')
        
        # Exclui o usuário atual da busca
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        
        return email