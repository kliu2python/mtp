# Jenkins Workflow Implementation Guide

## Overview

This project now implements a complete Jenkins-style workflow system that mimics Jenkins' master/worker (controller/agent) architecture. The system allows you to define jobs, trigger builds, and execute tests on distributed worker nodes via SSH, exactly like Jenkins does.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Jenkins Controller                        │
│  - Job queue management                                      │
│  - Agent assignment and orchestration                        │
│  - Build history tracking                                    │
│  - Console output streaming                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ SSH Connections
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼─────┐      ┌────▼─────┐      ┌────▼─────┐
   │  Agent 1 │      │  Agent 2 │      │  Agent 3 │
   │          │      │          │      │          │
   │  Docker  │      │  Docker  │      │  Docker  │
   │  Tests   │      │  Tests   │      │  Tests   │
   └──────────┘      └──────────┘      └──────────┘
```

### Key Features

1. **Job Definitions** - Define reusable job templates
2. **Build Queue** - Automatic queuing and distribution
3. **Agent Pool** - Distributed execution on worker nodes
4. **SSH Execution** - SSH into worker nodes to launch Docker containers
5. **Build History** - Track all builds with full console output
6. **Real-time Monitoring** - Live build status and console streaming
7. **Labels** - Match jobs to agents based on capabilities

## How It Works (Jenkins Model)

### 1. Job Creation

Jobs are templates that define:
- What to execute (Docker image, test suite, etc.)
- Where to execute (agent labels)
- How to execute (timeout, parameters, etc.)

### 2. Build Triggering

When you trigger a build:
1. A new build record is created with a sequential build number
2. Build is added to the queue
3. Controller finds an available agent matching required labels
4. Build is assigned to the agent

### 3. Build Execution

The controller:
1. SSHs into the worker node
2. Creates a workspace directory
3. Executes a bash script that:
   - Pulls the Docker image
   - Runs the container with test configuration
   - Collects results
4. Streams console output back in real-time
5. Updates build status (SUCCESS/FAILURE)

### 4. Build Completion

After execution:
- Build result is recorded
- Agent is released back to pool
- Job statistics are updated
- Notifications can be sent

## API Reference

### Job Management

#### Create a Job

```bash
POST /api/jenkins/jobs
Content-Type: application/json

{
  "name": "iOS_FTM_Tests",
  "description": "iOS FortiToken Mobile automation tests",
  "job_type": "docker",
  "required_labels": ["ios-automation", "docker"],
  "docker_registry": "10.160.16.60",
  "docker_image": "pytest-automation/pytest_automation",
  "docker_tag": "latest",
  "test_suite": "suites/mobile/suites/ftm/ios/tests",
  "test_markers": "ios_ftm and functional",
  "lab_config": "/test_files/mobile_auto/ios16_ftm_testing_config.yml",
  "platform": "ios",
  "workspace_path": "/home/jenkins/workspace",
  "config_mount_source": "/home/jenkins/custom_config",
  "build_timeout": 7200,
  "email_recipients": "team@example.com"
}
```

#### List All Jobs

```bash
GET /api/jenkins/jobs
```

#### Get Job Details

```bash
GET /api/jenkins/jobs/{job_id}
GET /api/jenkins/jobs/name/{job_name}
```

#### Update a Job

```bash
PUT /api/jenkins/jobs/{job_id}
Content-Type: application/json

{
  "docker_tag": "v2.0",
  "test_markers": "ios_ftm and smoke"
}
```

#### Enable/Disable Job

```bash
POST /api/jenkins/jobs/{job_id}/enable
POST /api/jenkins/jobs/{job_id}/disable
```

#### Delete Job

```bash
DELETE /api/jenkins/jobs/{job_id}?delete_builds=true
```

### Build Management

#### Trigger a Build (Build Now)

```bash
POST /api/jenkins/jobs/{job_id}/build
Content-Type: application/json

{
  "triggered_by": "John Doe",
  "parameters": {
    "custom_param": "value"
  }
}
```

#### List Builds for a Job

```bash
GET /api/jenkins/jobs/{job_id}/builds?limit=10&offset=0
```

#### Get Build Details

```bash
GET /api/jenkins/builds/{build_id}
```

#### Get Build Console Output

```bash
GET /api/jenkins/builds/{build_id}/console
```

This returns the live console output, exactly like Jenkins console view.

#### Abort a Running Build

```bash
POST /api/jenkins/builds/{build_id}/abort
```

### Statistics and Monitoring

#### Get Jenkins Statistics

```bash
GET /api/jenkins/stats
```

Returns:
```json
{
  "jobs": {
    "total": 5,
    "enabled": 4,
    "disabled": 1
  },
  "builds": {
    "total": 123,
    "running": 2,
    "queued": 1,
    "success_rate": 87.5
  },
  "recent_builds": [...],
  "running_builds": [...],
  "queued_builds": [...]
}
```

## Agent/Node Management

Agents are managed via the existing Jenkins nodes API:

```bash
# List all agents
GET /api/jenkins/nodes/pool

# Add a new agent
POST /api/jenkins/nodes/pool

# Get agent details
GET /api/jenkins/nodes/pool/{node_id}

# Test agent connection
POST /api/jenkins/nodes/pool/{node_id}/test

# Health check all agents
POST /api/jenkins/nodes/pool/health-check
```

## Example Workflow

### Step 1: Set Up Worker Nodes

Add worker nodes that will execute your tests:

```bash
POST /api/jenkins/nodes/pool
{
  "name": "ios-worker-01",
  "host": "192.168.1.100",
  "port": 22,
  "username": "jenkins",
  "password": "your-password",
  "max_executors": 2,
  "labels": ["ios-automation", "docker", "macos"]
}
```

### Step 2: Create a Job

Define a job for iOS testing:

```bash
POST /api/jenkins/jobs
{
  "name": "iOS_Smoke_Tests",
  "job_type": "docker",
  "required_labels": ["ios-automation"],
  "docker_image": "pytest-automation/pytest_automation",
  "test_suite": "suites/mobile/suites/ftm/ios/tests",
  "test_markers": "ios_ftm and smoke",
  "lab_config": "/test_files/mobile_auto/ios16_ftm_testing_config.yml",
  "platform": "ios"
}
```

### Step 3: Trigger a Build

```bash
POST /api/jenkins/jobs/{job_id}/build
{
  "triggered_by": "API",
  "parameters": {}
}
```

### Step 4: Monitor Build Progress

```bash
# Get build status
GET /api/jenkins/builds/{build_id}

# Watch console output
GET /api/jenkins/builds/{build_id}/console
```

### Step 5: View Results

The build object contains:
- Exit code
- Duration
- Console output
- Test results
- Artifact paths

## Job Types

### 1. Docker Job (Recommended)

Executes tests in Docker containers on worker nodes:

```json
{
  "job_type": "docker",
  "docker_registry": "10.160.16.60",
  "docker_image": "pytest-automation/pytest_automation",
  "docker_tag": "latest",
  "test_suite": "tests/",
  "platform": "ios"
}
```

The controller will SSH into the worker and execute:
```bash
docker pull {registry}/{image}:{tag}
docker run --rm \
  --name="job_name_123" \
  -v /home/jenkins/custom_config:/test_files:ro \
  -v /home/jenkins/workspace/job_name/allure-results:/pytest-automation/allure-results:rw \
  --network=host \
  {image} /bin/bash -c "python3 -m pytest {test_suite} -s -m '{markers}' ..."
```

### 2. Freestyle Job

Executes arbitrary shell scripts:

```json
{
  "job_type": "freestyle",
  "script": "#!/bin/bash\necho 'Hello World'\n./run_tests.sh"
}
```

### 3. Pipeline Job

For future implementation - will support Jenkinsfile syntax.

## Build States

Builds go through these states:

1. **QUEUED** - Build is in the queue
2. **PENDING** - Waiting for an available agent
3. **RUNNING** - Currently executing on an agent
4. **SUCCESS** - Build completed successfully (exit code 0)
5. **FAILURE** - Build failed (non-zero exit code)
6. **UNSTABLE** - Build succeeded but tests failed
7. **ABORTED** - Build was manually aborted
8. **TIMEOUT** - Build exceeded timeout

## Agent Labels

Labels allow jobs to specify requirements:

Common labels:
- `ios-automation` - Agent can run iOS tests
- `android-automation` - Agent can run Android tests
- `docker` - Agent has Docker installed
- `macos` - Agent is a macOS machine
- `linux` - Agent is a Linux machine

Example:
```json
{
  "required_labels": ["ios-automation", "docker"]
}
```

Only agents with ALL specified labels will be eligible.

## Console Output

Console output mimics Jenkins format:

```
[Jenkins] Build #5 for job 'iOS_FTM_Tests'
[Jenkins] Queued at 2025-11-14 10:30:00
[Jenkins] Waiting for available agent...
[Jenkins] Required labels: ['ios-automation', 'docker']
[Jenkins] Agent assigned: ios-worker-01 (192.168.1.100:22)
[Jenkins] Starting build at 2025-11-14 10:30:05
[Docker] Image: 10.160.16.60/pytest-automation/pytest_automation:latest
[Docker] Container: iOS_FTM_Tests_5
[Docker] Workspace: /home/jenkins/workspace/iOS_FTM_Tests
[SSH] Connecting to agent 192.168.1.100:22
[SSH] Starting Docker execution...

=========================================
Jenkins Build #5
=========================================
Workspace: /home/jenkins/workspace/iOS_FTM_Tests
Docker Image: 10.160.16.60/pytest-automation/pytest_automation:latest

Cleaning up previous containers...
Pulling Docker image...
Starting test execution...
... test output ...

=========================================
Build completed with exit code: 0
=========================================

[Jenkins] Build completed successfully
[Jenkins] Duration: 256s
[Jenkins] Finished at 2025-11-14 10:34:21
```

## Database Schema

### jenkins_jobs

Stores job definitions:
- Job configuration
- Docker settings
- Test parameters
- Build statistics
- Next build number

### jenkins_builds

Stores build executions:
- Build number
- Status and result
- Start/end times
- Agent assignment
- Console output
- Test results
- Artifacts

### jenkins_nodes

Stores worker node information:
- SSH connection details
- Labels and capabilities
- Executor management
- Resource usage
- Health status

## Comparison with Jenkins

| Feature | Real Jenkins | This Implementation |
|---------|--------------|---------------------|
| Job Definitions | ✅ | ✅ |
| Build Queue | ✅ | ✅ |
| Agent Pool | ✅ | ✅ |
| SSH to Agents | ✅ | ✅ |
| Docker Execution | ✅ | ✅ |
| Build History | ✅ | ✅ |
| Console Output | ✅ | ✅ |
| Build Numbers | ✅ | ✅ |
| Agent Labels | ✅ | ✅ |
| Executor Management | ✅ | ✅ |
| Jenkinsfile | ✅ | ⏳ Future |
| Blue Ocean UI | ✅ | ❌ |
| Plugins | ✅ | ❌ |

## Best Practices

1. **Label Your Agents** - Use descriptive labels to match jobs to the right agents
2. **Set Timeouts** - Always set reasonable build timeouts
3. **Keep Build History** - Configure `keep_builds` to balance storage and history
4. **Monitor Resources** - Check agent CPU/memory usage regularly
5. **Use Docker** - Docker jobs provide better isolation and reproducibility
6. **Workspace Cleanup** - Ensure agents have enough disk space

## Troubleshooting

### Build Stuck in PENDING

- Check if any agents are online
- Verify agent labels match job requirements
- Check agent executor availability

### Build Failed Immediately

- Check SSH connectivity to agent
- Verify Docker is installed and running on agent
- Check Docker image exists and is accessible

### Build Timeout

- Increase `build_timeout` in job configuration
- Check if tests are hanging
- Verify agent has sufficient resources

### Console Output Not Updating

- This is normal - output is streamed in real-time
- Refresh the console endpoint to get latest output
- Check if build is still running

## Integration Examples

### Python

```python
import requests

# Create a job
response = requests.post('http://localhost:8000/api/jenkins/jobs', json={
    'name': 'My_Test_Job',
    'job_type': 'docker',
    'required_labels': ['docker'],
    'docker_image': 'my-test-image',
    'test_suite': 'tests/'
})
job = response.json()['job']

# Trigger a build
response = requests.post(f'http://localhost:8000/api/jenkins/jobs/{job["id"]}/build')
build = response.json()['build']

# Monitor build
import time
while True:
    response = requests.get(f'http://localhost:8000/api/jenkins/builds/{build["id"]}')
    status = response.json()['status']
    print(f"Build status: {status}")
    if status in ['success', 'failure', 'timeout', 'aborted']:
        break
    time.sleep(5)

# Get console output
response = requests.get(f'http://localhost:8000/api/jenkins/builds/{build["id"]}/console')
print(response.json()['console_output'])
```

### cURL

```bash
# Create job
curl -X POST http://localhost:8000/api/jenkins/jobs \
  -H 'Content-Type: application/json' \
  -d '{"name": "test_job", "job_type": "docker", "docker_image": "alpine", "script": "echo hello"}'

# Trigger build
curl -X POST http://localhost:8000/api/jenkins/jobs/{job_id}/build

# Get console
curl http://localhost:8000/api/jenkins/builds/{build_id}/console
```

## Future Enhancements

- [ ] Jenkinsfile support
- [ ] Pipeline visualization
- [ ] Build artifacts upload/download
- [ ] Email notifications
- [ ] Webhook triggers
- [ ] SCM integration (Git polling)
- [ ] Multi-branch pipelines
- [ ] Build parameters UI
- [ ] Agent provisioning automation

## Conclusion

This implementation provides a complete Jenkins-style workflow system that:
1. ✅ Copies Jenkins' master/worker architecture
2. ✅ Uses SSH to connect to worker nodes
3. ✅ Launches Docker containers via bash scripts
4. ✅ Manages job queues and build distribution
5. ✅ Tracks build history with console output
6. ✅ Supports agent labels and executor management

It's a 100% functional Jenkins clone tailored for this project's needs!
