# Backend API Documentation

## Overview

The Momento Core backend API is built with FastAPI and provides a comprehensive RESTful interface plus WebSocket support for real-time data streaming.

**Base Path**: `/api/v1`  
**Documentation**: `/docs` (Swagger UI), `/redoc` (ReDoc)  
**WebSocket**: `/ws`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  Middleware Layer                                            │
│  - CORS                                                      │
│  - Scope Gateway (multi-scope auth)                         │
│  - Security Headers                                          │
│  - Zero Trust                                                │
├─────────────────────────────────────────────────────────────┤
│  Route Modules (24 endpoints)                               │
│  - core, rounds, analysis, market, forecasts                │
│  - engines, ingest, users, platform, backtest               │
│  - features, vocabulary, mega_pressure, fpga                │
│  - gpu, scopes, v5_admin, backup                            │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                        │
│  - momento/ (core modules)                                  │
│  - pattern_discovery, linguistics, store                    │
│  - hub (WebSocket), watcher, feed                           │
├─────────────────────────────────────────────────────────────┤
│  Data Access Layer                                           │
│  - SQLAlchemy ORM                                           │
│  - SQLite (WAL mode)                                        │
│  - Multi-scope schemas                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Route Modules

### Core Routes (`core.py`)
- `/health` - System health check
- `/version` - API version information
- `/stats` - Database and system statistics

### Rounds Routes (`rounds.py`)
- `/rounds` - List/query rounds
- `/rounds/{id}` - Get specific round
- `/rounds/recent` - Recent rounds
- `/rounds/patterns` - Pattern-associated rounds

### Analysis Routes (`analysis.py`)
- `/analysis` - Submit data for analysis
- `/analysis/results` - Get analysis results
- `/analysis/engines` - Available analysis engines

### Market Routes (`market.py`)
- `/market/data` - Market data feed
- `/market/ladder` - Market ladder view
- `/market/trends` - Market trend analysis

### Forecast Routes (`forecasts.py`)
- `/forecasts` - Generate forecasts
- `/forecasts/history` - Historical forecasts
- `/forecasts/accuracy` - Forecast accuracy metrics

### Engines Routes (`engines.py`)
- `/engines` - List available engines
- `/engines/{id}` - Engine details
- `/engines/{id}/execute` - Execute engine

### Ingest Routes (`ingest.py`)
- `/ingest` - Submit raw data
- `/ingest/batch` - Batch data ingestion
- `/ingest/status` - Ingestion status

### Users Routes (`users.py`)
- `/users` - User management
- `/users/{id}` - User details
- `/users/auth` - Authentication

### Platform Routes (`platform.py`)
- `/platform/config` - Platform configuration
- `/platform/status` - Platform status
- `/platform/deployments` - Deployment management

### Backtest Routes (`backtest.py`, `backtest_enhanced.py`)
- `/backtest` - Run backtest
- `/backtest/results` - Backtest results
- `/backtest/strategies` - Strategy management

### Features Routes (`features.py`)
- `/features` - Feature flags
- `/features/toggle` - Toggle features

### Vocabulary Routes (`vocabulary.py`)
- `/vocabulary` - Linguistic vocabulary
- `/vocabulary/terms` - Term management
- `/vocabulary/grow` - Vocabulary growth

### Mega Pressure Routes (`mega_pressure.py`)
- `/mega-pressure` - Pressure analysis
- `/mega-pressure/tracker` - Pressure tracking
- `/mega-pressure/alerts` - Pressure alerts

### FPGA Routes (`fpga.py`)
- `/fpga/status` - FPGA pipeline status
- `/fpga/config` - FPGA configuration
- `/fpga/metrics` - FPGA performance metrics

### GPU Routes (`gpu.py`)
- `/gpu/status` - GPU intelligence status
- `/gpu/process` - GPU-accelerated processing
- `/gpu/metrics` - GPU utilization metrics

### Scopes Routes (`scopes.py`)
- `/scopes` - Scope management
- `/scopes/{id}` - Scope details
- `/scopes/auth` - Scope authentication

### V5 Admin Routes (`v5_admin.py`)
- `/admin/dashboard` - Admin dashboard
- `/admin/users` - User administration
- `/admin/system` - System administration

### Backup Routes (`backup.py`)
- `/backup/create` - Create backup
- `/backup/restore` - Restore from backup
- `/backup/list` - List available backups

### WebSocket Routes (`ws.py`)
- `/ws` - WebSocket connection endpoint
- Real-time data streaming
- Event subscriptions

---

## Request/Response Flow

```
Client Request
    ↓
CORS Middleware
    ↓
Scope Gateway (if enabled)
    ↓
Security Headers (if enabled)
    ↓
Route Handler
    ↓
Business Logic
    ↓
Data Access
    ↓
Response
    ↓
Exception Handler (if error)
    ↓
Client Response
```

---

## Authentication & Authorization

### Multi-Scope System
- Scope-based data isolation
- JWT token authentication
- Role-based access control
- Commercial deployment support

### Security Features
- Zero-trust architecture (optional)
- Security headers middleware
- Anomaly detection
- Intrusion detection
- MFA support

---

## Error Handling

All errors are sanitized before reaching the client:

```json
{
  "detail": "Internal server error",
  "path": "/api/v1/endpoint",
  "timestamp": "2026-08-03T12:00:00Z"
}
```

Internal details are logged but never exposed to clients.

---

## Lifecycle Management

### Startup Sequence
1. Configure logging
2. Initialize database
3. Bootstrap authentication
4. Initialize multi-scope schema
5. Bind WebSocket hub to event loop
6. Initialize security monitoring
7. Start watcher (if enabled)
8. Auto-start feed (if configured)
9. Start FPGA pipeline (if enabled)
10. Start stream optimizer (if enabled)
11. Initialize GPU intelligence
12. Initialize CPU intelligence

### Shutdown Sequence
1. Stop feed
2. Stop watcher
3. Stop FPGA pipeline
4. Stop stream optimizer
5. Shutdown GPU intelligence
6. Close database connections

---

## Configuration

Key configuration options via `config` module:
- `API_HOST`, `API_PORT` - Server binding
- `CORS_ORIGINS`, `ALLOW_ALL_CORS` - CORS settings
- `WATCHER_ENABLED` - Enable file watcher
- `FPGA_ENABLED`, `DPDK_ENABLED` - Hardware acceleration
- `STREAM_OPTIMIZER_ENABLED` - Stream optimization
- `CPU_ML_ENABLED` - CPU-based ML
- `CORS_ORIGINS` - Allowed origins

---

## Related Documentation

- [Backend Services](../services/)
- [Analysis Engines](../analysis/)
- [Data Flow](../../flows/data/)
- [API Specifications](../../specifications/api/)

---

**Source File**: `backend/momento/api/app.py`  
**Last Updated**: 2026-08-03
