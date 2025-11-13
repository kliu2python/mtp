#!/bin/bash
# =============================================================================
# Generic Mobile Test Automation - Jenkins Docker Execution Template
# =============================================================================
# Description: Template for executing mobile automation tests in Docker
# Usage: Customize variables for your specific test suite
# Author: Mobile Test Pilot
# Date: 2025-11-13
# =============================================================================

# ============================================================================
# CUSTOMIZATION SECTION - Update these variables for your test suite
# ============================================================================

# Test Configuration - CUSTOMIZE THESE
TEST_SUITE="suites/mobile/suites/ftm/ios/tests"           # Path to test suite
TEST_MARKERS="ios_ftm and functional"                     # Pytest markers
LAB_CONFIG_PATH="/test_files/mobile_auto/lab_config.yml"  # Lab configuration file
TEST_PLATFORM="ios"                                       # Platform: ios, android, or both

# Docker Configuration - CUSTOMIZE THESE
DOCKER_REGISTRY="10.160.16.60"                            # Docker registry URL
DOCKER_IMAGE_NAME="pytest-automation/pytest_automation"   # Docker image name
DOCKER_TAG="${docker_tag:-latest}"                        # Docker image tag
CONTAINER_NAME_PREFIX="mobile_test"                       # Container name prefix

# Volume Mounts - CUSTOMIZE THESE
CONFIG_SOURCE="/home/jenkins/custom_config"               # Source for test configs
CONFIG_TARGET="/test_files"                               # Target mount point
RESULTS_TARGET="/pytest-automation/allure-results"        # Allure results directory

# Additional Pytest Arguments - CUSTOMIZE THESE
PYTEST_EXTRA_ARGS="--tb=short --verbose"                  # Extra pytest arguments
CAPTURE_VIDEO="false"                                     # Capture video: true/false
PARALLEL_TESTS="1"                                        # Number of parallel workers

# ============================================================================
# ENVIRONMENT VARIABLES (automatically set by Jenkins)
# ============================================================================
# JOB_BASE_NAME    - Jenkins job name
# BUILD_NUMBER     - Jenkins build number
# WORKSPACE        - Jenkins workspace directory
# NODE_NAME        - Jenkins node name
# BUILD_URL        - Jenkins build URL

# ============================================================================
# SCRIPT EXECUTION (DO NOT MODIFY BELOW THIS LINE)
# ============================================================================

# Set derived variables
CONTAINER_NAME="${JOB_BASE_NAME:-${CONTAINER_NAME_PREFIX}}_${BUILD_NUMBER:-0}"
WORKSPACE="${WORKSPACE:-$(pwd)}"
ALLURE_RESULTS_DIR="${WORKSPACE}/allure-results"
DOCKER_IMAGE="${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"

# Print configuration
echo "========================================================================="
echo "Mobile Test Automation - Docker Execution"
echo "========================================================================="
echo "Execution Details:"
echo "  Job Name:        ${JOB_BASE_NAME}"
echo "  Build Number:    ${BUILD_NUMBER}"
echo "  Node:            ${NODE_NAME}"
echo "  Build URL:       ${BUILD_URL}"
echo ""
echo "Test Configuration:"
echo "  Test Suite:      ${TEST_SUITE}"
echo "  Test Markers:    ${TEST_MARKERS}"
echo "  Platform:        ${TEST_PLATFORM}"
echo "  Lab Config:      ${LAB_CONFIG_PATH}"
echo ""
echo "Docker Configuration:"
echo "  Registry:        ${DOCKER_REGISTRY}"
echo "  Image:           ${DOCKER_IMAGE_NAME}"
echo "  Tag:             ${DOCKER_TAG}"
echo "  Container:       ${CONTAINER_NAME}"
echo ""
echo "Workspace:         ${WORKSPACE}"
echo "Results Directory: ${ALLURE_RESULTS_DIR}"
echo "========================================================================="

# ----------------------------- Pre-Execution Cleanup --------------------------
echo "[Step 1/6] Cleaning up previous test results..."
rm -rf ${ALLURE_RESULTS_DIR} || true
mkdir -p ${ALLURE_RESULTS_DIR}
echo "✓ Test results directory prepared: ${ALLURE_RESULTS_DIR}"

echo "[Step 2/6] Stopping existing containers..."
docker kill $(docker ps -aqf name=${CONTAINER_NAME}) 2>/dev/null || true
docker rm $(docker ps -aqf name=${CONTAINER_NAME}) 2>/dev/null || true
echo "✓ Existing containers cleaned up"

# ----------------------------- Docker Image Pull ------------------------------
echo "[Step 3/6] Pulling Docker image..."
echo "Pulling: ${DOCKER_IMAGE}"
docker pull ${DOCKER_IMAGE}
if [ $? -ne 0 ]; then
    echo "✗ ERROR: Failed to pull Docker image: ${DOCKER_IMAGE}"
    exit 1
fi
echo "✓ Docker image pulled successfully"

# ----------------------------- Docker Run Configuration -----------------------
echo "[Step 4/6] Preparing Docker run configuration..."

# Base Docker arguments
DOCKER_RUN_ARGS="--rm"
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --name=${CONTAINER_NAME}"
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --network=host"
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --shm-size=2g"

# Volume mounts
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} -v ${CONFIG_SOURCE}:${CONFIG_TARGET}:ro"
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} -v ${ALLURE_RESULTS_DIR}:${RESULTS_TARGET}:rw"

# Environment variables
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --env=DISPLAY"
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --env=QT_X11_NO_MITSHM=1"

# X11 display for GUI testing
DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} -v /tmp/.X11-unix/:/tmp/.X11-unix:rw"

# Platform-specific configurations
if [ "${TEST_PLATFORM}" == "android" ]; then
    echo "Configuring for Android platform..."
    DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} --privileged"
    DOCKER_RUN_ARGS="${DOCKER_RUN_ARGS} -v /dev/bus/usb:/dev/bus/usb:rw"
fi

# Build pytest command
PYTEST_CMD="python3 -m pytest ${TEST_SUITE} -s"
PYTEST_CMD="${PYTEST_CMD} -m '${TEST_MARKERS}'"
PYTEST_CMD="${PYTEST_CMD} --lab_config=${LAB_CONFIG_PATH}"
PYTEST_CMD="${PYTEST_CMD} --alluredir=${RESULTS_TARGET}"

# Add parallel execution if specified
if [ "${PARALLEL_TESTS}" -gt 1 ]; then
    PYTEST_CMD="${PYTEST_CMD} -n ${PARALLEL_TESTS}"
fi

# Add extra arguments
PYTEST_CMD="${PYTEST_CMD} ${PYTEST_EXTRA_ARGS}"

# Add video capture if enabled
if [ "${CAPTURE_VIDEO}" == "true" ]; then
    PYTEST_CMD="${PYTEST_CMD} --capture-video"
fi

echo "✓ Docker configuration prepared"

# ----------------------------- Test Execution ---------------------------------
echo "[Step 5/6] Starting test execution..."
echo "-------------------------------------------------------------------------"
echo "Docker Command:"
echo "  docker run ${DOCKER_RUN_ARGS} ${DOCKER_IMAGE} /bin/bash -c \"${PYTEST_CMD}\""
echo "-------------------------------------------------------------------------"

# Record start time
START_TIME=$(date +%s)

# Execute tests in Docker
docker run ${DOCKER_RUN_ARGS} ${DOCKER_IMAGE} /bin/bash -c "${PYTEST_CMD}"

# Capture test execution exit code
TEST_EXIT_CODE=$?

# Record end time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# ----------------------------- Post-Execution Analysis ------------------------
echo "========================================================================="
echo "[Step 6/6] Test Execution Completed"
echo "========================================================================="
echo "Exit Code:    ${TEST_EXIT_CODE}"
echo "Duration:     ${DURATION} seconds"
echo "Results Dir:  ${ALLURE_RESULTS_DIR}"

# Analyze results
if [ -d "${ALLURE_RESULTS_DIR}" ]; then
    RESULT_COUNT=$(ls -1 ${ALLURE_RESULTS_DIR}/*.json 2>/dev/null | wc -l)
    echo "Result Files: ${RESULT_COUNT}"

    # List result files
    if [ ${RESULT_COUNT} -gt 0 ]; then
        echo ""
        echo "Generated Files:"
        ls -lh ${ALLURE_RESULTS_DIR}/*.json 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    fi
fi

# Print result summary
echo ""
if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo "✓ SUCCESS: All tests passed"
    echo "========================================================================="
    exit 0
elif [ ${TEST_EXIT_CODE} -eq 1 ]; then
    echo "✗ FAILURE: Some tests failed"
    echo "========================================================================="
    exit 1
elif [ ${TEST_EXIT_CODE} -eq 2 ]; then
    echo "✗ ERROR: Test execution interrupted or error occurred"
    echo "========================================================================="
    exit 2
elif [ ${TEST_EXIT_CODE} -eq 3 ]; then
    echo "✗ ERROR: Internal pytest error"
    echo "========================================================================="
    exit 3
elif [ ${TEST_EXIT_CODE} -eq 4 ]; then
    echo "✗ ERROR: Pytest command usage error"
    echo "========================================================================="
    exit 4
elif [ ${TEST_EXIT_CODE} -eq 5 ]; then
    echo "⚠ WARNING: No tests were collected"
    echo "========================================================================="
    exit 5
else
    echo "✗ UNKNOWN: Unexpected exit code ${TEST_EXIT_CODE}"
    echo "========================================================================="
    exit ${TEST_EXIT_CODE}
fi
