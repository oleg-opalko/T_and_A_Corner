from django.contrib import admin

from .models import AccountProfile, UserFavorite


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city')


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'perfume', 'created_at')
    search_fields = ('user__username', 'perfume__name')
