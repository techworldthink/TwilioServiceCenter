#!/bin/bash
# Quick fix deployment script for production issues

set -e  # Exit on error

echo "=========================================="
echo "Production Fix Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo -e "${RED}Error: manage.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found Django project"

# Check if deployment directory exists
if [ ! -d "deployment" ]; then
    echo -e "${RED}Error: deployment directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found deployment directory"

# Ask for confirmation
echo ""
echo -e "${YELLOW}This script will:${NC}"
echo "  1. Pull latest code changes"
echo "  2. Restart production containers"
echo "  3. Run health check"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Pull latest changes (if in git repo)
if [ -d ".git" ]; then
    echo ""
    echo "Step 1: Pulling latest changes..."
    git pull || echo -e "${YELLOW}Warning: git pull failed (continuing anyway)${NC}"
else
    echo ""
    echo "Step 1: Skipping git pull (not a git repository)"
fi

# Step 2: Restart containers
echo ""
echo "Step 2: Restarting production containers..."
cd deployment

if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}Error: docker-compose.prod.yml not found${NC}"
    exit 1
fi

echo "  - Stopping containers..."
docker-compose -f docker-compose.prod.yml down

echo "  - Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

echo "  - Waiting for services to start (10 seconds)..."
sleep 10

cd ..

echo -e "${GREEN}✓${NC} Containers restarted"

# Step 3: Run health check
echo ""
echo "Step 3: Running health check..."
echo ""

# Try to determine the production URL
PROD_URL="https://twilio.uzhavoorlive.com"
if [ -f "deployment/.env.prod" ]; then
    # Try to extract from env file
    ALLOWED_HOSTS=$(grep ALLOWED_HOSTS deployment/.env.prod | cut -d'=' -f2)
    if [ ! -z "$ALLOWED_HOSTS" ]; then
        # Get first host that's not localhost
        for host in $(echo $ALLOWED_HOSTS | tr ',' ' '); do
            if [[ ! $host =~ ^(localhost|127\.0\.0\.1)$ ]]; then
                PROD_URL="https://$host"
                break
            fi
        done
    fi
fi

echo "Testing: $PROD_URL/relay/api/health"
echo ""

HEALTH_RESPONSE=$(curl -s "$PROD_URL/relay/api/health" || echo '{"error": "Connection failed"}')

# Check if response is valid JSON
if echo "$HEALTH_RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo "$HEALTH_RESPONSE" | python3 -m json.tool
    
    # Check overall status
    STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
    
    echo ""
    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ System is HEALTHY${NC}"
    else
        echo -e "${YELLOW}⚠ System is UNHEALTHY${NC}"
        echo ""
        echo "Please review the health check output above for specific issues."
        echo "See PRODUCTION_TROUBLESHOOTING.md for detailed fix instructions."
    fi
else
    echo -e "${RED}✗ Health check failed - could not connect or invalid response${NC}"
    echo "Response: $HEALTH_RESPONSE"
    echo ""
    echo "Possible issues:"
    echo "  - Containers not running: docker ps"
    echo "  - Check logs: docker logs -f twilio_web_1"
    echo "  - DNS/network issues"
fi

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review health check output above"
echo "  2. Check logs: docker logs -f twilio_web_1"
echo "  3. Test API: python3 diagnose_prod.py YOUR_API_KEY"
echo "  4. See PRODUCTION_FIX_SUMMARY.md for detailed troubleshooting"
echo ""
