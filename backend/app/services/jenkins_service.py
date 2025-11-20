"""
Jenkins Service

Bridge service between local database and real Jenkins API.
Handles job execution and result management using the real Jenkins instance.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.core.config import settings
from app.services.jenkins_api_client import JenkinsAPIClient
from app.models.jenkins_job import JenkinsJob, JobType
from app.models.jenkins_build import JenkinsBuild, BuildStatus

logger = logging.getLogger(__name__)


class JenkinsService:
    """Service for managing Jenkins jobs and builds using real Jenkins API"""

    def __init__(self):
        """Initialize Jenkins service with API client"""
        self.client = JenkinsAPIClient(
            base_url=settings.JENKINS_URL,
            username=settings.JENKINS_USERNAME if settings.JENKINS_USERNAME else None,
            api_token=settings.JENKINS_API_TOKEN if settings.JENKINS_API_TOKEN else None
        )
        logger.info(f"Jenkins service initialized with URL: {settings.JENKINS_URL}")

    async def verify_connection(self) -> bool:
        """Verify connection to Jenkins server"""
        try:
            return await self.client.verify_connection()
        except Exception as e:
            logger.error(f"Failed to connect to Jenkins: {e}")
            return False

    # ==================== Job Management ====================

    async def create_job_in_jenkins(self, job: JenkinsJob) -> bool:
        """
        Create job in Jenkins using configuration XML

        Args:
            job: Local job model

        Returns:
            True if successful
        """
        try:
            # Generate Jenkins job configuration XML based on job type
            config_xml = self._generate_job_config_xml(job)

            # Create job in Jenkins
            await self.client.create_job(job.name, config_xml)

            logger.info(f"Job '{job.name}' created in Jenkins")
            return True

        except Exception as e:
            logger.error(f"Failed to create job in Jenkins: {e}")
            raise

    async def delete_job_from_jenkins(self, job_name: str) -> bool:
        """
        Delete job from Jenkins

        Args:
            job_name: Name of job to delete

        Returns:
            True if successful
        """
        try:
            await self.client.delete_job(job_name)
            logger.info(f"Job '{job_name}' deleted from Jenkins")
            return True
        except Exception as e:
            logger.error(f"Failed to delete job from Jenkins: {e}")
            return False

    async def enable_job_in_jenkins(self, job_name: str) -> bool:
        """Enable job in Jenkins"""
        try:
            await self.client.enable_job(job_name)
            return True
        except Exception as e:
            logger.error(f"Failed to enable job in Jenkins: {e}")
            return False

    async def disable_job_in_jenkins(self, job_name: str) -> bool:
        """Disable job in Jenkins"""
        try:
            await self.client.disable_job(job_name)
            return True
        except Exception as e:
            logger.error(f"Failed to disable job in Jenkins: {e}")
            return False

    # ==================== Build Management ====================

    async def trigger_build(
        self,
        db: Session,
        job_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        triggered_by: str = "API"
    ) -> JenkinsBuild:
        """
        Trigger a build in Jenkins and track it locally

        Args:
            db: Database session
            job_id: Job ID
            parameters: Build parameters
            triggered_by: Who triggered the build

        Returns:
            JenkinsBuild model
        """
        # Get job from database
        job = db.get(JenkinsJob, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        if not job.enabled:
            raise ValueError(f"Job '{job.name}' is disabled")

        try:
            # Trigger build in Jenkins
            logger.info(f"Triggering build for job '{job.name}' in Jenkins")
            await self.client.trigger_build(job.name, parameters=parameters, wait=True)

            # Get the latest build number from Jenkins
            last_build = await self.client.get_last_build(job.name)
            build_number = last_build.get('number') if last_build else 1

            # Create build record locally
            build = JenkinsBuild(
                job_id=job.id,
                build_number=build_number,
                status=BuildStatus.RUNNING,
                parameters=parameters or {},
                triggered_by=triggered_by,
                trigger_cause="API",
                started_at=datetime.utcnow()
            )

            db.add(build)

            # Update job statistics
            job.total_builds += 1
            job.last_build_number = build_number
            job.last_build_at = datetime.utcnow()

            db.commit()
            db.refresh(build)

            # Start background task to monitor build
            asyncio.create_task(self._monitor_build(build.id, job.name, build_number))

            logger.info(f"Build #{build_number} triggered for job '{job.name}'")
            return build

        except Exception as e:
            logger.error(f"Failed to trigger build: {e}")
            raise

    async def _monitor_build(self, build_id: str, job_name: str, build_number: int):
        """
        Monitor build progress in Jenkins and update local database

        Args:
            build_id: Local build ID
            job_name: Jenkins job name
            build_number: Jenkins build number
        """
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            while True:
                await asyncio.sleep(5)  # Poll every 5 seconds

                # Get build status from Jenkins
                try:
                    build_info = await self.client.get_build(job_name, build_number)
                except Exception as e:
                    logger.error(f"Failed to get build info: {e}")
                    continue

                # Update local build record
                build = db.get(JenkinsBuild, build_id)
                if not build:
                    break

                # Check if build is still running
                if not build_info.get('building', False):
                    # Build finished
                    result = build_info.get('result', 'UNKNOWN')

                    if result == 'SUCCESS':
                        build.status = BuildStatus.SUCCESS
                        # Update job success statistics
                        job = db.get(JenkinsJob, build.job_id)
                        if job:
                            job.successful_builds += 1
                    elif result == 'FAILURE':
                        build.status = BuildStatus.FAILURE
                        job = db.get(JenkinsJob, build.job_id)
                        if job:
                            job.failed_builds += 1
                    elif result == 'ABORTED':
                        build.status = BuildStatus.ABORTED
                    else:
                        build.status = BuildStatus.FAILURE

                    build.completed_at = datetime.utcnow()
                    build.duration = build_info.get('duration', 0) / 1000  # Convert ms to seconds

                    # Get test results if available
                    test_results = await self.client.get_test_results(job_name, build_number)
                    if test_results:
                        build.test_results = test_results

                    db.commit()
                    logger.info(f"Build #{build_number} completed with status: {result}")
                    break

                # Update progress
                db.commit()

        except Exception as e:
            logger.error(f"Error monitoring build: {e}")
        finally:
            db.close()

    async def get_build_console_output(
        self,
        db: Session,
        build_id: str
    ) -> Optional[str]:
        """
        Get build console output from Jenkins

        Args:
            db: Database session
            build_id: Local build ID

        Returns:
            Console output string or None
        """
        build = db.get(JenkinsBuild, build_id)
        if not build:
            return None

        job = db.get(JenkinsJob, build.job_id)
        if not job:
            return None

        try:
            return await self.client.get_build_console_output(job.name, build.build_number)
        except Exception as e:
            logger.error(f"Failed to get console output: {e}")
            return f"Error fetching console output: {e}"

    async def abort_build(self, db: Session, build_id: str) -> bool:
        """
        Abort a running build in Jenkins

        Args:
            db: Database session
            build_id: Local build ID

        Returns:
            True if successful
        """
        build = db.get(JenkinsBuild, build_id)
        if not build:
            return False

        if build.status not in [BuildStatus.RUNNING, BuildStatus.PENDING]:
            return False

        job = db.get(JenkinsJob, build.job_id)
        if not job:
            return False

        try:
            await self.client.stop_build(job.name, build.build_number)

            build.status = BuildStatus.ABORTED
            build.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"Build #{build.build_number} aborted")
            return True

        except Exception as e:
            logger.error(f"Failed to abort build: {e}")
            return False

    # ==================== Sync Operations ====================

    async def sync_job_from_jenkins(self, db: Session, job_name: str) -> Optional[Dict]:
        """
        Sync job details from Jenkins to local database

        Args:
            db: Database session
            job_name: Jenkins job name

        Returns:
            Job details dictionary
        """
        try:
            jenkins_job = await self.client.get_job(job_name)

            # Find or create local job record
            local_job = db.execute(
                select(JenkinsJob).where(JenkinsJob.name == job_name)
            ).scalar_one_or_none()

            if not local_job:
                # Create new local record
                local_job = JenkinsJob(
                    name=job_name,
                    description=jenkins_job.get('description', ''),
                    job_type=JobType.FREESTYLE,  # Default
                    created_by="Jenkins Sync"
                )
                db.add(local_job)

            # Update statistics
            if 'lastBuild' in jenkins_job and jenkins_job['lastBuild']:
                local_job.last_build_number = jenkins_job['lastBuild'].get('number', 0)

            db.commit()
            db.refresh(local_job)

            return local_job.to_dict()

        except Exception as e:
            logger.error(f"Failed to sync job from Jenkins: {e}")
            return None

    async def sync_all_jobs(self, db: Session) -> List[Dict]:
        """
        Sync all jobs from Jenkins to local database

        Args:
            db: Database session

        Returns:
            List of synced jobs
        """
        try:
            jenkins_jobs = await self.client.get_jobs()

            synced_jobs = []
            for jenkins_job in jenkins_jobs:
                job_name = jenkins_job.get('name')
                if job_name:
                    job = await self.sync_job_from_jenkins(db, job_name)
                    if job:
                        synced_jobs.append(job)

            logger.info(f"Synced {len(synced_jobs)} jobs from Jenkins")
            return synced_jobs

        except Exception as e:
            logger.error(f"Failed to sync jobs from Jenkins: {e}")
            return []

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics from Jenkins

        Returns:
            Queue statistics dictionary
        """
        try:
            queue = await self.client.get_queue()

            return {
                "queue": {
                    "total_items": len(queue),
                    "items": queue
                },
                "note": "Queue data from real Jenkins instance"
            }

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "queue": {
                    "total_items": 0,
                    "items": []
                },
                "error": str(e)
            }

    # ==================== Helper Methods ====================

    def _generate_job_config_xml(self, job: JenkinsJob) -> str:
        """
        Generate Jenkins job configuration XML

        Args:
            job: Job model

        Returns:
            Configuration XML string
        """
        if job.job_type == JobType.DOCKER:
            return self._generate_docker_job_xml(job)
        elif job.job_type == JobType.PIPELINE:
            return self._generate_pipeline_job_xml(job)
        else:
            return self._generate_freestyle_job_xml(job)

    def _generate_freestyle_job_xml(self, job: JenkinsJob) -> str:
        """Generate freestyle job configuration XML"""
        script = job.script or "echo 'No script provided'"

        return f"""<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>{job.description or ''}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam>
  <disabled>{str(not job.enabled).lower()}</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>{str(job.max_concurrent_builds > 1).lower()}</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>{script}</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers>
    <hudson.plugins.build__timeout.BuildTimeoutWrapper>
      <strategy class="hudson.plugins.build_timeout.impl.AbsoluteTimeOutStrategy">
        <timeoutMinutes>{job.build_timeout // 60}</timeoutMinutes>
      </strategy>
    </hudson.plugins.build__timeout.BuildTimeoutWrapper>
  </buildWrappers>
</project>"""

    def _generate_docker_job_xml(self, job: JenkinsJob) -> str:
        """Generate Docker-based job configuration XML"""
        image = f"{job.docker_registry}/{job.docker_image}:{job.docker_tag}"

        # Build test command
        test_command = self._build_pytest_command(job)

        return f"""<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>{job.description or ''}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam>
  <disabled>{str(not job.enabled).lower()}</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>{str(job.max_concurrent_builds > 1).lower()}</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>
docker run --rm \\
  -v {job.workspace_path}:/workspace \\
  -v {job.config_mount_source}:/config \\
  -e PLATFORM={job.platform or 'ios'} \\
  {image} \\
  {test_command}
      </command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers>
    <hudson.plugins.build__timeout.BuildTimeoutWrapper>
      <strategy class="hudson.plugins.build_timeout.impl.AbsoluteTimeOutStrategy">
        <timeoutMinutes>{job.build_timeout // 60}</timeoutMinutes>
      </strategy>
    </hudson.plugins.build__timeout.BuildTimeoutWrapper>
  </buildWrappers>
</project>"""

    def _generate_pipeline_job_xml(self, job: JenkinsJob) -> str:
        """Generate Pipeline job configuration XML"""
        script = job.script or "echo 'No pipeline script provided'"

        return f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>{job.description or ''}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>{script}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>{str(not job.enabled).lower()}</disabled>
</flow-definition>"""

    def _build_pytest_command(self, job: JenkinsJob) -> str:
        """Build pytest command from job configuration"""
        parts = ["pytest"]

        if job.test_suite:
            parts.append(job.test_suite)

        if job.test_markers:
            parts.append(f"-m '{job.test_markers}'")

        if job.lab_config:
            parts.append(f"--config={job.lab_config}")

        parts.append("--alluredir=/workspace/allure-results")

        return " ".join(parts)


# Global instance
jenkins_service = JenkinsService()
