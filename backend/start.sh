#!/bin/bash
set -e

echo "Applying database migrations..."
python manage.py migrate

echo "Starting Gunicorn..."
exec gunicorn -c gunicorn.conf.py config.wsgi:application
