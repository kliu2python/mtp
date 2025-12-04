"""
Jenkins API service for triggering and monitoring Jenkins jobs
"""
from typing import Dict, List, Optional, Any

from jenkins import Jenkins
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class JenkinsService:
    """Service for interacting with Jenkins API"""

    def __init__(self):
        """Initialize Jenkins service with credentials from settings"""
        self.jenkins_url = settings.JENKINS_URL
        self.username = settings.JENKINS_USERNAME
        self.api_token = settings.JENKINS_API_TOKEN
        self._jenkins = None

    def configure(self, jenkins_url: str, username: str, api_token: str) -> None:
        """Update Jenkins connection details and reset cached client if needed."""
        if (
            jenkins_url != self.jenkins_url
            or username != self.username
            or api_token != self.api_token
        ):
            self.jenkins_url = jenkins_url
            self.username = username
            self.api_token = api_token
            # Force re-authentication with new credentials
            self._jenkins = None

    def _get_jenkins_instance(self) -> Jenkins:
        """Get or create Jenkins instance"""
        if self._jenkins is None:
            if not self.api_token or not self.username:
                raise ValueError("Jenkins credentials not configured. Please set JENKINS_USERNAME and JENKINS_API_TOKEN")

            try:
                self._jenkins = Jenkins(
                    self.jenkins_url,
                    username=self.username,
                    password=self.api_token,
                    timeout=30
                )
                logger.info(f"Connected to Jenkins at {self.jenkins_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Jenkins: {str(e)}")
                raise

        return self._jenkins

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all available Jenkins jobs

        Returns:
            List of job information dictionaries
        """
        try:
            jenkins = self._get_jenkins_instance()
            jobs = []

            for job_name, job in jenkins.get_jobs():
                jobs.append({
                    "name": job_name,
                    "url": job.baseurl,
                    "enabled": job.is_enabled(),
                    "running": job.is_running() if hasattr(job, 'is_running') else False
                })

            logger.info(f"Retrieved {len(jobs)} jobs from Jenkins")
            return jobs

        except Exception as e:
            logger.error(f"Error getting Jenkins jobs: {str(e)}")
            raise

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job

        Args:
            job_name: Name of the Jenkins job

        Returns:
            Job information dictionary
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)

            # Get last build info if available
            last_build_info = None
            try:
                if job.get_last_build():
                    last_build = job.get_last_build()
                    last_build_info = {
                        "number": last_build.buildno,
                        "status": last_build.get_status(),
                        "timestamp": last_build.get_timestamp().isoformat() if last_build.get_timestamp() else None,
                        "duration": last_build.get_duration().total_seconds() if last_build.get_duration() else None,
                        "url": last_build.baseurl
                    }
            except NoBuildData:
                pass

            return {
                "name": job_name,
                "url": job.baseurl,
                "description": job.get_description(),
                "enabled": job.is_enabled(),
                "running": job.is_running() if hasattr(job, 'is_running') else False,
                "last_build": last_build_info,
                "next_build_number": job.get_next_build_number()
            }

        except JenkinsAPIException as e:
            logger.error(f"Jenkins API error for job {job_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting job info for {job_name}: {str(e)}")
            raise

    def trigger_job(
        self,
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger a Jenkins job with optional parameters

        Args:
            job_name: Name of the Jenkins job to trigger
            parameters: Optional dictionary of job parameters

        Returns:
            Dictionary with job trigger information
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)

            # Check if job is enabled
            if not job.is_enabled():
                raise ValueError(f"Job '{job_name}' is disabled")

            # Trigger the job
            if parameters:
                logger.info(f"Triggering job '{job_name}' with parameters: {parameters}")
                queue_item = job.invoke(build_params=parameters)
            else:
                logger.info(f"Triggering job '{job_name}' without parameters")
                queue_item = job.invoke()

            # Get queue information
            queue_id = queue_item.get_queue_id() if hasattr(queue_item, 'get_queue_id') else None

            return {
                "job_name": job_name,
                "status": "triggered",
                "queue_id": queue_id,
                "message": f"Job '{job_name}' has been triggered successfully",
                "next_build_number": job.get_next_build_number()
            }

        except JenkinsAPIException as e:
            logger.error(f"Jenkins API error triggering job {job_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error triggering job {job_name}: {str(e)}")
            raise

    def get_build_status(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        Get status of a specific build

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            Build status information
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)
            build = job.get_build(build_number)

            return {
                "job_name": job_name,
                "build_number": build_number,
                "status": build.get_status(),
                "result": build.get_result(),
                "running": build.is_running(),
                "timestamp": build.get_timestamp().isoformat() if build.get_timestamp() else None,
                "duration": build.get_duration().total_seconds() if build.get_duration() else None,
                "url": build.baseurl,
                "console_url": f"{build.baseurl}/console"
            }

        except JenkinsAPIException as e:
            logger.error(f"Jenkins API error getting build {build_number} for job {job_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting build status for {job_name} #{build_number}: {str(e)}")
            raise

    def get_build_console_output(self, job_name: str, build_number: int) -> str:
        """
        Get console output of a specific build

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            Console output as string
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)
            build = job.get_build(build_number)

            return build.get_console()

        except JenkinsAPIException as e:
            logger.error(f"Jenkins API error getting console for {job_name} #{build_number}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting console output for {job_name} #{build_number}: {str(e)}")
            raise

    def stop_build(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        Stop a running build

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number to stop

        Returns:
            Stop operation result
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)
            build = job.get_build(build_number)

            if not build.is_running():
                return {
                    "job_name": job_name,
                    "build_number": build_number,
                    "status": "not_running",
                    "message": "Build is not currently running"
                }

            build.stop()
            logger.info(f"Stopped build {build_number} for job {job_name}")

            return {
                "job_name": job_name,
                "build_number": build_number,
                "status": "stopped",
                "message": f"Build #{build_number} has been stopped"
            }

        except JenkinsAPIException as e:
            logger.error(f"Jenkins API error stopping build {build_number} for job {job_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error stopping build {job_name} #{build_number}: {str(e)}")
            raise

    def get_job_parameters(self, job_name: str) -> List[Dict[str, Any]]:
        """
        Get parameters defined for a job

        Args:
            job_name: Name of the Jenkins job

        Returns:
            List of parameter definitions
        """
        try:
            jenkins = self._get_jenkins_instance()
            job = jenkins.get_job(job_name)

            # Get job configuration
            config = job.get_config()
            parameters = []

            # This is a simplified version - you might need to parse XML config
            # to get detailed parameter information
            if job.has_params():
                # Get parameter names from the job
                # Note: This is basic - for full parameter details,
                # you'd need to parse the job's XML configuration
                parameters.append({
                    "message": "This job accepts parameters. Please check Jenkins UI for parameter details.",
                    "has_parameters": True
                })
            else:
                parameters.append({
                    "message": "This job does not accept parameters.",
                    "has_parameters": False
                })

            return parameters

        except Exception as e:
            logger.error(f"Error getting parameters for job {job_name}: {str(e)}")
            raise


# Create singleton instance
jenkins_service = JenkinsService()
