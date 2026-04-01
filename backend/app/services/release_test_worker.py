"""
Background worker for polling Jenkins job status and updating release test records.
"""
import threading
import time
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.release_test import ReleaseCandidateTest, TestStatus
from app.services.jenkins_service import JenkinsService, extract_job_path
from app.services.logger import get_logger

logger = get_logger()


class ReleaseTestWorker:
    """Background worker for monitoring Jenkins jobs"""

    def __init__(self):
        self.running = False
        self._threads = {}

    def start_monitoring(self, test_id: str, job_url: str, db: Session):
        """Start monitoring a Jenkins job for a specific test"""
        if test_id in self._threads:
            logger.info(f"Already monitoring test {test_id}")
            return

        thread = threading.Thread(
            target=self._monitor_job,
            args=(test_id, job_url, db),
            daemon=True,
            name=f"monitor-{test_id}"
        )
        self._threads[test_id] = thread
        thread.start()
        logger.info(f"Started monitoring test {test_id}")

    def _monitor_job(self, test_id: str, job_url: str, db: Session):
        """Monitor a Jenkins job and update test status"""
        try:
            jenkins = JenkinsService()
            job_path = extract_job_path(job_url)

            # Poll every 5 seconds
            poll_interval = 5
            max_polls = 3600  # Max 5 hours (3600 * 5s)
            polls = 0

            while polls < max_polls:
                polls += 1

                try:
                    # Get job info
                    job_info = jenkins.server.get_job_info(job_path)
                    last_build = job_info.get('lastBuild')

                    if not last_build:
                        time.sleep(poll_interval)
                        continue

                    build_num = last_build.get('number')
                    build_url = last_build.get('url')
                    is_building = last_build.get('building', False)
                    result = last_build.get('result')

                    # Update test record
                    test = db.query(ReleaseCandidateTest).filter(
                        ReleaseCandidateTest.id == test_id
                    ).first()

                    if not test:
                        logger.info(f"Test {test_id} not found, stopping monitor")
                        return

                    # Update status
                    if is_building:
                        test.status = 'running'
                    elif result:
                        test.status = result.lower()
                        if test.status in ['success', 'passed']:
                            test.status = 'passed'
                        elif test.status in ['failure', 'failed']:
                            test.status = 'failed'

                        # Fetch Allure report on completion
                        if test.jenkins_build_url:
                            allure_url = f"{test.jenkins_build_url.rstrip('/')}allure"
                            allure_data = jenkins.fetch_allure_report_data(allure_url)
                            if allure_data:
                                test.passed_count = allure_data.get('passed_count', 0)
                                test.failed_count = allure_data.get('failed_count', 0)
                                test.skipped_count = allure_data.get('skipped_count', 0)
                                test.duration = allure_data.get('duration', 0)
                                if 'test_cases' not in (test.test_metadata or {}):
                                    test.test_metadata = test.test_metadata or {}
                                    test.test_metadata['test_cases'] = allure_data.get('test_cases', [])

                    test.jenkins_build_number = build_num
                    test.jenkins_build_url = build_url
                    test.updated_at = datetime.utcnow()
                    db.commit()

                    # Stop monitoring if complete
                    if result and result in ['SUCCESS', 'FAILURE', 'UNSTABLE']:
                        logger.info(f"Job {test_id} completed with status {test.status}")
                        return

                except Exception as e:
                    logger.warning(f"Error monitoring test {test_id}: {e}")
                    time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Monitor thread failed for test {test_id}: {e}")
        finally:
            # Clean up thread reference
            if test_id in self._threads:
                del self._threads[test_id]

    def get_running_monitors(self) -> List[str]:
        """Get list of currently running monitor thread IDs"""
        return list(self._threads.keys())


# Global worker instance
release_test_worker = ReleaseTestWorker()
