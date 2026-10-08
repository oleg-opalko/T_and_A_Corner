import os

import django
import uvicorn
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

call_command('migrate', interactive=False)
call_command('ensure_superuser')

uvicorn.run(
    'config.asgi:application',
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 80)),
    log_level='info',
    access_log=True,
)
