# Microservices Separation Strategy

## Service Boundaries

### Core Services

#### 1. Ingestion Service
- **Responsibility**: Real-time market data intake
- **Technology**: FPGA acceleration, WebSocket handlers
- **Dependencies**: Message queue, time-series DB
- **Scaling**: Horizontal based on data volume

#### 2. Analysis Service
- **Responsibility**: Pattern recognition, DNA matching
- **Technology**: GPU computing (CUDA), ML models
- **Dependencies**: Cache, pattern database
- **Scaling**: GPU instance autoscaling

#### 3. Pressure Service
- **Responsibility**: Mega pressure tracking, ladder analysis
- **Technology**: Real-time computation engine
- **Dependencies**: Time-series data, cache layer
- **Scaling**: Compute-optimized instances

#### 4. Linguistics Service
- **Responsibility**: NLP for insights, vocabulary processing
- **Technology**: Transformer models, rule engines
- **Dependencies**: Knowledge graph, cache
- **Scaling**: CPU-optimized with memory

#### 5. API Gateway Service
- **Responsibility**: Request routing, authentication
- **Technology**: Reverse proxy, JWT validation
- **Dependencies**: Auth service, rate limiter
- **Scaling**: Stateless horizontal scaling

#### 6. User Service
- **Responsibility**: Authentication, authorization, profiles
- **Technology**: OAuth2, JWT, PostgreSQL
- **Dependencies**: Session store, email service
- **Scaling**: Standard horizontal scaling

#### 7. Notification Service
- **Responsibility**: Alerts, emails, push notifications
- **Technology**: Message queue, SMTP, Firebase
- **Dependencies**: User preferences, templates
- **Scaling**: Event-driven scaling

#### 8. Backtest Service
- **Responsibility**: Historical strategy testing
- **Technology**: Batch processing, parallel computation
- **Dependencies**: Historical data, compute cluster
- **Scaling**: On-demand batch scaling

## Communication Patterns

### Synchronous
- REST APIs for request/response
- gRPC for inter-service calls (performance-critical)
- GraphQL for flexible frontend queries

### Asynchronous
- NATS/RabbitMQ for event streaming
- Kafka for audit logs and analytics
- WebSockets for real-time updates

## Service Discovery

- **Kubernetes Services**: Internal DNS-based discovery
- **Service Mesh**: Istio for traffic management
- **Health Checks**: Prometheus-based monitoring

## Data Consistency

- **Eventual Consistency**: For non-critical data
- **Saga Pattern**: For distributed transactions
- **CQRS**: Separate read/write models where needed

## Related Documents

- [System Design](./01-system-design.md)
- [Scalability Patterns](./03-scalability.md)
- [Backend Core Services](../backend/core-services.md)
- [Infrastructure Overview](../infrastructure/00-index.md)
