# Infrastructure Overview

## Core Components
- [Kubernetes](./kubernetes.md) - Container orchestration
- [Monitoring](./monitoring.md) - Prometheus/Grafana/Loki stack
- [Security](./security.md) - Security configurations and policies
- [CI/CD](./ci-cd.md) - Continuous integration and deployment

## Cloud Provider
- Primary: AWS/GCP/Azure (multi-cloud ready)
- Regions: US-East, EU-West, Asia-Pacific
- Availability Zones: 3+ per region

## Key Services
- Compute: Kubernetes clusters (EKS/GKE/AKS)
- Database: RDS PostgreSQL, TimescaleDB
- Cache: ElastiCache Redis
- Message Queue: MSK Kafka / NATS
- Storage: S3 for objects, EBS for volumes
