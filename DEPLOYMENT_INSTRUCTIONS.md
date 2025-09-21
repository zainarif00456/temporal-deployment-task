# 🚀 Render.com Deployment Instructions

Complete step-by-step guide for deploying the Temporal Platform to Render.com production environment.

## 📋 Prerequisites Checklist

Before starting deployment, ensure you have:

- ✅ **GitHub Account** - For repository hosting
- ✅ **Render.com Account** - For cloud deployment  
- ✅ **Git Repository** - Code pushed to GitHub/GitLab
- ✅ **Domain Name** (Optional) - For custom domains
- ✅ **Environment Variables** - Production configuration ready

## 🔧 Step 1: Repository Preparation

### 1.1 Initialize Git Repository
```bash
# If not already done
cd /path/to/deployment-task
git init
git add .
git commit -m "Initial Temporal Platform implementation"
```

### 1.2 Push to GitHub
```bash
# Create repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/temporal-platform.git
git branch -M main
git push -u origin main
```

### 1.3 Verify Repository Structure
Ensure your repository contains:
```
deployment-task/
├── render.yaml                 ✅ (Main deployment config)
├── pyproject.toml              ✅ (Python dependencies)
├── src/temporal_platform/      ✅ (Application code)
├── infrastructure/render/      ✅ (Docker configs)
├── .devcontainer/             ✅ (Dev environment)
└── docs/                      ✅ (Documentation)
```

## 🌐 Step 2: Render.com Setup

### 2.1 Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up using GitHub OAuth (recommended)
3. Verify your email address
4. Complete profile setup

### 2.2 Connect GitHub Repository
1. **Dashboard** → **New** → **Blueprint**
2. **Connect GitHub** (if not already connected)
3. **Install Render GitHub App** on your repository
4. **Select Repository**: `temporal-platform` 
5. **Select Branch**: `main`

### 2.3 Review Blueprint Configuration
Render will automatically detect the `render.yaml` file and show:

**Services to be Created:**
- ✅ **2 PostgreSQL databases** (temporal, temporal_visibility)
- ✅ **1 Elasticsearch service** (for visibility)
- ✅ **4 Temporal services** (frontend, history, matching, worker)
- ✅ **1 Temporal UI** (web interface)
- ✅ **2 Python services** (worker app, API gateway)

**Total Resources:** ~7 services + 2 databases

## ⚙️ Step 3: Environment Configuration

### 3.1 Configure Environment Variable Groups

#### Temporal Config Group
In Render dashboard, create env var group named `temporal-config`:
```bash
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=temporal-platform-task-queue
MAX_CONCURRENT_WORKFLOWS=1000
MAX_CONCURRENT_ACTIVITIES=1000
WORKFLOW_EXECUTION_TIMEOUT_SECONDS=3600
ACTIVITY_EXECUTION_TIMEOUT_SECONDS=300
ACTIVITY_RETRY_MAXIMUM_ATTEMPTS=5
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### App Config Group  
Create env var group named `app-config`:
```bash
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECKS=true
HEALTH_CHECK_PORT=8081
ENABLE_TLS=false
HEARTBEAT_INTERVAL_SECONDS=10
PROGRESS_UPDATE_INTERVAL_SECONDS=5
```

### 3.2 Service-Specific Variables

#### For Python Application Services
```bash
ENVIRONMENT=production
DEBUG=false
PYTHON_VERSION=3.11
```

#### For API Gateway Service
```bash
API_PORT=8000
CORS_ORIGINS=*
```

## 🚀 Step 4: Deploy Services

### 4.1 Start Deployment
1. **Review Configuration** - Verify all settings
2. **Click "Apply"** - Start the deployment process
3. **Monitor Progress** - Watch the deployment logs

### 4.2 Deployment Sequence
Services will deploy in this order:
1. **PostgreSQL Databases** (5-10 minutes)
2. **Elasticsearch** (3-5 minutes) 
3. **Temporal Services** (5-10 minutes each)
4. **Temporal UI** (2-3 minutes)
5. **Python Applications** (5-10 minutes)

**Total Deployment Time:** 30-45 minutes

### 4.3 Monitor Deployment Status
In the Render dashboard, monitor:
- ✅ **Service Status** - All should show "Live"
- ✅ **Health Checks** - All should be passing
- ✅ **Logs** - No critical errors
- ✅ **Metrics** - Services responding

## 🔍 Step 5: Verification & Testing

### 5.1 Service Health Verification

#### Check Temporal UI
1. **Find Temporal UI URL** in Render dashboard
2. **Access URL**: `https://temporal-ui-xxx.onrender.com`
3. **Verify Default Namespace** is visible
4. **Check Cluster Status** - Should show "Serving"

#### Check API Gateway
1. **Find API URL** in Render dashboard  
2. **Test Health Endpoint**: 
   ```bash
   curl https://temporal-platform-api-xxx.onrender.com/health
   ```
3. **Expected Response**:
   ```json
   {"status": "healthy", "service": "temporal-platform-api"}
   ```

#### Check Database Connectivity
1. **PostgreSQL** - Check logs for successful connections
2. **Elasticsearch** - Access health endpoint:
   ```bash
   curl https://elasticsearch-xxx.onrender.com/_cluster/health
   ```

### 5.2 End-to-End Workflow Test
Run a test workflow to verify complete functionality:

```bash
# Using curl to trigger workflow via API
curl -X POST https://temporal-platform-api-xxx.onrender.com/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "production-test-001",
    "batch_count": 2,
    "items_per_batch": 10
  }'
```

### 5.3 Monitor Execution
1. **Check Temporal UI** for workflow execution
2. **Monitor Logs** in Render dashboard
3. **Verify Metrics** are being collected
4. **Check Notifications** (if configured)

## 🌍 Step 6: Domain & SSL Configuration

### 6.1 Custom Domain Setup (Optional)
For each service that needs a custom domain:

1. **Go to Service Settings** in Render
2. **Custom Domains** → **Add Custom Domain**
3. **Enter Domain**: e.g., `api.yourdomain.com`
4. **Configure DNS** at your domain registrar:
   ```
   CNAME api.yourdomain.com temporal-platform-api-xxx.onrender.com
   ```
5. **Wait for SSL** - Automatic via Let's Encrypt

### 6.2 Recommended Domain Structure
```
temporal-ui.yourdomain.com     → Temporal UI
api.yourdomain.com            → API Gateway
metrics.yourdomain.com        → Metrics endpoint
```

## 📊 Step 7: Monitoring & Observability

### 7.1 Set Up Monitoring
1. **Health Check URLs** - Configure external monitoring:
   - `https://api.yourdomain.com/health`
   - `https://temporal-ui.yourdomain.com/`
   - `https://elasticsearch-xxx.onrender.com/_cluster/health`

2. **Metrics Collection** - Configure Prometheus scraping:
   - `https://api.yourdomain.com:9090/metrics`

3. **Log Aggregation** - Set up log forwarding if needed

### 7.2 Configure Alerts
Set up alerts for:
- ✅ **Service Down** - Any service becomes unavailable
- ✅ **High Error Rate** - > 5% error rate for 5 minutes
- ✅ **High Response Time** - > 2s average for 5 minutes
- ✅ **Database Issues** - Connection failures
- ✅ **Workflow Failures** - High failure rate

## 🔐 Step 8: Security Configuration

### 8.1 Network Security
- ✅ **HTTPS Only** - Enabled by default on Render
- ✅ **Internal Communication** - Services communicate via internal network
- ✅ **Database Security** - Private database instances

### 8.2 Application Security
```bash
# Add these environment variables for production
ENABLE_AUTH=true
JWT_SECRET=your-secure-jwt-secret-key-here
API_KEY_HEADER=X-API-Key
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 8.3 Secrets Management
1. **Use Render's Secret Management** for sensitive values
2. **Never commit secrets** to repository
3. **Rotate secrets regularly**

## 📈 Step 9: Performance Optimization

### 9.1 Resource Scaling
Monitor resource usage and scale as needed:

1. **Vertical Scaling** - Upgrade service plans
2. **Horizontal Scaling** - Add more instances
3. **Database Scaling** - Use higher-tier database plans

### 9.2 Performance Monitoring
Track these metrics:
- **Response Time** - API and workflow execution
- **Throughput** - Requests/workflows per second
- **Error Rate** - Failed requests/workflows
- **Resource Usage** - CPU, memory, disk

### 9.3 Optimization Recommendations
```yaml
# For high-traffic production:
services:
  temporal-platform-app:
    plan: pro  # Upgrade from standard
    scaling:
      minInstances: 3
      maxInstances: 10
  
  temporal-platform-api:
    plan: pro
    scaling:
      minInstances: 2
      maxInstances: 5
```

## 🚨 Step 10: Troubleshooting

### 10.1 Common Deployment Issues

#### Services Won't Start
```bash
# Check logs in Render dashboard
# Common fixes:
1. Verify environment variables
2. Check Docker build logs
3. Ensure all dependencies are in pyproject.toml
4. Verify render.yaml syntax
```

#### Database Connection Issues
```bash
# Check these:
1. Database is fully deployed before apps start
2. Connection strings are correct
3. Database credentials are properly configured
4. Network connectivity between services
```

#### Temporal Cluster Issues
```bash
# Verify:
1. All Temporal services are running
2. Database schema is properly initialized
3. Elasticsearch is accessible
4. Service discovery is working
```

### 10.2 Performance Issues
```bash
# If experiencing slow performance:
1. Check resource utilization
2. Monitor database query performance
3. Verify network latency
4. Check for memory leaks
5. Scale up resources if needed
```

### 10.3 Getting Help
- **Render Support** - Use in-dashboard support chat
- **Temporal Community** - [community.temporal.io](https://community.temporal.io)
- **Documentation** - Check `/docs` folder in repository
- **GitHub Issues** - Create issue in repository

## ✅ Step 11: Post-Deployment Checklist

### 11.1 Immediate Verification (Day 1)
- [ ] All services show "Live" status
- [ ] Health checks are passing
- [ ] Temporal UI is accessible and functional
- [ ] API endpoints respond correctly
- [ ] Test workflow executes successfully
- [ ] Logs show no critical errors
- [ ] Metrics are being collected

### 11.2 Short-term Monitoring (Week 1)
- [ ] Monitor service stability
- [ ] Check resource utilization trends
- [ ] Verify backup and recovery procedures
- [ ] Test alerting and notifications
- [ ] Performance benchmarking
- [ ] Load testing under realistic traffic

### 11.3 Long-term Optimization (Month 1)
- [ ] Cost optimization review
- [ ] Performance optimization
- [ ] Security audit
- [ ] Disaster recovery testing
- [ ] Documentation updates
- [ ] Team training and runbooks

## 💡 Pro Tips for Production

### Resource Planning
- **Start Small** - Begin with standard plans and scale up
- **Monitor Closely** - Watch metrics for first few weeks  
- **Plan for Growth** - Design for 3x current expected load

### Cost Optimization
- **Right-size Services** - Don't over-provision initially
- **Use Sleep Mode** - For non-critical development services
- **Monitor Bills** - Set up billing alerts

### Reliability Best Practices
- **Health Checks** - Implement comprehensive health monitoring
- **Graceful Degradation** - Handle service failures elegantly  
- **Circuit Breakers** - Prevent cascade failures
- **Rate Limiting** - Protect against traffic spikes

---

## 🎉 Deployment Complete!

Congratulations! Your Temporal Platform is now running in production on Render.com. 

**Key URLs to bookmark:**
- 📊 **Temporal UI**: https://temporal-ui-xxx.onrender.com
- 🔗 **API Gateway**: https://temporal-platform-api-xxx.onrender.com  
- 📈 **Metrics**: https://temporal-platform-api-xxx.onrender.com:9090/metrics
- 🏥 **Health Check**: https://temporal-platform-api-xxx.onrender.com/health

**Next Steps:**
1. Set up monitoring and alerting
2. Configure regular backups
3. Create runbooks for operations team
4. Plan for scaling and optimization
5. Schedule regular health checks and maintenance

**Need Help?** Check the troubleshooting section or create an issue in the repository.

---

*Built with ❤️ for production-grade distributed systems*
