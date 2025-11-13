# Test Execution & Status Monitoring Guide

## 🚀 How to Trigger Tests

### Method 1: Using MTP API (Recommended)

#### Trigger Docker-based Test

```bash
# iOS FTM Test
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_method": "docker",
    "platform": "ios",
    "test_suite": "suites/mobile/suites/ftm/ios/tests",
    "test_markers": "ios_ftm and fac_ftc_token and functional",
    "lab_config": "/test_files/mobile_auto/ios16_ftm_testing_config.yml",
    "docker_registry": "10.160.16.60",
    "docker_image": "pytest-automation/pytest_automation",
    "docker_tag": "latest",
    "timeout": 3600,
    "labels": ["ios-automation"]
  }'

# Response:
# {
#   "task_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "message": "Test task queued successfully"
# }
```

```bash
# Android FTM Test
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_method": "docker",
    "platform": "android",
    "test_suite": "suites/mobile/suites/ftm/android/tests",
    "test_markers": "android_ftm and fac_ftc_token and functional",
    "lab_config": "/test_files/mobile_auto/android13_ftm_testing_config.yml",
    "docker_tag": "latest",
    "timeout": 3600,
    "labels": ["android-automation"]
  }'
```

#### Trigger SSH-based Test (Legacy)

```bash
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_method": "ssh",
    "vm_id": "your-vm-uuid",
    "test_suite": "smoke_tests",
    "test_cases": ["test_login", "test_dashboard"],
    "timeout": 1800,
    "labels": ["linux", "python"]
  }'
```

### Method 2: Using Jenkins Scripts

```bash
# Set environment variables
export docker_tag="latest"
export JOB_BASE_NAME="iOS_FTM_Smoke_Test"
export WORKSPACE="/tmp/workspace"
export BUILD_NUMBER="1"

# Run iOS tests
bash backend/app/uploads/lab_config/jenkins_scripts/ios_ftm_docker_test.sh

# Run Android tests
bash backend/app/uploads/lab_config/jenkins_scripts/android_ftm_docker_test.sh
```

### Method 3: Using Jenkins Pipeline

Create a Jenkins job with the provided Jenkinsfiles:

1. In Jenkins, create a new Pipeline job
2. Configure pipeline from SCM or paste the Jenkinsfile content
3. Build with parameters

---

## 📊 How to Check Running Test Status

### Method 1: Check Specific Test Status

```bash
# Get test status by task_id
curl http://localhost:8000/api/tests/status/{task_id}

# Example:
curl http://localhost:8000/api/tests/status/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 50,
  "result": null,
  "error": null,
  "node_id": "node-uuid-here",
  "start_time": "2025-11-13T10:30:00Z",
  "end_time": null,
  "duration": null
}
```

**Status Values:**
- `queued` - Test is waiting for available node
- `acquiring_node` - Looking for available Jenkins node
- `running` - Test is currently executing
- `completed` - Test finished successfully
- `failed` - Test failed or error occurred

**Progress Values:**
- `0-10%` - Queued
- `10-20%` - Acquiring node
- `20-50%` - Setting up test environment
- `50-90%` - Running tests
- `90-100%` - Collecting results
- `100%` - Completed

### Method 2: Get All Running Tests

```bash
# Get all test tasks
curl http://localhost:8000/api/tests/all

# Filter by status (if endpoint supports it)
curl http://localhost:8000/api/tests/all?status=running
```

### Method 3: Check Jenkins Node Status

```bash
# Get all Jenkins nodes
curl http://localhost:8000/api/jenkins/nodes

# Get specific node
curl http://localhost:8000/api/jenkins/nodes/{node_id}

# Get node pool statistics
curl http://localhost:8000/api/jenkins/nodes/pool/stats
```

**Node Status Response:**
```json
{
  "nodes": [
    {
      "id": "node-uuid",
      "name": "jenkins-slave-01",
      "host": "192.168.1.100",
      "port": 22,
      "status": "BUSY",
      "current_executors": 2,
      "max_executors": 5,
      "labels": ["ios-automation", "linux"],
      "total_tests_executed": 150,
      "pass_rate": 92.5,
      "average_test_duration": 450.2,
      "cpu_usage": 65.3,
      "memory_usage": 72.1,
      "disk_usage": 45.0
    }
  ]
}
```

### Method 4: Monitor Test Execution in Real-time

Using WebSocket (if available):

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/tests/{task_id}');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress);
  console.log('Status:', data.status);
  console.log('Logs:', data.logs);
};
```

### Method 5: View Test Results

```bash
# After test completes, view results
curl http://localhost:8000/api/tests/results/{task_id}

# Download Allure results
curl http://localhost:8000/api/tests/results/{task_id}/allure -o allure-results.zip

# View test logs
curl http://localhost:8000/api/tests/logs/{task_id}
```

---

## 🔍 Monitoring Commands

### Check Node Health

```bash
# Ping specific node
curl -X POST http://localhost:8000/api/jenkins/nodes/{node_id}/ping

# Health check all nodes
curl -X POST http://localhost:8000/api/jenkins/nodes/pool/health-check
```

### Monitor Docker Containers (on Jenkins node)

```bash
# SSH to Jenkins node
ssh jenkins@node-ip

# List running test containers
docker ps -f name=mtp_test

# View container logs
docker logs -f mtp_test_12345678

# Monitor container stats
docker stats mtp_test_12345678
```

### Monitor Test Workspace

```bash
# On Jenkins node
ls -lh /home/jenkins/workspace/mobile_automation/allure-results/

# Count result files
ls -1 /home/jenkins/workspace/mobile_automation/allure-results/*.json | wc -l

# Check latest test output
tail -f /home/jenkins/workspace/mobile_automation/test.log
```

---

## 📈 Example Monitoring Workflow

### 1. Start Test and Get Task ID

```bash
TASK_ID=$(curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_method": "docker",
    "platform": "ios",
    "test_suite": "suites/mobile/suites/ftm/ios/tests",
    "test_markers": "ios_ftm and smoke",
    "lab_config": "/test_files/mobile_auto/ios16_ftm_testing_config.yml",
    "docker_tag": "latest"
  }' | jq -r '.task_id')

echo "Task ID: $TASK_ID"
```

### 2. Monitor Progress

```bash
# Poll status every 5 seconds
while true; do
  STATUS=$(curl -s http://localhost:8000/api/tests/status/$TASK_ID | jq -r '.status')
  PROGRESS=$(curl -s http://localhost:8000/api/tests/status/$TASK_ID | jq -r '.progress')
  echo "$(date) - Status: $STATUS, Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 5
done
```

### 3. Get Results

```bash
# Get final result
curl http://localhost:8000/api/tests/status/$TASK_ID | jq

# Check if passed
RESULT=$(curl -s http://localhost:8000/api/tests/status/$TASK_ID | jq -r '.result.status')
if [ "$RESULT" = "passed" ]; then
  echo "✓ Tests passed!"
else
  echo "✗ Tests failed!"
fi
```

---

## 🛠️ Troubleshooting Test Execution

### Test Stuck in "queued" Status

**Cause:** No available Jenkins nodes

**Solution:**
```bash
# Check node availability
curl http://localhost:8000/api/jenkins/nodes/pool/stats

# Add more nodes or wait for current tests to finish
```

### Test Stuck in "acquiring_node" Status

**Cause:** Nodes exist but none match the required labels

**Solution:**
```bash
# Check node labels
curl http://localhost:8000/api/jenkins/nodes | jq '.[] | {name: .name, labels: .labels}'

# Update test request with correct labels
```

### Test Failed Immediately

**Cause:** SSH connection error, Docker image pull failure, or configuration error

**Solution:**
```bash
# Check error message
curl http://localhost:8000/api/tests/status/$TASK_ID | jq '.error'

# Test node connectivity
curl -X POST http://localhost:8000/api/jenkins/nodes/{node_id}/ping

# Check Docker image availability
ssh jenkins@node-ip "docker pull 10.160.16.60/pytest-automation/pytest_automation:latest"
```

### No Results After Test Completes

**Cause:** Allure results not collected, volume mount issue

**Solution:**
```bash
# SSH to node and check results directory
ssh jenkins@node-ip "ls -lh /home/jenkins/workspace/*/allure-results/"

# Check Docker volume mounts
ssh jenkins@node-ip "docker inspect mtp_test_container | jq '.[0].Mounts'"
```

---

## 📊 Advanced Monitoring

### Create Monitoring Dashboard Script

```bash
#!/bin/bash
# monitor_tests.sh

while true; do
  clear
  echo "=========================================="
  echo "MTP Test Execution Monitor"
  echo "$(date)"
  echo "=========================================="
  echo ""

  # Node status
  echo "Jenkins Nodes:"
  curl -s http://localhost:8000/api/jenkins/nodes | \
    jq -r '.[] | "\(.name): \(.status) (\(.current_executors)/\(.max_executors) executors)"'
  echo ""

  # Running tests
  echo "Running Tests:"
  curl -s http://localhost:8000/api/tests/all | \
    jq -r '.[] | select(.status == "running") | "\(.task_id): \(.progress)%"'
  echo ""

  # Pool stats
  echo "Pool Statistics:"
  curl -s http://localhost:8000/api/jenkins/nodes/pool/stats | jq

  sleep 10
done
```

### Create Test Completion Notifier

```bash
#!/bin/bash
# notify_completion.sh

TASK_ID=$1
EMAIL=$2

while true; do
  STATUS=$(curl -s http://localhost:8000/api/tests/status/$TASK_ID | jq -r '.status')

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    RESULT=$(curl -s http://localhost:8000/api/tests/status/$TASK_ID | jq)

    echo "$RESULT" | mail -s "Test $TASK_ID $STATUS" $EMAIL
    break
  fi

  sleep 30
done
```

---

## 🔗 API Reference Quick Guide

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tests/execute` | POST | Trigger new test |
| `/api/tests/status/{task_id}` | GET | Get test status |
| `/api/tests/all` | GET | List all tests |
| `/api/tests/results/{task_id}` | GET | Get test results |
| `/api/tests/logs/{task_id}` | GET | Get test logs |
| `/api/jenkins/nodes` | GET | List Jenkins nodes |
| `/api/jenkins/nodes/{node_id}` | GET | Get node details |
| `/api/jenkins/nodes/pool/stats` | GET | Get pool statistics |
| `/api/jenkins/nodes/{node_id}/ping` | POST | Ping node |

---

## 💡 Best Practices

1. **Always save the task_id** returned when triggering tests
2. **Use labels** to route tests to appropriate nodes
3. **Set appropriate timeouts** based on test complexity
4. **Monitor node health** regularly
5. **Clean up completed tasks** periodically
6. **Use WebSocket** for real-time monitoring instead of polling
7. **Archive test results** before they're cleared from memory

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
