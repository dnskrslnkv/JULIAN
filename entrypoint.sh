#!/bin/bash

set -e

echo "Starting application setup..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
max_attempts=30
attempt=1
while ! nc -z db 5432; do
    if [ $attempt -eq $max_attempts ]; then
        echo "PostgreSQL is not available after $max_attempts attempts. Exiting."
        exit 1
    fi
    echo "PostgreSQL not ready yet. Attempt $attempt/$max_attempts. Retrying in 2 seconds..."
    sleep 2
    attempt=$((attempt + 1))
done
echo "PostgreSQL started successfully!"

# Wait for Redis
echo "Waiting for Redis..."
attempt=1
while ! nc -z redis 6379; do
    if [ $attempt -eq $max_attempts ]; then
        echo "Redis is not available after $max_attempts attempts. Exiting."
        exit 1
    fi
    echo "Redis not ready yet. Attempt $attempt/$max_attempts. Retrying in 2 seconds..."
    sleep 2
    attempt=$((attempt + 1))
done
echo "Redis started successfully!"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Create superuser if doesn't exist
echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Set up default font for reportlab to avoid Helvetica error
echo "Setting up default fonts..."
python -c "
import matplotlib
matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
print('Fonts initialized')
"

# Start server
echo "Starting server with command: $@"
exec "$@"