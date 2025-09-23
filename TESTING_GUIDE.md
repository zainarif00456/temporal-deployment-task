# 🚀 Temporal Platform Testing Guide

## 📋 Complete Testing & Load Testing Instructions

This guide provides comprehensive testing strategies for your production-grade Temporal Platform, including stress testing with 1000+ concurrent requests.

---

## 🏃‍♂️ Quick Start Commands

### **1. Start the Complete System**
```bash
# Terminal 1: Start infrastructure
docker compose up -d

# Wait for services to be healthy (30-60 seconds)
sleep 60

# Terminal 2: Start Worker
poetry run python -m src.temporal_platform.main start-worker

# Terminal 3: Test connectivity
curl http://localhost:8080/api/v1/cluster-info
```

### **2. Verify System Health**
```bash
# Check all containers
docker ps

# Test Temporal UI
curl http://localhost:8080/api/v1/namespaces | jq .

# Test Elasticsearch
curl http://localhost:9200/_cluster/health | jq .

# Test Python app
python demo.py
```

---

## 🎯 Load Testing Scripts

### **Script 1: Basic Stress Test (No Worker Required)**
```bash
# Test 100 concurrent connections
python stress_test.py --connections 100 --ops-per-sec 10 --duration 60

# Test 1000 concurrent connections  
python stress_test.py --connections 1000 --ops-per-sec 50 --duration 120
```

### **Script 2: Full Workflow Load Test (Worker Required)**
```bash
# Start with small load
python load_test.py --workflows 50 --concurrent 10 --batch-size 5 --items-per-batch 10

# Medium load test
python load_test.py --workflows 500 --concurrent 25 --batch-size 5 --items-per-batch 20

# High load test (1000+ workflows)
python load_test.py --workflows 1000 --concurrent 50 --batch-size 10 --items-per-batch 25 --save-results
```

### **Script 3: System Monitoring**
```bash
# Real-time monitoring during load tests
python monitor_system.py --interval 5 --duration 600 --save-metrics

# In another terminal while monitoring
python load_test.py --workflows 1000 --concurrent 50 --batch-size 5
```

---

## 📊 Load Testing Scenarios

### **Scenario 1: Connection Stress Test**
```bash
# Test system's ability to handle many concurrent connections
python stress_test.py --connections 1000 --duration 300

# Expected Results:
# - Success Rate: >95%
# - Avg Response Time: <100ms
# - System should remain stable
```

### **Scenario 2: Sustained Load Test**
```bash
# Test sustained operations over time
python stress_test.py --connections 100 --ops-per-sec 20 --duration 1800  # 30 minutes

# Expected Results:
# - Consistent performance over time
# - No memory leaks
# - Stable response times
```

### **Scenario 3: Full Workflow Processing**
```bash
# Test complete workflow orchestration under load
python load_test.py --workflows 2000 --concurrent 100 --batch-size 5 --items-per-batch 50

# This will process:
# - 2,000 workflows
# - 10,000 batches (5 per workflow)
# - 500,000 individual items (50 per batch)
# - Up to 100 concurrent workflows
```

### **Scenario 4: Peak Load Burst Test**
```bash
# Test system behavior under sudden load spikes
python load_test.py --workflows 500 --concurrent 200 --batch-size 3 --items-per-batch 15

# Expected Results:
# - System should handle burst gracefully
# - Queuing mechanisms should work
# - No failures due to resource exhaustion
```

---

## 🎭 Performance Benchmarks

### **Expected Performance Metrics**

| Metric | Target | Excellent | Good | Needs Improvement |
|--------|--------|-----------|------|-------------------|
| **Success Rate** | >99% | >99.5% | >95% | <95% |
| **Avg Response Time** | <500ms | <100ms | <500ms | >1000ms |
| **Concurrent Workflows** | 1000+ | 2000+ | 1000+ | <500 |
| **Throughput** | 100+ wf/sec | 500+ wf/sec | 100+ wf/sec | <50 wf/sec |
| **P95 Response Time** | <1s | <200ms | <1s | >2s |
| **P99 Response Time** | <2s | <500ms | <2s | >5s |

### **Resource Utilization Targets**

| Resource | Normal Load | High Load | Critical |
|----------|-------------|-----------|----------|
| **CPU Usage** | <50% | <80% | >95% |
| **Memory Usage** | <60% | <85% | >95% |
| **Disk I/O** | <70% | <90% | >95% |
| **Network** | <100MB/s | <500MB/s | >1GB/s |

---

## 🔬 Advanced Testing Commands

### **1. Gradual Load Ramp-Up**
```bash
# Ramp up gradually to find breaking point
for concurrent in 10 20 50 100 200 500; do
    echo "Testing with $concurrent concurrent workflows..."
    python load_test.py --workflows 100 --concurrent $concurrent --batch-size 3
    sleep 30  # Cool down between tests
done
```

### **2. Endurance Testing**
```bash
# Run for extended periods
python load_test.py --workflows 5000 --concurrent 50 --batch-size 5 --items-per-batch 20

# Monitor system during endurance test
python monitor_system.py --interval 10 --duration 7200 --save-metrics  # 2 hours
```

### **3. Failure Recovery Testing**
```bash
# Test system recovery after failures
python load_test.py --workflows 100 --concurrent 20 --batch-size 5 &
LOAD_PID=$!

# Simulate failures (in another terminal)
docker stop deployment-task-postgres-1
sleep 30
docker start deployment-task-postgres-1

# Wait for load test to complete
wait $LOAD_PID
```

### **4. Multi-Client Testing**
```bash
# Simulate multiple clients simultaneously
for i in {1..5}; do
    python load_test.py --workflows 200 --concurrent 10 --batch-size 3 &
done
wait  # Wait for all to complete
```

---

## 📈 Monitoring & Metrics Collection

### **Real-Time Monitoring Dashboard**
```bash
# Start monitoring before load tests
python monitor_system.py --interval 2 --save-metrics &
MONITOR_PID=$!

# Run your load tests
python load_test.py --workflows 1000 --concurrent 50 --batch-size 5

# Stop monitoring
kill $MONITOR_PID
```

### **Key Metrics to Watch**

1. **System Metrics:**
   - CPU utilization across all cores
   - Memory usage and swap
   - Disk I/O and space
   - Network throughput

2. **Docker Container Metrics:**
   - Container CPU and memory usage
   - Container restart counts
   - Network traffic between containers

3. **Temporal Metrics:**
   - Workflow execution times
   - Activity success/failure rates
   - Queue depths and processing times
   - Retry patterns and failure modes

4. **Application Metrics:**
   - Throughput (workflows/second)
   - Latency percentiles (P50, P95, P99)
   - Error rates and types
   - Resource utilization patterns

---

## 🎯 Stress Testing Best Practices

### **1. Progressive Load Testing**
```bash
# Start small and increase gradually
python stress_test.py --connections 10 --duration 60
python stress_test.py --connections 50 --duration 60  
python stress_test.py --connections 100 --duration 60
python stress_test.py --connections 500 --duration 60
python stress_test.py --connections 1000 --duration 60
```

### **2. Sustained Load Testing**
```bash
# Test system stability over time
python load_test.py --workflows 100 --concurrent 10 --batch-size 5 &
python monitor_system.py --interval 5 --duration 3600  # 1 hour
```

### **3. Peak Load Testing**
```bash
# Test maximum capacity
python load_test.py --workflows 2000 --concurrent 200 --batch-size 10 --items-per-batch 50
```

### **4. Recovery Testing**
```bash
# Test system recovery capabilities
# Run this script while load testing is active:

#!/bin/bash
echo "Starting recovery test..."
python load_test.py --workflows 500 --concurrent 25 --batch-size 5 &

sleep 60
echo "Simulating Elasticsearch failure..."
docker stop deployment-task-elasticsearch-1
sleep 30
docker start deployment-task-elasticsearch-1

sleep 60  
echo "Simulating database failure..."
docker stop deployment-task-postgres-1
sleep 15
docker start deployment-task-postgres-1

wait
echo "Recovery test complete"
```

---

## 🏆 Expected Results for 1000+ Concurrent Requests

### **System Capabilities Demonstrated:**

1. **✅ Scalability:**
   - Handle 1000+ concurrent workflows
   - Process 50,000+ individual items
   - Maintain sub-second response times

2. **✅ Fault Tolerance:**
   - Automatic retries with exponential backoff
   - Graceful degradation under load
   - Recovery from transient failures

3. **✅ Performance:**
   - High throughput (100+ workflows/second)
   - Low latency (P95 < 1 second)
   - Consistent performance under load

4. **✅ Resource Efficiency:**
   - Optimal CPU and memory utilization
   - Efficient network usage
   - Proper queue management

### **Sample Output from 1000 Workflow Test:**
```
🎯 Load Test Results
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value        ┃ Details                                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Total Workflows           │ 1,000        │                                            │
│ ✅ Completed             │ 987          │ 98.7% success rate                        │
│ ❌ Failed                │ 13           │ 1.3% failure rate                         │
│ 📊 Total Items Processed │ 98,700       │                                            │
│ ⚡ Throughput            │ 45.2 wf/sec  │                                            │
│ ⏱️ Avg Execution Time    │ 2.34s        │                                            │
│ 📈 Median Execution Time │ 1.89s        │                                            │
│ ⚡ Min Execution Time    │ 0.45s        │                                            │
│ 🐌 Max Execution Time    │ 8.92s        │                                            │
│ 📊 95th Percentile       │ 4.23s        │                                            │
│ 📊 99th Percentile       │ 6.78s        │                                            │
└───────────────────────────┴──────────────┴────────────────────────────────────────────┘

🕒 Total Test Duration: 22.1 seconds
📈 Overall Throughput: 4,466 items/second  
🎯 System Performance: 🟢 EXCELLENT
🔧 Fault Tolerance: 🟢 ROBUST
```

---

## 🔧 Troubleshooting Load Tests

### **Common Issues & Solutions:**

1. **Connection Failures:**
   ```bash
   # Check service health
   docker ps
   curl http://localhost:8080/api/v1/cluster-info
   
   # Restart services if needed
   docker compose restart
   ```

2. **Worker Not Running:**
   ```bash
   # Check worker process
   ps aux | grep temporal_platform
   
   # Restart worker
   poetry run python -m src.temporal_platform.main start-worker
   ```

3. **Memory Issues:**
   ```bash
   # Monitor memory usage
   python monitor_system.py --interval 1 --duration 60
   
   # Reduce concurrent load
   python load_test.py --workflows 100 --concurrent 10
   ```

4. **Timeout Errors:**
   ```bash
   # Increase timeouts in settings
   export ACTIVITY_EXECUTION_TIMEOUT_SECONDS=600
   export WORKFLOW_EXECUTION_TIMEOUT_SECONDS=3600
   ```

---

## 🎉 Success Criteria

Your Temporal Platform passes the 1000+ concurrent request test if:

- ✅ **Success Rate:** >95%
- ✅ **Throughput:** >50 workflows/second
- ✅ **P95 Latency:** <3 seconds
- ✅ **System Stability:** No crashes or memory leaks
- ✅ **Fault Recovery:** Graceful handling of failures
- ✅ **Resource Usage:** <90% CPU/Memory under peak load

**🏆 Your Temporal Platform is production-ready for enterprise-scale workflow orchestration!**
