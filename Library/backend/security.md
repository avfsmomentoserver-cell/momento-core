# Security

## Authentication & Authorization

### JWT-Based Authentication

#### Token Structure
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "role": "pro",
    "permissions": ["read:market", "write:patterns"],
    "iat": 1704067200,
    "exp": 1704068100
  },
  "signature": "HMACSHA256(...)"
}
```

#### Token Lifecycle
- **Access Token**: 15 minutes validity
- **Refresh Token**: 7 days validity (stored in HTTP-only cookie)
- **Rotation**: Refresh tokens rotate on each use
- **Revocation**: Immediate via token blacklist in Redis

#### Security Measures
- HMAC-SHA256 signing with 256-bit secret
- Secret rotation every 90 days
- Token binding to user agent fingerprint
- Concurrent session limits per tier

---

### OAuth2 Integration

#### Supported Providers
- Google
- GitHub
- Microsoft

#### Flow
1. User initiates OAuth login
2. Redirect to provider with PKCE challenge
3. Provider redirects back with authorization code
4. Exchange code for tokens (server-side)
5. Create/join user account
6. Issue Momento JWT tokens

#### Security
- PKCE (Proof Key for Code Exchange) required
- State parameter for CSRF protection
- Scope validation before token issuance

---

### Role-Based Access Control (RBAC)

#### Roles
| Role | Permissions |
|------|-------------|
| `free` | Basic market data, limited patterns |
| `pro` | Full market data, unlimited patterns, backtesting |
| `enterprise` | API access, custom integrations, SLA |
| `admin` | System administration, user management |

#### Permission Checks
```python
from functools import wraps

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.state.user
            if permission not in user.permissions:
                raise HTTPException(403, "Insufficient permissions")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.get("/api/v1/backtest/run")
@require_permission("execute:backtest")
async def run_backtest(request):
    ...
```

---

## Data Encryption

### At-Rest Encryption

#### Database Encryption
- PostgreSQL TDE (Transparent Data Encryption)
- AES-256 encryption for sensitive columns
- Separate key management service (AWS KMS/HashiCorp Vault)

#### Encrypted Fields
```sql
-- Password hashes (bcrypt with cost=12)
password_hash VARCHAR(255)

-- API keys (encrypted at rest)
api_key_encrypted BYTEA

-- Sensitive user data
personal_data_encrypted BYTEA
```

### In-Transit Encryption

#### TLS Configuration
- TLS 1.3 minimum
- Strong cipher suites only
- HSTS enabled (max-age=31536000)
- Certificate pinning for mobile apps

#### Internal Service Communication
- mTLS between all microservices
- Service mesh (Istio) for automatic mTLS
- Certificate rotation every 30 days

---

## API Security

### Rate Limiting

#### Limits by Tier
| Tier | Requests/Min | Requests/Hour | Burst |
|------|--------------|---------------|-------|
| Free | 100 | 1,000 | 150 |
| Pro | 500 | 5,000 | 750 |
| Enterprise | Custom | Custom | Custom |

#### Implementation
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/market/data")
@limiter.limit("100/minute")
async def get_market_data(request: Request):
    ...
```

### Input Validation

#### Schema Validation
```python
from pydantic import BaseModel, validator

class PatternRequest(BaseModel):
    symbol: str
    timeframe: str
    sensitivity: float
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not re.match(r'^[A-Z]{6}$', v):
            raise ValueError('Invalid symbol format')
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
        if v not in valid:
            raise ValueError(f'Timeframe must be one of {valid}')
        return v
    
    @validator('sensitivity')
    def validate_sensitivity(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Sensitivity must be between 0 and 1')
        return v
```

#### SQL Injection Prevention
- Parameterized queries only
- ORM with built-in escaping
- Input sanitization for search queries

#### XSS Prevention
- Content-Type validation
- Output encoding for user-generated content
- CSP headers configured

---

## Security Headers

### HTTP Response Headers
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; script-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## Audit Logging

### Logged Events
- Authentication attempts (success/failure)
- Authorization decisions
- API key creation/revocation
- Data export requests
- Administrative actions
- Security configuration changes

### Log Format
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "event": "auth.login.success",
  "userId": "uuid",
  "ip": "192.168.1.1",
  "userAgent": "Mozilla/5.0...",
  "requestId": "req_123456",
  "metadata": {
    "method": "password",
    "mfaUsed": true
  }
}
```

### Retention
- Security logs: 2 years
- Audit logs: 7 years (compliance)
- Access logs: 90 days

---

## Vulnerability Management

### Regular Security Activities
- **Weekly**: Dependency vulnerability scanning
- **Monthly**: Penetration testing
- **Quarterly**: Security audit
- **Annually**: Third-party security assessment

### Incident Response
1. Detection and identification
2. Containment (isolate affected systems)
3. Eradication (remove threat)
4. Recovery (restore services)
5. Post-incident review

### Bug Bounty Program
- Scope: All production APIs and applications
- Rewards: $100 - $10,000 based on severity
- Submission: security@momento.core

---

## Related Documents

- [Backend Overview](./00-index.md)
- [API Layer](./api-layer.md)
- [Infrastructure Security](../infrastructure/security.md)
- [Data Layer](./data-layer.md)
