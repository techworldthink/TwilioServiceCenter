# Production Issue Fix Summary

## Problem
WhatsApp API works locally (`http://127.0.0.1:8000`) but fails in production (`https://twilio.uzhavoorlive.com`) with:
- HTTP Status: 500
- Error: `Expecting value: line 2 column 1 (char 1)` (JSON parse error)
- Root cause: Server returning HTML error page instead of JSON

## Solutions Implemented

### 1. **Global Exception Handler** ✅
**File**: `relay/exception_middleware.py`

- Catches all unhandled exceptions in `/relay/api/` endpoints
- Returns JSON error responses instead of HTML
- Provides specific error messages for common issues:
  - Database connection errors → 503
  - Redis/Cache errors → 503
  - Encryption key errors → 500
  - Validation errors → 400
  - Permission errors → 403

**Added to**: `twilio_service_center/settings.py` → `MIDDLEWARE`

### 2. **Health Check Endpoint** ✅
**File**: `relay/health_views.py`

**Endpoint**: `GET /relay/api/health` (no authentication required)

Checks:
- ✓ Database connectivity
- ✓ Redis/Cache connectivity
- ✓ Encryption key validity
- ✓ Configuration completeness (clients, API keys, accounts, routing rules)
- ✓ Environment info

**Usage**:
```bash
# Local
curl http://127.0.0.1:8000/relay/api/health

# Production
curl https://twilio.uzhavoorlive.com/relay/api/health
```

### 3. **Diagnostic Endpoint** ✅
**File**: `relay/health_views.py`

**Endpoint**: `GET /relay/api/diagnostic` (requires X-Proxy-Auth header)

Returns:
- Client balance and status
- API key permissions
- Routing rules configuration
- Twilio account counts

**Usage**:
```bash
curl -H "X-Proxy-Auth: YOUR_API_KEY" https://twilio.uzhavoorlive.com/relay/api/diagnostic
```

### 4. **Diagnostic Tool** ✅
**File**: `diagnose_prod.py`

Python script to compare local vs production responses:
```bash
python3 diagnose_prod.py YOUR_API_KEY
```

### 5. **Troubleshooting Guide** ✅
**File**: `PRODUCTION_TROUBLESHOOTING.md`

Comprehensive guide covering:
- Common error patterns
- Step-by-step diagnostics
- Quick fix commands
- Production setup checklist

## How to Fix Your Production Issue

### Step 1: Check Health Status
```bash
curl https://twilio.uzhavoorlive.com/relay/api/health | python3 -m json.tool
```

Look for any `"status": "error"` in the response.

### Step 2: Most Likely Issues

#### A. Missing/Invalid MASTER_ENCRYPTION_KEY
**Symptoms**: Encryption check fails in health endpoint

**Fix**:
```bash
# SSH to production server
cd /path/to/TwilioServiceCenter/deployment

# Check if key is set
grep MASTER_ENCRYPTION_KEY .env.prod

# If missing or invalid, generate new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env.prod
echo "MASTER_ENCRYPTION_KEY=<generated_key>" >> .env.prod

# Restart
docker-compose -f docker-compose.prod.yml restart web
```

#### B. Database Connection Issues
**Symptoms**: Database check fails in health endpoint

**Fix**:
```bash
# Check database container
docker ps | grep db

# Check logs
docker logs twilio_db_1

# Verify DATABASE_URL in .env.prod
# Restart database
docker-compose -f docker-compose.prod.yml restart db
```

#### C. Redis Connection Issues
**Symptoms**: Cache check fails in health endpoint

**Fix**:
```bash
# Check Redis container
docker ps | grep redis

# Test Redis
docker exec -it twilio_redis_1 redis-cli ping

# Restart Redis
docker-compose -f docker-compose.prod.yml restart redis
```

#### D. Missing Routing Rules
**Symptoms**: Configuration check shows "No routing rules configured"

**Fix**:
1. Access admin: `https://twilio.uzhavoorlive.com/secure-portal/`
2. Go to "Routing Rules"
3. Create new rule:
   - Pattern: `^\+1.*` (for US numbers) or `.*` (for all)
   - Priority: 100
   - Account: Select your Twilio account
   - Is Active: ✓

### Step 3: Deploy Changes

```bash
# Pull latest code with fixes
cd /path/to/TwilioServiceCenter
git pull

# Restart containers
cd deployment
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker logs -f twilio_web_1
```

### Step 4: Test Again

```bash
# Test health
curl https://twilio.uzhavoorlive.com/relay/api/health

# Test WhatsApp API
curl -X POST https://twilio.uzhavoorlive.com/relay/api/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Proxy-Auth: YOUR_API_KEY" \
  -d '{"To": "+1234567890", "Body": "Test"}'
```

## Files Changed

1. **relay/exception_middleware.py** (NEW) - Global exception handler
2. **relay/health_views.py** (NEW) - Health check and diagnostic endpoints
3. **relay/urls.py** (MODIFIED) - Added health/diagnostic routes
4. **relay/middleware.py** (MODIFIED) - Exempted health endpoint from auth
5. **twilio_service_center/settings.py** (MODIFIED) - Added exception middleware
6. **diagnose_prod.py** (NEW) - Diagnostic tool
7. **PRODUCTION_TROUBLESHOOTING.md** (NEW) - Troubleshooting guide

## Benefits

1. **Better Error Messages**: JSON errors instead of HTML
2. **Easy Diagnostics**: Health check endpoint for monitoring
3. **Faster Debugging**: Diagnostic endpoint shows configuration
4. **Production Ready**: Proper error handling for all edge cases
5. **Monitoring**: Can integrate health endpoint with uptime monitors

## Next Steps

1. Deploy changes to production
2. Run health check to identify specific issue
3. Fix the identified issue (likely encryption key or routing rules)
4. Test WhatsApp API again
5. Set up monitoring on `/relay/api/health` endpoint

## Support

If issues persist after following this guide:
1. Check production logs: `docker logs -f twilio_web_1`
2. Enable DEBUG temporarily (see PRODUCTION_TROUBLESHOOTING.md)
3. Check diagnostic endpoint output
4. Review all environment variables are set correctly
