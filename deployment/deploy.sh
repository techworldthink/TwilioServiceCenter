#!/bin/bash

# Deployment Script for Twilio Service Center
# Usage: ./deploy.sh

# Exit on error
set -e

echo "Starting Deployment..."

# 1. Navigate to project root (assuming script is in deployment/)
cd "$(dirname "$0")/.."

# 2. Check for .env.prod and Export Variables
if [ ! -f deployment/.env.prod ]; then
    echo "Error: deployment/.env.prod file not found!"
    echo "Please copy deployment/.env.prod.example to deployment/.env.prod and configure it."
    exit 1
fi

# Load variables into shell for docker-compose substitution
echo "Loading environment variables..."
set -a
source deployment/.env.prod
set +a

# 3. Build and Start Containers
echo "Building and starting containers..."
docker-compose --env-file deployment/.env.prod -f deployment/docker-compose.prod.yml up -d --build

# 4. Wait for Database to be ready
echo "Waiting for database to initialize (this may take a minute)..."
# Simple wait loop - try to reach the port
count=0
while [ $count -lt 45 ]; do
    if docker-compose --env-file deployment/.env.prod -f deployment/docker-compose.prod.yml exec -T db mysqladmin ping -h localhost --silent; then
        echo "Database is up!"
        break
    fi
    # Check if container is crashing
    if [ $(docker inspect -f '{{.State.Restarting}}' twilio_relay_db) == "true" ]; then
        echo "Warning: DB container is restarting. Checking logs..."
        docker logs twilio_relay_db --tail 10
    fi
    echo "Waiting for DB ($count)..."
    sleep 2
    count=$((count+1))
done
sleep 5 # extra safety buffer

# 5. Run Migrations
echo "Running database migrations..."
if ! docker-compose --env-file deployment/.env.prod -f deployment/docker-compose.prod.yml exec -T web python manage.py migrate; then
    echo "Migration failed. Checking DB logs..."
    docker logs twilio_relay_db --tail 20
    exit 1
fi

# 6. Collect Static Files
echo "Collecting static files..."
docker-compose --env-file deployment/.env.prod -f deployment/docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

echo "Deployment Complete!"
echo "App is running on port 8085"
echo "Database (MySQL) is on port 3307"

