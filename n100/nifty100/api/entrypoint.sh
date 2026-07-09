#!/bin/sh
set -e

python manage.py migrate --noinput
exec gunicorn nifty100_project.wsgi:application --bind 0.0.0.0:8000
