# Data Flow Overview

Complete data pipeline documentation.

## Contents
- [Ingestion](./ingestion.md) - Data ingestion pipeline
- [Processing](./processing.md) - Analysis and transformation
- [Output](./output.md) - Output and visualization

## Pipeline Architecture
```
External Sources → FPGA Ingestion → Message Queue → 
GPU Processing → Database → Cache → API → Client
```

## Data Latency Targets
- Ingestion to Queue: < 1ms
- Queue to Processing: < 5ms
- Processing to Database: < 10ms
- Database to Cache: < 2ms
- Cache to Client: < 50ms (p95)
