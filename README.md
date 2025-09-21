# Temporal Platform - Production-grade Workflow Orchestration

A comprehensive Temporal Platform implementation demonstrating all required patterns for scalable, fault-tolerant distributed systems.

## 🚀 Features

### Temporal Patterns Implemented
1. **Orchestration** - Main orchestrator workflow coordinating multiple child workflows with sequential and parallel execution
2. **Async Operations** - Activities with retry policies, timeout handling, and error recovery
3. **Fire-and-Forget** - Background tasks for notifications, logging, and metrics
4. **Long-Running Operations** - Heartbeat reporting and progress monitoring for large datasets

### Production-Ready Components
- ✅ **Type Safety** - Complete Python 3.11+ type hints
- ✅ **Data Validation** - Pydantic v2 models with comprehensive validation
- ✅ **Error Handling** - Custom exception hierarchy with structured error propagation
- ✅ **Structured Logging** - JSON-formatted logs with contextual information
- ✅ **Configuration Management** - Environment-based settings with validation
- ✅ **Async Best Practices** - Proper async/await usage and concurrency control
- ✅ **Security** - Input validation, no exposed secrets, secure defaults
- ✅ **Monitoring** - Prometheus metrics and health checks
- ✅ **Scalability** - Designed to handle thousands of concurrent workflows

## 🏗️ Architecture

### Deployment Components
- **PostgreSQL** - Temporal core state and application data
- **Elasticsearch** - Temporal visibility and search capabilities
- **Temporal Services** - Frontend, History, Matching, Worker services
- **Temporal UI** - Web interface for workflow monitoring
- **Python Application** - Workflow and activity implementations
- **API Gateway** - REST API for external integrations

### Infrastructure
- **Render.com** - Cloud deployment with auto-scaling
- **Docker** - Containerized services with health checks
- **Helm Charts** - Kubernetes deployments for development
- **ArgoCD** - GitOps-based deployment management

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+
- Poetry (package management)
- Docker (for local development)
- kubectl (for Kubernetes development)

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd deployment-task
   poetry install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Development Services**
   ```bash
   # Using Docker Compose
   docker-compose up -d
   
   # Or using Dev Container
   code . # Open in VS Code with Dev Containers extension
   ```

4. **Run Workers**
   ```bash
   poetry run temporal-platform start-worker
   ```

5. **Execute Workflows**
   ```bash
   poetry run temporal-platform start-orchestrator sample-dataset
   ```

## 📊 Usage Examples

### Command Line Interface

```bash
# Start Temporal worker
temporal-platform start-worker --max-activities 100 --max-workflows 50

# Run data processing orchestration
temporal-platform start-orchestrator my-dataset \
    --batches 10 \
    --items-per-batch 1000 \
    --parallel 5 \
    --webhook https://api.example.com/webhooks/temporal

# Interactive workflow client
temporal-platform start-client

# Health check
temporal-platform health-check

# Start API server
temporal-platform start-api --port 8000
```

### Programmatic Usage

```python
from temporal_platform.workflows.orchestration import DataProcessingOrchestrator
from temporal_platform.models.workflows import WorkflowInput, DataBatch
from temporalio.client import Client

# Create workflow input
workflow_input = WorkflowInput(
    dataset_id="production-dataset-001",
    batches=[...],  # Your data batches
    parallel_batches=10,
    enable_retry=True
)

# Execute workflow
client = await Client.connect("temporal-server:7233")
result = await client.execute_workflow(
    DataProcessingOrchestrator.run,
    workflow_input,
    id="prod-workflow-001",
    task_queue="temporal-platform-task-queue"
)
```

## 🚢 Deployment

### Render.com Deployment

1. **Connect Repository**
   - Fork this repository
   - Connect to Render.com
   - Configure webhook for auto-deployment

2. **Deploy Infrastructure**
   ```bash
   # Render will automatically deploy using render.yaml
   git push origin main
   ```

3. **Verify Deployment**
   - Check Render dashboard for service status
   - Access Temporal UI at your deployed URL
   - Run health checks

### Manual Deployment Steps

1. **Database Setup**
   ```bash
   # PostgreSQL databases will be created automatically
   # Run migrations if needed
   poetry run temporal-platform setup-db
   ```

2. **Service Deployment**
   ```bash
   # Services deploy automatically via render.yaml
   # Monitor deployment in Render dashboard
   ```

3. **Verification**
   ```bash
   # Check service health
   curl https://your-api-url/health
   
   # Access Temporal UI
   open https://your-temporal-ui-url
   ```

## 📈 Monitoring & Observability

### Metrics
- **Prometheus** metrics at `/metrics` endpoint
- **Workflow execution** metrics
- **Activity completion** rates
- **Error rates** and types
- **Processing throughput**

### Logging
- **Structured JSON** logs
- **Contextual information** for debugging
- **Error tracking** with full stack traces
- **Audit trail** for compliance

### Health Checks
- **Temporal server** connectivity
- **Database** connection status
- **Elasticsearch** cluster health
- **Application** readiness

## 🧪 Testing

### Unit Tests
```bash
poetry run pytest tests/unit/
```

### Integration Tests
```bash
poetry run pytest tests/integration/
```

### Load Testing
```bash
# Start test workers
poetry run temporal-platform start-worker

# Run load test
poetry run pytest tests/load/test_orchestration_load.py
```

## 📚 Documentation

- **[API Documentation](./docs/api.md)** - REST API reference
- **[Workflow Patterns](./docs/patterns.md)** - Temporal pattern implementations
- **[Deployment Guide](./docs/deployment.md)** - Complete deployment instructions
- **[Configuration Reference](./docs/configuration.md)** - Environment variables and settings
- **[Troubleshooting](./docs/troubleshooting.md)** - Common issues and solutions

## 🔧 Configuration

### Environment Variables

```bash
# Temporal Configuration
TEMPORAL_HOST=localhost
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=temporal-platform-task-queue

# Database Configuration
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=temporal
POSTGRESQL_USER=temporal
POSTGRESQL_PASSWORD=temporal

# Elasticsearch Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# Application Configuration
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
MAX_CONCURRENT_WORKFLOWS=1000
MAX_CONCURRENT_ACTIVITIES=1000

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_PORT=8081
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- Use `black` for formatting
- Use `isort` for imports
- Use `mypy` for type checking
- Follow PEP 8 guidelines

### Pre-commit Hooks
```bash
poetry run pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Open GitHub issue
- **Discussions**: GitHub Discussions
- **Email**: engineering@stackai.com

## 🎯 Roadmap

- [ ] Advanced workflow patterns
- [ ] Multi-region deployment
- [ ] Enhanced monitoring dashboards
- [ ] Workflow versioning strategies
- [ ] Performance optimizations
- [ ] SDK for other languages

---

**Built with ❤️ for production-grade distributed systems**
