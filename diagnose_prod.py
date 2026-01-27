#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot production WhatsApp API issues
"""
import requests
import json
import sys

# Configuration
PROD_URL = "https://twilio.uzhavoorlive.com/relay/api/whatsapp"
LOCAL_URL = "http://127.0.0.1:8000/relay/api/whatsapp"

# Test payload
payload = {
    "To": "+1234567890",
    "Body": "Test message"
}

def test_endpoint(url, api_key):
    """Test an endpoint and print detailed diagnostics"""
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print(f"{'='*60}")
    
    headers = {
        "Content-Type": "application/json",
        "X-Proxy-Auth": api_key
    }
    
    print(f"\nRequest Headers:")
    for key, value in headers.items():
        if key == "X-Proxy-Auth":
            print(f"  {key}: {value[:8]}..." if len(value) > 8 else f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\nRequest Body:")
    print(f"  {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body (raw):")
        print(f"  {response.text[:500]}")
        
        # Try to parse as JSON
        try:
            json_data = response.json()
            print(f"\nParsed JSON:")
            print(f"  {json.dumps(json_data, indent=2)}")
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON Parse Error: {e}")
            print(f"   This means the server returned HTML or invalid JSON")
            print(f"   First 200 chars: {response.text[:200]}")
            
            # Check if it's HTML
            if response.text.strip().startswith('<'):
                print(f"\n   ⚠️  Server returned HTML (likely an error page)")
                print(f"   This usually happens when:")
                print(f"      - DEBUG=False and there's an unhandled exception")
                print(f"      - Middleware is raising an exception")
                print(f"      - Database/Redis connection issues")
                
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request Error: {e}")
        return False
    
    return True

def main():
    # Get API key from command line or use default
    api_key = sys.argv[1] if len(sys.argv) > 1 else "test_api_key"
    
    print("WhatsApp API Diagnostic Tool")
    print("=" * 60)
    print(f"Using API Key: {api_key[:8]}..." if len(api_key) > 8 else f"Using API Key: {api_key}")
    
    # Test local first
    print("\n\n🔍 TESTING LOCAL ENVIRONMENT")
    test_endpoint(LOCAL_URL, api_key)
    
    # Test production
    print("\n\n🔍 TESTING PRODUCTION ENVIRONMENT")
    test_endpoint(PROD_URL, api_key)
    
    print("\n\n" + "="*60)
    print("TROUBLESHOOTING TIPS:")
    print("="*60)
    print("""
1. If you get 401 "Missing Authorization Header":
   - Check that X-Proxy-Auth header is being sent
   - Verify middleware is loaded in settings.py
   
2. If you get 401 "Invalid API Key":
   - Verify the API key exists in the database
   - Check that the key is active (is_active=True)
   
3. If you get HTML instead of JSON (500 error):
   - Check production logs: docker logs <container_name>
   - Verify DEBUG=0 in production .env
   - Check database connection (DATABASE_URL)
   - Check Redis connection (REDIS_URL)
   - Verify MASTER_ENCRYPTION_KEY is set
   
4. If you get 402 "Insufficient Funds":
   - Check client balance in admin panel
   - Add credits to the client account
   
5. If you get 503 "No Route Found":
   - Verify routing rules exist for the destination number
   - Check TwilioAccount is configured and active
    """)

if __name__ == "__main__":
    main()
