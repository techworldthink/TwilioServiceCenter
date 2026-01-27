# Production Troubleshooting Guide

## Issue: Code works locally but fails in production with 500 error

### Symptoms
- Local: `HTTP 200` with valid JSON response
- Production: `HTTP 500` with HTML error page (causes JSON parse error)

### Root Causes & Solutions

## 1. **Missing or Invalid MASTER_ENCRYPTION_KEY** ⚠️ MOST COMMON

**Problem**: Production can't decrypt Twilio auth tokens

**Check**:
```bash
# SSH into production server or check docker logs
docker logs twilio_web_1 2>&1 | grep -i "encryption\|fernet\|invalid"
```

**Fix**:
```bash
# Generate a new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to deployment/.env.prod
MASTER_ENCRYPTION_KEY=<generated_key_here>

# Restart containers
cd deployment
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## 2. **Database Connection Issues**

**Problem**: Can't connect to MySQL/PostgreSQL

**Check**:
```bash
# Check if database container is running
docker ps | grep db

# Check database logs
docker logs twilio_db_1

# Test connection from web container
docker exec -it twilio_web_1 python manage.py dbshell
```

**Fix**:
```bash
# Verify DATABASE_URL in .env.prod matches docker-compose.prod.yml
# Format: mysql://user:password@host:port/database
# or: postgresql://user:password@host:port/database

# Restart database
docker-compose -f docker-compose.prod.yml restart db
```

## 3. **Redis Connection Issues**

**Problem**: Can't connect to Redis for caching

**Check**:
```bash
# Check if Redis is running
docker ps | grep redis

# Test Redis connection
docker exec -it twilio_redis_1 redis-cli ping
# Should return: PONG

# Check from web container
docker exec -it twilio_web_1 python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
```

**Fix**:
```bash
# Verify REDIS_URL in .env.prod
REDIS_URL=redis://redis:6379/1

# Restart Redis
docker-compose -f docker-compose.prod.yml restart redis
```

## 4. **Missing Routing Rules or Twilio Accounts**

**Problem**: No routing rule configured for the destination number

**Check**:
```bash
# Access Django shell in production
docker exec -it twilio_web_1 python manage.py shell

# Check routing rules
from relay.models import RoutingRule, TwilioAccount
print(f"Routing Rules: {RoutingRule.objects.count()}")
print(f"Twilio Accounts: {TwilioAccount.objects.count()}")

# List all rules
for rule in RoutingRule.objects.all():
    print(f"Pattern: {rule.pattern}, Priority: {rule.priority}, Account: {rule.account}")
```

**Fix**:
```bash
# Access admin panel
https://twilio.uzhavoorlive.com/secure-portal/

# Create routing rule:
# - Pattern: ^\+1.*  (for US numbers)
# - Priority: 100
# - Account: Select your Twilio account
# - Is Active: ✓
```

## 5. **API Key Not in Production Database**

**Problem**: API key exists locally but not in production

**Check**:
```bash
docker exec -it twilio_web_1 python manage.py shell

from relay.models import APIKey
print(f"API Keys: {APIKey.objects.count()}")

# List all keys
for key in APIKey.objects.all():
    print(f"Prefix: {key.prefix}, Client: {key.client.name}, Active: {key.is_active}")
```

**Fix**:
- Create API key via admin panel: https://twilio.uzhavoorlive.com/secure-portal/clients/
- Or export from local and import to production

## 6. **DEBUG=True in Production** (Security Risk!)

**Problem**: Detailed error pages exposed to public

**Check**:
```bash
grep DEBUG deployment/.env.prod
```

**Fix**:
```bash
# Ensure DEBUG=0 in .env.prod
DEBUG=0

# Restart
docker-compose -f docker-compose.prod.yml restart web
```

## Quick Diagnostic Commands

### View Production Logs (Real-time)
```bash
docker logs -f twilio_web_1
```

### Check All Environment Variables
```bash
docker exec -it twilio_web_1 env | grep -E "DEBUG|DATABASE|REDIS|MASTER_ENCRYPTION"
```

### Test API with Verbose Output
```bash
curl -v -X POST https://twilio.uzhavoorlive.com/relay/api/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Proxy-Auth: YOUR_API_KEY_HERE" \
  -d '{"To": "+1234567890", "Body": "Test"}'
```

### Access Production Django Shell
```bash
docker exec -it twilio_web_1 python manage.py shell
```

### Run Migrations (if needed)
```bash
docker exec -it twilio_web_1 python manage.py migrate
```

## Common Error Patterns

### Error: "Expecting value: line 2 column 1 (char 1)"
**Meaning**: Server returned HTML instead of JSON
**Cause**: Unhandled exception with DEBUG=0
**Solution**: Check logs for the actual error

### Error: "Invalid token"
**Meaning**: MASTER_ENCRYPTION_KEY mismatch
**Cause**: Key changed or not set
**Solution**: Verify encryption key is correct

### Error: "No Route Found"
**Meaning**: No routing rule matches the destination number
**Cause**: Missing or incorrect routing rules
**Solution**: Create routing rule with pattern matching your numbers

### Error: "Insufficient Funds"
**Meaning**: Client balance is too low
**Cause**: Balance depleted
**Solution**: Add credits via admin panel

## Recommended Production Setup Checklist

- [ ] DEBUG=0 in .env.prod
- [ ] MASTER_ENCRYPTION_KEY set and matches across deployments
- [ ] DATABASE_URL configured correctly
- [ ] REDIS_URL configured correctly
- [ ] At least one TwilioAccount created
- [ ] At least one RoutingRule created
- [ ] At least one Client with positive balance
- [ ] At least one APIKey created and active
- [ ] Migrations run: `docker exec -it twilio_web_1 python manage.py migrate`
- [ ] Static files collected: `docker exec -it twilio_web_1 python manage.py collectstatic --noinput`
- [ ] Logs monitored: `docker logs -f twilio_web_1`

## Emergency: Enable DEBUG Temporarily

**⚠️ ONLY FOR TROUBLESHOOTING - DISABLE IMMEDIATELY AFTER**

```bash
# Edit .env.prod
DEBUG=1

# Restart
docker-compose -f docker-compose.prod.yml restart web

# Test your request and see detailed error

# IMMEDIATELY DISABLE
DEBUG=0
docker-compose -f docker-compose.prod.yml restart web
```
