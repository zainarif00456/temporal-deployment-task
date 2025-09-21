# ArgoCD GitOps Configuration

This directory contains ArgoCD configuration for GitOps-based deployment and management of the Temporal Platform.

## 🚀 Setup ArgoCD

### Install ArgoCD
```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
```

### Access ArgoCD UI
```bash
# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Access at: https://localhost:8080
# Username: admin
# Password: (from above command)
```

## 📋 Deploy Temporal Platform

### Create Application
```bash
# Apply the ArgoCD application
kubectl apply -f infrastructure/argocd/application.yaml

# Or using ArgoCD CLI
argocd app create temporal-platform \
  --repo https://github.com/stackai/temporal-platform.git \
  --path infrastructure/helm/temporal-platform \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace temporal-platform \
  --helm-set-file values=infrastructure/argocd/values-production.yaml
```

### Monitor Deployment
```bash
# Check application status
argocd app get temporal-platform

# Watch deployment
argocd app sync temporal-platform --watch

# Check application health
argocd app wait temporal-platform --health
```

## 🔧 Configuration

### Application Settings
- **Repository**: https://github.com/stackai/temporal-platform.git
- **Path**: infrastructure/helm/temporal-platform
- **Target**: HEAD (main branch)
- **Destination**: temporal-platform namespace

### Sync Policy
- **Automated Sync**: Enabled
- **Self Heal**: Enabled
- **Prune**: Enabled
- **Auto-Create Namespace**: Enabled

### Health Checks
ArgoCD monitors the health of:
- Deployments
- Services  
- Ingresses
- Persistent Volume Claims
- Custom Resources

## 📊 Observability

### Application Metrics
ArgoCD provides metrics for:
- Sync status and frequency
- Application health
- Resource status
- Deployment history

### Notifications
Configure notifications for:
- Sync failures
- Health degradation
- Out-of-sync alerts

```yaml
# Example Slack notification
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
  template.app-deployed: |
    message: Application {{.app.metadata.name}} is now running new version.
  template.app-health-degraded: |
    message: Application {{.app.metadata.name}} has degraded health.
  trigger.on-deployed: |
    - when: app.status.operationState.phase in ['Succeeded'] and app.status.health.status == 'Healthy'
      send: [app-deployed]
  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]
```

## 🔐 Security

### RBAC Configuration
```yaml
apiVersion: v1
kind: ConfigMap  
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    # Developers can view and sync applications
    p, role:developer, applications, get, *, allow
    p, role:developer, applications, sync, *, allow
    p, role:developer, repositories, get, *, allow
    
    # Admins have full access
    p, role:admin, applications, *, *, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    
    # Group mappings
    g, temporal-platform-developers, role:developer
    g, temporal-platform-admins, role:admin
```

### Secret Management
Use Sealed Secrets or External Secrets Operator:
```bash
# Example with Sealed Secrets
kubectl create secret generic temporal-secrets \
  --from-literal=postgres-password=CHANGEME \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secrets.yaml
```

## 🔄 GitOps Workflow

### Development Workflow
1. **Code Changes** → Push to feature branch
2. **PR Review** → Merge to main branch
3. **ArgoCD Sync** → Automatically deploys changes
4. **Health Check** → Verifies deployment success
5. **Notifications** → Team alerted of deployment status

### Rollback Process
```bash
# View deployment history
argocd app history temporal-platform

# Rollback to previous version
argocd app rollback temporal-platform 5

# Or rollback via UI
# Applications → temporal-platform → History → Rollback
```

## 📈 Scaling and Updates

### Resource Scaling
Update values in `values-production.yaml`:
```yaml
application:
  worker:
    replicaCount: 10  # Scale workers
  api:
    replicaCount: 5   # Scale API servers
```

### Version Updates
Update image tags in values file:
```yaml
application:
  image:
    tag: "v1.1.0"  # New version
```

ArgoCD will automatically sync the changes.

## 🚨 Troubleshooting

### Common Issues

#### Sync Failures
```bash
# Check sync status
argocd app get temporal-platform

# View sync logs
argocd app logs temporal-platform

# Manual sync
argocd app sync temporal-platform
```

#### Resource Conflicts
```bash
# Check resource diff
argocd app diff temporal-platform

# Force sync with prune
argocd app sync temporal-platform --prune --force
```

#### Health Check Failures
```bash
# Check application health
argocd app get temporal-platform --show-managed-resources

# Check Kubernetes events
kubectl get events -n temporal-platform --sort-by='.lastTimestamp'
```

## 📚 Best Practices

### Repository Structure
- Keep Helm charts in `infrastructure/helm/`
- Environment-specific values in `infrastructure/argocd/`
- Separate repositories for different environments if needed

### Application Management
- Use App-of-Apps pattern for complex deployments
- Implement proper RBAC
- Monitor sync frequency and failures
- Set up proper notifications

### Security
- Use GitOps for audit trail
- Implement proper secret management
- Regular RBAC reviews
- Monitor access patterns

This ArgoCD setup provides full GitOps observability and management for the Temporal Platform deployment.
