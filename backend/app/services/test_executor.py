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

logger = logging.getLogger(__name__)


class TestTask:
    """Represents a test execution task"""

    def __init__(self, task_id: str, config: Dict[str, Any]):
        self.task_id = task_id
        self.config = config
        self.status = "queued"  # queued, running, completed, failed
        self.progress = 0
        self.result = None
        self.error = None
        self.node_id = None
        self.start_time = None
        self.end_time = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "config": self.config,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "node_id": self.node_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None
        }


class TestExecutor:
    """Test executor with Jenkins node pool integration"""

    def __init__(self):
        self.tasks: Dict[str, TestTask] = {}
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
        task = TestTask(task_id, config)
        self.tasks[task_id] = task

        # Start execution in background
        asyncio.create_task(self._execute_test(task, db))

        logger.info(f"Test task {task_id} queued for VM {config.get('vm_id')}")
        return task_id

    async def _execute_test(self, task: TestTask, db: Session):
        """
        Execute a test task on an available Jenkins node

        Args:
            task: Test task to execute
            db: Database session
        """
        try:
            task.status = "acquiring_node"
            task.progress = 10

            # Get required labels from config
            labels = task.config.get("labels", [])

            # Acquire a node from the pool
            node = connection_pool.acquire_node(db, labels=labels)

            if not node:
                task.status = "failed"
                task.error = "No available nodes in the pool"
                logger.error(f"Task {task.task_id}: No available nodes")
                return

            task.node_id = str(node.id)
            task.status = "running"
            task.start_time = datetime.utcnow()
            task.progress = 20

            logger.info(f"Task {task.task_id} acquired node {node.name}")

            try:
                # Check execution method (docker or ssh)
                execution_method = task.config.get("execution_method", "ssh")

                if execution_method == "docker":
                    # Execute test in Docker container
                    result = await self._run_docker_test_on_node(node, task, db)
                else:
                    # Get VM details for SSH execution
                    vm_id = task.config.get("vm_id")
                    vm = db.get(VirtualMachine, vm_id)

                    if not vm:
                        raise Exception(f"VM {vm_id} not found")

                    # Execute test on the node via SSH
                    result = await self._run_test_on_node(node, vm, task, db)

                task.status = "completed"
                task.progress = 100
                task.result = result
                task.end_time = datetime.utcnow()

                # Update node metrics
                test_passed = result.get("status") == "passed"
                duration = int((task.end_time - task.start_time).total_seconds())
                connection_pool.update_node_metrics(db, task.node_id, test_passed, duration)

                logger.info(f"Task {task.task_id} completed successfully on node {node.name}")

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.end_time = datetime.utcnow()
                logger.error(f"Task {task.task_id} failed: {e}")

            finally:
                # Release the node back to the pool
                connection_pool.release_node(db, task.node_id)
                logger.info(f"Task {task.task_id} released node {node.name}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Task {task.task_id} error: {e}")

    async def _run_test_on_node(
        self,
        node: JenkinsNode,
        vm: VirtualMachine,
        task: TestTask,
        db: Session
    ) -> Dict[str, Any]:
        """
        Run test commands on a Jenkins slave node via SSH

        Args:
            node: Jenkins node to run tests on
            vm: VM being tested
            task: Test task
            db: Database session

        Returns:
            Test result dictionary
        """
        test_suite = task.config.get("test_suite", "default")
        test_cases = task.config.get("test_cases", [])

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
        task.progress = 50
        logger.info(f"Task {task.task_id}: Executing tests on node {node.name}")

        try:
            # Run the test command with timeout
            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            timeout = task.config.get("timeout", 3600)  # Default 1 hour
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            task.progress = 90

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
            logger.error(f"Task {task.task_id}: Test execution timed out")
            return {
                "status": "failed",
                "error": f"Test execution timed out after {timeout} seconds",
                "test_suite": test_suite,
                "vm_id": str(vm.id),
                "node_id": str(node.id)
            }
        except Exception as e:
            logger.error(f"Task {task.task_id}: Test execution error: {e}")
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
        task: TestTask,
        db: Session
    ) -> Dict[str, Any]:
        """
        Run test commands in Docker container on a Jenkins slave node via SSH
        This method implements the Jenkins-style Docker execution pattern

        Args:
            node: Jenkins node to run tests on
            task: Test task
            db: Database session

        Returns:
            Test result dictionary
        """
        # Extract configuration from task
        test_suite = task.config.get("test_suite", "suites/mobile/suites/ftm/ios/tests")
        test_markers = task.config.get("test_markers", "ios_ftm and functional")
        lab_config_path = task.config.get("lab_config", "/test_files/mobile_auto/ios16_ftm_testing_config.yml")
        platform = task.config.get("platform", "ios")  # ios or android

        # Docker configuration
        docker_registry = task.config.get("docker_registry", "10.160.16.60")
        docker_image = task.config.get("docker_image", "pytest-automation/pytest_automation")
        docker_tag = task.config.get("docker_tag", "latest")
        container_name = task.config.get("container_name", f"mtp_test_{task.task_id[:8]}")

        # Workspace configuration
        workspace = task.config.get("workspace", "/home/jenkins/workspace/mobile_automation")
        config_mount_source = task.config.get("config_mount", "/home/jenkins/custom_config")

        # Build Docker execution script
        docker_script = f"""#!/bin/bash
set -e

# Configuration
JOB_BASE_NAME="{container_name}"
WORKSPACE="{workspace}"
ALLURE_RESULTS_DIR="${{WORKSPACE}}/allure-results"
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
        task.progress = 50
        logger.info(f"Task {task.task_id}: Executing Docker-based tests on node {node.name}")

        try:
            # Run the Docker test script with timeout
            process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for completion with timeout
            timeout = task.config.get("timeout", 3600)  # Default 1 hour
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            task.progress = 90

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
                "execution_method": "docker"
            }

            logger.info(f"Task {task.task_id}: Docker test completed with return code {process.returncode}")
            return result

        except asyncio.TimeoutError:
            logger.error(f"Task {task.task_id}: Docker test execution timed out")
            return {
                "status": "failed",
                "error": f"Docker test execution timed out after {timeout} seconds",
                "test_suite": test_suite,
                "node_id": str(node.id),
                "execution_method": "docker"
            }
        except Exception as e:
            logger.error(f"Task {task.task_id}: Docker test execution error: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "test_suite": test_suite,
                "node_id": str(node.id),
                "execution_method": "docker"
            }

    async def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test task status

        Args:
            task_id: Task identifier

        Returns:
            Task status dictionary or None if not found
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        return task.to_dict()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get status of all tasks"""
        return [task.to_dict() for task in self.tasks.values()]

    def clear_completed_tasks(self):
        """Clear completed and failed tasks from memory"""
        completed_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.status in ["completed", "failed"]
        ]
        for task_id in completed_ids:
            del self.tasks[task_id]
        logger.info(f"Cleared {len(completed_ids)} completed tasks")


# Global test executor instance
test_executor = TestExecutor()
