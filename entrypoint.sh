#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "import psycopg2; import os; psycopg2.connect(os.environ.get('DATABASE_URL')).close()" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is up - running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting server..."
exec "$@"

