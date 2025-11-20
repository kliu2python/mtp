# Jenkins API Integration

## Overview

The Mobile Test Pilot (MTP) now integrates with a real Jenkins instance for core job execution and result management, while maintaining custom features for mobile test automation.

## Architecture

### Jenkins Integration (10.160.13.30:8080)

The following features use the **real Jenkins API**:

- **Job Execution**: Jobs are created and executed on the Jenkins server
- **Build Management**: Builds are triggered and monitored via Jenkins API
- **Build Results**: Console output, artifacts, and test results come from Jenkins
- **Queue Management**: Build queue is managed by Jenkins
- **Node Management**: Jenkins agents handle job execution

### Custom MTP Features (Retained)

The following features remain as custom implementations:

- **AI-Powered Log Analyzer**: Claude/OpenAI integration for intelligent log analysis
- **APK/IPA Manager**: Mobile app package management and metadata extraction
- **Device Management**: iOS/Android device pool management
- **VM Management**: FortiGate/FortiAuthenticator VM lifecycle
- **STF Integration**: Smartphone Test Farm integration
- **Test Scheduling**: Cron-based test automation
- **Custom Notifications**: Email and Teams webhook notifications
- **Real-time Updates**: WebSocket support for live monitoring

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Jenkins Integration
JENKINS_URL=http://10.160.13.30:8080
JENKINS_USERNAME=your-jenkins-username  # Optional for anonymous access
JENKINS_API_TOKEN=your-jenkins-api-token  # Optional for anonymous access
```

### Getting Jenkins API Token

1. Log into Jenkins web interface
2. Click on your username (top right)
3. Click "Configure"
4. Under "API Token", click "Add new Token"
5. Copy the generated token

## API Endpoints

### Jenkins Job Management

```
POST   /api/jenkins/jobs                    - Create a new job
GET    /api/jenkins/jobs                    - List all jobs
GET    /api/jenkins/jobs/{job_id}           - Get job details
PUT    /api/jenkins/jobs/{job_id}           - Update job
DELETE /api/jenkins/jobs/{job_id}           - Delete job
POST   /api/jenkins/jobs/{job_id}/enable    - Enable job
POST   /api/jenkins/jobs/{job_id}/disable   - Disable job
```

### Build Management

```
POST   /api/jenkins/jobs/{job_id}/build     - Trigger a build
GET    /api/jenkins/jobs/{job_id}/builds    - List builds
GET    /api/jenkins/builds/{build_id}       - Get build details
GET    /api/jenkins/builds/{build_id}/console - Get console output
POST   /api/jenkins/builds/{build_id}/abort - Abort running build
```

### Jenkins Sync & Status

```
POST   /api/jenkins/sync/jobs               - Sync all jobs from Jenkins
POST   /api/jenkins/sync/job/{job_name}     - Sync specific job
GET    /api/jenkins/connection/status       - Check Jenkins connection
GET    /api/jenkins/queue/stats             - Get queue statistics
GET    /api/jenkins/stats                   - Get Jenkins statistics
```

## Usage Examples

### 1. Check Jenkins Connection

```bash
curl http://localhost:8000/api/jenkins/connection/status
```

Response:
```json
{
  "connected": true,
  "jenkins_url": "http://10.160.13.30:8080",
  "message": "Connected to Jenkins"
}
```

### 2. Create a Job

```bash
curl -X POST http://localhost:8000/api/jenkins/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-test-job",
    "description": "Test job for mobile automation",
    "job_type": "DOCKER",
    "docker_image": "pytest-automation/pytest_automation",
    "docker_tag": "latest",
    "test_suite": "tests/mobile/",
    "test_markers": "smoke",
    "platform": "ios"
  }'
```

### 3. Trigger a Build

```bash
curl -X POST http://localhost:8000/api/jenkins/jobs/{job_id}/build \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "DEVICE_ID": "iPhone-13",
      "TEST_ENV": "staging"
    },
    "triggered_by": "API"
  }'
```

### 4. Get Build Console Output

```bash
curl http://localhost:8000/api/jenkins/builds/{build_id}/console
```

### 5. Sync Existing Jenkins Jobs

```bash
curl -X POST http://localhost:8000/api/jenkins/sync/jobs
```

## How It Works

### Job Creation Flow

1. User creates job via MTP API
2. Job metadata saved to local database
3. Job configuration XML generated
4. Job created in Jenkins via API
5. Both systems now track the job

### Build Execution Flow

1. User triggers build via MTP API
2. Build triggered in Jenkins via API
3. Local build record created with status `RUNNING`
4. Background monitor polls Jenkins for updates
5. When complete, local record updated with results
6. Console output fetched from Jenkins on demand

### Build Monitoring

- Background task polls Jenkins every 5 seconds
- Updates local build status automatically
- Captures final results, duration, and test data
- Stops monitoring when build completes

## Database Models

### Local Tracking

MTP maintains local database records for:

- **JenkinsJob**: Job metadata and configuration
- **JenkinsBuild**: Build execution history and results
- **JenkinsNode**: Jenkins agent nodes (if used)

This allows for:
- Fast local queries without hitting Jenkins API
- Historical data retention
- Custom analytics and reporting
- Offline access to build history

## Migration from Custom Implementation

### Automatic Migration

The system automatically detects if you're migrating from the custom Jenkins-inspired implementation. No manual migration is needed for the data structure as it uses the same database models.

### Syncing Existing Jenkins Jobs

If you have existing jobs in Jenkins:

```bash
curl -X POST http://localhost:8000/api/jenkins/sync/jobs
```

This will import all Jenkins jobs into the local database.

## Architecture Benefits

### Why Hybrid Approach?

1. **Reliability**: Use battle-tested Jenkins for core execution
2. **Scalability**: Leverage Jenkins distributed build capabilities
3. **Flexibility**: Maintain custom mobile testing features
4. **Performance**: Local database caching for fast queries
5. **Integration**: Easy integration with existing Jenkins infrastructure

### Component Responsibilities

**Jenkins (10.160.13.30:8080)**:
- Job definition and configuration
- Build execution and scheduling
- Build queue management
- Agent/node management
- Artifact storage

**MTP Backend**:
- Job metadata tracking
- Build history caching
- AI-powered analysis
- Mobile device management
- APK/IPA management
- Custom notifications
- WebSocket real-time updates

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Jenkins

**Solutions**:
1. Verify Jenkins URL is correct: `http://10.160.13.30:8080`
2. Check network connectivity: `curl http://10.160.13.30:8080/api/json`
3. Verify authentication credentials if required
4. Check firewall rules

### Job Creation Fails

**Problem**: Job created locally but not in Jenkins

**Solution**:
- Check Jenkins API response in logs
- Verify user has permission to create jobs
- Check job name doesn't already exist

### Build Status Not Updating

**Problem**: Build shows as RUNNING but completed

**Solution**:
- Background monitor may have stopped
- Restart the application
- Check Jenkins build status directly

### Missing Console Output

**Problem**: Console output is empty

**Solution**:
- Build may still be queued
- Jenkins may not have started the build yet
- Check build status first

## Development

### Adding New Jenkins Features

To add new Jenkins API features:

1. Add method to `jenkins_api_client.py`
2. Add business logic to `jenkins_service.py`
3. Add API endpoint to `jenkins_jobs.py`
4. Update this documentation

### Testing Locally

```bash
# Set Jenkins URL in environment
export JENKINS_URL=http://10.160.13.30:8080

# Start the backend
cd backend
python main.py
```

## Support

For issues or questions:
- Check Jenkins logs: `{JENKINS_URL}/log/all`
- Check MTP logs: Application console output
- Review API documentation: `http://localhost:8000/docs`

## References

- [Jenkins REST API Documentation](https://www.jenkins.io/doc/book/using/remote-access-api/)
- [MTP API Documentation](http://localhost:8000/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
