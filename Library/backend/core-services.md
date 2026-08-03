# Core Services

## Service Catalog

### 1. Ingestion Service
**Purpose**: Real-time market data intake and validation

**Features**:
- FPGA-accelerated data parsing
- Multi-exchange connectivity
- Data normalization and validation
- Tick-by-tick processing
- Volume profile construction

**Technology**:
- Python/C++ for performance-critical paths
- WebSocket clients for exchange feeds
- NATS for event distribution
- TimescaleDB for time-series storage

**API Endpoints**:
```
POST /api/v1/ingestion/start
POST /api/v1/ingestion/stop
GET /api/v1/ingestion/status
GET /api/v1/ingestion/symbols
```

---

### 2. GPU Intelligence Service
**Purpose**: Pattern recognition and DNA similarity analysis

**Features**:
- CUDA-accelerated pattern matching
- DNA similarity scoring
- Multi-timeframe analysis
- Real-time pattern detection
- Historical pattern database

**Technology**:
- NVIDIA CUDA kernels
- PyTorch for ML models
- Redis for caching results
- PostgreSQL for pattern storage

**API Endpoints**:
```
POST /api/v1/gpu/analyze
GET /api/v1/gpu/dna/:patternId
GET /api/v1/gpu/similarity/:symbol
POST /api/v1/gpu/train
```

---

### 3. Pressure Tracking Service
**Purpose**: Mega pressure ladder collapse detection

**Features**:
- Real-time pressure calculation
- Ladder level tracking
- Collapse prediction
- Alert generation
- Historical pressure analysis

**Technology**:
- Real-time computation engine
- In-memory data structures
- Event-driven architecture
- Time-windowed aggregations

**API Endpoints**:
```
GET /api/v1/pressure/current/:symbol
GET /api/v1/pressure/ladder/:symbol
GET /api/v1/pressure/history/:symbol
POST /api/v1/pressure/alerts/subscribe
```

---

### 4. Linguistics Service
**Purpose**: NLP for market insights and vocabulary processing

**Features**:
- Sentiment analysis
- Keyword extraction
- Insight generation
- Vocabulary matching
- Multi-language support

**Technology**:
- Transformer models (BERT, GPT)
- Rule-based engines
- Knowledge graph
- Caching for common phrases

**API Endpoints**:
```
POST /api/v1/linguistics/analyze
GET /api/v1/linguistics/insights/:symbol
GET /api/v1/linguistics/vocabulary/:term
POST /api/v1/linguistics/custom-terms
```

---

### 5. Backtest Service
**Purpose**: Historical strategy validation

**Features**:
- Multi-year backtesting
- Walk-forward analysis
- Performance metrics calculation
- Strategy optimization
- Report generation

**Technology**:
- Batch processing framework
- Parallel computation
- Historical data warehouse
- Statistical analysis libraries

**API Endpoints**:
```
POST /api/v1/backtest/run
GET /api/v1/backtest/status/:jobId
GET /api/v1/backtest/results/:jobId
DELETE /api/v1/backtest/cancel/:jobId
```

---

### 6. User Management Service
**Purpose**: Authentication, authorization, and user profiles

**Features**:
- JWT-based authentication
- Role-based access control
- API key management
- Subscription handling
- Audit logging

**Technology**:
- OAuth2/OIDC
- PostgreSQL for user data
- Redis for sessions
- bcrypt for password hashing

**API Endpoints**:
```
POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/refresh
GET /api/v1/users/profile
PUT /api/v1/users/profile
```

---

### 7. Notification Service
**Purpose**: Alerts and user communications

**Features**:
- Email notifications
- Push notifications
- SMS alerts (planned)
- Webhook integrations
- Template management

**Technology**:
- Message queue consumers
- SMTP integration
- Firebase Cloud Messaging
- Template engines

**API Endpoints**:
```
POST /api/v1/notifications/send
GET /api/v1/notifications/history
PUT /api/v1/notifications/preferences
POST /api/v1/notifications/webhooks
```

---

## Inter-Service Communication

### Synchronous (gRPC/REST)
- API Gateway → Core Services
- Service-to-service queries
- Health checks

### Asynchronous (NATS/Kafka)
- Event streaming
- Audit logs
- Analytics data
- Background jobs

## Service Health Monitoring

- **Health Endpoints**: `/health`, `/ready`, `/live`
- **Metrics**: Prometheus exporters
- **Tracing**: OpenTelemetry integration
- **Logging**: Structured JSON logs

## Related Documents

- [Backend Overview](./00-index.md)
- [API Layer](./api-layer.md)
- [Data Layer](./data-layer.md)
- [Performance Optimization](./performance.md)
