# WebSocket Protocol

## Connection

### Endpoint
`wss://ws.momento-core.com/v1`

### Authentication
Include JWT token in connection handshake:
```javascript
const ws = new WebSocket('wss://ws.momento-core.com/v1', {
  headers: { 'Authorization': 'Bearer <token>' }
});
```

## Subscription Messages

### Subscribe to Market Data
```json
{
  "action": "subscribe",
  "channel": "market",
  "params": {
    "symbol": "EURUSD",
    "timeframe": "M5"
  }
}
```

### Subscribe to Patterns
```json
{
  "action": "subscribe",
  "channel": "patterns",
  "params": {
    "symbols": ["EURUSD", "GBPUSD"]
  }
}
```

### Subscribe to Pressure
```json
{
  "action": "subscribe",
  "channel": "pressure",
  "params": {
    "symbols": ["EURUSD"]
  }
}
```

## Server Messages

### Candle Update
```json
{
  "type": "candle",
  "channel": "market",
  "data": {
    "symbol": "EURUSD",
    "timeframe": "M5",
    "candle": {...}
  }
}
```

### Pattern Alert
```json
{
  "type": "pattern_detected",
  "channel": "patterns",
  "data": {
    "symbol": "EURUSD",
    "pattern": {...},
    "confidence": 0.89
  }
}
```

### Pressure Update
```json
{
  "type": "pressure_change",
  "channel": "pressure",
  "data": {
    "symbol": "EURUSD",
    "levels": [...],
    "trend": "building"
  }
}
```

## Heartbeat
Server sends ping every 30 seconds. Client must respond with pong within 10 seconds or connection is closed.
