import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nifty100_project.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402 (must follow django.setup())

username = os.environ.get("ADMIN_USERNAME")
email = os.environ.get("ADMIN_EMAIL")
password = os.environ.get("ADMIN_PASSWORD")

if not (username and email and password):
    sys.exit("ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD env vars are required.")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Admin superuser created: {username}")
else:
    print("Admin superuser already exists")
