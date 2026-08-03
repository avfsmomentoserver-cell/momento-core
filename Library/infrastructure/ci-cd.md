# CI/CD Pipelines

## GitHub Actions Workflow
```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test
      - run: npm run lint
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: azure/k8s-deploy@v1
      - run: kubectl rollout status deployment/api-gateway
```

## Environments
- Development: Auto-deploy on PR
- Staging: Auto-deploy on merge to main
- Production: Manual approval required

## Rollback Strategy
- Automatic rollback on health check failure
- Blue-green deployments for zero downtime
- Database migrations are backward compatible
