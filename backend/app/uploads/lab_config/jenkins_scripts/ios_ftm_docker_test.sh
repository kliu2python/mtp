#!/bin/bash
# =============================================================================
# iOS FTM Automation Test - Jenkins Docker Execution Script
# =============================================================================
# Description: Execute iOS FortiToken Mobile automation tests in Docker container
# Usage: This script is designed to run on Jenkins slave nodes
# Author: Mobile Test Pilot
# Date: 2025-11-13
# =============================================================================

# ----------------------------- Configuration ---------------------------------
# Jenkins Environment Variables (automatically provided by Jenkins)
# JOB_BASE_NAME: Name of the Jenkins job
# BUILD_NUMBER: Current build number
# WORKSPACE: Jenkins workspace directory
# docker_tag: Docker image tag (passed as Jenkins parameter)

# Test Configuration
TEST_SUITE="suites/mobile/suites/ftm/ios/tests"
TEST_MARKERS="ios_ftm and fac_ftc_token and functional"
LAB_CONFIG_PATH="/test_files/mobile_auto/ios16_ftm_testing_config.yml"

# Docker Configuration
DOCKER_REGISTRY="10.160.16.60"
DOCKER_IMAGE="${DOCKER_REGISTRY}/pytest-automation/pytest_automation"
DOCKER_TAG="${docker_tag:-latest}"
CONTAINER_NAME="${JOB_BASE_NAME:-ios_ftm_test}"

# Paths Configuration
ORIOLE_REPORT_DST="/test_files/oriole/mobile_auto_test/${JOB_BASE_NAME}"
WORKSPACE="${WORKSPACE:-$(pwd)}"
ALLURE_RESULTS_DIR="${WORKSPACE}/allure-results"

# ----------------------------- Pre-Execution Cleanup --------------------------
echo "========================================================================="
echo "Starting iOS FTM Automation Test Execution"
echo "========================================================================="
echo "Job Name: ${JOB_BASE_NAME}"
echo "Build Number: ${BUILD_NUMBER}"
echo "Docker Tag: ${DOCKER_TAG}"
echo "Workspace: ${WORKSPACE}"
echo "========================================================================="

# Clean up previous test results
echo "[1/5] Cleaning up previous test results..."
rm -rf ${ALLURE_RESULTS_DIR} || true
mkdir -p ${ALLURE_RESULTS_DIR}
echo "✓ Test results directory prepared: ${ALLURE_RESULTS_DIR}"

# Stop and remove existing containers
echo "[2/5] Stopping existing containers..."
docker kill $(docker ps -aqf name=${CONTAINER_NAME}) 2>/dev/null || true
docker rm $(docker ps -aqf name=${CONTAINER_NAME}) 2>/dev/null || true
echo "✓ Existing containers cleaned up"

# ----------------------------- Docker Image Pull ------------------------------
echo "[3/5] Pulling Docker image..."
docker pull ${DOCKER_IMAGE}:${DOCKER_TAG}
if [ $? -ne 0 ]; then
    echo "✗ Failed to pull Docker image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    exit 1
fi
echo "✓ Docker image pulled successfully"

# ----------------------------- Test Execution ---------------------------------
echo "[4/5] Starting test execution in Docker container..."
echo "Container Name: ${CONTAINER_NAME}"
echo "Test Suite: ${TEST_SUITE}"
echo "Test Markers: ${TEST_MARKERS}"
echo "Lab Config: ${LAB_CONFIG_PATH}"
echo "-------------------------------------------------------------------------"

docker run --rm \
    --name="${CONTAINER_NAME}" \
    -v /home/jenkins/custom_config:/test_files \
    -v ${ALLURE_RESULTS_DIR}:/pytest-automation/allure-results \
    --env="DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \
    --shm-size=2g \
    --network=host \
    ${DOCKER_IMAGE}:${DOCKER_TAG} /bin/bash -c \
    "python3 -m pytest ${TEST_SUITE} -s -m '${TEST_MARKERS}' \
    --lab_config=${LAB_CONFIG_PATH} \
    --alluredir=/pytest-automation/allure-results \
    --tb=short \
    --verbose
    "

# Capture test execution exit code
TEST_EXIT_CODE=$?

# ----------------------------- Post-Execution ---------------------------------
echo "========================================================================="
echo "[5/5] Test Execution Completed"
echo "========================================================================="
echo "Exit Code: ${TEST_EXIT_CODE}"
echo "Results Directory: ${ALLURE_RESULTS_DIR}"

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo "✓ All tests passed successfully"
else
    echo "✗ Tests failed with exit code: ${TEST_EXIT_CODE}"
fi

# Count test results
if [ -d "${ALLURE_RESULTS_DIR}" ]; then
    RESULT_COUNT=$(ls -1 ${ALLURE_RESULTS_DIR}/*.json 2>/dev/null | wc -l)
    echo "Total test results: ${RESULT_COUNT}"
fi

echo "========================================================================="
exit ${TEST_EXIT_CODE}
