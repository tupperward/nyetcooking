# CI/CD Quick Start Guide

Get your CI/CD pipeline up and running in 5 minutes.

## Prerequisites

- [ ] GitHub repository for this project
- [ ] Docker Hub account
- [ ] Kubernetes cluster with `kubectl` access
- [ ] Namespace `blog` exists in cluster

## Step 1: Setup GitHub Secrets (2 minutes)

### 1.1 Docker Hub Token

```bash
# 1. Go to https://hub.docker.com/settings/security
# 2. Create new access token: "GitHub Actions - Nyetcooking"
# 3. Copy the token (dckr_pat_xxxx...)
```

### 1.2 Encode Kubeconfig

```bash
# macOS
cat ~/.kube/config | base64 | pbcopy

# Linux
cat ~/.kube/config | base64 -w 0 | xclip -selection clipboard
```

### 1.3 Add Secrets to GitHub

Go to: **Repository → Settings → Secrets and variables → Actions**

Add three secrets:

| Name | Value |
|------|-------|
| `DOCKER_USERNAME` | Your Docker Hub username (e.g., `tupperward`) |
| `DOCKER_PASSWORD` | The token from step 1.1 |
| `KUBECONFIG` | The base64 string from step 1.2 |

## Step 2: Verify Kubernetes Setup (1 minute)

```bash
# Ensure namespace exists
kubectl create namespace blog

# Apply Kubernetes manifests
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/deployment.yaml

# Verify resources
kubectl get all -n blog
```

## Step 3: Test Locally (1 minute)

```bash
# Run tests
./run_tests.sh

# Build Docker image
docker build -t tupperward/nyetcooking:test .

# Run locally
docker run -p 5000:5000 tupperward/nyetcooking:test

# Test in browser: http://localhost:5000/health
```

## Step 4: Trigger Pipeline (1 minute)

```bash
# Push to main branch
git add .
git commit -m "Enable CI/CD pipeline"
git push origin main
```

## Step 5: Monitor Deployment (2-5 minutes)

### Watch in GitHub

1. Go to **Actions** tab
2. See three workflows running:
   - ✅ Test Suite (~16 seconds)
   - ✅ Build and Push Docker Image (~3 minutes)
   - ✅ Deploy to Kubernetes (~2 minutes)

### Watch in Kubernetes

```bash
# Watch deployment rollout
kubectl rollout status deployment/nyetcooking -n blog

# Watch pods
kubectl get pods -n blog -l app=nyetcooking -w

# Check logs
kubectl logs -n blog -l app=nyetcooking --tail=50 -f
```

## Step 6: Verify Success

### Check Application

```bash
# Port-forward to pod
kubectl port-forward -n blog deployment/nyetcooking 5000:5000

# Test health endpoint
curl http://localhost:5000/health

# Expected response:
# {"status":"healthy","timestamp":"...","cache_backend":"redis"}
```

### Check Deployment

```bash
# Get deployment info
kubectl get deployment nyetcooking -n blog

# Expected output:
# NAME          READY   UP-TO-DATE   AVAILABLE   AGE
# nyetcooking   2/2     2            2           5m
```

## What Just Happened?

1. ✅ **Tests ran** - All 36 tests passed with 58% coverage
2. ✅ **Image built** - Docker image built for linux/amd64
3. ✅ **Image pushed** - Pushed to `tupperward/nyetcooking:latest`
4. ✅ **Deployment updated** - Kubernetes rolling update completed
5. ✅ **Health verified** - Application health check passed

## Next Steps

### Make a Change

```bash
# Edit code
vim web/app.py

# Run tests locally
./run_tests.sh

# Commit and push
git add .
git commit -m "Update feature"
git push origin main

# Watch it deploy automatically!
```

### Create a Release

```bash
# Tag a version
git tag v1.0.0
git push origin v1.0.0

# This will:
# - Build image with tags: v1.0.0, 1.0, latest
# - Deploy to Kubernetes
```

### Manual Deployment

```bash
# Via GitHub Actions UI:
# 1. Actions → Deploy to Kubernetes → Run workflow
# 2. Choose: production
# 3. Image tag: latest (or specific version)
# 4. Click "Run workflow"

# Via gh CLI:
gh workflow run deploy.yml -f environment=production -f image_tag=v1.0.0
```

### Rollback

```bash
# Quick rollback
kubectl rollout undo deployment/nyetcooking -n blog

# Rollback to specific version
kubectl rollout undo deployment/nyetcooking -n blog --to-revision=3

# Check history
kubectl rollout history deployment/nyetcooking -n blog
```

## Troubleshooting

### ❌ "Error: Invalid username or password"

**Problem:** Docker credentials invalid

**Solution:**
```bash
# Test credentials locally
echo "YOUR_TOKEN" | docker login -u YOUR_USERNAME --password-stdin

# If fails, regenerate token at hub.docker.com
# Update DOCKER_PASSWORD secret in GitHub
```

### ❌ "Error: Unable to connect to server"

**Problem:** Kubeconfig invalid

**Solution:**
```bash
# Test kubeconfig locally
echo "YOUR_BASE64_STRING" | base64 -d > /tmp/test.config
KUBECONFIG=/tmp/test.config kubectl get nodes
rm /tmp/test.config

# If fails, re-encode and update KUBECONFIG secret
cat ~/.kube/config | base64 | pbcopy
```

### ❌ Tests fail in CI

**Problem:** Tests pass locally but fail in CI

**Solution:**
```bash
# Check Python version matches CI
python3 --version  # Should be 3.9, 3.10, or 3.11

# Run in clean environment
python3 -m venv clean-env
source clean-env/bin/activate
pip install -r requirements.txt
./run_tests.sh
deactivate
rm -rf clean-env
```

### ❌ Deployment fails

**Problem:** Kubernetes deployment rollout fails

**Solution:**
```bash
# Check pod status
kubectl describe pod -n blog -l app=nyetcooking

# Check logs
kubectl logs -n blog -l app=nyetcooking --tail=100

# Check events
kubectl get events -n blog --sort-by='.lastTimestamp' | tail -20

# Manual rollback
kubectl rollout undo deployment/nyetcooking -n blog
```

## Pipeline Overview

```
Code Change
    ↓
GitHub Push
    ↓
Test Suite (16s)
    ├─ Python 3.9  ✅
    ├─ Python 3.10 ✅
    └─ Python 3.11 ✅
    ↓
Docker Build (3m)
    ├─ Build image
    ├─ Tag: latest, main, main-abc1234
    └─ Push to Docker Hub
    ↓
Deploy to K8s (2m)
    ├─ Rolling update (2 replicas)
    ├─ Health check
    └─ Verify deployment
    ↓
Production Live! 🚀
```

**Total time:** 5-10 minutes from push to production

## Workflow Files

All workflows are in `.github/workflows/`:

- **test.yml** - Runs pytest with coverage
- **build.yml** - Builds and pushes Docker image
- **deploy.yml** - Deploys to Kubernetes with rolling update

## Documentation

- **Full CI/CD docs:** `CICD_PIPELINE.md`
- **Secrets setup guide:** `.github/SECRETS_SETUP.md`
- **Workflow summary:** `WORKFLOWS_SUMMARY.md`
- **Testing guide:** `TESTING.md`

## Success Checklist

After following this guide, you should have:

- ✅ Three GitHub secrets configured
- ✅ Kubernetes cluster with resources deployed
- ✅ Tests passing locally and in CI
- ✅ Docker image built and pushed automatically
- ✅ Application deployed to Kubernetes
- ✅ Health checks passing
- ✅ Rolling updates working
- ✅ Auto-rollback on failure

## Quick Commands

```bash
# Run tests locally
./run_tests.sh --coverage

# Build and run locally
docker build -t test . && docker run -p 5000:5000 test

# Trigger deployment
git push origin main

# Watch deployment
kubectl rollout status deployment/nyetcooking -n blog

# Check health
kubectl port-forward -n blog deployment/nyetcooking 5000:5000
curl http://localhost:5000/health

# Rollback if needed
kubectl rollout undo deployment/nyetcooking -n blog
```

## Support

If you encounter issues:

1. Check workflow logs: Repository → Actions → Click on failed run
2. Review detailed docs: `CICD_PIPELINE.md`
3. Verify secrets: `.github/SECRETS_SETUP.md`
4. Test components individually (tests, build, deploy)

## You're Done! 🎉

Your CI/CD pipeline is now fully operational. Every push to `main` will automatically:

1. Run comprehensive tests
2. Build a Docker image
3. Deploy to your Kubernetes cluster
4. Verify health
5. Rollback if anything fails

Welcome to continuous deployment!
