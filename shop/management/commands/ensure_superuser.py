import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the configured superuser if it does not already exist.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username and not password:
            self.stdout.write('Superuser variables are not set; skipping.')
            return
        if not username or not password:
            raise CommandError('Set both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD.')

        User = get_user_model()
        user = User._default_manager.filter(**{User.USERNAME_FIELD: username}).first()
        if user:
            if not user.is_superuser:
                raise CommandError(f'User {username!r} exists but is not a superuser.')
            self.stdout.write(f'Superuser {username!r} already exists.')
            return

        User._default_manager.create_superuser(
            **{User.USERNAME_FIELD: username},
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'Created superuser {username!r}.'))
