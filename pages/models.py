from django.contrib.auth import get_user_model
from django.db import models

from shop.models import Perfume


class AccountProfile(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='account_profile',
    )
    phone = models.CharField('Телефон', max_length=32, blank=True)
    city = models.CharField('Місто', max_length=120, blank=True)

    class Meta:
        verbose_name = 'Профіль користувача'
        verbose_name_plural = 'Профілі користувачів'

    def __str__(self):
        return f'Профіль {self.user.username}'


class UserFavorite(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='favorite_perfumes',
    )
    perfume = models.ForeignKey(
        Perfume,
        on_delete=models.CASCADE,
        related_name='favorite_records',
    )
    created_at = models.DateTimeField('Додано', auto_now_add=True)

    class Meta:
        verbose_name = 'Улюблений товар'
        verbose_name_plural = 'Улюблені товари'
        unique_together = [('user', 'perfume')]

    def __str__(self):
        return f'{self.user.username} → {self.perfume.name}'
