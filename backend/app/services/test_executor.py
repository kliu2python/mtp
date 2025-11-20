"""Test Executor Service with Jenkins Node Pool Integration"""
import uuid
import logging
import subprocess
import asyncio
import time
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.jenkins_pool import connection_pool
from app.models.vm import VirtualMachine
from app.models.jenkins_node import JenkinsNode
from app.models.test_execution import TestExecution, TestStatus

logger = logging.getLogger(__name__)


class TestExecutor:
    """Test executor with Jenkins node pool integration and database persistence"""

    def __init__(self):
        self.task_queue: asyncio.Queue = None
        self.running = False

    async def start(self):
        """Start the test executor background worker"""
        if self.running:
            return

        self.running = True
        self.task_queue = asyncio.Queue()
        logger.info("Test executor started")

    async def stop(self):
        """Stop the test executor"""
        self.running = False
        logger.info("Test executor stopped")

    async def queue_test(self, config: Dict[str, Any], db: Session):
        """
        Queue a test for execution

        Args:
            config: Test configuration with keys:
                - vm_id: ID of the VM to test
                - test_suite: Name of the test suite
                - test_cases: List of test cases to run
                - labels: Optional list of required node labels
            db: Database session

        Returns:
            task_id: Unique task identifier
        """
        task_id = str(uuid.uuid4())

        # Create database record
        execution = TestExecution(
            task_id=task_id,
            config=config,
            status=TestStatus.QUEUED,
            progress=0
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Start execution in background - pass task_id instead of task object
        asyncio.create_task(self._execute_test(task_id))

        logger.info(f"Test task {task_id} queued for VM {config.get('vm_id')}")
        return task_id

    async def _execute_test(self, task_id: str):
        """
        Execute a test task on an available Jenkins node

        Args:
            task_id: Task identifier
        """
        # Create a new database session for this background task
        from app.core.database import SessionLocal
        db = SessionLocal()

        try:
            # Get execution from database
            execution = db.query(TestExecution).filter(TestExecution.task_id == task_id).first()
            if not execution:
                logger.error(f"Task {task_id}: Not found in database")
                return

            # Update status
            execution.status = TestStatus.ACQUIRING_NODE
            execution.progress = 10
            db.commit()

            # Get required labels from config
            labels = execution.config.get("labels", [])

            # Acquire a node from the pool
            node = connection_pool.acquire_node(db, labels=labels)

            if not node:
                execution.status = TestStatus.FAILED
                execution.error = "No available nodes in the pool"
                db.commit()
                logger.error(f"Task {task_id}: No available nodes")
                return

            execution.node_id = str(node.id)
            execution.status = TestStatus.RUNNING
            execution.start_time = datetime.utcnow()
            execution.progress = 20
            db.commit()

            logger.info(f"Task {task_id} acquired node {node.name}")

            try:
                # Check execution method (docker or ssh)
                execution_method = execution.config.get("execution_method", "ssh")

                if execution_method == "docker":
                    # Execute test in Docker container
                    result = await self._run_docker_test_on_node(node, execution, db)
                else:
                    # Get VM details for SSH execution
                    vm_id = execution.config.get("vm_id")
                    vm = db.get(VirtualMachine, vm_id)

                    if not vm:
                        raise Exception(f"VM {vm_id} not found")

                    # Execute test on the node via SSH
                    result = await self._run_test_on_node(node, vm, execution, db)

                execution.status = TestStatus.COMPLETED
                execution.progress = 100
                execution.result = result
                execution.end_time = datetime.utcnow()
                db.commit()

                # Update node metrics
                test_passed = result.get("status") == "passed"
                duration = int((execution.end_time - execution.start_time).total_seconds())
                connection_pool.update_node_metrics(db, execution.node_id, test_passed, duration)

                logger.info(f"Task {task_id} completed successfully on node {node.name}")

            except Exception as e:
                execution.status = TestStatus.FAILED
                execution.error = str(e)
                execution.end_time = datetime.utcnow()
                db.commit()
                logger.error(f"Task {task_id} failed: {e}")

            finally:
                # Release the node back to the pool
                connection_pool.release_node(db, execution.node_id)
                logger.info(f"Task {task_id} released node {node.name}")

        except Exception as e:
            logger.error(f"Task {task_id} error: {e}")
            # Try to update database if possible
            try:
                execution = db.query(TestExecution).filter(TestExecution.task_id == task_id).first()
                if execution:
                    execution.status = TestStatus.FAILED
                    execution.error = str(e)
                    db.commit()
            except:
                pass
        finally:
            db.close()

    async def _run_test_on_node(
        self,
        node: JenkinsNode,
        vm: VirtualMachine,
        execution: TestExecution,
        db: Session
    ) -> Dict[str, Any]:
        """
        Run test commands on a Jenkins slave node via SSH

        Args:
            node: Jenkins node to run tests on
            vm: VM being tested
            execution: Test execution record
            db: Database session

        Returns:
            Test result dictionary
        """
        test_suite = execution.config.get("test_suite", "default")
        test_cases = execution.config.get("test_cases", [])

        # Build test command
        # This is a simplified example - you would customize this based on your test framework
        test_command = f"""
            cd /workspace/tests && \\
            python -m pytest {test_suite} \\
                --vm-host={vm.ip_address} \\
                --vm-username={vm.ssh_username} \\
                --vm-password={vm.ssh_password} \\
                --test-cases={','.join(test_cases)} \\
                --json-report
        """

        # Build SSH command
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(node.port),
        ]

        if node.ssh_key:
            ssh_cmd.extend(["-i", node.ssh_key])
        elif node.password:
            ssh_cmd = ["sshpass", "-p", node.password] + ssh_cmd

        ssh_cmd.append(f"{node.username}@{node.host}")
        ssh_cmd.append(test_command)

        # Execute test
        execution.progress = 50
        db.commit()
        logger.info(f"Task {execution.task_id}: Executing tests on node {node.name}")

        try:
            # Run the test command with timeout
            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            timeout = execution.config.get("timeout", 3600)  # Default 1 hour
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            execution.progress = 90
            db.commit()

            # Parse results
            result = {
                "status": "passed" if process.returncode == 0 else "failed",
                "return_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "test_suite": test_suite,
                "vm_id": str(vm.id),
                "node_id": str(node.id)
            }

            return result

        except asyncio.TimeoutError:
            logger.error(f"Task {execution.task_id}: Test execution timed out")
            return {
                "status": "failed",
                "error": f"Test execution timed out after {timeout} seconds",
                "test_suite": test_suite,
                "vm_id": str(vm.id),
                "node_id": str(node.id)
            }
        except Exception as e:
            logger.error(f"Task {execution.task_id}: Test execution error: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "test_suite": test_suite,
                "vm_id": str(vm.id),
                "node_id": str(node.id)
            }

    async def _run_docker_test_on_node(
        self,
        node: JenkinsNode,
        execution: TestExecution,
        db: Session
    ) -> Dict[str, Any]:
        """
        Run test commands in Docker container on a Jenkins slave node via SSH
        This method implements the Jenkins-style Docker execution pattern

        Args:
            node: Jenkins node to run tests on
            execution: Test execution record
            db: Database session

        Returns:
            Test result dictionary
        """
        # Extract configuration from execution
        test_suite = execution.config.get("test_suite", "suites/mobile/suites/ftm/ios/tests")
        test_markers = execution.config.get("test_markers", "ios_ftm and functional")
        lab_config_path = execution.config.get("lab_config", "/test_files/mobile_auto/ios16_ftm_testing_config.yml")
        platform = execution.config.get("platform", "ios")  # ios or android

        # Docker configuration
        docker_registry = execution.config.get("docker_registry", "10.160.16.60")
        docker_image = execution.config.get("docker_image", "pytest-automation/pytest_automation")
        docker_tag = execution.config.get("docker_tag", "latest")
        container_name = execution.config.get("container_name", f"mtp_test_{execution.task_id[:8]}")

        # Workspace configuration
        workspace = execution.config.get("workspace", "/home/jenkins/workspace/mobile_automation")
        config_mount_source = execution.config.get("config_mount", "/home/jenkins/custom_config")

        # Report directories
        allure_results_dir = f"{workspace}/allure-results"
        allure_report_dir = f"{workspace}/allure-report"

        # Build Docker execution script
        docker_script = f"""#!/bin/bash
set -e

# Configuration
JOB_BASE_NAME="{container_name}"
WORKSPACE="{workspace}"
ALLURE_RESULTS_DIR="{allure_results_dir}"
ALLURE_REPORT_DIR="{allure_report_dir}"
DOCKER_IMAGE="{docker_registry}/{docker_image}:{docker_tag}"

# Check if Docker daemon is running
echo "Checking Docker daemon..."
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running!"
    echo "Please start Docker with: sudo systemctl start docker"
    exit 1
fi
echo "Docker daemon is running"

# Check Docker version
echo "Docker version:"
docker version --format '{{{{.Server.Version}}}}'

# Cleanup
echo "Cleaning up previous test results..."
rm -rf ${{ALLURE_RESULTS_DIR}} || true
mkdir -p ${{ALLURE_RESULTS_DIR}}
mkdir -p ${{ALLURE_REPORT_DIR}}

echo "Stopping existing containers..."
docker kill $(docker ps -aqf name=${{JOB_BASE_NAME}}) 2>/dev/null || true
docker rm $(docker ps -aqf name=${{JOB_BASE_NAME}}) 2>/dev/null || true

# Pull Docker image
echo "Pulling Docker image: ${{DOCKER_IMAGE}}"
docker pull ${{DOCKER_IMAGE}}

# Run tests in Docker
echo "Starting test execution..."
"""

        # Add Docker run command based on platform
        if platform.lower() == "android":
            docker_script += f"""
docker run --rm \\
    --name="${{JOB_BASE_NAME}}" \\
    -v {config_mount_source}:/test_files:ro \\
    -v ${{ALLURE_RESULTS_DIR}}:/pytest-automation/allure-results:rw \\
    --env="DISPLAY" \\
    --env="QT_X11_NO_MITSHM=1" \\
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \\
    --shm-size=2g \\
    --network=host \\
    --privileged \\
    -v /dev/bus/usb:/dev/bus/usb:rw \\
    ${{DOCKER_IMAGE}} /bin/bash -c \\
    "python3 -m pytest {test_suite} -s -m '{test_markers}' \\
    --lab_config={lab_config_path} \\
    --alluredir=/pytest-automation/allure-results \\
    --tb=short \\
    --verbose"
"""
        else:  # iOS or default
            docker_script += f"""
docker run --rm \\
    --name="${{JOB_BASE_NAME}}" \\
    -v {config_mount_source}:/test_files:ro \\
    -v ${{ALLURE_RESULTS_DIR}}:/pytest-automation/allure-results:rw \\
    --env="DISPLAY" \\
    --env="QT_X11_NO_MITSHM=1" \\
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \\
    --shm-size=2g \\
    --network=host \\
    ${{DOCKER_IMAGE}} /bin/bash -c \\
    "python3 -m pytest {test_suite} -s -m '{test_markers}' \\
    --lab_config={lab_config_path} \\
    --alluredir=/pytest-automation/allure-results \\
    --tb=short \\
    --verbose"
"""

        docker_script += """
# Capture exit code
EXIT_CODE=$?

# Print results
echo "Test execution completed with exit code: ${EXIT_CODE}"
if [ -d "${ALLURE_RESULTS_DIR}" ]; then
    RESULT_COUNT=$(ls -1 ${ALLURE_RESULTS_DIR}/*.json 2>/dev/null | wc -l)
    echo "Total test results: ${RESULT_COUNT}"
fi

exit ${EXIT_CODE}
"""

        # Build SSH command to execute the script on the node
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-p", str(node.port),
        ]

        if node.ssh_key:
            ssh_cmd.extend(["-i", node.ssh_key])
        elif node.password:
            ssh_cmd = ["sshpass", "-p", node.password] + ssh_cmd

        ssh_cmd.append(f"{node.username}@{node.host}")
        ssh_cmd.append(docker_script)

        # Execute test
        execution.progress = 50
        db.commit()
        logger.info(f"Task {execution.task_id}: Executing Docker-based tests on node {node.name}")

        try:
            # Run the Docker test script with timeout
            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            timeout = execution.config.get("timeout", 3600)  # Default 1 hour
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            execution.progress = 90
            db.commit()

            # Store report paths
            execution.allure_report_path = allure_results_dir
            db.commit()

            # Parse results
            result = {
                "status": "passed" if process.returncode == 0 else "failed",
                "return_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "test_suite": test_suite,
                "test_markers": test_markers,
                "platform": platform,
                "docker_image": f"{docker_registry}/{docker_image}:{docker_tag}",
                "container_name": container_name,
                "node_id": str(node.id),
                "execution_method": "docker",
                "allure_results_dir": allure_results_dir,
                "allure_report_dir": allure_report_dir
            }

            logger.info(f"Task {execution.task_id}: Docker test completed with return code {process.returncode}")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Task {execution.task_id}: Docker test execution timed out")
            return {
                "status": "failed",
                "error": f"Docker test execution timed out after {timeout} seconds",
                "test_suite": test_suite,
                "node_id": str(node.id),
                "execution_method": "docker"
            }
        except Exception as e:
            logger.error(f"Task {execution.task_id}: Docker test execution error: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "test_suite": test_suite,
                "node_id": str(node.id),
                "execution_method": "docker"
            }

    async def get_status(self, task_id: str, db: Session = None) -> Optional[Dict[str, Any]]:
        """
        Get test task status from database

        Args:
            task_id: Task identifier
            db: Database session (optional, will create one if not provided)

        Returns:
            Task status dictionary or None if not found
        """
        should_close_db = False
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            should_close_db = True

        try:
            execution = db.query(TestExecution).filter(TestExecution.task_id == task_id).first()
            if not execution:
                return None
            return execution.to_dict()
        finally:
            if should_close_db:
                db.close()

    def get_all_tasks(self, db: Session = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get status of all tasks from database

        Args:
            db: Database session (optional)
            limit: Maximum number of tasks to return

        Returns:
            List of task status dictionaries
        """
        should_close_db = False
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            should_close_db = True

        try:
            executions = db.query(TestExecution).order_by(
                TestExecution.created_at.desc()
            ).limit(limit).all()
            return [execution.to_dict() for execution in executions]
        finally:
            if should_close_db:
                db.close()

    def clear_completed_tasks(self, db: Session = None, days_old: int = 7):
        """
        Clear completed and failed tasks older than specified days from database

        Args:
            db: Database session (optional)
            days_old: Delete tasks older than this many days
        """
        should_close_db = False
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            should_close_db = True

        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            deleted_count = db.query(TestExecution).filter(
                TestExecution.status.in_([TestStatus.COMPLETED, TestStatus.FAILED]),
                TestExecution.created_at < cutoff_date
            ).delete()
            db.commit()

            logger.info(f"Cleared {deleted_count} old completed tasks")
        finally:
            if should_close_db:
                db.close()


# Global test executor instance
test_executor = TestExecutor()
