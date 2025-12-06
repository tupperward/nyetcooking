# GitHub Actions Workflows Summary

Quick reference guide for all CI/CD workflows in this repository.

## Workflows Overview

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **Test Suite** | `test.yml` | Push/PR | Run pytest with coverage |
| **Docker Build** | `build.yml` | Push/Tag | Build and push Docker images |
| **Deploy** | `deploy.yml` | After build / Manual | Deploy to Kubernetes |

## Workflow Files

### 1. Test Suite (`.github/workflows/test.yml`)

**When it runs:**
- Push to: `main`, `flask-rewrite`, `flask-rewrite-redis`
- Pull requests to: `main`

**What it does:**
- Runs 36 tests across Python 3.9, 3.10, 3.11
- Generates coverage reports (58% currently)
- Uploads coverage to Codecov

**Duration:** ~16 seconds per Python version

**Required secrets:** None

**How to run manually:**
```bash
# Locally
./run_tests.sh --coverage
```

---

### 2. Docker Build (`.github/workflows/build.yml`)

**When it runs:**
- Push to: `main`, `flask-rewrite`, `flask-rewrite-redis`
- Git tags: `v*` (e.g., `v1.2.3`)
- Pull requests: Build only, no push

**What it does:**
- Builds Docker image for `linux/amd64`
- Tags with branch name, SHA, version, `latest`
- Pushes to `tupperward/nyetcooking` on Docker Hub
- Uses GitHub Actions cache for speed

**Duration:** ~2-5 minutes (cached builds faster)

**Required secrets:**
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

**How to run manually:**
```bash
# Locally
docker build -t tupperward/nyetcooking:test .
docker push tupperward/nyetcooking:test
```

**Image tags generated:**
```
latest                    # main branch only
main                      # main branch
flask-rewrite-redis       # branch name
main-abc1234              # branch + commit SHA
v1.2.3                    # git tag
1.2                       # major.minor from tag
pr-42                     # pull request (build only)
```

---

### 3. Kubernetes Deploy (`.github/workflows/deploy.yml`)

**When it runs:**
- Automatically after successful Docker build
- Manually via Actions UI with custom parameters

**What it does:**
- Updates Kubernetes deployment with new image
- Performs rolling update (2 replicas, 25% surge/unavailable)
- Verifies deployment health
- Automatically rolls back on failure

**Duration:** ~1-3 minutes

**Required secrets:**
- `KUBECONFIG`

**How to run manually:**

Via GitHub UI:
1. Actions → Deploy to Kubernetes
2. Run workflow
3. Choose environment: production/staging
4. Choose image tag: latest (default) or specific tag

Via gh CLI:
```bash
gh workflow run deploy.yml \
  -f environment=production \
  -f image_tag=latest
```

Via kubectl (bypass GitHub Actions):
```bash
kubectl set image deployment/nyetcooking \
  nyetcooking=tupperward/nyetcooking:v1.2.3 \
  -n blog
kubectl rollout status deployment/nyetcooking -n blog
```

---

## Complete Flow

### Typical Push to Main

```
1. git push origin main
   ↓
2. Test workflow runs (36 tests)
   ├─ Python 3.9: ✅ Pass
   ├─ Python 3.10: ✅ Pass
   └─ Python 3.11: ✅ Pass
   ↓
3. Build workflow runs
   ├─ Build Docker image
   ├─ Tag: latest, main, main-abc1234
   └─ Push to tupperward/nyetcooking
   ↓
4. Deploy workflow runs (auto-triggered)
   ├─ Update deployment: nyetcooking
   ├─ Rolling update: 2 pods
   ├─ Health check: ✅ /health
   └─ Deployment complete
   ↓
5. Application live at https://nyetcooking.worstwizard.online
```

**Total time:** ~5-10 minutes from push to production

### Pull Request Flow

```
1. Open PR to main
   ↓
2. Test workflow runs (36 tests)
   └─ All Python versions
   ↓
3. Build workflow runs
   ├─ Build Docker image (PR)
   └─ Does NOT push (build verification only)
   ↓
4. Deploy workflow does NOT run
   ↓
5. PR ready for review with test results
```

### Hotfix/Rollback Flow

```
Option 1: Deploy previous version
1. Actions → Deploy to Kubernetes → Run workflow
2. Image tag: <previous-tag>
3. Deploy

Option 2: Kubectl rollback
kubectl rollout undo deployment/nyetcooking -n blog
```

---

## Monitoring Workflows

### GitHub Actions UI

**View all runs:**
```
Repository → Actions tab
```

**View specific workflow:**
```
Actions → [Workflow name] → Latest runs
```

**View logs:**
```
Click on run → Click on job → Expand steps
```

**View summary:**
```
Click on run → Scroll to bottom → Summary section
```

### Workflow Status Badges

Add to README.md:

```markdown
![Test Suite](https://github.com/YOUR_USERNAME/nyetcooking/workflows/Test%20Suite/badge.svg)
![Docker Build](https://github.com/YOUR_USERNAME/nyetcooking/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![Deploy](https://github.com/YOUR_USERNAME/nyetcooking/workflows/Deploy%20to%20Kubernetes/badge.svg)
```

---

## Troubleshooting

### Test workflow fails

**Check:**
```bash
# Run tests locally
./run_tests.sh

# Check Python version
python3 --version

# Check dependencies
pip3 install -r requirements.txt
```

### Build workflow fails

**Common issues:**
- Docker secrets not set → See `.github/SECRETS_SETUP.md`
- Dockerfile syntax error → Test: `docker build -t test .`
- Build context too large → Check `.dockerignore`

**Check:**
```bash
# Test build locally
docker build -t tupperward/nyetcooking:test .

# Test credentials
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
```

### Deploy workflow fails

**Common issues:**
- Kubeconfig secret invalid → Re-encode and update
- Image doesn't exist → Check Docker Hub
- Health check fails → Check application logs
- Insufficient permissions → Check RBAC

**Check:**
```bash
# Check deployment status
kubectl get deployment nyetcooking -n blog

# Check pods
kubectl get pods -n blog -l app=nyetcooking

# Check logs
kubectl logs -n blog -l app=nyetcooking --tail=50

# Manual rollback
kubectl rollout undo deployment/nyetcooking -n blog
```

---

## Workflow Customization

### Change deployment namespace

Edit `.github/workflows/deploy.yml`:
```yaml
env:
  NAMESPACE: your-namespace  # Change from 'blog'
```

### Add staging environment

1. Create `deployment-staging.yaml` in `k8s/`
2. Add environment in GitHub: Settings → Environments → New
3. Add staging secrets to environment
4. Modify `deploy.yml` to support staging namespace

### Change Docker image name

Edit `.github/workflows/build.yml` and `deploy.yml`:
```yaml
env:
  IMAGE_NAME: your-username/your-image
```

Update `k8s/deployment.yaml`:
```yaml
image: your-username/your-image
```

### Add Slack notifications

Add to workflow (after deployment):
```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Add security scanning

Add to `build.yml` (after build):
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.tags }}
    format: 'table'
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
```

---

## Quick Commands Reference

### Local Development

```bash
# Run tests
./run_tests.sh

# Run tests with coverage
./run_tests.sh --coverage

# Build Docker image
docker build -t tupperward/nyetcooking:dev .

# Run container locally
docker run -p 5000:5000 tupperward/nyetcooking:dev
```

### Triggering Workflows

```bash
# Push to trigger all workflows
git push origin main

# Create tag to trigger versioned build
git tag v1.2.3
git push origin v1.2.3

# Trigger deploy manually (requires gh CLI)
gh workflow run deploy.yml -f environment=production -f image_tag=latest
```

### Kubernetes Operations

```bash
# Check deployment
kubectl get deployment nyetcooking -n blog

# Check pods
kubectl get pods -n blog -l app=nyetcooking

# Check rollout status
kubectl rollout status deployment/nyetcooking -n blog

# View rollout history
kubectl rollout history deployment/nyetcooking -n blog

# Rollback to previous version
kubectl rollout undo deployment/nyetcooking -n blog

# Rollback to specific revision
kubectl rollout undo deployment/nyetcooking -n blog --to-revision=3

# Scale deployment
kubectl scale deployment nyetcooking -n blog --replicas=3

# Update image manually
kubectl set image deployment/nyetcooking nyetcooking=tupperward/nyetcooking:v1.2.3 -n blog
```

---

## Additional Resources

- **Detailed CI/CD docs:** `CICD_PIPELINE.md`
- **Test suite docs:** `TESTING.md`
- **Test infrastructure:** `TEST_INFRASTRUCTURE.md`
- **Secrets setup:** `.github/SECRETS_SETUP.md`

## Workflow Health

| Metric | Status |
|--------|--------|
| Tests passing | ✅ 36/36 (100%) |
| Coverage | 🟡 58% |
| Build time | ✅ ~3 min |
| Deploy time | ✅ ~2 min |
| Auto-rollback | ✅ Enabled |
| Health checks | ✅ Configured |
| Resource limits | ✅ Set |
| Secrets | ✅ Required docs available |

**Status:** Production Ready ✅
