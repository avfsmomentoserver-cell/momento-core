# Authentication

## Methods

### JWT Token Authentication
Primary method for API access.

**Header:**
```
Authorization: Bearer <jwt_token>
```

**Token Acquisition:**
```bash
POST /api/v1/auth/login
Content-Type: application/json

{"email": "user@example.com", "password": "secure_password"}
```

**Response:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "dGhpcyBpcyBhIHJlZnJl...",
  "expiresIn": 900
}
```

### API Key Authentication
For server-to-server communication.

**Header:**
```
X-API-Key: your_api_key_here
```

**Create API Key:**
```bash
POST /api/v1/users/api-keys
Authorization: Bearer <token>

{"name": "Production Server", "permissions": ["read:market", "write:patterns"]}
```

## Token Refresh Flow

```javascript
async function refreshToken() {
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    credentials: 'include' // Send refresh token cookie
  });
  const { accessToken } = await response.json();
  return accessToken;
}
```

## Security Best Practices
1. Store tokens securely (httpOnly cookies or secure storage)
2. Never expose tokens in client-side code
3. Implement token rotation
4. Use HTTPS only
5. Set appropriate token expiration
