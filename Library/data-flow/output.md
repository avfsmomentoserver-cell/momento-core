# Data Output Pipeline

## Output Channels

### WebSocket Streaming
- Real-time candle updates
- Pattern alerts
- Pressure changes
- System notifications

### REST API Responses
- On-demand data retrieval
- Historical queries
- Aggregated results

### Export Functions
- CSV download
- JSON export
- Report generation

## Response Formatting
- Consistent JSON schema
- ISO 8601 timestamps
- Standardized error formats
- Pagination for large datasets

## Caching Strategy
- Hot data: Redis (sub-ms access)
- Warm data: PostgreSQL with indexes
- Cold data: Compressed storage

## Rate Limiting
- Per-user limits based on tier
- Burst allowance
- Graceful degradation
