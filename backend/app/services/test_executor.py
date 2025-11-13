"""Test Executor Service with Jenkins Node Pool Integration"""
import uuid
import logging
import subprocess
import asyncio
import time
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
                # Get VM details
                vm_id = task.config.get("vm_id")
                vm = db.get(VirtualMachine, vm_id)

                if not vm:
                    raise Exception(f"VM {vm_id} not found")

                # Execute test on the node
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
