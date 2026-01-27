# Quick Reference: Production Issue Fix

## TL;DR - What to Do Right Now

### 1. Check What's Wrong
```bash
curl https://twilio.uzhavoorlive.com/relay/api/health | python3 -m json.tool
```

### 2. Most Common Fix (90% of cases)
```bash
# SSH to your production server
cd /path/to/TwilioServiceCenter/deployment

# Check encryption key
grep MASTER_ENCRYPTION_KEY .env.prod

# If missing or looks wrong, generate new one
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env.prod (replace YOUR_KEY with generated key)
echo "MASTER_ENCRYPTION_KEY=YOUR_KEY" >> .env.prod

# Restart
docker-compose -f docker-compose.prod.yml restart web

# Test again
curl -X POST https://twilio.uzhavoorlive.com/relay/api/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Proxy-Auth: YOUR_API_KEY" \
  -d '{"To": "+1234567890", "Body": "Test"}'
```

### 3. If Still Not Working - Check Routing Rules
```bash
# Access admin panel
https://twilio.uzhavoorlive.com/secure-portal/

# Create routing rule:
# Pattern: .*  (matches all numbers)
# Priority: 100
# Account: Select your Twilio account
# Is Active: ✓
```

## Error Messages Decoded

| Error | Meaning | Fix |
|-------|---------|-----|
| `Expecting value: line 2 column 1` | Server returned HTML instead of JSON | Check logs: `docker logs twilio_web_1` |
| `Missing Authorization Header` | No X-Proxy-Auth header sent | Add header to your request |
| `Invalid API Key` | API key not found or inactive | Create/activate API key in admin |
| `Insufficient Funds` | Client balance too low | Add credits in admin panel |
| `No Route Found` | No routing rule matches number | Create routing rule |
| `Encryption configuration error` | MASTER_ENCRYPTION_KEY wrong | Regenerate and set in .env.prod |

## Quick Commands

```bash
# View logs (real-time)
docker logs -f twilio_web_1

# Check all containers running
docker ps

# Restart everything
cd deployment
docker-compose -f docker-compose.prod.yml restart

# Run health check
curl https://twilio.uzhavoorlive.com/relay/api/health

# Test with your API key
python3 diagnose_prod.py YOUR_API_KEY

# Deploy latest fixes
./deploy_fix.sh
```

## Files You Need to Know

- **PRODUCTION_FIX_SUMMARY.md** - Complete fix guide
- **PRODUCTION_TROUBLESHOOTING.md** - Detailed troubleshooting
- **diagnose_prod.py** - Diagnostic tool
- **deploy_fix.sh** - Auto-deployment script

## Emergency: See Detailed Error

```bash
# Temporarily enable debug (DISABLE AFTER!)
cd deployment
echo "DEBUG=1" >> .env.prod
docker-compose -f docker-compose.prod.yml restart web

# Make your request and see detailed error

# IMMEDIATELY DISABLE
sed -i 's/DEBUG=1/DEBUG=0/' .env.prod
docker-compose -f docker-compose.prod.yml restart web
```

## Contact Points

- Health Check: `https://twilio.uzhavoorlive.com/relay/api/health`
- Admin Panel: `https://twilio.uzhavoorlive.com/secure-portal/`
- API Docs: `https://twilio.uzhavoorlive.com/api/docs/swagger/`

## Success Looks Like

```json
{
  "status": "sent",
  "sid": "SM...",
  "cost": 0.005
}
```

If you see this, you're good! 🎉
