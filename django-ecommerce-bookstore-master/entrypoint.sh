#!/bin/sh

# Wait for the micro collector to be available.
/usr/local/bin/wait-for-it.sh micro:9090 -- echo "Snowplow Micro is up"

# Apply database migrations.
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --no-input --clear

# Start the Gunicorn application server.
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 ecom_project.wsgi:application
