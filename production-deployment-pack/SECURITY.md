# Security Integration Guide

## Quick Start

Add these lines to your `server.py` to enable security features:

### 1. Import Security Module

```python
# At the top of server.py, add:
from security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TokenEncryption,
    encrypt_api_token,
    decrypt_api_token,
    sanitize_input,
    AuditLogger
)
```

### 2. Add Middleware (after app creation)

```python
# After: app = FastAPI(...)
# Add these lines:

# Security headers (XSS protection, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting (60 req/min, 1000 req/hour per user)
app.add_middleware(RateLimitMiddleware)
```

### 3. Encrypt ClickUp Tokens

When saving ClickUp config, encrypt the token:

```python
# In save_clickup_config endpoint, change:
# OLD:
await db.clickup_configs.update_one(
    {"user_id": current_user["id"]},
    {"$set": {"api_token": config.api_token, ...}},
    upsert=True
)

# NEW:
await db.clickup_configs.update_one(
    {"user_id": current_user["id"]},
    {"$set": {"api_token": encrypt_api_token(config.api_token), ...}},
    upsert=True
)
```

When reading ClickUp config, decrypt the token:

```python
# When using the token:
config = await db.clickup_configs.find_one({"user_id": user_id})
api_token = decrypt_api_token(config["api_token"])
```

### 4. Add Audit Logging

```python
# Create audit logger
audit = AuditLogger()

# In login endpoint:
audit.login_attempt(email=credentials.email, success=True, ip=request.client.host)

# In token access:
audit.api_token_access(user_id=current_user["id"], action="read", integration="clickup")

# In data export:
audit.data_export(user_id=current_user["id"], data_type="report", record_count=len(projects))
```

### 5. Input Validation

```python
# In project creation:
from security import sanitize_input, validate_project_name

@api_router.post("/projects")
async def create_project(project: ProjectCreate):
    # Sanitize and validate
    name = sanitize_input(project.name, max_length=100)
    if not validate_project_name(name):
        raise HTTPException(400, "Invalid project name")
    
    # Continue with creation...
```

---

## Environment Variables Required

Add these to your `.env`:

```bash
# Encryption key for API tokens
ENCRYPTION_KEY=your-fernet-key-here

# Rate limiting
RATE_LIMIT_RPM=60    # Requests per minute
RATE_LIMIT_RPH=1000  # Requests per hour

# Environment
ENVIRONMENT=production
```

Generate encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Full server.py Integration Example

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    AuditLogger
)

app = FastAPI(title="Risk Radar API")

# CORS (be specific in production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Audit logger
audit = AuditLogger()
```

---

## Testing Security

### Test Rate Limiting
```bash
# This should get rate limited after 5 requests
for i in {1..10}; do
  curl -X POST http://localhost:8001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"test"}' \
    -w "\n%{http_code}\n"
done
```

### Test Encryption
```python
from security import TokenEncryption

enc = TokenEncryption()
token = "pk_12345_abcdef"
encrypted = enc.encrypt(token)
decrypted = enc.decrypt(encrypted)

assert token == decrypted
print(f"Original: {token}")
print(f"Encrypted: {encrypted}")
print(f"Decrypted: {decrypted}")
```

---

## Security Checklist

- [ ] Set strong `JWT_SECRET` (64+ random bytes)
- [ ] Set strong `ENCRYPTION_KEY` (Fernet key)
- [ ] Configure `CORS_ORIGINS` to your domain only
- [ ] Enable HTTPS in production
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure rate limits appropriately
- [ ] Enable audit logging
- [ ] Set up log aggregation (CloudWatch, Datadog, etc.)
- [ ] Regular security updates for dependencies
- [ ] Database backups configured
