# Lab Configuration & Jenkins Docker Execution

This directory contains lab configurations and Jenkins Docker execution scripts for the Mobile Test Pilot (MTP) platform.

## 📁 Directory Structure

```
lab_config/
├── README.md                           # This file
├── jenkins_scripts/                    # Jenkins execution scripts
│   ├── ios_ftm_docker_test.sh         # iOS FTM Docker test script
│   ├── android_ftm_docker_test.sh     # Android FTM Docker test script
│   ├── generic_docker_test_template.sh # Generic template for custom tests
│   ├── Jenkinsfile.ios_ftm            # Jenkins pipeline for iOS
│   └── Jenkinsfile.android_ftm        # Jenkins pipeline for Android
├── samples/                            # Sample lab configurations
│   ├── ios16_ftm_testing_config.yml   # iOS 16 FTM lab config
│   └── android13_ftm_testing_config.yml # Android 13 FTM lab config
└── lab_definitions/                    # Custom lab definitions (create your own)
```

## 🚀 Quick Start

### 1. Copy Sample Configuration

```bash
# For iOS testing
cp lab_config/samples/ios16_ftm_testing_config.yml /test_files/mobile_auto/

# For Android testing
cp lab_config/samples/android13_ftm_testing_config.yml /test_files/mobile_auto/
```

### 2. Update Configuration

Edit the copied configuration file and update:
- Device UDIDs
- VM IP addresses and credentials
- Network settings
- Test parameters

### 3. Run Tests

**Using Jenkins:**
```bash
# iOS tests
bash lab_config/jenkins_scripts/ios_ftm_docker_test.sh

# Android tests
bash lab_config/jenkins_scripts/android_ftm_docker_test.sh
```

**Using Mobile Test Pilot API:**
```bash
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_method": "docker",
    "platform": "ios",
    "test_suite": "suites/mobile/suites/ftm/ios/tests",
    "test_markers": "ios_ftm and functional",
    "lab_config": "/test_files/mobile_auto/ios16_ftm_testing_config.yml",
    "docker_tag": "latest",
    "labels": ["ios-automation"]
  }'
```

## 📋 Lab Configuration Files

### Configuration Format (YAML)

Lab configuration files define the test environment including devices, VMs, network settings, and test parameters.

**Example Structure:**

```yaml
lab_info:
  name: "iOS 16 FTM Testing Lab"
  location: "Jenkins Slave Node"
  owner: "Mobile Automation Team"

devices:
  - device_id: "ios_device_01"
    device_name: "iPhone 13 Pro"
    platform: "iOS"
    platform_version: "16.7"
    udid: "00008110-001234567890001E"
    appium_port: 4724

virtual_machines:
  - vm_id: "fac_vm_01"
    vm_name: "FortiAuthenticator-6.5"
    ip_address: "10.160.16.100"
    credentials:
      username: "admin"
      password: "fortinet123"

test_settings:
  timeouts:
    test_case: 300
    test_suite: 3600
  reporting:
    allure_enabled: true
    log_level: "INFO"
```

### Configuration Sections

| Section | Description |
|---------|-------------|
| `lab_info` | Lab metadata and description |
| `devices` | Physical/virtual mobile devices |
| `virtual_machines` | FortiGate/FortiAuthenticator VMs |
| `network` | Network topology and settings |
| `test_settings` | Timeouts, retries, reporting |
| `docker` | Docker configuration |
| `jenkins` | Jenkins job settings |
| `markers` | Pytest markers for test selection |
| `features` | Feature flags for test control |

## 🐳 Jenkins Docker Execution

### Overview

The Jenkins Docker execution pattern runs tests in isolated Docker containers on Jenkins slave nodes. This provides:

- **Isolation**: Each test run in a clean environment
- **Reproducibility**: Consistent execution environment
- **Scalability**: Parallel execution on multiple nodes
- **Portability**: Easy to move between environments

### Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│               Jenkins Master                            │
│          (Triggers build on slave)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               Jenkins Slave Node                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Pull Docker image                             │  │
│  │  2. Stop existing containers                      │  │
│  │  3. Create workspace directories                  │  │
│  │  4. Mount volumes:                                │  │
│  │     - /test_files (lab configs)                   │  │
│  │     - /allure-results (test results)              │  │
│  │  5. Run pytest in container                       │  │
│  │  6. Collect results                               │  │
│  │  7. Cleanup containers                            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Docker Run Parameters

**iOS Tests:**
```bash
docker run --rm \
    --name="JOB_NAME" \
    -v /home/jenkins/custom_config:/test_files:ro \
    -v ${WORKSPACE}/allure-results:/pytest-automation/allure-results:rw \
    --env="DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \
    --shm-size=2g \
    --network=host \
    10.160.16.60/pytest-automation/pytest_automation:latest \
    /bin/bash -c "pytest ... "
```

**Android Tests (additional USB access):**
```bash
docker run --rm \
    ... (same as iOS) ...
    --privileged \
    -v /dev/bus/usb:/dev/bus/usb:rw \
    ...
```

### Volume Mounts

| Source | Target | Mode | Purpose |
|--------|--------|------|---------|
| `/home/jenkins/custom_config` | `/test_files` | `ro` | Lab configs, test data |
| `${WORKSPACE}/allure-results` | `/pytest-automation/allure-results` | `rw` | Test results output |
| `/tmp/.X11-unix/` | `/tmp/.X11-unix` | `rw` | X11 display for GUI |
| `/dev/bus/usb` | `/dev/bus/usb` | `rw` | USB devices (Android) |

## 📝 Jenkins Script Templates

### 1. iOS FTM Docker Test Script

**File:** `jenkins_scripts/ios_ftm_docker_test.sh`

**Features:**
- Automated cleanup of previous results
- Docker image pull with error handling
- Test execution with configurable markers
- Result collection and reporting
- Exit code propagation

**Usage:**
```bash
export docker_tag="v2.0"
export JOB_BASE_NAME="iOS_FTM_Automation"
export WORKSPACE="/home/jenkins/workspace/iOS_FTM"
bash jenkins_scripts/ios_ftm_docker_test.sh
```

### 2. Android FTM Docker Test Script

**File:** `jenkins_scripts/android_ftm_docker_test.sh`

**Features:**
- All iOS features plus:
- USB device access for physical Android devices
- Privileged mode for ADB
- Android-specific test markers

**Usage:**
```bash
export docker_tag="v2.0"
export JOB_BASE_NAME="Android_FTM_Automation"
bash jenkins_scripts/android_ftm_docker_test.sh
```

### 3. Generic Template

**File:** `jenkins_scripts/generic_docker_test_template.sh`

**Features:**
- Fully customizable template
- Platform-agnostic (iOS/Android/Both)
- Detailed comments for customization
- Advanced error handling
- Result analysis and reporting

**Customization Points:**
```bash
# Test Configuration
TEST_SUITE="your/test/suite"
TEST_MARKERS="your and markers"
LAB_CONFIG_PATH="/test_files/your_config.yml"
TEST_PLATFORM="ios"  # or "android"

# Docker Configuration
DOCKER_REGISTRY="your.registry.com"
DOCKER_IMAGE_NAME="your/image"
DOCKER_TAG="your-tag"

# Volume Mounts
CONFIG_SOURCE="/your/config/path"
```

## 🔧 Jenkins Pipeline Files

### Jenkinsfile Features

Both iOS and Android Jenkinsfiles include:

- **Parameters**: Docker tag, test suite, markers, lab config
- **Stages**: Preparation → Cleanup → Pull Image → Execute → Collect Results
- **Post Actions**: Archive results, send notifications, cleanup
- **Email Notifications**: Success/failure notifications with HTML formatting
- **Allure Integration**: Automatic report generation

### Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `docker_tag` | String | `latest` | Docker image tag |
| `test_suite` | String | Platform-specific | Test suite path |
| `test_markers` | String | Platform-specific | Pytest markers |
| `lab_config` | String | Platform-specific | Lab config file |
| `email_recipients` | String | Team email | Email for notifications |
| `capture_video` | Boolean | `false` | Capture test videos |
| `clean_workspace` | Boolean | `true` | Clean workspace before build |

### Running Jenkins Pipeline

**Option 1: Via Jenkins UI**
1. Navigate to Jenkins job
2. Click "Build with Parameters"
3. Fill in parameters
4. Click "Build"

**Option 2: Via Jenkins CLI**
```bash
java -jar jenkins-cli.jar -s http://jenkins-server:8080/ \
  build "iOS_FTM_Automation" \
  -p docker_tag=v2.0 \
  -p test_markers="ios_ftm and smoke"
```

**Option 3: Via API**
```bash
curl -X POST "http://jenkins-server:8080/job/iOS_FTM_Automation/buildWithParameters" \
  --user "username:token" \
  --data "docker_tag=v2.0&test_markers=ios_ftm and smoke"
```

## 🔌 Mobile Test Pilot API Integration

### Execute Docker-based Test

```bash
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
```

### Check Test Status

```bash
# Get task status
curl http://localhost:8000/api/tests/status/{task_id}

# Response
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "result": {
    "status": "passed",
    "return_code": 0,
    "test_suite": "suites/mobile/suites/ftm/ios/tests",
    "execution_method": "docker"
  },
  "duration": 1234.5
}
```

## 📊 Test Results

### Allure Reports

Test results are generated in Allure format and stored in:
- Local: `${WORKSPACE}/allure-results/`
- Docker: `/pytest-automation/allure-results/`

**View Allure Report:**
```bash
# Generate and serve report
allure serve ${WORKSPACE}/allure-results
```

### Result Files

| File Type | Description |
|-----------|-------------|
| `*-result.json` | Individual test results |
| `*-container.json` | Test suite containers |
| `*-attachment.*` | Screenshots, logs, videos |
| `environment.properties` | Environment information |

## 🛠️ Customization Guide

### Creating Custom Lab Configuration

1. **Copy Sample Configuration:**
   ```bash
   cp lab_config/samples/ios16_ftm_testing_config.yml \
      lab_config/lab_definitions/my_custom_lab.yml
   ```

2. **Update Device Configuration:**
   ```yaml
   devices:
     - device_id: "my_device_01"
       device_name: "My iPhone"
       udid: "YOUR_DEVICE_UDID"  # Get from: xcrun xctrace list devices
       platform_version: "17.0"
       appium_port: 4724
   ```

3. **Update VM Configuration:**
   ```yaml
   virtual_machines:
     - vm_id: "my_fac_01"
       ip_address: "YOUR_VM_IP"
       credentials:
         username: "admin"
         password: "YOUR_PASSWORD"
   ```

4. **Customize Test Settings:**
   ```yaml
   test_settings:
     timeouts:
       test_case: 600  # Increase for complex tests
     markers:
       platform: "ios_ftm"
       tags: ["smoke", "custom_tag"]
   ```

### Creating Custom Jenkins Script

1. **Copy Generic Template:**
   ```bash
   cp lab_config/jenkins_scripts/generic_docker_test_template.sh \
      lab_config/jenkins_scripts/my_custom_test.sh
   ```

2. **Update Configuration Section:**
   ```bash
   # Test Configuration - CUSTOMIZE THESE
   TEST_SUITE="your/custom/suite"
   TEST_MARKERS="your_custom_markers"
   LAB_CONFIG_PATH="/test_files/your_lab_config.yml"
   ```

3. **Make Executable:**
   ```bash
   chmod +x lab_config/jenkins_scripts/my_custom_test.sh
   ```

## 🐛 Troubleshooting

### Common Issues

**1. Docker Image Pull Failed**
```bash
# Error: Failed to pull Docker image
# Solution: Check network connectivity and registry access
docker pull 10.160.16.60/pytest-automation/pytest_automation:latest

# If using private registry, login first:
docker login 10.160.16.60
```

**2. No Devices Found (iOS)**
```bash
# Check connected devices
xcrun xctrace list devices

# Restart usbmuxd
sudo killall usbmuxd
```

**3. No Devices Found (Android)**
```bash
# Check ADB devices
adb devices

# Restart ADB server
adb kill-server
adb start-server

# Check USB permissions
ls -l /dev/bus/usb/*/*
```

**4. Permission Denied on Volume Mounts**
```bash
# Check directory permissions
ls -l /home/jenkins/custom_config

# Fix permissions
sudo chmod -R 755 /home/jenkins/custom_config
sudo chown -R jenkins:jenkins /home/jenkins/custom_config
```

**5. Container Exits Immediately**
```bash
# Check container logs
docker logs CONTAINER_NAME

# Run container interactively for debugging
docker run -it --entrypoint /bin/bash \
  10.160.16.60/pytest-automation/pytest_automation:latest
```

### Debug Mode

**Enable verbose output in Jenkins scripts:**
```bash
# Add to beginning of script
set -x  # Enable debug mode
set -e  # Exit on error
```

**Run pytest with verbose output:**
```bash
pytest -vv --tb=long --capture=no
```

## 📚 Additional Resources

### Documentation
- [Mobile Test Pilot README](../../../README.md)
- [Pytest Documentation](https://docs.pytest.org/)
- [Allure Documentation](https://docs.qameta.io/allure/)
- [Docker Documentation](https://docs.docker.com/)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)

### Support
- GitHub Issues: [Mobile Test Pilot Issues](https://github.com/your-org/mtp/issues)
- Email: mobile-automation-team@fortinet.com
- Slack: #mobile-automation

## 📄 License

Copyright © 2025 Fortinet. All rights reserved.

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
**Maintainer:** Mobile Automation Team
