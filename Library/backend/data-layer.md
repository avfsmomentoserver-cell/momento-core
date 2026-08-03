# Data Layer

## Database Architecture

### Primary Databases

#### PostgreSQL (Relational Data)
**Purpose**: User data, configurations, patterns, metadata

**Schema Overview**:
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Patterns table
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    dna_hash VARCHAR(64),
    configuration JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Backtest results table
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_id VARCHAR(64) UNIQUE,
    symbol VARCHAR(20),
    metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes**:
- B-tree on user_id for foreign key lookups
- GIN on JSONB columns for flexible querying
- Partial indexes for active records

---

#### TimescaleDB (Time-Series Data)
**Purpose**: Market data, OHLCV, pressure levels, real-time metrics

**Hypertables**:
```sql
-- OHLCV data hypertable
SELECT create_hypertable('ohlc_data', 'time');
CREATE TABLE ohlc_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT
);

-- Pressure data hypertable
SELECT create_hypertable('pressure_data', 'time');
CREATE TABLE pressure_data (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    ladder_level INTEGER,
    pressure_value DOUBLE PRECISION,
    collapse_event BOOLEAN DEFAULT FALSE
);
```

**Compression**:
- Enable compression for data older than 7 days
- Segment by symbol and timeframe
- Achieve 10x storage reduction

---

#### Redis (Cache & Sessions)
**Purpose**: Hot data caching, session storage, pub/sub

**Data Structures**:
```
# Session storage
SESS:<user_id> -> JSON(user_session)

# Real-time cache
MARKET:<symbol>:<timeframe> -> JSON(latest_candle)
PRESSURE:<symbol> -> JSON(current_levels)

# Rate limiting
RATE:<api_key>:<minute> -> INTEGER(count)

# Pub/Sub channels
channel:market:<symbol>
channel:patterns:<user_id>
channel:pressure:<symbol>
```

**Eviction Policy**:
- LRU for general cache
- TTL-based for rate limiting
- Persistent for sessions

---

## Data Models

### Market Data Model
```typescript
interface Candle {
  timestamp: Date;
  symbol: string;
  timeframe: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trades: number;
}

interface VolumeProfile {
  symbol: string;
  date: Date;
  levels: {
    price: number;
    volume: number;
    trades: number;
    isPOC: boolean; // Point of Control
  }[];
}
```

### Pattern Model
```typescript
interface Pattern {
  id: string;
  userId?: string;
  name: string;
  type: 'DNA' | 'Pressure' | 'Custom';
  dnaHash: string;
  similarity: number;
  timeframes: string[];
  symbols: string[];
  configuration: PatternConfig;
  createdAt: Date;
}

interface PatternConfig {
  sensitivity: number;
  minLength: number;
  maxLength: number;
  minSimilarity: number;
}
```

### Pressure Model
```typescript
interface PressureLevel {
  ladderLevel: number;
  price: number;
  volume: number;
  strength: number;
  collapsed: boolean;
  collapseTime?: Date;
}

interface PressureState {
  symbol: string;
  timestamp: Date;
  currentLevel: number;
  levels: PressureLevel[];
  trend: 'building' | 'collapsing' | 'stable';
}
```

---

## Data Access Patterns

### Repository Pattern
```python
class MarketDataRepository:
    def __init__(self, db_connection, redis_client):
        self.db = db_connection
        self.cache = redis_client
    
    async def get_ohlc(self, symbol: str, timeframe: str, 
                       start: datetime, end: datetime) -> List[Candle]:
        # Check cache first
        cache_key = f"OHLC:{symbol}:{timeframe}:{start}:{end}"
        cached = await self.cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Query database
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlc_data
            WHERE symbol = $1 AND timeframe = $2
            AND time BETWEEN $3 AND $4
            ORDER BY time ASC
        """
        rows = await self.db.fetch(query, symbol, timeframe, start, end)
        
        # Cache result
        await self.cache.setex(cache_key, 300, json.dumps(rows))
        
        return rows
```

### Query Optimization
- Use prepared statements for repeated queries
- Implement connection pooling (max 20 connections)
- Batch insert for time-series data
- Covering indexes for common queries

---

## Data Migration Strategy

### Version Control
- Use migration files (e.g., `001_create_users.sql`)
- Track migrations in `schema_migrations` table
- Rollback support for each migration

### Example Migration
```sql
-- 005_add_dna_hash_index.sql
-- Up migration
CREATE INDEX CONCURRENTLY idx_patterns_dna_hash 
ON patterns USING HASH (dna_hash);

-- Down migration
DROP INDEX IF EXISTS idx_patterns_dna_hash;
```

---

## Backup & Recovery

### Backup Schedule
- **PostgreSQL**: Daily full backup, hourly WAL archiving
- **TimescaleDB**: Daily backup with retention policy
- **Redis**: RDB snapshots every 5 minutes + AOF

### Recovery Procedures
1. Restore from latest full backup
2. Apply WAL logs for point-in-time recovery
3. Verify data integrity with checksums
4. Test recovery quarterly

---

## Related Documents

- [Backend Overview](./00-index.md)
- [Core Services](./core-services.md)
- [Infrastructure Monitoring](../infrastructure/monitoring.md)
- [Security](./security.md)
