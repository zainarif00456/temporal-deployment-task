#!/bin/bash

# Development container setup script
echo "🚀 Setting up Temporal Platform development environment..."

# Install Python dependencies
echo "📦 Installing Python dependencies with Poetry..."
poetry install

# Setup pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Development environment configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Temporal configuration
TEMPORAL_HOST=temporal-server
TEMPORAL_PORT=7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=temporal-platform-task-queue

# Database configuration
POSTGRESQL_HOST=postgres
POSTGRESQL_PORT=5432
POSTGRESQL_DATABASE=temporal
POSTGRESQL_USER=temporal
POSTGRESQL_PASSWORD=temporal

# Elasticsearch configuration
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# Workflow configuration
MAX_CONCURRENT_WORKFLOWS=100
MAX_CONCURRENT_ACTIVITIES=100
WORKFLOW_EXECUTION_TIMEOUT_SECONDS=3600
ACTIVITY_EXECUTION_TIMEOUT_SECONDS=300

# Monitoring configuration
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECKS=true
HEALTH_CHECK_PORT=8081
EOF
fi

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."

# Wait for PostgreSQL
while ! pg_isready -h postgres -U temporal; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Wait for Elasticsearch
while ! curl -s http://elasticsearch:9200/_cluster/health > /dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 2
done
echo "✅ Elasticsearch is ready"

# Wait for Temporal server
while ! temporal operator cluster health --address temporal-server:7233 > /dev/null 2>&1; do
    echo "Waiting for Temporal server..."
    sleep 2
done
echo "✅ Temporal server is ready"

# Setup database schema if needed
echo "🗄️ Setting up database schema..."
poetry run python -c "
try:
    import asyncio
    from src.temporal_platform.main import setup_database
    print('Database setup completed')
except Exception as e:
    print(f'Database setup error: {e}')
"

echo "🎉 Development environment setup complete!"
echo ""
echo "Available commands:"
echo "  poetry run temporal-platform start-worker     # Start Temporal worker"
echo "  poetry run temporal-platform start-orchestrator sample-dataset  # Run orchestration"
echo "  poetry run temporal-platform start-client     # Interactive client"
echo "  poetry run temporal-platform health-check     # Health check"
echo ""
echo "Services:"
echo "  Temporal UI:    http://localhost:8080"
echo "  API Server:     http://localhost:8000 (when running)"
echo "  Elasticsearch:  http://localhost:9200"
echo "  PostgreSQL:     postgres://temporal:temporal@postgres:5432/temporal"
echo ""
echo "Happy coding! 🚀"
