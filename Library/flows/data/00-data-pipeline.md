# Data Pipeline Flow Documentation

## Overview

The Momento Core data pipeline processes market data from collection through analysis to forecasting and storage.

**Pipeline**: Collector → Ingest API → Analysis → Forecast Engine → Database → Dashboard

---

## Complete Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA COLLECTION LAYER                             │
├──────────────────────────────────────────────────────────────────────────┤
│  Browser Automation (Playwright)         Live Engine (Provably Fair)    │
│  - Scrape market data                    - Generate round events        │
│  - Extract crash points                  - Validate fairness            │
│  - Handle anti-bot measures              - Stream via WebSocket         │
└────────────────────┬─────────────────────────────────┬──────────────────┘
                     │                                 │
                     └─────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Raw Events     │
                          │  (JSON Lines)   │
                          └────────┬────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  File Watcher                            FPGA/DKPD Acceleration         │
│  - Monitor inbox directory               - Hardware-accelerated parse   │
│  - Validate file format                  - Zero-copy processing         │
│  - Trigger processing                    - High throughput              │
└────────────────────┬─────────────────────────────────┬──────────────────┘
                     │                                 │
                     └─────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Validation     │
                          │  - Schema check │
                          │  - Deduplication│
                          │  - Enrichment   │
                          └────────┬────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS LAYER                                    │
├──────────────────────────────────────────────────────────────────────────┤
│  Pattern Discovery                       DNA Analysis                   │
│  - Identify recurring patterns           - Genetic pattern matching     │
│  - Feature extraction                    - Similarity scoring           │
│  - Multi-scope analysis                  - Historical comparison        │
│                                                                        │
│  Pressure Analysis                       Time-Based Patterns            │
│  - Mega Pressure tracking                - Temporal pattern detection   │
│  - Market pressure indicators            - Seasonal adjustments         │
│                                                                        │
│  Technical Indicators                    Anomaly Detection              │
│  - Standard indicators (RSI, MACD)       - Outlier identification      │
│  - Custom calculations                   - Fraud detection              │
└────────────────────┬─────────────────────────────────┬──────────────────┘
                     │                                 │
                     └─────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Analysis       │
                          │  Results        │
                          └────────┬────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                         FORECAST LAYER                                    │
├──────────────────────────────────────────────────────────────────────────┤
│  ML Models                               Confidence Scoring             │
│  - GPU-accelerated inference             - Prediction reliability       │
│  - CPU fallback (free tier)              - Risk assessment              │
│                                                                        │
│  Linguistics Layer                       Decision Engine                │
│  - Semantic interpretation               - Trade logic                  │
│  - Vocabulary growth                     - Bankroll management          │
│  - Natural language output               - Execution signals            │
└────────────────────┬─────────────────────────────────┬──────────────────┘
                     │                                 │
                     └─────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Forecasts      │
                          │  + Confidence   │
                          └────────┬────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                                     │
├──────────────────────────────────────────────────────────────────────────┤
│  SQLite (WAL Mode)                       Multi-Scope Isolation          │
│  - Rounds table                        - Schema per scope              │
│  - Analysis results                    - Data access control            │
│  - Forecasts                           - Commercial separation          │
│  - Patterns                            - Tenant resources               │
│                                                                        │
│  Backup System                           Archive Management             │
│  - Automated backups                   - Historical data retention      │
│  - Point-in-time recovery              - Compression                    │
└────────────────────┬─────────────────────────────────┬──────────────────┘
                     │                                 │
                     └─────────────┬───────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Persistent     │
                          │  Storage        │
                          └────────┬────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                                │
├──────────────────────────────────────────────────────────────────────────┤
│  REST API                                WebSocket Hub                  │
│  - Query endpoints                     - Real-time streaming            │
│  - Filtering/sorting                   - Event subscriptions            │
│  - Pagination                          - Multiplexed connections        │
│                                                                        │
│  Frontend (React/TypeScript)                                           │
│  - MomentoFX v2 Interface                                              │
│  - Real-time charts                                                    │
│  - Analytics dashboard                                                 │
│  - Backtesting interface                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow Stages

### Stage 1: Data Collection

**Input Sources:**
- Browser automation (Playwright) scraping live market data
- Provably-fair random engine for simulation/testing
- External API feeds (optional)

**Output:** Raw JSON lines files in inbox directory

**Files Involved:**
- `backend/collector_aviator.js` - Browser automation
- `backend/momento/feed.py` - Feed management
- `backend/v5_realtime/` - Real-time data handling

### Stage 2: Ingestion

**Process:**
1. File watcher monitors inbox directory
2. New files trigger validation pipeline
3. Schema validation ensures data integrity
4. Deduplication prevents duplicate processing
5. Enrichment adds metadata

**Optimization Options:**
- FPGA acceleration for high-throughput scenarios
- DPDK for network-level optimization
- Stream optimizer for memory efficiency

**Files Involved:**
- `backend/watcher/watcher.py` - File monitoring
- `backend/fpga_ingest.py` - Hardware acceleration
- `backend/stream_optimizer.py` - Memory optimization

### Stage 3: Analysis

**Analysis Engines:**
- Pattern Discovery - Identifies recurring market patterns
- DNA Analysis - Genetic algorithm-based pattern matching
- Pressure Analysis - Mega Pressure tracking system
- Time-Based Patterns - Temporal analysis
- Technical Indicators - Standard financial indicators
- Anomaly Detection - Outlier and fraud detection

**Multi-Scope Support:**
- Each scope has isolated analysis context
- Commercial deployments have dedicated resources
- Tenant-specific pattern libraries

**Files Involved:**
- `backend/momento/pattern_discovery*.py` - Pattern engines
- `backend/momento/linguistics.py` - Semantic analysis
- `backend/cpu_intelligence/` - CPU-based ML
- `backend/gpu_intelligence/` - GPU-accelerated analysis

### Stage 4: Forecasting

**ML Pipeline:**
1. Feature vector construction
2. Model inference (GPU or CPU)
3. Confidence scoring
4. Linguistic interpretation
5. Decision generation

**Decision Engine:**
- Trade execution logic
- Risk management
- Bankroll optimization
- Position sizing

**Files Involved:**
- `backend/momento/megaplan_orchestrator.py` - Orchestration
- `backend/features/` - Feature implementations

### Stage 5: Storage

**Database Schema:**
- Rounds table - Raw round data
- Analysis table - Pattern matches and scores
- Forecasts table - Predictions with confidence
- Patterns table - Discovered patterns
- Users/Scopes tables - Multi-tenant support

**Backup Strategy:**
- Automated periodic backups
- Point-in-time recovery capability
- Archive compression for historical data

**Files Involved:**
- `backend/momento/store.py` - Data persistence
- `backend/momento/db.py` - Database management
- `backend/backups/` - Backup utilities

### Stage 6: Presentation

**API Endpoints:**
- RESTful queries with filtering/sorting
- Real-time WebSocket subscriptions
- Paginated responses for large datasets

**Frontend Features:**
- Real-time chart updates
- Interactive analytics
- Backtesting interface
- Admin dashboards

**Files Involved:**
- `backend/momento/api/routes/*` - API endpoints
- `backend/momento/hub.py` - WebSocket hub
- `web/src/` - Frontend application

---

## Error Handling & Recovery

### Data Validation Errors
- Invalid schema → Quarantine and alert
- Duplicate data → Skip with log entry
- Missing fields → Attempt repair or reject

### Processing Failures
- Analysis engine failure → Fallback to basic analysis
- Database errors → Retry with exponential backoff
- Network issues → Queue and retry

### Recovery Mechanisms
- Transaction rollback on failures
- Checkpoint-based resumption
- Dead letter queue for unprocessable items

---

## Performance Optimizations

### Throughput
- Batch processing for bulk operations
- Parallel analysis engine execution
- Async I/O for database operations

### Latency
- In-memory caching for frequent queries
- Stream processing for real-time data
- WebSocket multiplexing

### Resource Utilization
- GPU offloading for ML inference
- FPGA acceleration for parsing
- Connection pooling for database

---

## Monitoring & Observability

### Metrics Tracked
- Ingestion rate (events/second)
- Analysis latency (ms per event)
- Forecast accuracy (%)
- Database query performance
- API response times

### Logging
- Structured JSON logging
- Log rotation and archival
- Centralized log aggregation (Loki)

### Alerting
- Pipeline stall detection
- Error rate thresholds
- Resource utilization warnings

---

## Related Documentation

- [Architecture Overview](../../architecture/00-index.md)
- [Backend API](../../backend/api/00-api-overview.md)
- [System Flows](../system/)
- [Analysis Engines](../../backend/analysis/)

---

**Last Updated**: 2026-08-03
