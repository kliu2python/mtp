"""
Jenkins Controller Service
Implements the Jenkins master/controller functionality for job orchestration
This is the brain that manages job queue, agent assignment, and build execution
"""
import asyncio
import logging
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.jenkins_job import JenkinsJob, JobType
from app.models.jenkins_build import JenkinsBuild, BuildStatus
from app.models.jenkins_node import JenkinsNode, NodeStatus
from app.services.jenkins_pool import connection_pool

logger = logging.getLogger(__name__)


class JenkinsController:
    """
    Jenkins Controller - Main orchestration service
    Mimics Jenkins master/controller functionality
    """

    def __init__(self):
        self.build_queue: asyncio.Queue = None
        self.running = False
        self.active_builds: Dict[str, JenkinsBuild] = {}

    async def start(self):
        """Start the Jenkins controller"""
        if self.running:
            return

        self.running = True
        self.build_queue = asyncio.Queue()

        # Start background worker to process build queue
        asyncio.create_task(self._process_build_queue())
        logger.info("Jenkins Controller started")

    async def stop(self):
        """Stop the Jenkins controller"""
        self.running = False
        logger.info("Jenkins Controller stopped")

    async def trigger_build(
        self,
        db: Session,
        job_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        triggered_by: str = "Manual",
        trigger_cause: str = "User"
    ) -> JenkinsBuild:
        """
        Trigger a new build for a job (like clicking "Build Now" in Jenkins)

        Args:
            db: Database session
            job_id: UUID of the job to build
            parameters: Optional build parameters
            triggered_by: Who triggered the build
            trigger_cause: Reason for triggering

        Returns:
            JenkinsBuild object
        """
        # Get job definition
        job = db.get(JenkinsJob, job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        if not job.enabled:
            raise Exception(f"Job {job.name} is disabled")

        # Create new build
        build = JenkinsBuild(
            job_id=job.id,
            job_name=job.name,
            build_number=job.next_build_number,
            status=BuildStatus.QUEUED,
            parameters=parameters or {},
            triggered_by=triggered_by,
            trigger_cause=trigger_cause,
            queued_time=datetime.utcnow(),
            build_config={
                "job_type": job.job_type.value,
                "required_labels": job.required_labels,
                "docker_registry": job.docker_registry,
                "docker_image": job.docker_image,
                "docker_tag": job.docker_tag,
                "test_suite": job.test_suite,
                "test_markers": job.test_markers,
                "lab_config": job.lab_config,
                "platform": job.platform,
                "workspace_path": job.workspace_path,
                "config_mount_source": job.config_mount_source,
                "build_timeout": job.build_timeout,
                "script": job.script,
            }
        )

        db.add(build)

        # Update job statistics
        job.next_build_number += 1
        job.total_builds += 1

        db.commit()
        db.refresh(build)

        # Queue the build for execution
        await self.build_queue.put((str(build.id), db))

        logger.info(f"Build #{build.build_number} queued for job {job.name}")
        return build

    async def _process_build_queue(self):
        """
        Background worker that processes the build queue
        This is like Jenkins' queue processor that assigns builds to agents
        """
        while self.running:
            try:
                # Get next build from queue (with timeout to allow checking self.running)
                try:
                    build_id, db = await asyncio.wait_for(self.build_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process the build in background
                asyncio.create_task(self._execute_build(build_id, db))

            except Exception as e:
                logger.error(f"Error in build queue processor: {e}")
                await asyncio.sleep(1)

    async def _execute_build(self, build_id: str, db: Session):
        """
        Execute a build on an agent (like Jenkins executing a job on a slave node)

        Args:
            build_id: UUID of the build
            db: Database session
        """
        build = None
        node = None

        try:
            # Get build from database
            build = db.get(JenkinsBuild, build_id)
            if not build:
                logger.error(f"Build {build_id} not found")
                return

            self.active_builds[build_id] = build

            # Update build status to PENDING (waiting for agent)
            build.status = BuildStatus.PENDING
            self._append_console_output(build, f"[Jenkins] Build #{build.build_number} for job '{build.job_name}'\n")
            self._append_console_output(build, f"[Jenkins] Queued at {build.queued_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._append_console_output(build, f"[Jenkins] Waiting for available agent...\n")
            db.commit()

            # Acquire an agent from the pool
            required_labels = build.build_config.get("required_labels", [])
            self._append_console_output(build, f"[Jenkins] Required labels: {required_labels}\n")

            node = connection_pool.acquire_node(db, labels=required_labels)

            if not node:
                build.status = BuildStatus.FAILURE
                build.result = "FAILURE"
                build.error_message = "No available agents matching the required labels"
                self._append_console_output(build, f"[Jenkins] ERROR: No available agents\n")
                db.commit()
                return

            # Assign agent to build
            build.node_id = node.id
            build.node_name = node.name
            build.status = BuildStatus.RUNNING
            build.start_time = datetime.utcnow()

            # Update node status
            node.status = NodeStatus.TESTING

            self._append_console_output(build, f"[Jenkins] Agent assigned: {node.name} ({node.host}:{node.port})\n")
            self._append_console_output(build, f"[Jenkins] Starting build at {build.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            db.commit()

            # Execute on the agent via SSH
            job_type = build.build_config.get("job_type", "docker")

            if job_type == "docker" or job_type == "DOCKER":
                result = await self._execute_docker_build(node, build, db)
            elif job_type == "freestyle" or job_type == "FREESTYLE":
                result = await self._execute_freestyle_build(node, build, db)
            else:
                raise Exception(f"Unsupported job type: {job_type}")

            # Update build with results
            build.end_time = datetime.utcnow()
            build.duration = int((build.end_time - build.start_time).total_seconds())
            build.exit_code = result.get("exit_code", -1)

            if build.exit_code == 0:
                build.status = BuildStatus.SUCCESS
                build.result = "SUCCESS"
                self._append_console_output(build, f"\n[Jenkins] Build completed successfully\n")
            else:
                build.status = BuildStatus.FAILURE
                build.result = "FAILURE"
                build.error_message = result.get("error", "Build failed")
                self._append_console_output(build, f"\n[Jenkins] Build failed with exit code {build.exit_code}\n")

            self._append_console_output(build, f"[Jenkins] Duration: {build.duration}s\n")
            self._append_console_output(build, f"[Jenkins] Finished at {build.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Update job statistics
            job = db.get(JenkinsJob, build.job_id)
            if job:
                job.last_build_time = build.end_time
                job.last_build_status = build.result
                if build.result == "SUCCESS":
                    job.successful_builds += 1
                else:
                    job.failed_builds += 1

            # Update node metrics
            test_passed = build.exit_code == 0
            connection_pool.update_node_metrics(db, str(build.node_id), test_passed, build.duration)

            db.commit()

            logger.info(f"Build #{build.build_number} completed with status {build.result}")

        except asyncio.TimeoutError:
            if build:
                build.status = BuildStatus.TIMEOUT
                build.result = "TIMEOUT"
                build.end_time = datetime.utcnow()
                build.error_message = "Build execution timeout"
                self._append_console_output(build, f"\n[Jenkins] ERROR: Build timeout\n")
                db.commit()
                logger.error(f"Build {build_id} timed out")

        except Exception as e:
            logger.error(f"Error executing build {build_id}: {e}")
            if build:
                build.status = BuildStatus.FAILURE
                build.result = "FAILURE"
                build.end_time = datetime.utcnow()
                build.error_message = str(e)
                self._append_console_output(build, f"\n[Jenkins] ERROR: {str(e)}\n")
                db.commit()

        finally:
            # Release the agent back to pool
            if node:
                connection_pool.release_node(db, str(node.id))
                logger.info(f"Released agent {node.name}")

            # Remove from active builds
            if build_id in self.active_builds:
                del self.active_builds[build_id]

    async def _execute_docker_build(
        self,
        node: JenkinsNode,
        build: JenkinsBuild,
        db: Session
    ) -> Dict[str, Any]:
        """
        Execute a Docker-based build on an agent
        This mimics how Jenkins executes Docker containers on agent nodes via SSH

        Args:
            node: The agent node to execute on
            build: The build to execute
            db: Database session

        Returns:
            Result dictionary
        """
        config = build.build_config

        # Extract configuration
        docker_registry = config.get("docker_registry", "10.160.16.60")
        docker_image = config.get("docker_image", "pytest-automation/pytest_automation")
        docker_tag = config.get("docker_tag", "latest")
        test_suite = config.get("test_suite", "tests")
        test_markers = config.get("test_markers", "")
        lab_config = config.get("lab_config", "")
        platform = config.get("platform", "ios")
        workspace = config.get("workspace_path", "/home/jenkins/workspace")
        config_mount = config.get("config_mount_source", "/home/jenkins/custom_config")

        # Generate unique container name
        container_name = f"{build.job_name.replace(' ', '_')}_{build.build_number}"
        build.container_name = container_name

        # Build workspace path
        workspace_dir = f"{workspace}/{build.job_name}"
        build.workspace = workspace_dir

        # Full Docker image name
        full_docker_image = f"{docker_registry}/{docker_image}:{docker_tag}"
        build.docker_image = full_docker_image

        self._append_console_output(build, f"[Docker] Image: {full_docker_image}\n")
        self._append_console_output(build, f"[Docker] Container: {container_name}\n")
        self._append_console_output(build, f"[Docker] Workspace: {workspace_dir}\n")
        db.commit()

        # Build the Docker execution script
        # This is exactly how Jenkins executes Docker containers on slave nodes
        docker_script = self._build_docker_script(
            container_name=container_name,
            workspace_dir=workspace_dir,
            docker_image=full_docker_image,
            config_mount=config_mount,
            test_suite=test_suite,
            test_markers=test_markers,
            lab_config=lab_config,
            platform=platform,
            build_number=build.build_number
        )

        # SSH into the agent and execute the script
        ssh_command = self._build_ssh_command(node, docker_script)

        self._append_console_output(build, f"[SSH] Connecting to agent {node.host}:{node.port}\n")
        self._append_console_output(build, f"[SSH] Starting Docker execution...\n\n")
        db.commit()

        try:
            # Execute the command via SSH
            process = await asyncio.create_subprocess_exec(
                *ssh_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT  # Combine stderr with stdout
            )

            # Stream output in real-time
            timeout = config.get("build_timeout", 7200)
            async for line in self._stream_output(process.stdout):
                self._append_console_output(build, line)
                # Commit periodically to update console output
                if len(build.console_output) % 1000 < 100:  # Commit every ~1000 chars
                    db.commit()

            # Wait for process to complete
            await asyncio.wait_for(process.wait(), timeout=timeout)

            exit_code = process.returncode

            return {
                "exit_code": exit_code,
                "success": exit_code == 0,
                "container_name": container_name
            }

        except asyncio.TimeoutError:
            self._append_console_output(build, f"\n[Jenkins] ERROR: Build timeout after {timeout}s\n")
            db.commit()
            return {
                "exit_code": -1,
                "success": False,
                "error": f"Timeout after {timeout} seconds"
            }
        except Exception as e:
            self._append_console_output(build, f"\n[Jenkins] ERROR: {str(e)}\n")
            db.commit()
            return {
                "exit_code": -1,
                "success": False,
                "error": str(e)
            }

    async def _execute_freestyle_build(
        self,
        node: JenkinsNode,
        build: JenkinsBuild,
        db: Session
    ) -> Dict[str, Any]:
        """
        Execute a freestyle build (shell script) on an agent
        This mimics Jenkins freestyle job execution

        Args:
            node: The agent node
            build: The build to execute
            db: Database session

        Returns:
            Result dictionary
        """
        config = build.build_config
        script = config.get("script", "")

        if not script:
            return {
                "exit_code": -1,
                "success": False,
                "error": "No script defined"
            }

        workspace = config.get("workspace_path", "/home/jenkins/workspace")
        workspace_dir = f"{workspace}/{build.job_name}"
        build.workspace = workspace_dir

        # Build execution script
        execution_script = f"""#!/bin/bash
set -e

# Create workspace
mkdir -p {workspace_dir}
cd {workspace_dir}

echo "========================================="
echo "Executing build script..."
echo "========================================="

{script}
"""

        # SSH into agent and execute
        ssh_command = self._build_ssh_command(node, execution_script)

        self._append_console_output(build, f"[SSH] Connecting to agent {node.host}:{node.port}\n")
        self._append_console_output(build, f"[SSH] Workspace: {workspace_dir}\n")
        self._append_console_output(build, f"[SSH] Executing script...\n\n")
        db.commit()

        try:
            process = await asyncio.create_subprocess_exec(
                *ssh_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output
            timeout = config.get("build_timeout", 7200)
            async for line in self._stream_output(process.stdout):
                self._append_console_output(build, line)
                if len(build.console_output) % 1000 < 100:
                    db.commit()

            await asyncio.wait_for(process.wait(), timeout=timeout)

            return {
                "exit_code": process.returncode,
                "success": process.returncode == 0
            }

        except Exception as e:
            self._append_console_output(build, f"\n[Jenkins] ERROR: {str(e)}\n")
            db.commit()
            return {
                "exit_code": -1,
                "success": False,
                "error": str(e)
            }

    def _build_docker_script(
        self,
        container_name: str,
        workspace_dir: str,
        docker_image: str,
        config_mount: str,
        test_suite: str,
        test_markers: str,
        lab_config: str,
        platform: str,
        build_number: int
    ) -> str:
        """
        Build the Docker execution script
        This mimics the Jenkinsfile execution pattern
        """
        allure_results = f"{workspace_dir}/allure-results"

        script = f"""#!/bin/bash
set -e

# Jenkins-style workspace setup
echo "========================================="
echo "Jenkins Build #{build_number}"
echo "========================================="
echo "Workspace: {workspace_dir}"
echo "Docker Image: {docker_image}"
echo ""

# Create directories
mkdir -p {workspace_dir}
mkdir -p {allure_results}

# Cleanup previous containers
echo "Cleaning up previous containers..."
docker kill $(docker ps -aqf name={container_name}) 2>/dev/null || true
docker rm $(docker ps -aqf name={container_name}) 2>/dev/null || true

# Pull Docker image
echo "Pulling Docker image..."
docker pull {docker_image}

# Run tests in Docker container
echo "Starting test execution..."
"""

        # Add platform-specific Docker run command
        if platform.lower() == "android":
            script += f"""
docker run --rm \\
    --name="{container_name}" \\
    -v {config_mount}:/test_files:ro \\
    -v {allure_results}:/pytest-automation/allure-results:rw \\
    --env="DISPLAY" \\
    --env="QT_X11_NO_MITSHM=1" \\
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \\
    --shm-size=2g \\
    --network=host \\
    --privileged \\
    -v /dev/bus/usb:/dev/bus/usb:rw \\
    {docker_image} /bin/bash -c \\
    "python3 -m pytest {test_suite} -s -m '{test_markers}' \\
    --lab_config={lab_config} \\
    --alluredir=/pytest-automation/allure-results \\
    --tb=short \\
    --verbose"
"""
        else:  # iOS or default
            script += f"""
docker run --rm \\
    --name="{container_name}" \\
    -v {config_mount}:/test_files:ro \\
    -v {allure_results}:/pytest-automation/allure-results:rw \\
    --env="DISPLAY" \\
    --env="QT_X11_NO_MITSHM=1" \\
    -v /tmp/.X11-unix/:/tmp/.X11-unix:rw \\
    --shm-size=2g \\
    --network=host \\
    {docker_image} /bin/bash -c \\
    "python3 -m pytest {test_suite} -s -m '{test_markers}' \\
    --lab_config={lab_config} \\
    --alluredir=/pytest-automation/allure-results \\
    --tb=short \\
    --verbose"
"""

        script += """
# Capture exit code
EXIT_CODE=$?

# Print results
echo ""
echo "========================================="
echo "Build completed with exit code: ${EXIT_CODE}"
echo "========================================="

exit ${EXIT_CODE}
"""

        return script

    def _build_ssh_command(self, node: JenkinsNode, script: str) -> List[str]:
        """Build SSH command to execute script on agent"""
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
        ssh_cmd.append(script)

        return ssh_cmd

    async def _stream_output(self, stream):
        """Stream output line by line"""
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode('utf-8', errors='replace')

    def _append_console_output(self, build: JenkinsBuild, text: str):
        """Append text to build console output"""
        if build.console_output is None:
            build.console_output = ""
        build.console_output += text

    async def get_build_status(self, db: Session, build_id: str) -> Optional[Dict[str, Any]]:
        """Get build status and details"""
        build = db.get(JenkinsBuild, build_id)
        if not build:
            return None
        return build.to_dict()

    async def get_build_console_output(self, db: Session, build_id: str) -> Optional[str]:
        """Get build console output"""
        build = db.get(JenkinsBuild, build_id)
        if not build:
            return None
        return build.console_output

    async def abort_build(self, db: Session, build_id: str) -> bool:
        """Abort a running build"""
        build = db.get(JenkinsBuild, build_id)
        if not build or build.status not in [BuildStatus.QUEUED, BuildStatus.PENDING, BuildStatus.RUNNING]:
            return False

        build.status = BuildStatus.ABORTED
        build.result = "ABORTED"
        build.end_time = datetime.utcnow()
        self._append_console_output(build, "\n[Jenkins] Build aborted by user\n")

        db.commit()

        # Release node if assigned
        if build.node_id:
            connection_pool.release_node(db, str(build.node_id))

        return True


# Global Jenkins controller instance
jenkins_controller = JenkinsController()
