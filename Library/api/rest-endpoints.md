# REST API Reference

## Market Data Endpoints

### GET /market/symbols
List all available trading symbols.

**Response:**
```json
{
  "symbols": [
    {"symbol": "EURUSD", "name": "Euro/US Dollar", "type": "forex"},
    {"symbol": "GBPUSD", "name": "British Pound/US Dollar", "type": "forex"}
  ]
}
```

### GET /market/ohlc/:symbol
Get OHLCV data for a symbol.

**Parameters:**
- timeframe: M1, M5, M15, M30, H1, H4, D1
- from: Start timestamp
- to: End timestamp

**Response:**
```json
{
  "symbol": "EURUSD",
  "timeframe": "M5",
  "candles": [
    {"time": "2024-01-01T00:00:00Z", "open": 1.1050, "high": 1.1065, "low": 1.1045, "close": 1.1060, "volume": 1500}
  ]
}
```

## Pattern Endpoints

### POST /patterns/scan
Scan for patterns in specified data.

### GET /patterns/:id
Get details of a specific pattern.

### GET /patterns/similar/:id
Find similar patterns based on DNA.

## Pressure Endpoints

### GET /pressure/current/:symbol
Get current pressure levels.

### GET /pressure/ladder/:symbol
Get full pressure ladder structure.

## Backtest Endpoints

### POST /backtest/run
Start a backtest job.

### GET /backtest/status/:jobId
Check job status.

### GET /backtest/results/:jobId
Get completed results.
