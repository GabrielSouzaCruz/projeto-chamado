# accounts/models.py
"""
Modelo de usuário customizado do sistema.

Define o modelo User que estende AbstractUser, adicionando campos
específicos do sistema de chamados: is_technician, departamento, telefone.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_technician = models.BooleanField(
        default=False,
        verbose_name='É Técnico de TI',
        help_text='Marque se este usuário é um técnico de suporte'
    )

    departamento = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Departamento'
    )

    telefone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefone'
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username}'