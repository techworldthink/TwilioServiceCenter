# Twilio Relay Server

A high-performance API relay server built with Django that sits between clients and Twilio. It handles custom authentication, enforces billing/rate limits, and dynamically routes requests to different Twilio subaccounts based on configurable rules.

## Features

- **Custom Authentication**: API key-based authentication with Redis caching
- **Billing Management**: Atomic balance deduction with transaction safety
- **Dynamic Routing**: Route messages to different Twilio accounts based on phone number patterns
- **Token Encryption**: Secure storage of Twilio credentials using Fernet encryption
- **Webhook Support**: Handle Twilio status callbacks
- **Docker Support**: Fully containerized with PostgreSQL and Redis

## Architecture

```
Client → Relay Server → Twilio API
         ├─ Auth Middleware (Redis Cache)
         ├─ Billing Service (PostgreSQL)
         └─ Routing Service (Pattern Matching)
```

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL 15+ (if running locally)
- Redis 7+ (if running locally)

## Quick Start

### Using Docker Compose (Recommended)

1. **Generate Encryption Key**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

2. **Set Environment Variables**
```bash
export MASTER_ENCRYPTION_KEY="your_generated_key_here"
```

3. **Start Services**
```bash
docker-compose up -d
```

4. **Run Migrations**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Local Development

1. **Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Run Migrations**
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. **Start Development Server**
```bash
python manage.py runserver
```

### Project URLs

Once the server is running, you can access the following:

- **Home Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Portal**: [http://127.0.0.1:8000/secure-portal/](http://127.0.0.1:8000/secure-portal/)
- **API Swagger UI**: [http://127.0.0.1:8000/api/docs/swagger/](http://127.0.0.1:8000/api/docs/swagger/)
- **API ReDoc**: [http://127.0.0.1:8000/api/docs/redoc/](http://127.0.0.1:8000/api/docs/redoc/)


## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///db.sqlite3` |
| `REDIS_URL` | Redis connection string | `redis://127.0.0.1:6379/1` |
| `MASTER_ENCRYPTION_KEY` | Fernet key for token encryption | Required |
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DEBUG` | Enable debug mode | `0` |

### Database Models

- **Client**: Represents API consumers with balance tracking
- **APIKey**: Authentication keys linked to clients
- **TwilioAccount**: Twilio subaccount credentials (encrypted)
- **RoutingRule**: Pattern-based routing configuration

## API Usage

### Send SMS

**Endpoint**: `POST /relay/sms`

**Headers**:
```
X-Proxy-Auth: your_api_key_here
Content-Type: application/json
```

**Request Body**:
```json
{
  "To": "+1234567890",
  "From": "+0987654321",
  "Body": "Hello World"
}
```

**Response**:
```json
{
  "sid": "SM...",
  "status": "queued",
  "cost": "0.0075",
  "remaining_balance": "99.9925"
}
```

**Error Responses**:
- `401`: Invalid or missing API key
- `402`: Insufficient funds
- `500`: No routing rule found or Twilio error

### Webhook Endpoint

**Endpoint**: `POST /relay/twilio/webhook`

Receives Twilio status callbacks for message delivery updates.

## Admin Setup

1. **Access Admin Panel**: http://localhost:8000/admin

2. **Create a Client**:
   - Name: "Test Client"
   - Balance: 100.0000

3. **Generate API Key**:
```python
import hashlib
raw_key = "my_secret_key_12345"
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
# Use key_hash in APIKey.key_hash field
# Use first 8 chars of raw_key as prefix
```

4. **Add Twilio Account**:
   - SID: Your Twilio Account SID
   - Use `set_token()` method to encrypt and store auth token
   - Description: "Primary Account"

5. **Create Routing Rule**:
   - Pattern: `^\+1.*` (matches US numbers)
   - Priority: 100
   - Account: Select your Twilio account

## Testing

### Test Authentication
```bash
curl -X POST http://localhost:8000/relay/sms \
  -H "X-Proxy-Auth: invalid_key" \
  -H "Content-Type: application/json"
# Expected: 401 Unauthorized
```

### Test Billing
```bash
# Set client balance to 0.0001 in admin
curl -X POST http://localhost:8000/relay/sms \
  -H "X-Proxy-Auth: your_valid_key" \
  -H "Content-Type: application/json" \
  -d '{"To": "+1234567890", "Body": "Test"}'
# Expected: 402 Payment Required
```

### Test Routing
```bash
curl -X POST http://localhost:8000/relay/sms \
  -H "X-Proxy-Auth: your_valid_key" \
  -H "Content-Type: application/json" \
  -d '{"To": "+1234567890", "From": "+0987654321", "Body": "Hello"}'
# Check logs to verify correct Twilio account selection
```

## Project Structure

```
TwilioServiceCenter/
├── relay/                    # Main application
│   ├── models.py            # Data models
│   ├── services.py          # Business logic
│   ├── middleware.py        # Auth middleware
│   ├── views.py             # API endpoints
│   └── urls.py              # URL routing
├── twilio_service_center/   # Django project
│   ├── settings.py          # Configuration
│   └── urls.py              # Root URLs
├── docker-compose.yml       # Container orchestration
├── Dockerfile               # Container image
├── requirements.txt         # Python dependencies
└── manage.py                # Django CLI
```

## Security Considerations

- **Encryption Key**: Store `MASTER_ENCRYPTION_KEY` securely (e.g., AWS Secrets Manager)
- **API Keys**: Use SHA256 hashing for key storage
- **HTTPS**: Always use HTTPS in production
- **Webhook Validation**: Implement Twilio signature validation for webhooks
- **Rate Limiting**: Consider adding rate limiting middleware

## Production Deployment

1. **Set DEBUG=0**
2. **Use strong SECRET_KEY**
3. **Configure ALLOWED_HOSTS**
4. **Use Gunicorn/uWSGI**
5. **Set up reverse proxy (Nginx)**
6. **Enable SSL/TLS**
7. **Configure database backups**
8. **Set up monitoring and logging**

## Troubleshooting

### Redis Connection Issues
```bash
docker-compose logs redis
# Verify Redis is running on correct port
```

### Database Migration Errors
```bash
python manage.py showmigrations
python manage.py migrate --fake-initial
```

### Encryption Key Errors
```bash
# Ensure key is 32 bytes URL-safe base64
python -c "from cryptography.fernet import Fernet; print(len(Fernet.generate_key()))"
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.




















docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
