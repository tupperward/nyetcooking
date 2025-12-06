# GitHub Secrets Setup Guide

This guide explains how to set up the required secrets for the CI/CD pipeline.

## Required Secrets

Navigate to your repository: **Settings → Secrets and variables → Actions → New repository secret**

### 1. DOCKER_USERNAME

**Description:** Your Docker Hub username

**How to get it:**
1. Log in to https://hub.docker.com/
2. Your username is visible in the top-right corner
3. Example: `tupperward`

**How to add:**
```
Name: DOCKER_USERNAME
Value: your-docker-hub-username
```

### 2. DOCKER_PASSWORD

**Description:** Docker Hub access token (recommended) or password

**How to get it (Access Token - RECOMMENDED):**
1. Log in to https://hub.docker.com/
2. Click your username → Account Settings
3. Click "Security" → "New Access Token"
4. Description: "GitHub Actions - Nyetcooking"
5. Access permissions: "Read, Write, Delete"
6. Generate token and **copy it immediately** (won't be shown again)

**Alternative (Password - NOT RECOMMENDED):**
- Use your Docker Hub password
- Less secure, not recommended

**How to add:**
```
Name: DOCKER_PASSWORD
Value: dckr_pat_xxxxxxxxxxxxxxxxxxxxx (token)
```

### 3. KUBECONFIG

**Description:** Base64-encoded Kubernetes config file

**How to get it:**

**Option 1: Full kubeconfig (Recommended for testing)**
```bash
# Linux
cat ~/.kube/config | base64 -w 0

# macOS
cat ~/.kube/config | base64

# Copy the output
```

**Option 2: Service Account Token (Recommended for production)**

Create a service account with deployment permissions:

```bash
# 1. Create service account
kubectl create serviceaccount github-deployer -n blog

# 2. Create role with necessary permissions
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: github-deployer
  namespace: blog
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "update", "patch"]
- apiGroups: [""]
  resources: ["pods", "events"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments/rollback"]
  verbs: ["create"]
EOF

# 3. Bind role to service account
kubectl create rolebinding github-deployer-binding \
  --role=github-deployer \
  --serviceaccount=blog:github-deployer \
  -n blog

# 4. Get service account token
kubectl create token github-deployer -n blog --duration=8760h

# 5. Create kubeconfig with token
CLUSTER_URL=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
CA_CERT=$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')
TOKEN=$(kubectl create token github-deployer -n blog --duration=8760h)

cat > github-kubeconfig.yaml <<EOF
apiVersion: v1
kind: Config
clusters:
- name: kubernetes
  cluster:
    server: ${CLUSTER_URL}
    certificate-authority-data: ${CA_CERT}
contexts:
- name: github-deployer
  context:
    cluster: kubernetes
    user: github-deployer
    namespace: blog
current-context: github-deployer
users:
- name: github-deployer
  user:
    token: ${TOKEN}
EOF

# 6. Encode it
cat github-kubeconfig.yaml | base64

# 7. Copy the output and delete the file
rm github-kubeconfig.yaml
```

**How to add:**
```
Name: KUBECONFIG
Value: (paste the long base64 string)
```

## Verifying Secrets

### Test Docker Credentials Locally

```bash
echo "YOUR_DOCKER_PASSWORD" | docker login -u YOUR_DOCKER_USERNAME --password-stdin

# Expected output:
# Login Succeeded
```

### Test Kubeconfig Locally

```bash
# Decode and save temporarily
echo "YOUR_BASE64_KUBECONFIG" | base64 -d > /tmp/test-kubeconfig

# Test it
KUBECONFIG=/tmp/test-kubeconfig kubectl get nodes

# Expected: Should list your cluster nodes

# Clean up
rm /tmp/test-kubeconfig
```

## Updating Secrets

Secrets can be updated at any time:

1. Settings → Secrets and variables → Actions
2. Click on the secret name
3. Click "Update secret"
4. Enter new value
5. Click "Update secret"

## Security Best Practices

### Docker Token

- ✅ Use access token instead of password
- ✅ Set specific permissions (Read, Write, Delete for this repo)
- ✅ Create separate token for each project
- ✅ Rotate tokens every 6-12 months
- ❌ Don't share tokens
- ❌ Don't commit tokens to git

### Kubeconfig

- ✅ Use service account with minimal permissions
- ✅ Limit to specific namespace (`blog`)
- ✅ Set token expiration
- ✅ Use RBAC to restrict actions
- ❌ Don't use admin kubeconfig
- ❌ Don't grant cluster-wide permissions

### General

- ✅ Rotate secrets periodically
- ✅ Monitor secret usage in Actions logs
- ✅ Delete secrets when no longer needed
- ✅ Use environment-specific secrets for staging/prod
- ❌ Don't echo secrets in workflows
- ❌ Don't log secrets to console

## Troubleshooting

### "Error: Invalid username or password" (Docker)

**Solutions:**
1. Verify DOCKER_USERNAME is correct (case-sensitive)
2. Regenerate Docker access token
3. Ensure token has "Read, Write, Delete" permissions
4. Try logging in manually with the same credentials

### "Error: Unable to connect to the server" (Kubernetes)

**Solutions:**
1. Verify kubeconfig is properly base64 encoded
2. Check cluster endpoint is accessible from GitHub Actions
3. Ensure service account has correct permissions
4. Verify token hasn't expired
5. Test kubeconfig locally (see verification steps above)

### "Error: Unauthorized" (Kubernetes)

**Solutions:**
1. Check service account has correct RBAC permissions
2. Verify token is valid (not expired)
3. Ensure namespace is correct (`blog`)
4. Re-create role binding

### Secret Not Found in Workflow

**Solutions:**
1. Verify secret name matches exactly (case-sensitive)
2. Check secret exists in repository settings
3. Ensure you're in the correct repository
4. Refresh the Actions page

## Environment-Specific Secrets

For multiple environments (staging, production):

### Option 1: Environment Secrets

1. Settings → Environments → New environment
2. Create "production" and "staging" environments
3. Add environment-specific secrets to each

In workflow:
```yaml
environment:
  name: production  # Uses production secrets
```

### Option 2: Secret Naming

Use different secret names:
```
DOCKER_USERNAME_PROD
DOCKER_PASSWORD_PROD
KUBECONFIG_PROD

DOCKER_USERNAME_STAGING
DOCKER_PASSWORD_STAGING
KUBECONFIG_STAGING
```

In workflow:
```yaml
env:
  DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME_PROD }}
```

## Quick Setup Checklist

- [ ] Docker Hub account created
- [ ] Docker Hub repository created (`tupperward/nyetcooking`)
- [ ] Docker access token generated
- [ ] `DOCKER_USERNAME` secret added to GitHub
- [ ] `DOCKER_PASSWORD` secret added to GitHub
- [ ] Kubernetes cluster accessible
- [ ] Service account created in cluster
- [ ] RBAC permissions configured
- [ ] Kubeconfig generated and encoded
- [ ] `KUBECONFIG` secret added to GitHub
- [ ] Secrets tested locally
- [ ] First workflow run tested

## Next Steps

After setting up secrets:

1. **Test the build workflow:**
   ```bash
   git push origin main
   ```
   Check Actions tab for "Build and Push Docker Image"

2. **Verify Docker image:**
   ```bash
   docker pull tupperward/nyetcooking:latest
   ```

3. **Test deployment workflow:**
   - Should run automatically after successful build
   - Or trigger manually: Actions → Deploy to Kubernetes → Run workflow

4. **Verify deployment:**
   ```bash
   kubectl get pods -n blog -l app=nyetcooking
   ```

## Support

If you encounter issues:
1. Check workflow logs in Actions tab
2. Verify secrets are set correctly
3. Test credentials locally
4. Review `CICD_PIPELINE.md` for detailed troubleshooting
