# Quick Start Guide - Jenkins Docker Execution

## 🚀 5-Minute Setup

### Step 1: Choose Your Platform

**For iOS Testing:**
```bash
export PLATFORM="ios"
export LAB_CONFIG="ios16_ftm_testing_config.yml"
export SCRIPT="ios_ftm_docker_test.sh"
```

**For Android Testing:**
```bash
export PLATFORM="android"
export LAB_CONFIG="android13_ftm_testing_config.yml"
export SCRIPT="android_ftm_docker_test.sh"
```

### Step 2: Copy Lab Configuration

```bash
# Navigate to lab_config directory
cd /home/user/mtp/backend/app/uploads/lab_config

# Copy sample configuration
cp samples/${LAB_CONFIG} /test_files/mobile_auto/${LAB_CONFIG}
```

### Step 3: Update Configuration

Edit the lab configuration file:
```bash
vi /test_files/mobile_auto/${LAB_CONFIG}
```

**Minimum Required Updates:**
- Device UDID (line ~24)
- VM IP address (line ~42)
- VM credentials (line ~47-49)

### Step 4: Run Tests

**Option A: Direct Execution**
```bash
cd jenkins_scripts
export docker_tag="latest"
export JOB_BASE_NAME="MTP_Test"
export WORKSPACE="/tmp/mtp-workspace"
bash ${SCRIPT}
```

**Option B: Via MTP API**
```bash
curl -X POST http://localhost:8000/api/tests/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"execution_method\": \"docker\",
    \"platform\": \"${PLATFORM}\",
    \"test_suite\": \"suites/mobile/suites/ftm/${PLATFORM}/tests\",
    \"test_markers\": \"${PLATFORM}_ftm and functional\",
    \"lab_config\": \"/test_files/mobile_auto/${LAB_CONFIG}\",
    \"docker_tag\": \"latest\"
  }"
```

### Step 5: View Results

```bash
# Check results directory
ls -lh ${WORKSPACE}/allure-results/

# Generate Allure report
allure serve ${WORKSPACE}/allure-results
```

## 📋 Checklist

Before running tests, ensure:

- [ ] Docker is installed and running
- [ ] Docker image is accessible: `docker pull 10.160.16.60/pytest-automation/pytest_automation:latest`
- [ ] Lab configuration file exists in `/test_files/mobile_auto/`
- [ ] Device UDIDs are updated in lab config
- [ ] VM IP addresses and credentials are correct
- [ ] Jenkins workspace directory exists and is writable
- [ ] For iOS: Devices are connected and trusted
- [ ] For Android: USB debugging is enabled and devices are authorized

## 🔍 Verification Commands

**Check Docker:**
```bash
docker --version
docker ps
docker images | grep pytest-automation
```

**Check iOS Devices:**
```bash
xcrun xctrace list devices
idevice_id -l
```

**Check Android Devices:**
```bash
adb devices -l
adb shell getprop ro.build.version.release
```

**Check Lab Config:**
```bash
cat /test_files/mobile_auto/${LAB_CONFIG} | grep -E '(device_id|ip_address|udid)'
```

## ⚡ Common Commands

**Pull Latest Docker Image:**
```bash
docker pull 10.160.16.60/pytest-automation/pytest_automation:latest
```

**Clean Up Containers:**
```bash
docker rm -f $(docker ps -aq)
```

**View Container Logs:**
```bash
docker logs -f CONTAINER_NAME
```

**Test SSH Connection (if using Jenkins nodes):**
```bash
ssh -p 22 jenkins@your-node-ip "docker ps"
```

## 🎯 Example: Full iOS Test Run

```bash
# 1. Set environment
export docker_tag="v2.0"
export JOB_BASE_NAME="iOS_FTM_Smoke_Test"
export WORKSPACE="/tmp/ios-test-$(date +%Y%m%d-%H%M%S)"
mkdir -p ${WORKSPACE}

# 2. Copy and update config
cp samples/ios16_ftm_testing_config.yml /test_files/mobile_auto/
# Edit config file to update device UDID and VM details

# 3. Run tests
cd jenkins_scripts
bash ios_ftm_docker_test.sh

# 4. View results
echo "Exit Code: $?"
ls -lh ${WORKSPACE}/allure-results/
allure serve ${WORKSPACE}/allure-results
```

## 🎯 Example: Full Android Test Run

```bash
# 1. Check connected devices
adb devices

# 2. Set environment
export docker_tag="v2.0"
export JOB_BASE_NAME="Android_FTM_Smoke_Test"
export WORKSPACE="/tmp/android-test-$(date +%Y%m%d-%H%M%S)"
mkdir -p ${WORKSPACE}

# 3. Copy and update config
cp samples/android13_ftm_testing_config.yml /test_files/mobile_auto/
# Edit config file

# 4. Run tests
cd jenkins_scripts
bash android_ftm_docker_test.sh

# 5. View results
allure serve ${WORKSPACE}/allure-results
```

## 🔧 Customization Quick Reference

### Change Docker Image
```bash
# Edit script or set environment variable
export DOCKER_IMAGE="your-registry/your-image:your-tag"
```

### Change Test Markers
```bash
# Edit script
TEST_MARKERS="ios_ftm and smoke"
```

### Change Timeout
```bash
# Edit lab config YAML
test_settings:
  timeouts:
    test_suite: 7200  # 2 hours
```

### Run Specific Tests
```bash
# Modify pytest command in script
pytest tests/test_login.py -k "test_successful_login"
```

## 📞 Getting Help

**View full documentation:**
```bash
cat lab_config/README.md
```

**Check MTP status:**
```bash
curl http://localhost:8000/health
```

**View Jenkins node pool:**
```bash
curl http://localhost:8000/api/jenkins/nodes
```

## 🎓 Next Steps

1. ✅ Complete Quick Start
2. 📖 Read full [README](README.md)
3. 🔧 Customize lab configuration for your environment
4. 🚀 Set up Jenkins pipelines
5. 📊 Configure Allure reporting
6. 🤖 Automate with scheduled builds

---

**Need Help?** Check the [Troubleshooting](README.md#-troubleshooting) section in the main README.
