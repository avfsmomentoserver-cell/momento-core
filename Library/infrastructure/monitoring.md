# Monitoring Stack

## Prometheus
- Metrics collection every 15s
- Retention: 30 days
- Federation for multi-cluster

## Grafana Dashboards
- System overview
- Service performance
- Business metrics
- Alert status

## Loki Logging
- Log aggregation from all pods
- Retention: 7 days hot, 90 days cold
- Full-text search capability

## Alerting Rules
- Critical: Page on-call immediately
- Warning: Notify during business hours
- Info: Log for trending analysis

## OpenTelemetry Tracing
- Distributed tracing across services
- Sample rate: 10% for production
- Jaeger for trace visualization
