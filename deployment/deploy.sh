#!/bin/bash

# Deployment Script for Twilio Service Center
# Usage: ./deploy.sh

# Exit on error
set -e

echo "Starting Deployment..."

# 1. Navigate to project root (assuming script is in deployment/)
cd "$(dirname "$0")/.."

# 2. Check for .env.prod
if [ ! -f deployment/.env.prod ]; then
    echo "Error: deployment/.env.prod file not found!"
    echo "Please copy deployment/.env.prod.example to deployment/.env.prod and configure it."
    exit 1
fi

# 3. Build and Start Containers
echo "Building and starting containers..."
docker-compose -f deployment/docker-compose.prod.yml up -d --build

# 4. Wait for Database (simple sleep, or rely on depends_on/healthcheck)
echo "Waiting for services to stabilize..."
sleep 10

# 5. Run Migrations
echo "Running database migrations..."
docker-compose -f deployment/docker-compose.prod.yml exec -T web python manage.py migrate

# 6. Collect Static Files
echo "Collecting static files..."
docker-compose -f deployment/docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

echo "Deployment Complete!"
echo "App is running on port 8085"
echo "Database (MySQL) is on port 3307"

