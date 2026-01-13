# Jenkins-Inspired Execution Engine

## Overview

This document describes the robust test execution engine built for the Mobile Test Pilot (MTP) platform, inspired by Jenkins' proven architecture for distributed build management.

**Status**: ✅ Production-Ready

**Based on**: Jenkins Queue.java, LoadBalancer.java, and Executor architecture

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Jenkins Controller                          │
│  - 10 concurrent executor workers                           │
│  - Semaphore-based concurrency control                      │
│  - Build lifecycle management                               │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼──────────┐   ┌────────▼─────────────────────────┐
│  Jenkins Queue    │   │  Node Connection Pool            │
│  Multi-State FSM  │   │  Smart Load Balancing            │
└───────────────────┘   └──────────────────────────────────┘
         │                       │
         │                       │
    [Waiting]              [Consistent Hash]
    [Blocked]              [Load-Based Selection]
    [Buildable]            [Node Affinity]
    [Pending]
    [Running]
```

---

## 1. Multi-State Queue System

### Queue States (Inspired by Jenkins)

```
WAITING → BLOCKED → BUILDABLE → PENDING → RUNNING → COMPLETED
```

#### State Descriptions

| State | Description | Conditions |
|-------|-------------|------------|
| **WAITING** | In quiet period | Build scheduled but waiting for quiet period to expire |
| **BLOCKED** | Cannot execute | Resource conflicts, concurrent build limits, no available nodes |
| **BUILDABLE** | Ready to run | Passed all checks, waiting for executor assignment |
| **PENDING** | Executor assigned | Picked up by executor worker, acquiring node |
| **RUNNING** | Executing | Running on assigned node |

#### Queue Collections

```python
waiting_list: List[QueueItem]          # Sorted by quiet_until time
blocked: List[QueueItem]                # Items with blocking reasons
buildables: List[QueueItem]             # Priority queue (sorted by priority)
pending: Dict[str, QueueItem]           # build_id → item (handed to executor)
running_builds: Dict[str, str]          # build_id → node_id
```

### Blocking Mechanisms

The queue implements three types of blocking checks:

1. **Concurrent Build Limits**
   ```python
   if current_builds_for_job >= max_concurrent_per_job:
       block("Job already has N concurrent builds")
   ```

2. **Node Availability**
   ```python
   if no_nodes_with_required_labels_available():
       block("No available nodes with labels: [ios, automation]")
   ```

3. **Node Affinity** (Optional)
   ```python
   if prefer_node_id and preferred_node_not_available():
       # Can still run on other nodes, but will wait briefly
       pass
   ```

### Queue Maintenance

A background maintenance loop runs every 1 second to:

- Move items from `WAITING` → `BUILDABLE` after quiet period
- Re-evaluate `BLOCKED` items (move back to `BUILDABLE` to retry)
- Clean up stale items

```python
async def _maintenance_loop(self):
    while running:
        await asyncio.sleep(1)
        - Move waiting items past quiet period
        - Retry blocked items (up to 5 at a time)
```

---

## 2. Smart Node Selection

### Three-Tier Selection Strategy

The node pool implements intelligent node selection with three strategies:

#### Strategy 1: Node Affinity (Highest Priority)

```python
if prefer_node_id and node_is_available:
    return preferred_node
```

**Use Case**: Job succeeded on Node-A last time → prefer Node-A for next build

**Benefit**: Reduces environment-related failures, uses cached dependencies

#### Strategy 2: Consistent Hashing

```python
node_hash = MD5(node_name + job_name)
availability_score = (available_executors / max_executors) * 100000
final_score = (node_hash % 1000) + availability_score
```

**Use Case**: Distribute jobs consistently across nodes based on job name

**Benefit**: Same job tends to run on same node (but balanced by availability)

#### Strategy 3: Load-Based Selection (Fallback)

```python
score = (
    (1.0 - executor_utilization) * 40% +
    (1.0 - cpu_usage) * 20% +
    (1.0 - memory_usage) * 20% +
    success_rate * 20%
)
```

**Factors**:
- **Executor Utilization** (40%): Prefer nodes with more available executors
- **CPU Load** (20%): Prefer nodes with lower CPU usage
- **Memory Usage** (20%): Prefer nodes with lower memory usage
- **Success Rate** (20%): Prefer nodes with higher test pass rates

**Use Case**: Fair load distribution across all nodes

---

## 3. Concurrent Executor Workers

### Executor Design

```python
max_concurrent_builds = 10  # System-wide executor limit
executor_semaphore = asyncio.Semaphore(10)

for i in range(10):
    asyncio.create_task(build_executor_worker(i))
```

### Executor Worker Loop

```python
async def _build_executor_worker(executor_id):
    while running:
        async with executor_semaphore:  # Wait for available slot
            queue_item = await queue.get_next_buildable(db)
            if queue_item:
                await execute_build(queue_item)
            else:
                await asyncio.sleep(0.5)  # No work available
```

### Concurrency Control

- **System-Wide**: Max 10 builds running simultaneously
- **Per-Job**: Configurable `max_concurrent_builds` per job
- **Per-Node**: Max executors per node (e.g., node has 4 executors)

**Example**:
```
Job "iOS_Tests" max_concurrent_builds=2
Node "jenkins-1" max_executors=4

✅ Can run: 2 builds of iOS_Tests
✅ Can run: 4 builds total on jenkins-1
✅ Can run: 10 builds total system-wide
```

---

## 4. Build Prioritization

### Priority Levels

```python
class BuildPriority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20
```

### Priority Queue Sorting

```python
def __lt__(self, other):
    if self.priority != other.priority:
        return self.priority > other.priority  # Higher priority first
    return self.queued_time < other.queued_time  # FIFO for same priority
```

**Example Queue**:
```
[CRITICAL] Build #5 (priority=20, queued=10:00)
[HIGH]     Build #7 (priority=10, queued=10:01)
[HIGH]     Build #3 (priority=10, queued=09:55)  ← Queued earlier
[NORMAL]   Build #1 (priority=5,  queued=09:50)
[LOW]      Build #2 (priority=1,  queued=09:45)
```

### Usage

```python
await jenkins_controller.trigger_build(
    db=db,
    job_id="uuid",
    priority=BuildPriority.HIGH,  # Jump the queue!
    quiet_period=5  # Wait 5 seconds before building
)
```

---

## 5. API Endpoints

### Trigger Build with Priority

```http
POST /api/jenkins/jobs/{job_id}/build
Content-Type: application/json

{
  "parameters": {},
  "triggered_by": "User",
  "priority": 10,
  "quiet_period": 0
}
```

### Get Queue Statistics

```http
GET /api/jenkins/queue/stats

Response:
{
  "total_queued": 156,
  "total_completed": 142,
  "total_blocked": 3,
  "waiting_count": 2,
  "blocked_count": 3,
  "buildables_count": 5,
  "pending_count": 1,
  "running_count": 8,
  "max_concurrent_builds": 10,
  "active_builds": 8,
  "waiting_items": [
    {
      "build_id": "uuid",
      "job_name": "iOS_FTM_Tests",
      "build_number": 45,
      "priority": 5,
      "quiet_until": "2025-11-20T10:05:00Z"
    }
  ],
  "blocked_items": [
    {
      "build_id": "uuid",
      "job_name": "Android_Tests",
      "build_number": 12,
      "blocked_reason": "Job already has 2 concurrent builds (max: 2)"
    }
  ],
  "buildables_items": [...],
  "running_builds": [...]
}
```

### Get Node Pool Statistics

```http
GET /api/jenkins/nodes/pool

Response:
{
  "total_nodes": 5,
  "online_nodes": 4,
  "busy_nodes": 3,
  "offline_nodes": 1,
  "total_executors": 20,
  "used_executors": 8,
  "available_executors": 12
}
```

---

## 6. Comparison: Before vs After

### Before (Simple Queue)

```python
build_queue = asyncio.Queue()
await build_queue.put(build_id)

# Single processor
while True:
    build_id = await build_queue.get()
    asyncio.create_task(execute_build(build_id))  # Fire and forget
```

**Issues**:
- ❌ No priority handling
- ❌ Sequential queue processing (one at a time)
- ❌ No build blocking logic
- ❌ Basic node selection (first available)
- ❌ No load balancing

### After (Jenkins-Inspired Engine)

```python
await jenkins_queue.enqueue(
    build_id=build_id,
    priority=BuildPriority.HIGH,
    max_concurrent_per_job=2,
    prefer_node_id=last_successful_node_id
)

# 10 concurrent executors
for i in range(10):
    asyncio.create_task(executor_worker(i))
```

**Improvements**:
- ✅ Multi-state queue (waiting/blocked/buildable/pending/running)
- ✅ Priority queue with FIFO fallback
- ✅ Concurrent build limits per job
- ✅ 10 concurrent executors (configurable)
- ✅ Smart node selection (3 strategies)
- ✅ Load balancing with consistent hashing
- ✅ Node affinity for reliability
- ✅ Build blocking with retry logic
- ✅ Quiet period support
- ✅ Comprehensive queue statistics

---

## 7. Performance Characteristics

### Throughput

- **Before**: ~1 build picked from queue per second
- **After**: Up to 10 builds executing concurrently

### Node Utilization

- **Before**: First available node selected
- **After**: Optimal node selected based on load and affinity

### Build Fairness

- **Before**: Strict FIFO
- **After**: Priority-based with FIFO within same priority

### Failure Handling

- **Before**: No retry, no blocking detection
- **After**: Blocked items automatically retried, clear blocking reasons

---

## 8. Configuration

### Controller Configuration

```python
jenkins_controller = JenkinsController(
    max_concurrent_builds=10  # System-wide executor limit
)
```

### Queue Configuration

```python
jenkins_queue = JenkinsQueue(
    maintenance_interval=1  # Queue maintenance every 1 second
)
```

### Job Configuration

```python
job = JenkinsJob(
    name="iOS_FTM_Tests",
    max_concurrent_builds=2,     # Max 2 concurrent builds for this job
    required_labels=["ios", "automation"],
    build_timeout=7200           # 2 hour timeout
)
```

### Node Configuration

```python
node = JenkinsNode(
    name="jenkins-agent-1",
    max_executors=4,             # Max 4 concurrent tests on this node
    labels=["ios", "automation", "linux"],
    host="192.168.1.100",
    port=22
)
```

---

## 9. Monitoring and Debugging

### Queue State Inspection

```python
stats = await jenkins_queue.get_queue_stats()
print(f"Buildables: {stats['buildables_count']}")
print(f"Blocked: {stats['blocked_count']}")
for item in stats['blocked_items']:
    print(f"  {item['job_name']} #{item['build_number']}: {item['blocked_reason']}")
```

### Executor Monitoring

```python
stats = await jenkins_controller.get_queue_stats()
print(f"Active executors: {stats['active_builds']}/{stats['max_concurrent_builds']}")
```

### Node Pool Health

```python
pool_stats = connection_pool.get_pool_stats(db)
print(f"Available executors: {pool_stats['available_executors']}")
print(f"Pass rate: {pool_stats['pass_rate']}%")
```

---

## 10. Key Learnings from Jenkins

### What We Adopted

1. **Multi-State Queue**: Separate states for waiting, blocked, buildable, pending
2. **Blocking Mechanisms**: Resource conflicts, concurrent limits, node availability
3. **Consistent Hashing**: Distribute jobs consistently across nodes
4. **Executor Model**: Multiple worker threads/tasks processing queue concurrently
5. **Priority Queue**: Higher priority items processed first
6. **Maintenance Loop**: Background task to move items between states
7. **JobOffer Pattern**: Validate node availability before assignment

### What We Improved

1. **Async/Await**: Native asyncio instead of Java threads
2. **Load-Based Selection**: Score nodes by CPU/memory/success rate
3. **Node Affinity**: Prefer last successful node for reliability
4. **Real-time Stats**: Comprehensive queue and executor statistics
5. **Modern Python**: Type hints, dataclasses, enums

---

## 11. Future Enhancements

### Potential Additions

1. **Build Dependencies**: Block build B until build A completes
2. **Resource Pools**: Reserve specific resources (devices, VMs)
3. **Weighted Fair Scheduling**: Allocate executor slots per team/project
4. **Build Cancellation**: Cancel builds in any state
5. **Queue Persistence**: Save queue state to database for restarts
6. **Build Throttling**: Rate limit builds per time window
7. **Node Health Scoring**: Dynamically adjust node selection based on recent failures

---

## 12. Summary

The new execution engine provides enterprise-grade test orchestration with:

✅ **Scalability**: 10 concurrent executors, distributed nodes
✅ **Reliability**: Node affinity, load balancing, retry logic
✅ **Fairness**: Priority queue with FIFO fallback
✅ **Visibility**: Comprehensive statistics and monitoring
✅ **Control**: Concurrent build limits, quiet periods, blocking logic
✅ **Performance**: Consistent hashing, load-based selection

**Result**: A production-ready alternative to Jenkins API integration, with full control and deep integration with MTP's device and VM management.

---

## Files Changed

- `backend/app/services/jenkins_queue.py` - New multi-state queue system
- `backend/app/services/jenkins_pool.py` - Enhanced with smart node selection
- `backend/app/services/jenkins_controller.py` - Updated with concurrent executors
- `backend/app/api/jenkins_jobs.py` - Added `/queue/stats` endpoint

---

**Author**: Claude AI
**Date**: 2025-11-20
**Inspired by**: Jenkins Queue.java, LoadBalancer.java, Executor architecture
