# Architecture Documentation Index

## Overview

This directory contains comprehensive architecture documentation for the Momento Core platform, analyzing the current system structure and documenting the path toward V6 microservices architecture.

## Documents

| Document | Description | Source |
|----------|-------------|--------|
| [00-system-overview.md](./00-system-overview.md) | Complete system overview and pipeline | docs/system/00-index.md |
| [01-architecture-analysis.md](./01-architecture-analysis.md) | Detailed architecture layer analysis | docs/system/01-architecture.md |
| [02-microservices-strategy.md](./02-microservices-strategy.md) | Service separation strategy for V6 | MOMENTO_V6_SPECIFICATION.md |
| [03-scalability-patterns.md](./03-scalability-patterns.md) | Scaling patterns and auto-scaling design | MOMENTO_V6_SPECIFICATION.md |

## Key Architecture Concepts

### Current Architecture (v4)

```
Collector → Ingest API → Analysis → Forecast Engine → Database → Dashboard
```

**Technology Stack:**
- Backend: Python 3.10+, FastAPI, SQLAlchemy, SQLite (WAL mode)
- Frontend: Vite + React 18 + TypeScript, shadcn/ui, TailwindCSS
- Realtime: Custom WebSocket hub (single multiplexed connection)
- Collection: Playwright browser automation + provably-fair live engine

### Target Architecture (V6)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   COLLECTOR  │  │   ANALYSIS   │  │  FORECAST    │
│   SERVICE    │  │   SERVICE    │  │   SERVICE    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                ┌────────▼────────┐
                │  EVENT BUS      │
                │  (NATS/RabbitMQ)│
                └────────┬────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐
│ORCHESTRATOR  │  │  LINGUISTICS │  │   DECISION   │
│   SERVICE    │  │   SERVICE    │  │   ENGINE     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                ┌────────▼────────┐
                │   API GATEWAY   │
                │   (Kong/Traefik)│
                └────────┬────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐
│ OPERATOR     │  │  CONSUMER    │  │   ADMIN      │
│  CONSOLE     │  │     APP      │  │  DASHBOARD   │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Service Definitions

| Service | Responsibility | Tech Stack | Scaling Strategy |
|---------|---------------|------------|------------------|
| Collector Service | Data ingestion, validation, deduplication | Python/FastAPI, Playwright | Event-driven, queue-based |
| Analysis Service | Pattern detection, feature extraction | Python/NumPy, Rust for compute-heavy | CPU-bound, horizontal |
| Forecast Service | Prediction models, confidence scoring | Python/PyTorch, ONNX runtime | GPU-accelerated, batch |
| Orchestrator Service | Decision logic, risk management | Python/FastAPI, Redis for state | Stateful, replicated |
| Linguistics Service | Semantic layer, vocabulary growth | Python/NLTK, Vector DB | Memory-bound, cached |
| Decision Engine | Trade execution logic, bankroll mgmt | Python/FastAPI, PostgreSQL | Transactional, ACID |
| API Gateway | Routing, auth, rate limiting | Kong/Traefik, Lua scripts | Edge-distributed |

## Core Design Principles

Each service must be:
- **Independently Deployable**: Containerized with Docker/Kubernetes
- **Autoscalable**: Horizontal scaling based on load metrics
- **Fault-Tolerant**: Circuit breakers, retries, fallbacks
- **Observable**: Metrics, logs, traces exported to central monitoring
- **Interoperable**: REST + gRPC + Event-driven communication

## The Momento Kernel

Core components that define the platform:
- **Round Event Model** — core data structure for a crash round
- **Database Layer** — SQLAlchemy ORM over SQLite
- **Schema Contracts** — explicit contracts between modules
- **Runtime / Event Bus** — event-driven communication
- **API Contracts** — REST + WebSocket
- **Engine Registry** — plugin system for analyzers

## Intelligence Engine Chain

```
Pattern → DNA → Similarity → Probability → Confidence → Forecast
```

Each engine is replaceable behind a clear contract, independently tested, and produces measurable output.

## Related Documentation

- [Backend Services](../backend/README.md)
- [Frontend Architecture](../frontend/README.md)
- [Infrastructure](../infrastructure/README.md)
- [Data Flow](../data-flow/README.md)

## Research Findings

Architecture decisions are informed by research findings documented in:
- [DNA Analysis Research](../research/dna-analysis.md)
- [Pressure Analysis](../research/pressure-analysis.md)
- [Time-Based Patterns](../research/time-patterns.md)

---

**Generated**: 2026-08-03  
**Source Documents**: docs/system/, MOMENTO_V6_SPECIFICATION.md
