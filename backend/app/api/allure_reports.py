"""
Allure Report Statistics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import uuid

from pydantic import BaseModel
from app.core.database import get_db
from app.services.allure_report_service import AllureReportService, get_allure_service
from app.models.allure_report import AllureReportSummary, AllureTestCase
from app.services.logger import get_logger

logger = get_logger()
router = APIRouter()


# ============ Pydantic Schemas ============

class AllureReportSummaryCreate(BaseModel):
    """Payload for creating an Allure report summary"""
    build_number: str
    version: str
    project: str = "ftm"
    platform: str
    jenkins_job_name: Optional[str] = None
    jenkins_build_number: Optional[int] = None
    jenkins_build_url: Optional[str] = None
    release_test_id: Optional[str] = None
    total: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    broken_count: int = 0
    duration_ms: int = 0
    metadata: Optional[dict] = None


class AllureTestCaseCreate(BaseModel):
    """Payload for creating test cases"""
    summary_id: str
    test_cases: List[dict]


# ============ Summary APIs ============

@router.get("/allure-reports", response_model=List[dict])
async def list_allure_reports(
    build_number: Optional[str] = None,
    platform: Optional[str] = None,
    version: Optional[str] = None,
    project: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List Allure report summaries with optional filters

    - **build_number**: Filter by build number
    - **platform**: Filter by platform (android, ios, etc.)
    - **version**: Filter by version
    - **project**: Filter by project
    - **days**: Filter by last N days
    """
    try:
        from sqlalchemy import func
        from datetime import timedelta

        query = db.query(AllureReportSummary)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if build_number:
            query = query.filter(AllureReportSummary.build_number == build_number)
        if platform:
            query = query.filter(AllureReportSummary.platform.like(f'{platform}%'))
        if version:
            query = query.filter(AllureReportSummary.version == version)
        if project:
            query = query.filter(AllureReportSummary.project == project)

        query = query.filter(AllureReportSummary.report_timestamp >= cutoff_date)

        summaries = query.order_by(
            AllureReportSummary.report_timestamp.desc()
        ).offset(skip).limit(limit).all()

        return [s.to_dict() for s in summaries]

    except Exception as e:
        logger.error(f"Error listing allure reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Allure reports")


@router.get("/allure-reports/{summary_id}", response_model=dict)
async def get_allure_report(summary_id: str, db: Session = Depends(get_db)):
    """
    Get a specific Allure report summary by ID
    """
    try:
        summary_uuid = uuid.UUID(summary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid summary ID format")

    summary = db.query(AllureReportSummary).filter(
        AllureReportSummary.id == summary_uuid
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Allure report not found")

    return summary.to_dict()


@router.post("/allure-reports", response_model=dict, status_code=201)
async def create_allure_report(
    report_data: AllureReportSummaryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Allure report summary

    This endpoint stores the summary. Use /allure-reports/{id}/test-cases
    to add test cases.
    """
    try:
        # Handle release_test_id conversion
        release_test_uuid = None
        if report_data.release_test_id:
            try:
                release_test_uuid = uuid.UUID(report_data.release_test_id)
            except (ValueError, TypeError):
                pass

        allure_service = get_allure_service(db)

        summary = allure_service.store_report_summary(
            build_number=report_data.build_number,
            version=report_data.version,
            project=report_data.project,
            platform=report_data.platform,
            total=report_data.total,
            passed_count=report_data.passed_count,
            failed_count=report_data.failed_count,
            skipped_count=report_data.skipped_count,
            broken_count=report_data.broken_count,
            duration_ms=report_data.duration_ms,
            jenkins_job_name=report_data.jenkins_job_name,
            jenkins_build_number=report_data.jenkins_build_number,
            jenkins_build_url=report_data.jenkins_build_url,
            release_test_id=release_test_uuid,
            metadata=report_data.metadata,
        )

        return summary.to_dict()

    except Exception as e:
        logger.error(f"Error creating allure report: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Allure report")


@router.post("/allure-reports/{summary_id}/test-cases", response_model=List[dict])
async def add_test_cases(
    summary_id: str,
    test_data: AllureTestCaseCreate,
    db: Session = Depends(get_db)
):
    """
    Add test cases to an existing summary
    """
    try:
        summary_uuid = uuid.UUID(summary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid summary ID format")

        # Verify summary exists
    summary = db.query(AllureReportSummary).filter(
        AllureReportSummary.id == summary_uuid
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    allure_service = get_allure_service(db)
    cases = allure_service.store_test_cases(summary_uuid, test_data.test_cases)

    return [c.to_dict() for c in cases]


@router.get("/allure-reports/{summary_id}/test-cases", response_model=List[dict])
async def get_test_cases(
    summary_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get test cases for a summary

    - **status**: Optional filter by status (passed, failed, skipped, broken)
    """
    try:
        summary_uuid = uuid.UUID(summary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid summary ID format")

    # Verify summary exists
    summary = db.query(AllureReportSummary).filter(
        AllureReportSummary.id == summary_uuid
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    allure_service = get_allure_service(db)
    cases = allure_service.get_test_cases_for_summary(summary_uuid, status_filter=status)

    return [c.to_dict() for c in cases]


@router.delete("/allure-reports/{summary_id}", status_code=200)
async def delete_allure_report(summary_id: str, db: Session = Depends(get_db)):
    """
    Delete an Allure report summary and all associated test cases
    """
    try:
        summary_uuid = uuid.UUID(summary_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid summary ID format")

    summary = db.query(AllureReportSummary).filter(
        AllureReportSummary.id == summary_uuid
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    db.delete(summary)
    db.commit()

    return {"detail": "Allure report deleted successfully"}


# ============ Statistics & Trend APIs ============

@router.get("/allure-stats/pass-rate-trend", response_model=List[dict])
async def get_pass_rate_trend(
    project: str,
    platform: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get pass rate trend for a project/platform

    - **project**: Project name (ftm, fortiexplorer, fortiedr)
    - **platform**: Platform name
    - **days**: Number of days to look back
    """
    try:
        allure_service = get_allure_service(db)
        trend_data = allure_service.get_pass_rate_trend(project, platform, days)
        return trend_data

    except Exception as e:
        logger.error(f"Error fetching pass rate trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pass rate trend")


@router.get("/allure-stats/top-failures", response_model=List[dict])
async def get_top_failures(
    platform: str,
    limit: int = Query(default=10, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get top failing test cases

    - **platform**: Platform name
    - **limit**: Max number of results (default: 10)
    - **days**: Number of days to look back
    """
    try:
        allure_service = get_allure_service(db)
        failures = allure_service.get_top_failing_tests(platform, limit, days)
        return failures

    except Exception as e:
        logger.error(f"Error fetching top failures: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch top failures")


@router.get("/allure-statistics", response_model=dict)
async def get_allure_statistics(
    project: Optional[str] = None,
    platform: Optional[str] = None,
    version: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get overall statistics for Allure reports

    - **project**: Optional project filter
    - **platform**: Optional platform filter
    - **version**: Optional version filter
    - **days**: Number of days to look back
    """
    try:
        allure_service = get_allure_service(db)
        stats = allure_service.get_statistics(project, platform, version, days)
        return stats

    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


# ============ Build-specific APIs ============

@router.get("/allure-by-build/{build_number}", response_model=List[dict])
async def get_reports_by_build(
    build_number: str,
    platform: Optional[str] = None,
    project: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all Allure reports for a specific build number
    """
    try:
        allure_service = get_allure_service(db)
        summaries = allure_service.get_summaries_by_build(build_number, platform, project)
        return [s.to_dict() for s in summaries]

    except Exception as e:
        logger.error(f"Error fetching reports by build: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reports")


@router.delete("/allure-by-build/{build_number}", status_code=200)
async def delete_reports_by_build(
    build_number: str,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Delete all Allure reports for a specific build number
    """
    try:
        allure_service = get_allure_service(db)
        count = allure_service.delete_summaries_by_build(build_number, platform)
        return {"message": f"Deleted {count} report(s)", "build_number": build_number}

    except Exception as e:
        logger.error(f"Error deleting reports by build: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete reports")


# ============ Test Case APIs ============

@router.get("/allure-test-cases", response_model=List[dict])
async def list_test_cases(
    name_contains: Optional[str] = None,
    suite: Optional[str] = None,
    status: Optional[str] = None,
    summary_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List test cases with optional filters

    - **name_contains**: Filter by test case name (partial match)
    - **suite**: Filter by suite name
    - **status**: Filter by status (passed, failed, skipped, broken)
    - **summary_id**: Filter by summary ID
    """
    try:
        query = db.query(AllureTestCase)

        if name_contains:
            query = query.filter(AllureTestCase.name.like(f'%{name_contains}%'))
        if suite:
            query = query.filter(AllureTestCase.suite == suite)
        if status:
            query = query.filter(AllureTestCase.status == status)
        if summary_id:
            try:
                summary_uuid = uuid.UUID(summary_id)
                query = query.filter(AllureTestCase.summary_id == summary_uuid)
            except ValueError:
                pass  # Invalid UUID, ignore filter

        cases = query.offset(skip).limit(limit).all()
        return [c.to_dict() for c in cases]

    except Exception as e:
        logger.error(f"Error listing test cases: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch test cases")


# ============ Import APIs ============

@router.post("/allure-import/from-jenkins", response_model=dict)
async def import_allure_from_jenkins(
    platform: Optional[str] = None,
    version: Optional[str] = None,
    project: Optional[str] = None,
    reimport: bool = False,
    db: Session = Depends(get_db)
):
    """
    Import Allure reports from Jenkins for existing release tests

    This endpoint fetches Allure data from Jenkins and stores it in the
    allure_report_summaries and allure_test_cases tables.

    - **platform**: Optional platform filter (e.g., 'android', 'ios')
    - **version**: Optional version filter (e.g., '6.4.0')
    - **project**: Optional project filter (e.g., 'ftm')
    - **reimport**: If True, re-import even if already imported
    """
    try:
        from app.services.allure_import_service import AllureImportService

        allure_service = AllureImportService(db)
        stats = allure_service.import_from_existing_release_tests(
            platform_filter=platform,
            version_filter=version,
            project_filter=project,
            reimport_existing=reimport,
        )

        return {
            "success": True,
            "message": "Allure reports imported successfully",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error importing Allure reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import Allure reports: {str(e)}")


@router.get("/allure-import/status", response_model=dict)
async def get_import_status(db: Session = Depends(get_db)):
    """
    Get import status - shows how many release tests have been imported
    """
    try:
        from app.models.release_test import ReleaseCandidateTest
        from app.models.allure_report import AllureReportSummary

        # Total release tests
        total_tests = db.query(ReleaseCandidateTest).count()

        # Tests with Allure summaries
        imported_tests = db.query(ReleaseCandidateTest).join(
            AllureReportSummary,
            ReleaseCandidateTest.id == AllureReportSummary.release_test_id
        ).distinct().count()

        # Total summaries
        total_summaries = db.query(AllureReportSummary).count()

        # Total test cases
        total_test_cases = db.query(AllureTestCase).count()

        return {
            "total_release_tests": total_tests,
            "imported_release_tests": imported_tests,
            "total_summaries": total_summaries,
            "total_test_cases": total_test_cases,
            "import_percentage": round(imported_tests / total_tests * 100, 2) if total_tests > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get import status: {str(e)}")
