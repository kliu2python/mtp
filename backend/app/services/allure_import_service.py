"""
Allure Report Import Service
用于将现有的 Jenkins Allure 报告数据导入到 allure_report_summaries 表中
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from app.models.allure_report import AllureReportSummary, AllureTestCase, TestStatusEnum
from app.models.release_test import ReleaseCandidateTest
from app.services.jenkins_service import JenkinsService
from app.services.logger import get_logger

logger = get_logger()


class AllureImportService:
    """Service for importing Allure reports from Jenkins"""

    def __init__(self, db: Session):
        self.db = db
        self.jenkins_service = JenkinsService()

    def import_from_existing_release_tests(
        self,
        platform_filter: Optional[str] = None,
        version_filter: Optional[str] = None,
        project_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        reimport_existing: bool = False,
    ) -> Dict[str, int]:
        """
        Import Allure data from existing ReleaseCandidateTest records

        Args:
            platform_filter: Optional platform filter (e.g., 'android', 'ios')
            version_filter: Optional version filter (e.g., '6.4.0')
            project_filter: Optional project filter (e.g., 'ftm')
            status_filter: Filter by status to fetch from Jenkins (e.g., 'passed', 'failed')
            reimport_existing: If True, re-import even if summary already exists
                               (default: False, skip existing)

        Returns:
            Dict with import statistics
        """
        stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0,
            'failed': 0,
            'test_cases_imported': 0,
        }

        # Build query for existing release tests
        query = self.db.query(ReleaseCandidateTest)

        if platform_filter:
            query = query.filter(ReleaseCandidateTest.platform.like(f'{platform_filter}%'))
        if version_filter:
            query = query.filter(ReleaseCandidateTest.version == version_filter)
        if project_filter:
            query = query.filter(ReleaseCandidateTest.project == project_filter)

        release_tests = query.all()
        stats['total'] = len(release_tests)

        logger.info(f"Found {len(release_tests)} release tests to process")

        for test in release_tests:
            try:
                # Check if already imported
                existing_summary = self.db.query(AllureReportSummary).filter(
                    AllureReportSummary.release_test_id == test.id
                ).first()

                if existing_summary and not reimport_existing:
                    stats['skipped'] += 1
                    logger.info(f"Skipping test {test.id} - already imported")
                    continue

                # Check if test has Jenkins build URL
                if not test.jenkins_build_url:
                    logger.info(f"Skipping test {test.id} - no Jenkins build URL")
                    stats['skipped'] += 1
                    continue

                # Fetch Allure data from Jenkins
                build_url = test.jenkins_build_url.rstrip('/') + '/'
                build_num = test.jenkins_build_number

                logger.info(f"Fetching Allure data for test {test.id} from {build_url}")
                allure_data = self.jenkins_service.fetch_allure_report_data(build_url, build_num)

                if not allure_data or allure_data.get('total', 0) == 0:
                    logger.warning(f"No Allure data found for test {test.id}")
                    stats['skipped'] += 1
                    continue

                # Create summary
                summary = self._create_summary(test, allure_data)
                self.db.add(summary)
                self.db.flush()  # Get the ID

                # Create test cases
                test_cases = allure_data.get('test_cases', [])
                if test_cases:
                    self._create_test_cases(summary.id, test_cases)
                    stats['test_cases_imported'] += len(test_cases)

                stats['imported'] += 1
                logger.info(f"Imported {test.id} - {allure_data.get('total', 0)} test cases")

            except Exception as e:
                logger.error(f"Failed to import test {test.id}: {e}")
                stats['failed'] += 1

        self.db.commit()
        logger.info(f"Import complete: {stats}")
        return stats

    def _create_summary(self, test: ReleaseCandidateTest, allure_data: Dict[str, Any]) -> AllureReportSummary:
        """Create AllureReportSummary from release test and allure data"""
        total = allure_data.get('total', 0)
        passed = allure_data.get('passed_count', 0)
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        summary = AllureReportSummary(
            release_test_id=test.id,
            build_number=test.build_number,
            version=test.version,
            project=test.project,
            platform=test.platform,
            jenkins_job_name=test.jenkins_job_name,
            jenkins_build_number=test.jenkins_build_number,
            jenkins_build_url=test.jenkins_build_url,
            total=total,
            passed_count=passed,
            failed_count=allure_data.get('failed_count', 0),
            skipped_count=allure_data.get('skipped_count', 0),
            broken_count=allure_data.get('broken_count', 0),
            duration_ms=allure_data.get('duration', 0),
            pass_rate=pass_rate,
            report_timestamp=datetime.utcnow(),
            metadata={
                'source': 'jenkins_import',
                'imported_at': datetime.utcnow().isoformat(),
            }
        )
        return summary

    def _create_test_cases(self, summary_id: uuid.UUID, test_cases: List[Dict]) -> List[AllureTestCase]:
        """Create test cases for a summary"""
        created = []
        for tc_data in test_cases:
            status_str = tc_data.get('status', 'passed')
            try:
                status = TestStatusEnum(status_str)
            except ValueError:
                status = TestStatusEnum.PASSED  # default

            tc = AllureTestCase(
                summary_id=summary_id,
                name=tc_data.get('name', ''),
                test_class=tc_data.get('test_class'),
                test_method=tc_data.get('test_method'),
                parent_suite=tc_data.get('parent_suite'),
                suite=tc_data.get('suite'),
                sub_suite=tc_data.get('sub_suite'),
                status=status,
                duration_ms=tc_data.get('duration_ms', 0),
                metadata=tc_data
            )
            self.db.add(tc)
            created.append(tc)

        self.db.commit()
        return created

    def refresh_existing_summaries(self) -> Dict[str, int]:
        """
        Refresh Allure data for summaries that have release_test_id
        but no data yet (or have stale data)

        Returns:
            Dict with refresh statistics
        """
        stats = {'refreshed': 0, 'failed': 0}

        # Find summaries without complete data
        summaries = self.db.query(AllureReportSummary).filter(
            AllureReportSummary.release_test_id.isnot(None),
            AllureReportSummary.total == 0  # No data yet
        ).all()

        for summary in summaries:
            try:
                if not summary.jenkins_build_url:
                    continue

                # Fetch fresh data
                build_url = summary.jenkins_build_url.rstrip('/') + '/'
                allure_data = self.jenkins_service.fetch_allure_report_data(
                    build_url,
                    summary.jenkins_build_number
                )

                if allure_data and allure_data.get('total', 0) > 0:
                    # Update summary
                    summary.total = allure_data.get('total', 0)
                    summary.passed_count = allure_data.get('passed_count', 0)
                    summary.failed_count = allure_data.get('failed_count', 0)
                    summary.skipped_count = allure_data.get('skipped_count', 0)
                    summary.broken_count = allure_data.get('broken_count', 0)
                    summary.duration_ms = allure_data.get('duration', 0)
                    summary.pass_rate = (summary.passed_count / summary.total * 100) if summary.total > 0 else 0

                    # Update test cases
                    test_cases = allure_data.get('test_cases', [])
                    if test_cases:
                        self._create_test_cases(summary.id, test_cases)

                    self.db.commit()
                    stats['refreshed'] += 1
                    logger.info(f"Refreshed summary {summary.id}")

            except Exception as e:
                logger.error(f"Failed to refresh summary {summary.id}: {e}")
                stats['failed'] += 1

        return stats


def import_allure_data(
    db: Session,
    platform_filter: Optional[str] = None,
    version_filter: Optional[str] = None,
    project_filter: Optional[str] = None,
    reimport: bool = False,
) -> Dict[str, int]:
    """
    Convenience function to import Allure data from existing release tests

    Args:
        db: Database session
        platform_filter: Optional platform filter
        version_filter: Optional version filter
        project_filter: Optional project filter
        reimport: If True, re-import existing data

    Returns:
        Import statistics
    """
    service = AllureImportService(db)
    return service.import_from_existing_release_tests(
        platform_filter=platform_filter,
        version_filter=version_filter,
        project_filter=project_filter,
        reimport_existing=reimport,
    )
