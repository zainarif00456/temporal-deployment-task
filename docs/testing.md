# Testing Guide

Complete testing strategy for the Temporal Platform including unit tests, integration tests, load testing, and end-to-end verification.

## 🧪 Testing Strategy

### Test Pyramid
```
    /\
   /  \     E2E Tests (Few)
  /____\
 /      \   Integration Tests (Some)  
/________\  Unit Tests (Many)
```

### Test Categories
1. **Unit Tests** - Individual functions and classes
2. **Integration Tests** - Component interactions
3. **Contract Tests** - API contracts
4. **Load Tests** - Performance and scalability
5. **End-to-End Tests** - Complete workflows
6. **Chaos Tests** - Fault tolerance

## 🔬 Unit Testing

### Setup
```bash
# Install test dependencies
poetry install --with dev

# Run unit tests
poetry run pytest tests/unit/ -v

# Run with coverage
poetry run pytest tests/unit/ --cov=src --cov-report=html
```

### Test Structure
```python
# tests/unit/test_data_processing.py
import pytest
from unittest.mock import Mock, patch
from src.temporal_platform.activities.data_processing import process_single_item
from src.temporal_platform.models.workflows import DataItem, ActivityStatus

class TestDataProcessing:
    @pytest.mark.asyncio
    async def test_process_single_item_success(self):
        # Arrange
        data_item = DataItem(
            content="test content",
            content_type="text/plain",
            size_bytes=12
        )
        
        # Act
        result = await process_single_item(data_item)
        
        # Assert
        assert result.status == ActivityStatus.COMPLETED
        assert result.processed_content == "TEST CONTENT"
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_process_single_item_timeout(self):
        # Test timeout handling
        with patch('asyncio.sleep', side_effect=asyncio.TimeoutError()):
            data_item = DataItem(
                content="test content",
                content_type="text/plain", 
                size_bytes=12
            )
            
            result = await process_single_item(data_item)
            assert result.status == ActivityStatus.TIMEOUT
```

### Key Test Files
- `tests/unit/test_activities/` - Activity function tests
- `tests/unit/test_workflows/` - Workflow logic tests  
- `tests/unit/test_models/` - Data model validation tests
- `tests/unit/test_config/` - Configuration tests
- `tests/unit/test_exceptions/` - Exception handling tests

### Running Unit Tests
```bash
# All unit tests
poetry run pytest tests/unit/

# Specific module
poetry run pytest tests/unit/test_activities/test_data_processing.py

# With verbose output
poetry run pytest tests/unit/ -v -s

# With coverage report
poetry run pytest tests/unit/ --cov=src --cov-report=term-missing

# Generate HTML coverage report
poetry run pytest tests/unit/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## 🔗 Integration Testing

### Test Environment Setup
```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Wait for services
./scripts/wait-for-services.sh

# Run integration tests
poetry run pytest tests/integration/ -v
```

### Temporal Testing
```python
# tests/integration/test_orchestration.py
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.temporal_platform.workflows.orchestration import DataProcessingOrchestrator
from src.temporal_platform.activities import data_processing

class TestOrchestration:
    @pytest.mark.asyncio
    async def test_data_processing_orchestration(self):
        async with WorkflowEnvironment() as env:
            # Create worker with activities
            worker = Worker(
                env.client,
                task_queue="test-queue",
                workflows=[DataProcessingOrchestrator],
                activities=[
                    data_processing.process_single_item,
                    data_processing.process_batch_parallel,
                    data_processing.validate_processing_results,
                ]
            )
            
            # Start worker
            async with worker:
                # Execute workflow
                workflow_input = create_test_workflow_input()
                result = await env.client.execute_workflow(
                    DataProcessingOrchestrator.run,
                    workflow_input,
                    id="test-orchestration",
                    task_queue="test-queue"
                )
                
                # Assertions
                assert result.status == WorkflowStatus.COMPLETED
                assert result.successful_items > 0
```

### Database Integration Tests
```python
# tests/integration/test_database.py
import pytest
from sqlalchemy import create_engine
from src.temporal_platform.config.settings import settings

@pytest.mark.integration
class TestDatabaseIntegration:
    @pytest.fixture
    def db_engine(self):
        engine = create_engine(settings.database.postgresql_dsn)
        yield engine
        engine.dispose()
    
    def test_database_connection(self, db_engine):
        with db_engine.connect() as conn:
            result = conn.execute("SELECT 1")
            assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_workflow_persistence(self, db_engine):
        # Test workflow state persistence
        # Implementation depends on your schema
        pass
```

## 🚀 Load Testing

### Load Test Setup
```bash
# Install load testing tools
poetry add --group dev locust pytest-benchmark

# Start application
poetry run temporal-platform start-worker &

# Run load tests
poetry run locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### Locust Load Tests
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between
import random
import json

class TemporalPlatformUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup for each user"""
        self.dataset_id = f"load-test-{random.randint(1000, 9999)}"
    
    @task(3)
    def health_check(self):
        """Test health endpoint"""
        self.client.get("/health")
    
    @task(1)
    def start_workflow(self):
        """Test workflow creation"""
        payload = {
            "dataset_id": self.dataset_id,
            "batch_count": random.randint(1, 5),
            "items_per_batch": random.randint(10, 100)
        }
        response = self.client.post("/workflows", json=payload)
        if response.status_code == 201:
            self.workflow_id = response.json().get("workflow_id")
    
    @task(2)
    def get_workflow_status(self):
        """Test workflow status endpoint"""
        if hasattr(self, 'workflow_id'):
            self.client.get(f"/workflows/{self.workflow_id}/status")

# Run with: locust -f tests/load/locustfile.py --users 100 --spawn-rate 10 --run-time 300s
```

### Performance Benchmarks
```python
# tests/load/test_performance.py
import pytest
from temporal_platform.activities.data_processing import process_single_item

@pytest.mark.benchmark
def test_process_single_item_performance(benchmark):
    """Benchmark single item processing"""
    data_item = create_test_data_item(size_bytes=1000)
    
    result = benchmark(
        lambda: asyncio.run(process_single_item(data_item))
    )
    
    # Performance assertions
    assert result.processing_time_seconds < 0.1  # < 100ms
```

### Load Test Scenarios
1. **Baseline Load** - Normal operation (100 concurrent users)
2. **Peak Load** - High traffic (500 concurrent users)  
3. **Stress Test** - Beyond normal capacity (1000+ users)
4. **Spike Test** - Sudden traffic increases
5. **Volume Test** - Large data processing workflows
6. **Endurance Test** - Extended duration (24+ hours)

## 🔄 End-to-End Testing

### E2E Test Setup
```bash
# Start full environment
docker-compose up -d

# Wait for all services
./scripts/wait-for-all-services.sh

# Run E2E tests
poetry run pytest tests/e2e/ -v --timeout=300
```

### Complete Workflow Tests
```python
# tests/e2e/test_complete_workflows.py
import pytest
from temporalio.client import Client
from src.temporal_platform.workflows.orchestration import DataProcessingOrchestrator

@pytest.mark.e2e
class TestCompleteWorkflows:
    @pytest.fixture
    async def temporal_client(self):
        client = await Client.connect(
            "localhost:7233",
            namespace="default"
        )
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_full_data_processing_pipeline(self, temporal_client):
        """Test complete data processing from start to finish"""
        
        # 1. Create workflow input with real data
        workflow_input = create_large_dataset_input(
            dataset_id="e2e-test-dataset",
            batch_count=10,
            items_per_batch=1000
        )
        
        # 2. Execute workflow
        result = await temporal_client.execute_workflow(
            DataProcessingOrchestrator.run,
            workflow_input,
            id="e2e-full-pipeline",
            task_queue="temporal-platform-task-queue",
            execution_timeout=timedelta(minutes=30)
        )
        
        # 3. Verify results
        assert result.status == WorkflowStatus.COMPLETED
        assert result.total_items == 10000
        assert result.successful_items > 9500  # Allow 5% failure rate
        assert result.processing_time_seconds > 0
        
        # 4. Verify side effects (notifications, metrics, etc.)
        await verify_notifications_sent(workflow_input.notification_webhook)
        await verify_metrics_updated(workflow_input.dataset_id)
        await verify_audit_logs(result.workflow_id)
```

### API Integration Tests
```python
# tests/e2e/test_api_integration.py
import pytest
import httpx

@pytest.mark.e2e
class TestAPIIntegration:
    @pytest.fixture
    def api_client(self):
        return httpx.AsyncClient(base_url="http://localhost:8000")
    
    @pytest.mark.asyncio
    async def test_workflow_lifecycle_via_api(self, api_client):
        """Test complete workflow lifecycle through REST API"""
        
        # 1. Create workflow
        create_response = await api_client.post("/workflows", json={
            "dataset_id": "api-test-dataset",
            "batch_count": 3,
            "items_per_batch": 100
        })
        assert create_response.status_code == 201
        workflow_id = create_response.json()["workflow_id"]
        
        # 2. Monitor workflow progress
        status_response = await api_client.get(f"/workflows/{workflow_id}")
        assert status_response.status_code == 200
        
        # 3. Wait for completion
        import asyncio
        for _ in range(60):  # Wait up to 60 seconds
            status_response = await api_client.get(f"/workflows/{workflow_id}")
            status = status_response.json()["status"]
            if status in ["completed", "failed"]:
                break
            await asyncio.sleep(1)
        
        # 4. Verify final status
        assert status == "completed"
```

## 🌪️ Chaos Testing

### Chaos Engineering Setup
```bash
# Install chaos testing tools
pip install chaos-toolkit chaos-toolkit-kubernetes

# Run chaos experiments
chaos run chaos-experiments/network-partition.json
```

### Chaos Experiments
```json
{
  "title": "Network partition between Temporal and database",
  "description": "Test system resilience during database connectivity issues",
  "steady-state-hypothesis": {
    "title": "Workflows continue processing",
    "probes": [
      {
        "name": "workflow-processing-rate",
        "type": "probe",
        "provider": {
          "type": "http",
          "url": "http://localhost:8000/metrics",
          "expected_status": 200
        },
        "tolerance": {
          "type": "probe",
          "name": "workflow-rate-above-threshold"
        }
      }
    ]
  },
  "method": [
    {
      "type": "action",
      "name": "introduce-network-delay",
      "provider": {
        "type": "process",
        "path": "tc",
        "arguments": ["qdisc", "add", "dev", "eth0", "root", "netem", "delay", "2000ms"]
      }
    }
  ],
  "rollbacks": [
    {
      "type": "action",
      "name": "remove-network-delay",
      "provider": {
        "type": "process", 
        "path": "tc",
        "arguments": ["qdisc", "del", "dev", "eth0", "root"]
      }
    }
  ]
}
```

## 📊 Test Reporting

### Coverage Reports
```bash
# Generate coverage report
poetry run pytest --cov=src --cov-report=html --cov-report=xml

# View HTML report
open htmlcov/index.html

# Upload to Codecov (CI)
codecov -f coverage.xml
```

### Test Results
```bash
# Generate JUnit XML for CI
poetry run pytest --junitxml=test-results.xml

# Generate test report
poetry run pytest --html=test-report.html --self-contained-html
```

### Performance Reports
```bash
# Benchmark report
poetry run pytest --benchmark-only --benchmark-json=benchmark-results.json

# Load test report (Locust generates automatically)
# View at: http://localhost:8089 during test run
```

## 🚀 Continuous Testing (CI/CD)

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: temporal
          POSTGRES_USER: temporal
          POSTGRES_PASSWORD: temporal
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run unit tests
      run: poetry run pytest tests/unit/ --cov=src --cov-report=xml
    
    - name: Start services
      run: docker-compose up -d
    
    - name: Wait for services
      run: ./scripts/wait-for-services.sh
    
    - name: Run integration tests
      run: poetry run pytest tests/integration/
    
    - name: Run E2E tests
      run: poetry run pytest tests/e2e/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
      with:
        file: ./coverage.xml
```

## 📋 Test Checklist

### Pre-Deployment Testing
- [ ] All unit tests pass
- [ ] All integration tests pass  
- [ ] End-to-end scenarios work
- [ ] Load tests show acceptable performance
- [ ] Security tests pass
- [ ] Database migrations work
- [ ] Health checks respond correctly
- [ ] Metrics are collected
- [ ] Logs are properly formatted
- [ ] Error handling works as expected

### Production Validation
- [ ] Smoke tests pass after deployment
- [ ] Health endpoints respond
- [ ] Workflows can be created
- [ ] Workflows execute successfully
- [ ] UI is accessible
- [ ] Metrics are being collected
- [ ] Alerts are configured
- [ ] Backups are working

## 🛠️ Testing Tools

### Required Tools
- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage measurement
- **pytest-mock** - Mocking support
- **locust** - Load testing
- **httpx** - HTTP testing client

### Optional Tools
- **pytest-benchmark** - Performance benchmarking
- **pytest-xdist** - Parallel test execution
- **pytest-html** - HTML test reports
- **chaos-toolkit** - Chaos engineering

### Development Tools
```bash
# Install all testing dependencies
poetry install --with dev

# Pre-commit hooks for testing
pre-commit install

# Test command shortcuts
alias test-unit="poetry run pytest tests/unit/"
alias test-integration="poetry run pytest tests/integration/"
alias test-e2e="poetry run pytest tests/e2e/"
alias test-all="poetry run pytest"
```

This comprehensive testing strategy ensures the Temporal Platform is robust, performant, and reliable in production environments.
