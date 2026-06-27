#!/bin/bash
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Starting gRPC server on :50051..."
python grpc_server.py &

echo "==> Starting Django dev server on :8000..."
exec python manage.py runserver 0.0.0.0:8000
