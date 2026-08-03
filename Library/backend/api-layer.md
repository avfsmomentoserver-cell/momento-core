# API Layer

## REST API Endpoints

### Authentication
```
POST   /api/v1/auth/login          - User login
POST   /api/v1/auth/register       - User registration
POST   /api/v1/auth/refresh        - Refresh JWT token
POST   /api/v1/auth/logout         - User logout
POST   /api/v1/auth/forgot-password - Password reset request
POST   /api/v1/auth/reset-password  - Password reset execution
```

### Market Data
```
GET    /api/v1/market/symbols      - List available symbols
GET    /api/v1/market/ohlc/:symbol - OHLC data for symbol
GET    /api/v1/market/volume/:symbol - Volume profile
GET    /api/v1/market/depth/:symbol - Order book depth
WS     /ws/market/:symbol          - Real-time market data
```

### Pattern Analysis
```
POST   /api/v1/patterns/scan       - Scan for patterns
GET    /api/v1/patterns/:id        - Get pattern details
GET    /api/v1/patterns/similar/:id - Find similar patterns
GET    /api/v1/patterns/dna/:symbol - DNA analysis results
POST   /api/v1/patterns/save       - Save custom pattern
DELETE /api/v1/patterns/:id        - Delete pattern
```

### Pressure Tracking
```
GET    /api/v1/pressure/current/:symbol - Current pressure levels
GET    /api/v1/pressure/ladder/:symbol  - Pressure ladder
GET    /api/v1/pressure/history/:symbol - Historical pressure
POST   /api/v1/pressure/alerts     - Create pressure alert
GET    /api/v1/pressure/alerts     - List user alerts
DELETE /api/v1/pressure/alerts/:id - Delete alert
```

### Insights
```
GET    /api/v1/insights/:symbol    - Market insights
GET    /api/v1/insights/trending   - Trending insights
POST   /api/v1/insights/feedback   - Submit feedback
GET    /api/v1/insights/history    - Insight history
```

### Backtesting
```
POST   /api/v1/backtest/run        - Run backtest job
GET    /api/v1/backtest/status/:jobId - Job status
GET    /api/v1/backtest/results/:jobId - Job results
GET    /api/v1/backtest/jobs       - List user jobs
DELETE /api/v1/backtest/cancel/:jobId - Cancel job
```

### User Profile
```
GET    /api/v1/users/profile       - Get user profile
PUT    /api/v1/users/profile       - Update profile
GET    /api/v1/users/subscriptions - Subscription details
PUT    /api/v1/users/preferences   - Update preferences
GET    /api/v1/users/api-keys      - List API keys
POST   /api/v1/users/api-keys      - Create API key
DELETE /api/v1/users/api-keys/:id  - Revoke API key
```

## WebSocket Endpoints

### Market Data Stream
```
WS /ws/market
Subscriptions:
- { "action": "subscribe", "symbol": "EURUSD", "timeframe": "M5" }
- { "action": "unsubscribe", "symbol": "EURUSD" }

Messages:
- { "type": "tick", "symbol": "EURUSD", "data": {...} }
- { "type": "candle", "symbol": "EURUSD", "data": {...} }
- { "type": "volume", "symbol": "EURUSD", "data": {...} }
```

### Pattern Alerts
```
WS /ws/patterns
Subscriptions:
- { "action": "subscribe", "patterns": ["DNA", "Pressure"] }

Messages:
- { "type": "pattern_detected", "symbol": "EURUSD", "pattern": {...} }
- { "type": "similarity_found", "symbol": "EURUSD", "match": {...} }
```

### Pressure Alerts
```
WS /ws/pressure
Subscriptions:
- { "action": "subscribe", "symbols": ["EURUSD", "GBPUSD"] }

Messages:
- { "type": "pressure_change", "symbol": "EURUSD", "levels": {...} }
- { "type": "ladder_collapse", "symbol": "EURUSD", "event": {...} }
```

## API Authentication

### JWT Token Flow
1. User logs in with credentials
2. Server returns access token (15 min) and refresh token (7 days)
3. Client includes access token in Authorization header
4. On expiration, use refresh token to get new access token
5. On refresh token expiration, re-authenticate

### Header Format
```
Authorization: Bearer <jwt_token>
```

### Rate Limiting
- **Free Tier**: 100 requests/minute, 1000 requests/hour
- **Pro Tier**: 500 requests/minute, 5000 requests/hour
- **Enterprise**: Custom limits

### API Key Authentication
For server-to-server communication:
```
X-API-Key: <api_key>
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "The provided symbol is not valid",
    "details": {
      "symbol": "INVALID",
      "validSymbols": ["EURUSD", "GBPUSD", ...]
    },
    "timestamp": "2024-01-01T00:00:00Z",
    "requestId": "req_123456"
  }
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid auth
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Versioning

API versions are specified in the URL path:
- `/api/v1/...` - Current stable version
- `/api/v2/...` - Next version (when available)

Deprecated endpoints return `Deprecation` header with sunset date.

## Related Documents

- [Backend Overview](./00-index.md)
- [Core Services](./core-services.md)
- [API Specifications](../api/00-index.md)
- [Authentication](./security.md)
