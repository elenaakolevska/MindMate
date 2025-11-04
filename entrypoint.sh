#!/bin/sh
set -e

# Wait for the database to be ready
echo "Waiting for database..."
while ! python - <<'PY'
import os, sys
import psycopg2

dsn = os.environ.get('DATABASE_URL')
if not dsn:
    sys.exit(1)
try:
    conn = psycopg2.connect(dsn)
    conn.close()
except Exception:
    sys.exit(1)
sys.exit(0)
PY
do
  sleep 1
done

# Run migrations and collectstatic
echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Execute the CMD
exec "$@"

