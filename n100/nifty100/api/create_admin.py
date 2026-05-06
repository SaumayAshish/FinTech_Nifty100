import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nifty100_project.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@nifty100.com', 'admin123')
    print('Admin superuser created: admin / admin123')
else:
    print('Admin superuser already exists')
