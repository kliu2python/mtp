# Worker Dashboard Guide

## 📊 Overview

The Worker Dashboard provides real-time monitoring of Jenkins worker nodes and test execution across your distributed testing infrastructure. It gives you complete visibility into node status, test progress, resource utilization, and system health.

---

## 🎯 Features

### 1. Real-Time Monitoring
- **Auto-refresh**: Automatically updates every 5 seconds
- **Live Status**: Real-time node and test status
- **Performance Metrics**: CPU, memory, and disk usage
- **Queue Monitoring**: View queued and running tests

### 2. Node Management
- **Node Control**: Ping, enable, and disable nodes
- **Resource Tracking**: Monitor CPU, memory, and disk utilization
- **Executor Status**: See executor availability and utilization
- **Performance Metrics**: Track test pass rates and execution times

### 3. Test Execution Tracking
- **Running Tests**: Monitor currently executing tests with progress
- **Test Queue**: View tests waiting for execution
- **Recent History**: Timeline of completed tests
- **Success Metrics**: Real-time success rate and completion stats

### 4. Alerts & Notifications
- **System Alerts**: Automatic alerts for node issues
- **Resource Warnings**: High CPU/memory/disk usage alerts
- **Long-running Tests**: Alerts for tests exceeding time limits
- **Queue Depth**: Warnings for high queue depths

---

## 🚀 Accessing the Dashboard

### Web UI
1. Open Mobile Test Pilot: `http://localhost:3000`
2. Click "Worker Dashboard" in the left sidebar
3. The dashboard will load with real-time data

### Direct API Access
```bash
# Get dashboard overview
curl http://localhost:8000/api/dashboard/overview

# Get live node status
curl http://localhost:8000/api/dashboard/nodes/live

# Get running tests
curl http://localhost:8000/api/dashboard/tests/running

# Get queued tests
curl http://localhost:8000/api/dashboard/tests/queue

# Get recent test history
curl http://localhost:8000/api/dashboard/tests/recent?limit=20

# Get system alerts
curl http://localhost:8000/api/dashboard/alerts

# Get hourly statistics
curl http://localhost:8000/api/dashboard/stats/hourly
```

---

## 📖 Dashboard Sections

### 1. Statistics Overview

Four key metrics cards at the top:

#### Total Nodes
- Shows total number of registered Jenkins nodes
- Displays count of online nodes
- Icon: Cluster
- **Example**: "8 total (6 online)"

#### Executor Utilization
- Percentage of active executors
- Shows active/total executor count
- Color-coded: Green (<80%), Red (>80%)
- **Example**: "75.5% (15 / 20 active)"

#### Running Tests
- Number of currently executing tests
- Shows queued tests count
- **Example**: "3 (+2 queued)"

#### Success Rate (Today)
- Percentage of passed tests today
- Shows completed/total count
- Color-coded: Green (>80%), Red (<80%)
- **Example**: "92.5% (37 passed / 40 total)"

### 2. Worker Nodes Table

Comprehensive table showing all Jenkins nodes:

| Column | Description | Actions |
|--------|-------------|---------|
| **Node Name** | Node identifier with status badge | - |
| **Status** | Current node status (ONLINE, BUSY, OFFLINE, ERROR) | Color-coded tag |
| **Executors** | Utilization bar showing current/max executors | Progress bar |
| **Running Tests** | Count of tests currently running on this node | Badge counter |
| **Resources** | CPU and memory usage percentages | Tooltips for details |
| **Performance** | Total tests and pass rate statistics | - |
| **Labels** | Node labels for test routing | Expandable tags |
| **Actions** | Node control buttons | Ping, Enable/Disable |

**Node Status Colors:**
- 🟢 **ONLINE** (Green) - Node is available and ready
- 🔵 **BUSY** (Blue) - Node is executing tests
- ⚪ **OFFLINE** (Gray) - Node is offline or disabled
- 🔴 **ERROR** (Red) - Node has errors

### 3. Running Tests Panel

Shows all currently executing tests:

- **Task ID**: Short identifier (first 8 characters)
- **Status**: Current execution status
- **Progress**: Visual progress bar (0-100%)
- **Duration**: Elapsed time
- **Node**: Which worker node is running the test

**Real-time Progress Tracking:**
- 0-10%: Queued
- 10-20%: Acquiring node
- 20-50%: Setting up environment
- 50-90%: Executing tests
- 90-100%: Collecting results
- 100%: Completed

### 4. Queued Tests Panel

Lists tests waiting for execution:

- Shows test task IDs
- Displays queue position
- Updates in real-time as tests are picked up

**Empty State**: "No tests in queue" when no tests are waiting

### 5. Recent Test History

Timeline view of completed tests:

- Last 10 test executions
- Visual timeline with status icons
- ✓ Green checkmark for passed tests
- ✗ Red X for failed tests
- Duration for each test
- Chronological order (newest first)

### 6. System Alerts

Dynamic alert panel showing:

**Alert Types:**
- ⚠️ **Warning** (Yellow) - Non-critical issues
  - Node offline
  - High resource usage (CPU/memory)
  - Long-running tests
  - High queue depth

- ❌ **Error** (Red) - Critical issues
  - Node in error state
  - Disk space critical (>90%)
  - Test execution failures

**Alert Examples:**
```
⚠ Node 'jenkins-slave-01' is offline
⚠ Node 'jenkins-slave-02' has high CPU usage (95.3%)
❌ Node 'jenkins-slave-03' has high disk usage (92.1%)
⚠ Test 12345678 has been running for 2.5 hours
⚠ 12 tests are waiting in queue
```

---

## 🎮 Dashboard Controls

### Auto-Refresh Toggle
- **Location**: Top right corner
- **ON** (Blue button): Updates every 5 seconds
- **OFF** (Gray button): Manual refresh only
- **Use Case**: Turn off during detailed inspection

### Refresh Now Button
- **Location**: Top right corner
- **Action**: Immediately fetches latest data
- **Icon**: Reload symbol
- **Use Case**: Force update without waiting

### Node Actions

#### Ping Node
- **Icon**: API connection icon
- **Action**: Tests SSH connectivity to node
- **Response**: Success/failure message
- **Use Case**: Verify node is reachable

#### Enable/Disable Node
- **Icon**: Play (enable) / Stop (disable)
- **Action**: Activates or deactivates node
- **Effect**:
  - **Disable**: Sets max_executors to 0, prevents new tests
  - **Enable**: Restores max_executors, allows test execution
- **Use Case**: Maintenance, debugging, capacity management

---

## 📊 API Endpoints Reference

### Dashboard Overview
```bash
GET /api/dashboard/overview
```

**Response:**
```json
{
  "timestamp": "2025-11-13T10:30:00Z",
  "nodes": {
    "total": 8,
    "online": 6,
    "busy": 2,
    "offline": 1,
    "error": 0
  },
  "executors": {
    "total": 40,
    "active": 15,
    "available": 25,
    "utilization": 37.5
  },
  "tests": {
    "running": 3,
    "queued": 2,
    "completed_today": 45,
    "failed_today": 3,
    "success_rate": 93.75,
    "total_today": 48
  },
  "node_details": [...],
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "disk_percent": 38.5
  },
  "pool_health": "healthy"
}
```

### Live Node Status
```bash
GET /api/dashboard/nodes/live
```

Optimized for frequent polling, returns minimal data:
- Node ID, name, status
- Executor counts
- Running test count
- Resource usage

### Running Tests
```bash
GET /api/dashboard/tests/running
```

Returns all currently executing tests with elapsed time.

### Test Queue
```bash
GET /api/dashboard/tests/queue
```

Returns tests in `queued` or `acquiring_node` status.

### Recent Tests
```bash
GET /api/dashboard/tests/recent?limit=20
```

Returns recently completed or failed tests, sorted by end time.

### System Alerts
```bash
GET /api/dashboard/alerts
```

Returns current system alerts and warnings.

### Hourly Statistics
```bash
GET /api/dashboard/stats/hourly
```

Returns test execution statistics for the last 24 hours.

### Node Actions
```bash
POST /api/dashboard/nodes/{node_id}/action?action={action_name}
```

**Actions:**
- `ping` - Test node connectivity
- `disable` - Disable the node
- `enable` - Enable the node

**Example:**
```bash
# Ping node
curl -X POST http://localhost:8000/api/dashboard/nodes/abc-123/action?action=ping

# Disable node
curl -X POST http://localhost:8000/api/dashboard/nodes/abc-123/action?action=disable

# Enable node
curl -X POST http://localhost:8000/api/dashboard/nodes/abc-123/action?action=enable
```

---

## 🔍 Monitoring Scenarios

### Scenario 1: Check System Health

1. Open Worker Dashboard
2. Review Statistics Overview
   - ✅ Executor utilization < 80%
   - ✅ Success rate > 80%
   - ✅ No errors in nodes count
3. Check Alerts panel
   - ✅ No critical (red) alerts
4. Review node table
   - ✅ All nodes ONLINE or BUSY
   - ✅ Resource usage < 90%

**Healthy System**: Green metrics, no alerts, nodes online

### Scenario 2: Investigate Slow Tests

1. Go to Running Tests panel
2. Look for tests with high duration
3. Note the Task ID
4. Check which node is running it (in table)
5. Review node resources
6. If resources high, node may be overloaded
7. Consider disabling node temporarily

### Scenario 3: Manage Queue Buildup

**Symptoms:**
- High number in Queued Tests
- Alert: "X tests are waiting in queue"

**Actions:**
1. Check executor utilization
2. If < 80%, check for offline nodes
3. Enable offline nodes if available
4. If > 80%, all nodes busy - normal
5. Consider adding more nodes long-term

### Scenario 4: Handle Node Failure

**Symptoms:**
- Node status shows ERROR (red)
- Alert: "Node 'X' is in error state"

**Actions:**
1. Click Ping button to test connectivity
2. If ping fails:
   - SSH to node manually
   - Check Docker daemon
   - Check disk space
   - Review node logs
3. If ping succeeds:
   - Disable node
   - Investigate on node
   - Enable when fixed

### Scenario 5: Capacity Planning

**Questions to Answer:**
1. What's average executor utilization?
   - View over time during peak hours
2. How often do tests queue?
   - Monitor queue depth
3. What's node distribution?
   - Count online vs total nodes
4. Are resources adequate?
   - Check CPU/memory across nodes

**Dashboard Metrics:**
- Utilization > 80% consistently = Need more capacity
- Queue depth > 10 frequently = Need more nodes
- Success rate < 80% = Investigate test quality or infrastructure

---

## ⚡ Performance Tips

### Optimize Dashboard Loading

**Reduce API Calls:**
```javascript
// Use live endpoint for frequent updates
GET /api/dashboard/nodes/live  // Lighter payload

// Use full overview less frequently
GET /api/dashboard/overview    // Complete data
```

**Adjust Refresh Rate:**
- **High Activity**: 5-second refresh
- **Normal Activity**: 10-second refresh
- **Low Activity**: 30-second refresh or manual

### Monitor Large Deployments

For 50+ nodes:

1. Use pagination in node table
2. Filter nodes by status
3. Use live endpoint for polling
4. Increase refresh interval
5. Use alerts instead of constant monitoring

---

## 🔧 Troubleshooting

### Dashboard Not Loading

**Issue**: Dashboard shows loading spinner indefinitely

**Causes & Solutions:**
1. Backend API not running
   - Check: `curl http://localhost:8000/health`
   - Fix: Start backend server

2. CORS errors
   - Check browser console
   - Fix: Verify CORS settings in backend

3. Network connectivity
   - Check: Can you reach API_URL?
   - Fix: Update .env file with correct URL

### No Data Showing

**Issue**: Dashboard loads but shows 0 for everything

**Causes & Solutions:**
1. No Jenkins nodes registered
   - Check: `curl http://localhost:8000/api/jenkins/nodes`
   - Fix: Add Jenkins nodes via UI or API

2. No tests executed
   - Check: `curl http://localhost:8000/api/tests/all`
   - Fix: Trigger a test

### Node Actions Not Working

**Issue**: Clicking Ping/Enable/Disable doesn't work

**Causes & Solutions:**
1. Check browser console for errors
2. Verify node ID is valid
3. Check backend logs
4. Ensure user has permissions

### Resource Metrics Show 0%

**Issue**: CPU/Memory/Disk show 0% or N/A

**Causes:**
- Node monitoring not configured
- psutil not installed on node
- SSH connection issues

**Solution:**
- Install psutil: `pip install psutil`
- Verify SSH connectivity
- Check node health script

---

## 📈 Best Practices

### 1. Regular Monitoring
- Check dashboard at start of day
- Monitor during peak test times
- Review alerts before leaving

### 2. Proactive Management
- Disable nodes before maintenance
- Monitor queue depth trends
- Track success rate over time

### 3. Alert Response
- Address errors immediately
- Investigate warnings within 1 hour
- Document recurring issues

### 4. Capacity Planning
- Review utilization weekly
- Plan node additions quarterly
- Monitor test growth trends

### 5. Documentation
- Document node maintenance
- Record resolution procedures
- Track performance baselines

---

## 🎓 Training Exercises

### Exercise 1: Health Check
1. Open Worker Dashboard
2. Identify all online nodes
3. Note executor utilization
4. Check for any alerts
5. Record success rate

### Exercise 2: Trigger and Monitor Test
1. Trigger a test via API
2. Watch it appear in queue
3. Monitor as it starts running
4. Track progress to completion
5. Verify in recent history

### Exercise 3: Node Management
1. Pick an online node
2. Ping the node
3. Disable the node
4. Verify no new tests go to it
5. Enable the node
6. Confirm it's available again

### Exercise 4: Alert Investigation
1. Wait for or create an alert
2. Read the alert message
3. Identify the affected resource
4. Take appropriate action
5. Verify alert clears

---

## 📞 Support

### Getting Help

**Documentation:**
- [Test Execution Guide](TEST_EXECUTION_GUIDE.md)
- [Main README](README.md)
- [Quick Start](QUICK_START.md)

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Logging:**
```bash
# Backend logs
docker logs mtp-backend

# Frontend logs
Check browser console (F12)
```

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
**Dashboard URL:** `http://localhost:3000/workers`
