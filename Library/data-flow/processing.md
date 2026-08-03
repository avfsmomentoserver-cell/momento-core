# Data Processing Pipeline

## Processing Stages

### Stage 1: Aggregation
- Tick to candle conversion
- Volume profile calculation
- OHLCV computation

### Stage 2: Analysis
- Pattern DNA encoding
- Pressure level calculation
- Indicator computation

### Stage 3: Enrichment
- Historical comparison
- Similarity scoring
- Signal generation

### Stage 4: Storage
- Time-series database write
- Cache update
- Index maintenance

## GPU Processing
- CUDA kernels for pattern matching
- Parallel processing across symbols
- Batch operations for efficiency

## Real-time vs Batch
- Real-time: Live market data (<100ms latency)
- Near-real-time: Analysis results (<1s latency)
- Batch: Historical backtesting (minutes to hours)
