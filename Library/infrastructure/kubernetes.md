# Kubernetes Configuration

## Cluster Architecture
- Control Plane: Managed (EKS/GKE/AKS)
- Worker Nodes: Spot + On-demand mix
- Node Groups: General, Compute-optimized, GPU

## Key Deployments
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

## Ingress Configuration
- NGINX Ingress Controller
- TLS termination at ingress
- Rate limiting per IP
- Path-based routing

## Auto-scaling
- HPA based on CPU/memory
- VPA for resource recommendations
- Cluster autoscaler for node scaling
