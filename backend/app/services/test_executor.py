"""
Test Execution Service for managing VM test executions
"""
from typing import Dict, Optional, Any
from datetime import datetime
from uuid import uuid4
import logging
from sqlalchemy.orm import Session

from app.schemas.test import (
    TestExecutionRequest,
    TestExecutionResponse,
    TestStatusResponse,
    TestStatus,
    TestScope,
    TestEnvironment,
    Platform
)
from app.models.vm import VirtualMachine, VMStatus
from app.models.apk_file import ApkFile
from app.services.jenkins_service import jenkins_service

logger = logging.getLogger(__name__)


class TestExecutor:
    """Service for executing tests on VMs"""

    def __init__(self):
        """Initialize test executor with in-memory task storage"""
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def _get_jenkins_job_name(self, platform: Platform, execution_method: str) -> str:
        """
        Determine Jenkins job name based on platform and execution method

        Args:
            platform: Mobile platform (ios/android)
            execution_method: Execution method (docker/ssh)

        Returns:
            Jenkins job name
        """
        if execution_method == "docker":
            if platform == Platform.IOS:
                return "ios_ftm_docker_test"
            else:
                return "android_ftm_docker_test"
        else:
            # SSH execution - could be different job names
            if platform == Platform.IOS:
                return "ios_ftm_ssh_test"
            else:
                return "android_ftm_ssh_test"

    def _prepare_jenkins_parameters(
        self,
        request: TestExecutionRequest,
        vm: VirtualMachine,
        apk: Optional[ApkFile] = None
    ) -> Dict[str, Any]:
        """
        Prepare Jenkins job parameters from test execution request

        Args:
            request: Test execution request
            vm: Virtual machine
            apk: APK/IPA file (optional)

        Returns:
            Dictionary of Jenkins parameters
        """
        parameters = {
            # VM parameters
            "VM_IP": vm.ip_address,
            "VM_NAME": vm.name,
            "VM_SSH_USERNAME": vm.ssh_username or "admin",
            "VM_SSH_PASSWORD": vm.ssh_password or "",

            # Test configuration
            "PLATFORM": request.platform.value,
            "TEST_SCOPE": request.test_scope.value,
            "TEST_ENVIRONMENT": request.environment.value,
            "TEST_SUITE": request.test_suite,
            "TIMEOUT": str(request.timeout),
        }

        # Add APK/IPA parameters if provided
        if apk:
            parameters["APP_VERSION"] = apk.version_name or "unknown"
            parameters["APP_FILE_PATH"] = apk.file_path
            parameters["APP_PACKAGE_NAME"] = apk.package_name or ""
            if request.platform == Platform.IOS:
                parameters["APP_BUNDLE_ID"] = apk.bundle_id or ""
            else:
                parameters["APP_VERSION_CODE"] = str(apk.version_code or 0)
        elif request.app_version:
            parameters["APP_VERSION"] = request.app_version

        # Add Docker configuration if using Docker execution
        if request.execution_method.value == "docker" and request.docker_config:
            parameters["DOCKER_REGISTRY"] = request.docker_config.registry
            parameters["DOCKER_IMAGE"] = request.docker_config.image
            parameters["DOCKER_TAG"] = request.docker_config.tag
            parameters["DOCKER_FULL_IMAGE"] = f"{request.docker_config.registry}/{request.docker_config.image}:{request.docker_config.tag}"

        # Add any additional parameters
        if request.additional_params:
            parameters.update(request.additional_params)

        return parameters

    def execute_test(
        self,
        request: TestExecutionRequest,
        db: Session
    ) -> TestExecutionResponse:
        """
        Execute a test on a VM

        Args:
            request: Test execution request
            db: Database session

        Returns:
            Test execution response with task ID
        """
        # Validate VM exists
        vm = db.query(VirtualMachine).filter(VirtualMachine.id == request.vm_id).first()
        if not vm:
            raise ValueError(f"VM with ID {request.vm_id} not found")

        # Get APK/IPA if specified
        apk = None
        if request.apk_id:
            apk = db.query(ApkFile).filter(
                ApkFile.id == request.apk_id,
                ApkFile.is_active == True
            ).first()
            if not apk:
                raise ValueError(f"APK/IPA with ID {request.apk_id} not found or inactive")

            # Validate platform matches
            if apk.platform.value != request.platform.value:
                raise ValueError(
                    f"APK/IPA platform ({apk.platform.value}) does not match "
                    f"requested platform ({request.platform.value})"
                )

        # Generate task ID
        task_id = str(uuid4())

        # Get Jenkins job name
        job_name = self._get_jenkins_job_name(request.platform, request.execution_method.value)

        # Prepare Jenkins parameters
        jenkins_params = self._prepare_jenkins_parameters(request, vm, apk)

        logger.info(f"Starting test execution {task_id} for VM {vm.name}")
        logger.info(f"Jenkins job: {job_name}, Parameters: {jenkins_params}")

        try:
            # Trigger Jenkins job
            trigger_result = jenkins_service.trigger_job(job_name, jenkins_params)

            # Update VM status to TESTING
            vm.status = VMStatus.TESTING
            db.commit()

            # Store task information
            self.tasks[task_id] = {
                "task_id": task_id,
                "name": request.name,
                "vm_id": str(request.vm_id),
                "vm_name": vm.name,
                "apk_id": str(request.apk_id) if request.apk_id else None,
                "app_version": apk.version_name if apk else request.app_version,
                "test_scope": request.test_scope.value,
                "environment": request.environment.value,
                "platform": request.platform.value,
                "execution_method": request.execution_method.value,
                "jenkins_job": job_name,
                "jenkins_build": trigger_result.get("next_build_number"),
                "status": TestStatus.PENDING.value,
                "progress": 0,
                "message": "Test execution triggered, waiting for Jenkins to start...",
                "started_at": datetime.utcnow(),
                "completed_at": None,
                "test_results": None,
                "request": request.dict()
            }

            return TestExecutionResponse(
                task_id=task_id,
                status=TestStatus.PENDING,
                message="Test execution triggered successfully",
                vm_id=request.vm_id,
                vm_name=vm.name,
                jenkins_job=job_name,
                jenkins_build=trigger_result.get("next_build_number")
            )

        except Exception as e:
            logger.error(f"Failed to trigger test execution: {str(e)}")

            # Reset VM status if trigger failed
            vm.status = VMStatus.RUNNING
            db.commit()

            raise

    def get_test_status(self, task_id: str) -> TestStatusResponse:
        """
        Get status of a test execution

        Args:
            task_id: Test execution task ID

        Returns:
            Test status response
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # If task has Jenkins build number, check Jenkins for updates
        if task.get("jenkins_job") and task.get("jenkins_build"):
            try:
                build_status = jenkins_service.get_build_status(
                    task["jenkins_job"],
                    task["jenkins_build"]
                )

                # Update task status based on Jenkins build status
                if build_status["running"]:
                    task["status"] = TestStatus.RUNNING.value
                    task["progress"] = 50  # Rough estimate
                    task["message"] = "Test is currently running on Jenkins"
                elif build_status["result"]:
                    if build_status["result"] == "SUCCESS":
                        task["status"] = TestStatus.COMPLETED.value
                        task["progress"] = 100
                        task["message"] = "Test completed successfully"
                        task["completed_at"] = datetime.utcnow()
                    else:
                        task["status"] = TestStatus.FAILED.value
                        task["progress"] = 100
                        task["message"] = f"Test failed with result: {build_status['result']}"
                        task["completed_at"] = datetime.utcnow()

                # Store console URL
                task["console_url"] = build_status.get("console_url")

            except Exception as e:
                logger.error(f"Failed to get Jenkins build status: {str(e)}")
                # Keep existing task status if Jenkins query fails

        return TestStatusResponse(
            task_id=task_id,
            status=TestStatus(task["status"]),
            progress=task.get("progress", 0),
            message=task.get("message", ""),
            vm_id=task["vm_id"],
            vm_name=task["vm_name"],
            started_at=task.get("started_at"),
            completed_at=task.get("completed_at"),
            jenkins_job=task.get("jenkins_job"),
            jenkins_build=task.get("jenkins_build"),
            console_url=task.get("console_url"),
            test_results=task.get("test_results")
        )

    def get_previous_test_config(self, vm_id: int, db: Session) -> Dict[str, Any]:
        """
        Get previous test configuration for a VM

        Args:
            vm_id: VM ID
            db: Database session

        Returns:
            Previous test configuration
        """
        vm = db.query(VirtualMachine).filter(VirtualMachine.id == vm_id).first()
        if not vm:
            raise ValueError(f"VM with ID {vm_id} not found")

        # Find previous tests for this VM
        previous_tests = [
            task for task in self.tasks.values()
            if task.get("vm_id") == str(vm_id)
        ]

        # Sort by start time descending
        previous_tests.sort(
            key=lambda x: x.get("started_at", datetime.min),
            reverse=True
        )

        last_test = previous_tests[0] if previous_tests else None

        return {
            "vm_id": vm_id,
            "vm_name": vm.name,
            "last_test": last_test,
            "available_configs": previous_tests[:5]  # Return last 5 tests
        }

    def rerun_test(self, task_id: str, docker_tag: Optional[str] = None, timeout: Optional[int] = None, db: Session = None) -> TestExecutionResponse:
        """
        Re-run a previous test with optional parameter overrides

        Args:
            task_id: Original task ID to rerun
            docker_tag: Override docker tag (optional)
            timeout: Override timeout (optional)
            db: Database session

        Returns:
            New test execution response
        """
        original_task = self.tasks.get(task_id)
        if not original_task:
            raise ValueError(f"Task {task_id} not found")

        # Get original request
        original_request = TestExecutionRequest(**original_task["request"])

        # Apply overrides
        if docker_tag and original_request.docker_config:
            original_request.docker_config.tag = docker_tag
        if timeout:
            original_request.timeout = timeout

        # Execute new test
        return self.execute_test(original_request, db)


# Create singleton instance
test_executor = TestExecutor()
