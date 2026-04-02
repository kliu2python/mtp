"""
Allure Report Service
用于存储和查询 Allure 测试报告数据
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import uuid

from app.models.allure_report import AllureReportSummary, AllureTestCase, AllureTestTrend, TestStatusEnum
from app.services.logger import get_logger

logger = get_logger()


class AllureReportService:
    """Service for managing Allure report data"""

    def __init__(self, db: Session):
        self.db = db

    def store_report_summary(
        self,
        build_number: str,
        version: str,
        project: str,
        platform: str,
        total: int,
        passed_count: int,
        failed_count: int,
        skipped_count: int,
        broken_count: int,
        duration_ms: int,
        jenkins_job_name: Optional[str] = None,
        jenkins_build_number: Optional[int] = None,
        jenkins_build_url: Optional[str] = None,
        release_test_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict] = None,
    ) -> AllureReportSummary:
        """
        Store an Allure report summary

        Args:
            build_number: Build number (e.g., "0022")
            version: App version (e.g., "6.4.0")
            project: Project name (ftm, fortiexplorer, fortiedr)
            platform: Platform (android_15, ios_16, etc.)
            total: Total test cases
            passed_count: Passed count
            failed_count: Failed count
            skipped_count: Skipped count
            broken_count: Broken count
            duration_ms: Duration in milliseconds
            jenkins_job_name: Jenkins job name
            jenkins_build_number: Jenkins build number
            jenkins_build_url: Jenkins build URL
            release_test_id: Optional link to release test
            metadata: Optional metadata

        Returns:
            Created AllureReportSummary
        """
        # Calculate pass rate
        pass_rate = (passed_count / total * 100) if total > 0 else 0.0

        summary = AllureReportSummary(
            release_test_id=release_test_id,
            build_number=build_number,
            version=version,
            project=project,
            platform=platform,
            jenkins_job_name=jenkins_job_name,
            jenkins_build_number=jenkins_build_number,
            jenkins_build_url=jenkins_build_url,
            total=total,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            broken_count=broken_count,
            duration_ms=duration_ms,
            pass_rate=pass_rate,
            report_timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )

        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)

        logger.info(
            f"Stored Allure report summary: {build_number}/{platform}, "
            f"total={total}, passed={passed_count}, pass_rate={pass_rate:.2f}%"
        )

        return summary

    def store_test_cases(
        self,
        summary_id: uuid.UUID,
        test_cases: List[Dict[str, Any]]
    ) -> List[AllureTestCase]:
        """
        Store test cases for a summary

        Args:
            summary_id: ID of the summary
            test_cases: List of test case data

        Returns:
            List of created AllureTestCase
        """
        created_cases = []

        for tc_data in test_cases:
            tc = AllureTestCase(
                summary_id=summary_id,
                name=tc_data.get('name', ''),
                test_class=tc_data.get('test_class'),
                test_method=tc_data.get('test_method'),
                parent_suite=tc_data.get('parent_suite'),
                suite=tc_data.get('suite'),
                sub_suite=tc_data.get('sub_suite'),
                status=tc_data.get('status', 'passed'),
                duration_ms=tc_data.get('duration_ms', 0),
                error_message=tc_data.get('error_message'),
                metadata=tc_data.get('metadata', {})
            )
            self.db.add(tc)
            created_cases.append(tc)

        self.db.commit()
        logger.info(f"Stored {len(created_cases)} test cases for summary {summary_id}")

        return created_cases

    def store_full_report(
        self,
        build_number: str,
        version: str,
        project: str,
        platform: str,
        allure_data: Dict[str, Any],
        jenkins_job_name: Optional[str] = None,
        jenkins_build_number: Optional[int] = None,
        jenkins_build_url: Optional[str] = None,
        release_test_id: Optional[uuid.UUID] = None,
    ) -> AllureReportSummary:
        """
        Store complete Allure report (summary + test cases)

        Args:
            build_number: Build number
            version: App version
            project: Project name
            platform: Platform
            allure_data: Allure data dict from JenkinsService
            jenkins_job_name: Jenkins job name
            jenkins_build_number: Jenkins build number
            jenkins_build_url: Jenkins build URL
            release_test_id: Optional link to release test

        Returns:
            Created AllureReportSummary
        """
        # Store summary
        summary = self.store_report_summary(
            build_number=build_number,
            version=version,
            project=project,
            platform=platform,
            total=allure_data.get('total', 0),
            passed_count=allure_data.get('passed_count', 0),
            failed_count=allure_data.get('failed_count', 0),
            skipped_count=allure_data.get('skipped_count', 0),
            broken_count=allure_data.get('broken_count', 0),
            duration_ms=allure_data.get('duration', 0),
            jenkins_job_name=jenkins_job_name,
            jenkins_build_number=jenkins_build_number,
            jenkins_build_url=jenkins_build_url,
            release_test_id=release_test_id,
            metadata={'source': 'allure_zip'}
        )

        # Store test cases
        test_cases = allure_data.get('test_cases', [])
        if test_cases:
            self.store_test_cases(summary.id, test_cases)

        return summary

    def get_summary_by_id(self, summary_id: uuid.UUID) -> Optional[AllureReportSummary]:
        """Get summary by ID"""
        return self.db.query(AllureReportSummary).filter(
            AllureReportSummary.id == summary_id
        ).first()

    def get_summaries_by_build(
        self,
        build_number: str,
        platform: Optional[str] = None,
        project: Optional[str] = None,
    ) -> List[AllureReportSummary]:
        """Get summaries by build number with optional filters"""
        query = self.db.query(AllureReportSummary).filter(
            AllureReportSummary.build_number == build_number
        )

        if platform:
            query = query.filter(AllureReportSummary.platform == platform)
        if project:
            query = query.filter(AllureReportSummary.project == project)

        return query.all()

    def get_test_cases_for_summary(
        self,
        summary_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> List[AllureTestCase]:
        """Get test cases for a summary"""
        query = self.db.query(AllureTestCase).filter(
            AllureTestCase.summary_id == summary_id
        )

        if status_filter:
            query = query.filter(AllureTestCase.status == status_filter)

        return query.all()

    def get_pass_rate_trend(
        self,
        project: str,
        platform: str,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get pass rate trend for a project/platform

        Args:
            project: Project name
            platform: Platform name
            days: Number of days to look back

        Returns:
            List of pass rate data points
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        summaries = self.db.query(AllureReportSummary).filter(
            AllureReportSummary.project == project,
            AllureReportSummary.platform.like(f'{platform}%'),
            AllureReportSummary.report_timestamp >= cutoff_date
        ).order_by(
            AllureReportSummary.report_timestamp
        ).all()

        return [s.to_dict() for s in summaries]

    def get_top_failing_tests(
        self,
        platform: str,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get top failing test cases

        Args:
            platform: Platform name
            limit: Max number of results
            days: Number of days to look back

        Returns:
            List of failing test cases with counts
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        failing_tests = self.db.query(
            AllureTestCase.name,
            func.count().label('fail_count')
        ).join(
            AllureReportSummary,
            AllureTestCase.summary_id == AllureReportSummary.id
        ).filter(
            AllureTestCase.status == TestStatusEnum.FAILED.value,
            AllureReportSummary.platform.like(f'{platform}%'),
            AllureReportSummary.report_timestamp >= cutoff_date
        ).group_by(
            AllureTestCase.name
        ).order_by(
            desc(func.count())
        ).limit(limit).all()

        return [{"name": name, "fail_count": count} for name, count in failing_tests]

    def get_statistics(
        self,
        project: Optional[str] = None,
        platform: Optional[str] = None,
        version: Optional[str] = None,
        days: int = 30,
    ) -> Dict:
        """
        Get overall statistics

        Args:
            project: Optional project filter
            platform: Optional platform filter
            version: Optional version filter
            days: Number of days to look back

        Returns:
            Statistics dict
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(AllureReportSummary)

        if project:
            query = query.filter(AllureReportSummary.project == project)
        if platform:
            query = query.filter(AllureReportSummary.platform.like(f'{platform}%'))
        if version:
            query = query.filter(AllureReportSummary.version == version)

        query = query.filter(AllureReportSummary.report_timestamp >= cutoff_date)

        summaries = query.all()

        if not summaries:
            return {
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "total_broken": 0,
                "average_pass_rate": 0.0,
                "total_builds": 0,
            }

        total_tests = sum(s.total for s in summaries)
        total_passed = sum(s.passed_count for s in summaries)
        total_failed = sum(s.failed_count for s in summaries)
        total_skipped = sum(s.skipped_count for s in summaries)
        total_broken = sum(s.broken_count for s in summaries)
        avg_pass_rate = sum(s.pass_rate for s in summaries) / len(summaries) if summaries else 0.0

        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_broken": total_broken,
            "average_pass_rate": round(avg_pass_rate, 2),
            "total_builds": len(summaries),
            "period_days": days,
        }

    def delete_summaries_by_build(
        self,
        build_number: str,
        platform: Optional[str] = None,
    ) -> int:
        """
        Delete summaries by build number

        Args:
            build_number: Build number to delete
            platform: Optional platform filter

        Returns:
            Number of deleted summaries
        """
        query = self.db.query(AllureReportSummary).filter(
            AllureReportSummary.build_number == build_number
        )

        if platform:
            query = query.filter(AllureReportSummary.platform == platform)

        summaries = query.all()
        count = len(summaries)

        for s in summaries:
            self.db.delete(s)

        self.db.commit()
        logger.info(f"Deleted {count} summaries for build {build_number}")

        return count


# Convenience function to create service instance
def get_allure_service(db: Session) -> AllureReportService:
    """Get AllureReportService instance"""
    return AllureReportService(db)
