# Jenkins API Integration

This document describes how to use the Jenkins API integration in the Mobile Test Pilot platform.

## Overview

The Jenkins integration allows you to trigger and monitor Jenkins jobs directly from the Mobile Test Pilot backend API. This is implemented using the `jenkinsapi` Python library.

## Configuration

### 1. Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Jenkins Configuration
JENKINS_URL=http://10.160.13.30:8080
JENKINS_USERNAME=your-jenkins-username
JENKINS_API_TOKEN=your-jenkins-api-token
```

### 2. Get Jenkins API Token

To get your Jenkins API token:

1. Log in to your Jenkins instance at `http://10.160.13.30:8080`
2. Click on your username in the top-right corner
3. Click on "Configure" in the left menu
4. Under "API Token" section, click "Add new Token"
5. Give it a name (e.g., "MTP Integration") and click "Generate"
6. Copy the generated token and add it to your `.env` file

## API Endpoints

All Jenkins endpoints are prefixed with `/api/jenkins`.

### 1. List All Jobs

Get all available Jenkins jobs:

**Request:**
```http
GET /api/jenkins/jobs
```

**Response:**
```json
[
  {
    "name": "build-android-app",
    "url": "http://10.160.13.30:8080/job/build-android-app/",
    "enabled": true,
    "running": false
  },
  {
    "name": "run-integration-tests",
    "url": "http://10.160.13.30:8080/job/run-integration-tests/",
    "enabled": true,
    "running": true
  }
]
```

### 2. Get Job Information

Get detailed information about a specific job:

**Request:**
```http
GET /api/jenkins/jobs/{job_name}
```

**Example:**
```http
GET /api/jenkins/jobs/build-android-app
```

**Response:**
```json
{
  "name": "build-android-app",
  "url": "http://10.160.13.30:8080/job/build-android-app/",
  "description": "Build Android application",
  "enabled": true,
  "running": false,
  "last_build": {
    "number": 42,
    "status": "SUCCESS",
    "timestamp": "2025-11-26T10:30:00",
    "duration": 120.5,
    "url": "http://10.160.13.30:8080/job/build-android-app/42/"
  },
  "next_build_number": 43
}
```

### 3. Trigger a Job

Trigger a Jenkins job with optional parameters:

**Request:**
```http
POST /api/jenkins/jobs/trigger
Content-Type: application/json

{
  "job_name": "build-android-app",
  "parameters": {
    "BRANCH": "main",
    "BUILD_TYPE": "release"
  }
}
```

**Response:**
```json
{
  "job_name": "build-android-app",
  "status": "triggered",
  "queue_id": 123,
  "message": "Job 'build-android-app' has been triggered successfully",
  "next_build_number": 43
}
```

### 4. Get Build Status

Get the status of a specific build:

**Request:**
```http
GET /api/jenkins/jobs/{job_name}/builds/{build_number}
```

**Example:**
```http
GET /api/jenkins/jobs/build-android-app/builds/42
```

**Response:**
```json
{
  "job_name": "build-android-app",
  "build_number": 42,
  "status": "SUCCESS",
  "result": "SUCCESS",
  "running": false,
  "timestamp": "2025-11-26T10:30:00",
  "duration": 120.5,
  "url": "http://10.160.13.30:8080/job/build-android-app/42/",
  "console_url": "http://10.160.13.30:8080/job/build-android-app/42/console"
}
```

### 5. Get Build Console Output

Get the console output of a specific build:

**Request:**
```http
GET /api/jenkins/jobs/{job_name}/builds/{build_number}/console
```

**Example:**
```http
GET /api/jenkins/jobs/build-android-app/builds/42/console
```

**Response:**
```json
{
  "job_name": "build-android-app",
  "build_number": 42,
  "console_output": "Started by user admin\nBuilding in workspace...\n..."
}
```

### 6. Stop a Build

Stop a running build:

**Request:**
```http
POST /api/jenkins/jobs/{job_name}/builds/{build_number}/stop
```

**Example:**
```http
POST /api/jenkins/jobs/build-android-app/builds/43/stop
```

**Response:**
```json
{
  "job_name": "build-android-app",
  "build_number": 43,
  "status": "stopped",
  "message": "Build #43 has been stopped"
}
```

### 7. Get Job Parameters

Get the parameters defined for a job:

**Request:**
```http
GET /api/jenkins/jobs/{job_name}/parameters
```

**Example:**
```http
GET /api/jenkins/jobs/build-android-app/parameters
```

**Response:**
```json
[
  {
    "message": "This job accepts parameters. Please check Jenkins UI for parameter details.",
    "has_parameters": true
  }
]
```

## Usage Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000/api/jenkins"

# List all jobs
response = requests.get(f"{BASE_URL}/jobs")
jobs = response.json()
print(f"Found {len(jobs)} jobs")

# Trigger a job with parameters
trigger_data = {
    "job_name": "build-android-app",
    "parameters": {
        "BRANCH": "develop",
        "BUILD_TYPE": "debug"
    }
}
response = requests.post(f"{BASE_URL}/jobs/trigger", json=trigger_data)
result = response.json()
print(f"Triggered job: {result['message']}")

# Check build status
job_name = "build-android-app"
build_number = 42
response = requests.get(f"{BASE_URL}/jobs/{job_name}/builds/{build_number}")
status = response.json()
print(f"Build status: {status['status']}")
```

### cURL Examples

```bash
# List all jobs
curl -X GET http://localhost:8000/api/jenkins/jobs

# Get job information
curl -X GET http://localhost:8000/api/jenkins/jobs/build-android-app

# Trigger a job
curl -X POST http://localhost:8000/api/jenkins/jobs/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "build-android-app",
    "parameters": {
      "BRANCH": "main",
      "BUILD_TYPE": "release"
    }
  }'

# Get build status
curl -X GET http://localhost:8000/api/jenkins/jobs/build-android-app/builds/42

# Get console output
curl -X GET http://localhost:8000/api/jenkins/jobs/build-android-app/builds/42/console

# Stop a build
curl -X POST http://localhost:8000/api/jenkins/jobs/build-android-app/builds/43/stop
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid request (e.g., missing credentials, disabled job)
- `404 Not Found` - Job or build not found
- `500 Internal Server Error` - Server error (e.g., Jenkins connection failed)

Example error response:
```json
{
  "detail": "Job 'invalid-job' not found or error occurred: Job not found"
}
```

## Security Considerations

1. **Store credentials securely**: Never commit your Jenkins API token to version control
2. **Use environment variables**: Always use `.env` file for credentials
3. **Restrict API access**: Consider adding authentication to the Jenkins endpoints if needed
4. **Network access**: Ensure your backend can reach the Jenkins server at `10.160.13.30:8080`

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Verify the Jenkins URL is correct and accessible from the backend
2. Check that your username and API token are correct
3. Ensure there are no firewall rules blocking the connection

### Authentication Issues

If you get authentication errors:
1. Verify your Jenkins username is correct
2. Regenerate your API token if it has expired
3. Ensure you're using an API token, not a password

### Job Not Found

If you get "job not found" errors:
1. Verify the job name is exactly as shown in Jenkins (case-sensitive)
2. Check that you have permission to access the job in Jenkins
3. Use the `/api/jenkins/jobs` endpoint to see all available jobs

## Integration with Mobile Test Pilot

The Jenkins integration can be used to:

1. **Trigger builds** after uploading new APK files
2. **Run automated tests** on deployed devices
3. **Monitor build status** and display in the frontend
4. **Retrieve test results** from Jenkins jobs

## API Documentation

Once the backend is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Look for the "Jenkins" tag to see all available Jenkins endpoints with detailed schemas.
