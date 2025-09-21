#!/bin/bash

# Temporal Platform Startup Script
echo "🚀 Starting Temporal Platform..."
echo "=================================="

# Activate conda environment
echo "📦 Activating conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate deployment-task

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --volumes --remove-orphans 2>/dev/null

# Start infrastructure services
echo "🏗️  Starting infrastructure services..."
echo "   • PostgreSQL Database"
echo "   • Elasticsearch"  
echo "   • Temporal Server (all services)"
echo "   • Temporal UI"

docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
echo "   This may take 2-3 minutes for first startup..."

# Function to check if service is responding
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=60
    local attempt=1
    
    echo "   Checking $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "   ✅ $service_name is ready!"
            return 0
        fi
        echo "   ⏳ $service_name starting... (attempt $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "   ❌ $service_name failed to start after $((max_attempts * 5)) seconds"
    return 1
}

# Check PostgreSQL
echo "   Checking PostgreSQL..."
for i in {1..12}; do
    if docker exec deployment-task-postgres-1 pg_isready -h localhost -U temporal > /dev/null 2>&1; then
        echo "   ✅ PostgreSQL is ready!"
        break
    fi
    echo "   ⏳ PostgreSQL starting... (attempt $i/12)"
    sleep 5
done

# Check Elasticsearch
check_service "Elasticsearch" "http://localhost:9200/_cluster/health"

# Check Temporal Server
check_service "Temporal Server" "http://localhost:7233"

# Start Temporal UI
echo "🖥️  Starting Temporal UI..."
docker-compose up -d temporal-ui

# Check Temporal UI
check_service "Temporal UI" "http://localhost:8080"

echo ""
echo "🎉 Temporal Platform is now running!"
echo "=================================="
echo ""
echo "🌐 Access Points:"
echo "   • Temporal UI:    http://localhost:8080"
echo "   • Elasticsearch:  http://localhost:9200"
echo "   • PostgreSQL:     localhost:5432 (user: temporal, pass: temporal)"
echo ""
echo "🛠️  Available Commands:"
echo "   poetry run python demo.py                    # Run demonstration"
echo "   poetry run python -m src.temporal_platform.main health-check  # Health check"
echo ""
echo "📚 Documentation:"
echo "   • README.md - Complete project overview"  
echo "   • DEPLOYMENT_INSTRUCTIONS.md - Render.com deployment"
echo "   • docs/ - Comprehensive documentation"
echo ""
echo "💡 Next Steps:"
echo "   1. Open http://localhost:8080 to see Temporal UI"
echo "   2. Run the demo: poetry run python demo.py"
echo "   3. Deploy to production using DEPLOYMENT_INSTRUCTIONS.md"
echo ""
echo "Happy workflow orchestrating! 🚀"
