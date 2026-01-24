#!/bin/bash

# Redeployment Script for Twilio Service Center
# Pulls latest changes and runs deploy.sh

# Exit on error
set -e

echo "Starting Redeployment..."

# 1. Navigate to project root
cd "$(dirname "$0")/.."

# 2. Pull latest changes
echo "Pulling latest changes from git..."
git pull

# Load variables for substitution in 'down -v'
if [ -f deployment/.env.prod ]; then
    set -a
    source deployment/.env.prod
    set +a
fi

# 3. Executing deployment script
echo "Tearing down old containers and volumes (to ensure DB password sync)..."
# Explicitly use the env file to avoid warnings during cleanup
docker-compose --env-file deployment/.env.prod -f deployment/docker-compose.prod.yml down -v

echo "Executing deployment script..."
sudo ./deployment/deploy.sh

echo "Redeployment Sequence Complete!"

