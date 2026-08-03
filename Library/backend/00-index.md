# Backend Overview

Comprehensive backend service documentation for Momento Core.

## Service Modules

- [Core Services](./core-services.md) - Main business logic and processing engines
- [API Layer](./api-layer.md) - REST and WebSocket endpoints
- [Data Layer](./data-layer.md) - Database schemas and persistence strategies
- [Security](./security.md) - Authentication, authorization, and encryption
- [Performance](./performance.md) - Optimization techniques and benchmarks

## Architecture Summary

### Technology Stack
- **Runtime**: Node.js/Python for services, CUDA for GPU computing
- **API**: FastAPI/Express, WebSocket, GraphQL (planned)
- **Database**: PostgreSQL, TimescaleDB, Redis
- **Message Queue**: NATS/RabbitMQ
- **Container**: Docker, Kubernetes

### Key Services
1. **Ingestion Engine**: FPGA-accelerated real-time data intake
2. **GPU Intelligence**: Pattern recognition and DNA matching
3. **Pressure Tracker**: Mega pressure ladder analysis
4. **Linguistics Engine**: NLP for market insights
5. **Backtest Engine**: Historical strategy validation

## Related Documentation

- [Architecture Overview](../architecture/00-index.md)
- [Data Flow](../data-flow/00-index.md)
- [API Specifications](../api/00-index.md)
- [Infrastructure](../infrastructure/00-index.md)
