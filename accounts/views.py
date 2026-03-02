# accounts/views.py

from django.contrib.auth.views import (

    LoginView, LogoutView, PasswordResetView, 

    PasswordResetDoneView, PasswordResetConfirmView

)

from django.contrib.messages.views import SuccessMessageMixin

from django.urls import reverse_lazy

from django.views.generic import CreateView

from django.contrib.auth import login

from django.contrib import messages

from .models import User

from django import forms

class LoginForm(forms.Form):

    username = forms.CharField(

        widget=forms.TextInput(attrs={

            'class': 'form-control',

            'placeholder': 'Nome de usuário'

        })

    )

    password = forms.CharField(

        widget=forms.PasswordInput(attrs={

            'class': 'form-control',

            'placeholder': 'Senha'

        })

    )

 

 

class CustomLoginView(SuccessMessageMixin, LoginView):

    template_name = 'accounts/login.html'

    form_class = LoginForm

    redirect_authenticated_user = True

    success_message = 'Bem-vindo(a), %(username)s!'

    

    def get_success_url(self):

        return reverse_lazy('tickets:dashboard')

 

 

class CustomLogoutView(LogoutView):

    next_page = reverse_lazy('accounts:login')

 

 

class UserRegistrationForm(forms.ModelForm):

    password1 = forms.CharField(

        label='Senha',

        widget=forms.PasswordInput(attrs={'class': 'form-control'})

    )

    password2 = forms.CharField(

        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})

    )

    

    class Meta:

        model = User

        fields = ['username', 'email', 'first_name', 'last_name', 

                  'departamento', 'telefone']

        widgets = {

            'username': forms.TextInput(attrs={'class': 'form-control'}),

            'email': forms.EmailInput(attrs={'class': 'form-control'}),

            'first_name': forms.TextInput(attrs={'class': 'form-control'}),

            'last_name': forms.TextInput(attrs={'class': 'form-control'}),

            'departamento': forms.TextInput(attrs={'class': 'form-control'}),

            'telefone': forms.TextInput(attrs={'class': 'form-control'}),

        }

    

    def clean_password2(self):

        password1 = self.cleaned_data.get('password1')

        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:

            raise forms.ValidationError('As senhas não conferem.')

        return password2

    

    def save(self, commit=True):

        user = super().save(commit=False)

        user.set_password(self.cleaned_data['password1'])

        if commit:

            user.save()

        return user

 

 

class RegisterView(SuccessMessageMixin, CreateView):

    model = User

    form_class = UserRegistrationForm

    template_name = 'accounts/register.html'

    success_url = reverse_lazy('tickets:dashboard')

    success_message = 'Conta criada com sucesso! Você está logado.'

    def form_valid(self, form):

        response = super().form_valid(form)

        login(self.request, self.object)

        return response