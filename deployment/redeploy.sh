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

# 3. Executing deployment script
echo "Tearing down old containers and volumes (to ensure DB password sync)..."
# This is aggressive but necessary if the DB password changed or failed Init
docker-compose -f deployment/docker-compose.prod.yml down -v

echo "Executing deployment script..."
sudo ./deployment/deploy.sh

echo "Redeployment Sequence Complete!"
