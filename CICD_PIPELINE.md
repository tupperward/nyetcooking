# CI/CD Pipeline Documentation

This document describes the complete CI/CD pipeline for the Nyetcooking application, from testing to deployment.

## Pipeline Overview

The CI/CD pipeline consists of three main workflows:

1. **Test Suite** (`test.yml`) - Run tests on every push/PR
2. **Docker Build** (`build.yml`) - Build and push Docker images
3. **Kubernetes Deploy** (`deploy.yml`) - Deploy to Kubernetes cluster

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Push to   │ ───▶ │  Run Tests   │ ───▶ │Build Docker │
│   GitHub    │      │   (pytest)   │      │   Image     │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                      │
                            │                      ▼
                            │              ┌─────────────┐
                            │              │  Push to    │
                            │              │ Docker Hub  │
                            │              └─────────────┘
                            │                      │
                            ▼                      ▼
                     ┌──────────────┐      ┌─────────────┐
                     │ Tests Failed │      │   Deploy    │
                     │  Stop Here   │      │to Kubernetes│
                     └──────────────┘      └─────────────┘
```

## Workflow Details

### 1. Test Suite (`test.yml`)

**Trigger:** Push or PR to `main`, `flask-rewrite`, `flask-rewrite-redis`

**What it does:**
- Runs on Python 3.9, 3.10, 3.11 (matrix)
- Installs dependencies from `requirements.txt`
- Runs pytest with coverage
- Generates coverage reports (terminal, XML, HTML)
- Uploads coverage to Codecov (optional)
- Stores coverage artifacts

**Exit conditions:**
- ✅ Success: All 36 tests pass
- ❌ Failure: Any test fails

**Outputs:**
- Test results in stdout
- Coverage reports as artifacts
- Coverage percentage in summary

**Configuration:**
```yaml
on:
  push:
    branches: [ main, flask-rewrite, flask-rewrite-redis ]
  pull_request:
    branches: [ main ]
```

### 2. Docker Build (`build.yml`)

**Trigger:** Push to main branches or version tags

**What it does:**
- Sets up Docker Buildx for multi-platform builds
- Logs into Docker Hub (requires secrets)
- Generates tags based on:
  - Branch name (e.g., `main`, `flask-rewrite-redis`)
  - PR number (e.g., `pr-123`)
  - Git tags (e.g., `v1.2.3`, `1.2`)
  - Commit SHA (e.g., `main-abc1234`)
  - `latest` tag for main branch
- Builds Docker image for `linux/amd64`
- Pushes to Docker Hub as `tupperward/nyetcooking`
- Uses GitHub Actions cache for faster builds

**Exit conditions:**
- ✅ Success: Image built and pushed
- ❌ Failure: Build error or authentication failure

**Outputs:**
- Docker image pushed to `tupperward/nyetcooking`
- Multiple tags as described above
- Build summary in GitHub Actions

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password or token

**Image Tags Examples:**
```
tupperward/nyetcooking:latest              # Main branch
tupperward/nyetcooking:main                # Main branch
tupperward/nyetcooking:flask-rewrite-redis # Branch name
tupperward/nyetcooking:main-abc1234        # Branch + SHA
tupperward/nyetcooking:v1.2.3              # Git tag
tupperward/nyetcooking:1.2                 # Major.minor
tupperward/nyetcooking:pr-42               # Pull request
```

### 3. Kubernetes Deploy (`deploy.yml`)

**Trigger:**
- Automatically after successful Docker build (workflow_run)
- Manually via workflow_dispatch with custom parameters

**What it does:**
- Sets up kubectl
- Configures kubeconfig from secrets
- Determines correct image tag to deploy
- Updates Kubernetes deployment with new image
- Performs rolling update (25% surge, 25% unavailable)
- Waits for rollout to complete (5 min timeout)
- Verifies deployment and pod health
- Checks application `/health` endpoint
- Automatically rolls back on failure

**Exit conditions:**
- ✅ Success: All pods healthy, health check passes
- ❌ Failure: Rollout fails or health check fails (auto-rollback)

**Outputs:**
- Deployment status
- Pod status
- Recent events
- Health check response
- Success/failure notification

**Required Secrets:**
- `KUBECONFIG` - Base64-encoded kubeconfig file

**Configuration:**
```yaml
env:
  NAMESPACE: blog
  DEPLOYMENT_NAME: nyetcooking
  IMAGE_NAME: tupperward/nyetcooking
```

**Manual Deployment:**
You can manually trigger deployment via GitHub Actions UI:
1. Go to Actions → Deploy to Kubernetes
2. Click "Run workflow"
3. Select environment (production/staging)
4. Optionally specify image tag (default: latest)

## Kubernetes Deployment Strategy

The deployment uses a **RollingUpdate** strategy:

```yaml
strategy:
  rollingUpdate:
    maxSurge: 25%        # Allow 25% more pods during update
    maxUnavailable: 25%  # Allow 25% pods to be unavailable
  type: RollingUpdate
```

With 2 replicas, this means:
- During deployment: 1-3 pods running
- Maximum 1 pod unavailable at a time
- New pods start before old ones terminate

**Health Checks:**
- **Readiness Probe**: Checks `/health` every 5s after 10s delay
- **Liveness Probe**: Checks `/health` every 10s after 30s delay

**Resource Limits:**
```yaml
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 200m
    memory: 256Mi
```

## Environment Variables

The application deployment receives:

```yaml
env:
  - name: REDIS_HOST
    value: redis-service
  - name: REDIS_PORT
    value: "6379"
```

## Complete Pipeline Flow

### Scenario 1: Feature Branch Push

```
1. Developer pushes to `flask-rewrite-redis` branch
2. Test workflow runs
   ├─ Runs on Python 3.9, 3.10, 3.11
   ├─ All tests pass ✅
   └─ Coverage: 58%
3. Build workflow runs
   ├─ Builds Docker image
   ├─ Tags: flask-rewrite-redis, flask-rewrite-redis-abc1234
   └─ Pushes to Docker Hub ✅
4. Deploy workflow runs
   ├─ Pulls image: tupperward/nyetcooking:flask-rewrite-redis-abc1234
   ├─ Updates deployment in namespace 'blog'
   ├─ Rolling update: 2 pods → new image
   ├─ Health check: ✅ healthy
   └─ Deployment complete ✅
```

### Scenario 2: Pull Request

```
1. Developer opens PR to `main`
2. Test workflow runs
   ├─ Runs on Python 3.9, 3.10, 3.11
   └─ All tests pass ✅
3. Build workflow runs (build only)
   ├─ Builds Docker image
   ├─ Tags: pr-42
   └─ Does NOT push (PR only builds)
4. Deploy workflow does NOT run
```

### Scenario 3: Main Branch Release

```
1. PR merged to `main` or tag `v1.2.3` pushed
2. Test workflow runs ✅
3. Build workflow runs
   ├─ Builds Docker image
   ├─ Tags: latest, main, v1.2.3, 1.2, main-abc1234
   └─ Pushes to Docker Hub ✅
4. Deploy workflow runs
   ├─ Pulls image: tupperward/nyetcooking:latest
   ├─ Updates production deployment
   ├─ Rolling update with health checks
   └─ Deployment complete ✅
```

### Scenario 4: Deployment Failure & Rollback

```
1. Deploy workflow starts
2. New image deployed
3. Health check fails ❌
4. Automatic rollback triggered
   ├─ kubectl rollout undo
   ├─ Previous version restored
   └─ Deployment stable ✅
5. Workflow fails with error
6. Notifications sent
```

## Setting Up the Pipeline

### Prerequisites

1. **GitHub Repository Secrets**

Navigate to Settings → Secrets and variables → Actions, add:

```
DOCKER_USERNAME=<your-docker-hub-username>
DOCKER_PASSWORD=<your-docker-hub-token>
KUBECONFIG=<base64-encoded-kubeconfig>
```

To encode kubeconfig:
```bash
cat ~/.kube/config | base64 -w 0  # Linux
cat ~/.kube/config | base64        # macOS
```

2. **Docker Hub Repository**

Create repository: `tupperward/nyetcooking`

3. **Kubernetes Cluster**

Ensure cluster is accessible and namespace exists:
```bash
kubectl create namespace blog
```

4. **Kubernetes Resources**

Apply existing manifests:
```bash
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/deployment.yaml
```

### Initial Setup Commands

```bash
# 1. Verify tests pass locally
./run_tests.sh

# 2. Build Docker image locally (test)
docker build -t tupperward/nyetcooking:test .

# 3. Test image locally
docker run -p 5000:5000 tupperward/nyetcooking:test

# 4. Push to GitHub (triggers pipeline)
git push origin main
```

## Monitoring Deployments

### GitHub Actions UI

1. Go to repository → Actions tab
2. See workflow runs for each pipeline
3. Click on run to see detailed logs
4. Check summary for deployment status

### Kubernetes Cluster

```bash
# Watch deployment rollout
kubectl rollout status deployment/nyetcooking -n blog

# Check deployment history
kubectl rollout history deployment/nyetcooking -n blog

# Get pod status
kubectl get pods -n blog -l app=nyetcooking

# Check logs
kubectl logs -n blog -l app=nyetcooking --tail=50 -f

# Check events
kubectl get events -n blog --sort-by='.lastTimestamp'

# Manual rollback (if needed)
kubectl rollout undo deployment/nyetcooking -n blog

# Rollback to specific revision
kubectl rollout undo deployment/nyetcooking -n blog --to-revision=3
```

### Application Health

```bash
# Port-forward to pod
kubectl port-forward -n blog deployment/nyetcooking 5000:5000

# Check health endpoint
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-06T12:00:00Z",
  "cache_backend": "redis"
}
```

## Troubleshooting

### Build Fails

**Problem:** Docker build fails

**Solutions:**
```bash
# Check Dockerfile syntax
docker build -t test .

# Check requirements.txt
pip install -r requirements.txt

# Review build logs in GitHub Actions
```

### Tests Fail in CI

**Problem:** Tests pass locally but fail in CI

**Solutions:**
```bash
# Check Python version
python3 --version

# Run tests in clean environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run_tests.sh

# Check for environment-specific issues
```

### Deployment Fails

**Problem:** Kubernetes deployment rollout fails

**Solutions:**
```bash
# Check pod status
kubectl describe pod -n blog -l app=nyetcooking

# Check pod logs
kubectl logs -n blog -l app=nyetcooking --tail=100

# Check image pull
kubectl get events -n blog | grep -i pull

# Verify image exists
docker pull tupperward/nyetcooking:latest

# Manual rollback
kubectl rollout undo deployment/nyetcooking -n blog
```

### Health Check Fails

**Problem:** `/health` endpoint returns unhealthy

**Solutions:**
```bash
# Port-forward to pod
kubectl port-forward -n blog pod/<pod-name> 5000:5000

# Test health endpoint
curl -v http://localhost:5000/health

# Check Redis connectivity
kubectl exec -n blog -it <pod-name> -- sh
# Inside pod:
curl http://redis-service:6379

# Check environment variables
kubectl exec -n blog <pod-name> -- env | grep REDIS
```

### Secrets Not Working

**Problem:** Docker or kubectl authentication fails

**Solutions:**
```bash
# Re-encode and update KUBECONFIG secret
cat ~/.kube/config | base64 | pbcopy

# Test Docker credentials locally
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Verify secrets exist in GitHub
# Settings → Secrets and variables → Actions
```

## Pipeline Optimization

### Speed Improvements

1. **Cache dependencies:**
   - Already enabled for pip (test workflow)
   - Already enabled for Docker layers (build workflow)

2. **Parallel matrix testing:**
   - Already running Python 3.9, 3.10, 3.11 in parallel

3. **Conditional workflows:**
   - Deploy only runs after successful build
   - Build skips push for PRs

### Security Best Practices

1. **Use secrets for sensitive data:**
   - Never hardcode credentials
   - Use GitHub encrypted secrets
   - Rotate credentials regularly

2. **Least privilege access:**
   - Kubeconfig should have minimal required permissions
   - Docker token should be read-only if possible

3. **Image scanning:**
   - Consider adding Trivy or Snyk scans to build workflow

### Cost Optimization

1. **PR builds don't push:**
   - Saves Docker Hub storage
   - Reduces build time

2. **Workflow caching:**
   - GitHub Actions cache reduces build time
   - Saves runner minutes

3. **Deploy only on success:**
   - Prevents wasted deployments

## Advanced Usage

### Deploy Specific Version

Via GitHub Actions UI:
1. Actions → Deploy to Kubernetes → Run workflow
2. Environment: production
3. Image tag: `v1.2.3`
4. Run workflow

Via CLI (requires gh CLI):
```bash
gh workflow run deploy.yml \
  -f environment=production \
  -f image_tag=v1.2.3
```

### Canary Deployments

Modify deployment strategy in `k8s/deployment.yaml`:

```yaml
spec:
  replicas: 4
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
```

### Blue-Green Deployments

Create separate deployments:
```bash
# Blue (current)
kubectl apply -f k8s/deployment-blue.yaml

# Green (new)
kubectl apply -f k8s/deployment-green.yaml

# Switch traffic (update service selector)
kubectl patch service nyetcooking -n blog -p '{"spec":{"selector":{"version":"green"}}}'
```

## Metrics and Observability

### Deployment Metrics

Track in your monitoring system:
- Deployment frequency
- Deployment success rate
- Rollback frequency
- Time to deploy
- Test coverage over time

### Application Metrics

Monitor:
- Pod restart count
- Request latency
- Error rates
- Cache hit rates (Redis)
- Resource usage (CPU/memory)

### Recommended Tools

- **Prometheus** - Metrics collection
- **Grafana** - Dashboards
- **Loki** - Log aggregation
- **ArgoCD** - GitOps deployments (alternative to this pipeline)

## Summary

Your CI/CD pipeline is now:
- ✅ **Fully automated** - Push to deploy
- ✅ **Safe** - Tests must pass, health checks, auto-rollback
- ✅ **Fast** - Parallel testing, caching, rolling updates
- ✅ **Visible** - Detailed logs, summaries, notifications
- ✅ **Flexible** - Manual triggers, multiple environments
- ✅ **Production-ready** - Kubernetes rolling updates with health checks

The complete flow from code push to production deployment is fully automated and safe!
