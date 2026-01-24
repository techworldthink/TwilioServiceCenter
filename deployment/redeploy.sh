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
echo "Executing deployment script..."
sudo ./deployment/deploy.sh

echo "Redeployment Sequence Complete!"
