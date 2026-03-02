# accounts/admin.py

from django.contrib import admin

from django.contrib.auth.admin import UserAdmin

from .models import User

 

@admin.register(User)

class CustomUserAdmin(UserAdmin):

    list_display = ['username', 'email', 'first_name', 'last_name', 

                    'is_technician', 'is_staff', 'is_active']

    list_filter = ['is_technician', 'is_staff', 'is_active', 'groups']

    fieldsets = UserAdmin.fieldsets + (

        ('Informações Adicionais', {

            'fields': ('is_technician', 'departamento', 'telefone')

        }),

    )

    add_fieldsets = UserAdmin.add_fieldsets + (

        ('Informações Adicionais', {

            'fields': ('is_technician', 'departamento', 'telefone')

        }),

    )