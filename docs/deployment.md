# Deployment Guide

This guide covers deploying the Temporal Platform to production on Render.com and development environments using Docker and Kubernetes.

## 🚀 Render.com Production Deployment

### Prerequisites
- GitHub repository with the code
- Render.com account
- Domain name (optional, for custom domains)

### Step 1: Repository Setup
1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Initial Temporal Platform implementation"
   git push origin main
   ```

### Step 2: Connect Repository to Render
1. Log into [Render.com](https://render.com)
2. Click "New" → "Blueprint"
3. Connect your GitHub repository
4. Select the repository and branch (main)

### Step 3: Environment Variables
Set these environment variables in Render dashboard:
```bash
# Production Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Temporal Configuration (will be auto-configured)
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=temporal-platform-task-queue

# Performance Settings
MAX_CONCURRENT_WORKFLOWS=1000
MAX_CONCURRENT_ACTIVITIES=1000

# Monitoring
ENABLE_METRICS=true
ENABLE_HEALTH_CHECKS=true
```

### Step 4: Deploy Services
Render will automatically deploy all services defined in `render.yaml`:
- ✅ PostgreSQL databases (2 instances)
- ✅ Elasticsearch cluster
- ✅ Temporal Frontend service
- ✅ Temporal History service
- ✅ Temporal Matching service
- ✅ Temporal Worker service
- ✅ Temporal UI
- ✅ Python application workers
- ✅ REST API gateway

### Step 5: Verify Deployment
1. **Check service status** in Render dashboard
2. **Access Temporal UI** at the provided URL
3. **Test API endpoint**: `curl https://your-api-url/health`
4. **Run health check**:
   ```bash
   curl https://your-api-url/health
   ```

### Step 6: Configure Domain (Optional)
1. Go to service settings in Render
2. Add custom domain
3. Configure DNS settings
4. Enable HTTPS (automatic with Render)

## 🏗️ Development Environment

### Docker Compose Setup
1. **Start services**
   ```bash
   docker-compose up -d
   ```

2. **Wait for services to be ready**
   ```bash
   # Check logs
   docker-compose logs -f
   ```

3. **Run application**
   ```bash
   poetry run temporal-platform start-worker
   ```

### Dev Container Setup (VS Code)
1. **Open in VS Code**
   ```bash
   code .
   ```

2. **Reopen in container**
   - Press `F1`
   - Select "Dev Containers: Reopen in Container"
   - Wait for container build

3. **Services are auto-configured**
   - Temporal UI: http://localhost:8080
   - API: http://localhost:8000
   - Elasticsearch: http://localhost:9200
   - PostgreSQL: localhost:5432

## ☸️ Kubernetes Deployment

### Prerequisites
- Kubernetes cluster
- Helm 3.x
- kubectl configured

### Step 1: Install Dependencies
```bash
# Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add elastic https://helm.elastic.co
helm repo update
```

### Step 2: Deploy with Helm
```bash
# Create namespace
kubectl create namespace temporal-platform

# Install the chart
helm install temporal-platform ./infrastructure/helm/temporal-platform \
  --namespace temporal-platform \
  --values ./infrastructure/helm/temporal-platform/values.yaml
```

### Step 3: Configure Ingress (if needed)
```yaml
# values-production.yaml
temporalUI:
  ingress:
    enabled: true
    className: "nginx"
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
    hosts:
      - host: temporal-ui.yourdomain.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: temporal-ui-tls
        hosts:
          - temporal-ui.yourdomain.com

application:
  api:
    service:
      type: ClusterIP
    ingress:
      enabled: true
      className: "nginx"
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt-prod"
      hosts:
        - host: api.yourdomain.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: api-tls
          hosts:
            - api.yourdomain.com
```

### Step 4: Apply Production Values
```bash
helm upgrade temporal-platform ./infrastructure/helm/temporal-platform \
  --namespace temporal-platform \
  --values ./infrastructure/helm/temporal-platform/values.yaml \
  --values ./values-production.yaml
```

## 🔧 Configuration Management

### Environment-Specific Settings

#### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text
MAX_CONCURRENT_WORKFLOWS=10
MAX_CONCURRENT_ACTIVITIES=20
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
MAX_CONCURRENT_WORKFLOWS=100
MAX_CONCURRENT_ACTIVITIES=200
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
LOG_FORMAT=json
MAX_CONCURRENT_WORKFLOWS=1000
MAX_CONCURRENT_ACTIVITIES=1000
```

### Database Configuration
```bash
# PostgreSQL settings
POSTGRESQL_POOL_SIZE=20
POSTGRESQL_MAX_OVERFLOW=30
POSTGRESQL_POOL_TIMEOUT=30

# Connection strings (auto-generated in Render)
POSTGRESQL_DSN=postgresql://user:pass@host:port/db
```

### Performance Tuning
```bash
# Workflow settings
WORKFLOW_EXECUTION_TIMEOUT_SECONDS=3600
ACTIVITY_EXECUTION_TIMEOUT_SECONDS=300
ACTIVITY_RETRY_MAXIMUM_ATTEMPTS=5

# Heartbeat settings
HEARTBEAT_INTERVAL_SECONDS=10
PROGRESS_UPDATE_INTERVAL_SECONDS=5

# Resource limits
MAX_MEMORY_MB=1024
MAX_CPU_CORES=2
```

## 📊 Monitoring Setup

### Prometheus Metrics
Metrics are exposed at `/metrics` endpoint:
```bash
# Scrape configuration
scrape_configs:
  - job_name: 'temporal-platform'
    static_configs:
      - targets: ['api.yourdomain.com:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

### Health Checks
Health check endpoints:
- **Application**: `/health`
- **Temporal UI**: `/`
- **Elasticsearch**: `/_cluster/health`
- **PostgreSQL**: Connection-based

### Log Aggregation
Structured JSON logs can be collected by:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Fluentd/Fluent Bit
- Datadog
- New Relic

## 🔐 Security Configuration

### TLS/SSL
```bash
# Enable TLS
ENABLE_TLS=true
TLS_CERT_PATH=/path/to/cert.pem
TLS_KEY_PATH=/path/to/key.pem

# Or use Render's automatic HTTPS
# (No configuration needed)
```

### Authentication
```bash
# JWT settings
JWT_SECRET=your-secret-key
ENABLE_AUTH=true
API_KEY_HEADER=X-API-Key
```

### Network Security
- Use private networks for internal communication
- Configure firewall rules
- Enable VPC peering if needed

## 🚨 Troubleshooting

### Common Issues

#### Service Not Starting
```bash
# Check logs
docker-compose logs service-name
# or in Kubernetes
kubectl logs deployment/service-name -n temporal-platform
```

#### Database Connection Issues
```bash
# Test PostgreSQL connection
pg_isready -h hostname -p port -U username

# Check environment variables
echo $POSTGRESQL_DSN
```

#### Temporal Server Issues
```bash
# Check cluster health
temporal operator cluster health --address frontend:7233

# List namespaces
temporal operator namespace list
```

#### Elasticsearch Issues
```bash
# Check cluster health
curl http://elasticsearch:9200/_cluster/health

# Check indices
curl http://elasticsearch:9200/_cat/indices
```

### Performance Issues

#### High Memory Usage
1. Check metrics at `/metrics`
2. Adjust resource limits
3. Tune garbage collection
4. Scale horizontally

#### Slow Workflow Execution
1. Check activity timeouts
2. Monitor database performance
3. Optimize activities
4. Add more workers

#### Database Bottlenecks
1. Monitor connection pool usage
2. Add read replicas
3. Optimize queries
4. Increase connection limits

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale workers
kubectl scale deployment temporal-platform-worker \
  --replicas=5 -n temporal-platform

# Scale API servers
kubectl scale deployment temporal-platform-api \
  --replicas=3 -n temporal-platform
```

### Auto-scaling
```yaml
# HPA configuration
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Database Scaling
- Use read replicas for PostgreSQL
- Configure Elasticsearch cluster
- Implement connection pooling
- Use database proxies (PgBouncer)

## 🔄 Updates and Migrations

### Application Updates
```bash
# Update Docker image
helm upgrade temporal-platform ./infrastructure/helm/temporal-platform \
  --set application.image.tag=v1.1.0

# Or in Render: push to main branch
git push origin main
```

### Database Migrations
```bash
# Run migrations
poetry run temporal-platform setup-db --migrate

# Or as Kubernetes job
kubectl apply -f migration-job.yaml
```

### Rolling Updates
- Use blue-green deployments
- Implement health checks
- Monitor metrics during updates
- Have rollback plan ready

## 💾 Backup and Recovery

### Database Backups
```bash
# Automated backups in Render
# Manual backup
pg_dump $POSTGRESQL_DSN > backup.sql

# Restore
psql $POSTGRESQL_DSN < backup.sql
```

### Elasticsearch Snapshots
```bash
# Create snapshot repository
curl -X PUT "elasticsearch:9200/_snapshot/my_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/snapshots"
  }
}'

# Take snapshot
curl -X PUT "elasticsearch:9200/_snapshot/my_backup/snapshot_1"
```

This deployment guide ensures your Temporal Platform runs reliably in production with proper monitoring, security, and scalability.
