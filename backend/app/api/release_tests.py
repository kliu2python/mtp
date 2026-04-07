"""
Release Candidate Test API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import uuid
import os
import threading

from app.core.database import get_db
from app.models.release_test import ReleaseCandidateTest, TestStatus, ReleaseTestCycle
from app.models.admin_config import AdminConfig
from app.services.logger import get_logger
from app.services.jenkins_service import JenkinsService

logger = get_logger()
router = APIRouter()


class VersionBuildNumber(BaseModel):
    """Build number range for a specific version"""
    version: str  # e.g., "6.4.0"
    platform: str  # "android" or "ios"
    min_build_number: str  # e.g., "0018"
    max_build_number: str  # e.g., "0022"


class ReleaseTestConfig(BaseModel):
    """Payload for release test configuration"""
    versions: List[str] = []
    build_numbers: List[str] = []
    disabled_versions: List[str] = []
    version_build_numbers: List[VersionBuildNumber] = []


class ReleaseTestCycleCreate(BaseModel):
    """Payload for creating a release test cycle"""
    version: str
    project: str = "ftm"
    platform: str = "all"
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ReleaseTestCycleUpdate(BaseModel):
    """Payload for updating a release test cycle"""
    version: Optional[str] = None
    project: Optional[str] = None
    platform: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


class ReleaseTestCreate(BaseModel):
    """Payload for creating a release candidate test entry"""
    cycle_id: Optional[str] = None  # Optional: link to a cycle
    build_number: str
    platform: str
    version: str
    project: str = "ftm"
    test_suite: str
    test_type: str
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None
    passed_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    jenkins_job_name: Optional[str] = None
    jenkins_build_number: Optional[int] = None
    jenkins_build_url: Optional[str] = None
    apk_file_id: Optional[str] = None
    test_metadata: Optional[dict] = None
    notes: Optional[str] = None


class ReleaseTestUpdate(BaseModel):
    """Payload for updating a release candidate test entry"""
    build_number: Optional[str] = None
    platform: Optional[str] = None
    version: Optional[str] = None
    project: Optional[str] = None
    test_suite: Optional[str] = None
    test_type: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None
    passed_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    jenkins_job_name: Optional[str] = None
    jenkins_build_number: Optional[int] = None
    jenkins_build_url: Optional[str] = None
    apk_file_id: Optional[str] = None
    test_metadata: Optional[dict] = None
    notes: Optional[str] = None


class ReleaseTestResponse(BaseModel):
    """Response model for release candidate test"""
    id: str
    build_number: str
    platform: str
    version: str
    project: str
    test_suite: str
    test_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: int
    passed_count: int
    failed_count: int
    skipped_count: int
    jenkins_job_name: Optional[str] = None
    jenkins_build_number: Optional[int] = None
    jenkins_build_url: Optional[str] = None
    apk_file_id: Optional[str] = None
    test_metadata: Optional[dict] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


@router.get("/release-tests", response_model=List[dict])
async def list_release_tests(
    platform: Optional[str] = None,
    status: Optional[str] = None,
    build_number: Optional[str] = None,
    version: Optional[str] = None,
    project: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all release candidate tests with optional filters"""
    try:
        # Manually specify columns to avoid the missing test_cases column
        # We need to handle this carefully to avoid SQL errors
        query = db.query(ReleaseCandidateTest)

        if platform:
            # Use LIKE for platform to match android_15, android_14, etc. when platform=android
            query = query.filter(ReleaseCandidateTest.platform.like(f'{platform}%'))
        if status:
            query = query.filter(ReleaseCandidateTest.status == status)
        if build_number:
            query = query.filter(
                ReleaseCandidateTest.build_number == build_number)
        if version:
            query = query.filter(ReleaseCandidateTest.version == version)
        if project:
            query = query.filter(ReleaseCandidateTest.project == project)

        # Order by build number for consistent sorting
        query = query.order_by(ReleaseCandidateTest.build_number)

        tests = query.offset(skip).limit(limit).all()

        return [test.to_dict() for test in tests]
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error fetching release tests: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch release tests")


@router.get("/release-tests/{test_id}", response_model=dict)
async def get_release_test(test_id: str, db: Session = Depends(get_db)):
    """Get release candidate test by ID"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    return test.to_dict()


@router.post("/release-tests", response_model=dict, status_code=201)
async def create_release_test(test_data: ReleaseTestCreate, db: Session = Depends(get_db)):
    """Create a new release candidate test entry"""
    # Handle numeric fields with safe conversion
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    duration = 0
    jenkins_build_number = None

    if test_data.passed_count is not None:
        try:
            passed_count = int(test_data.passed_count)
        except (ValueError, TypeError):
            pass

    if test_data.failed_count is not None:
        try:
            failed_count = int(test_data.failed_count)
        except (ValueError, TypeError):
            pass

    if test_data.skipped_count is not None:
        try:
            skipped_count = int(test_data.skipped_count)
        except (ValueError, TypeError):
            pass

    if test_data.duration is not None:
        try:
            duration = int(test_data.duration)
        except (ValueError, TypeError):
            pass

    if test_data.jenkins_build_number is not None:
        try:
            jenkins_build_number = int(test_data.jenkins_build_number)
        except (ValueError, TypeError):
            pass

    # Handle APK file ID conversion
    apk_file_id = None
    if test_data.apk_file_id:
        try:
            apk_file_id = uuid.UUID(test_data.apk_file_id)
        except (ValueError, TypeError):
            pass

    # Handle cycle_id if provided
    cycle_uuid = None
    if test_data.cycle_id:
        try:
            cycle_uuid = uuid.UUID(test_data.cycle_id)
        except (ValueError, TypeError):
            pass

    test = ReleaseCandidateTest(
        cycle_id=cycle_uuid,
        build_number=test_data.build_number,
        platform=test_data.platform,
        version=test_data.version,
        project=test_data.project,
        test_suite=test_data.test_suite,
        test_type=test_data.test_type,
        status=test_data.status if test_data.status else TestStatus.PENDING,
        started_at=test_data.started_at,
        completed_at=test_data.completed_at,
        apk_file_id=apk_file_id,
        test_metadata=test_data.test_metadata or {},
        notes=test_data.notes,
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        duration=duration,
        jenkins_job_name=test_data.jenkins_job_name,
        jenkins_build_number=jenkins_build_number,
        jenkins_build_url=test_data.jenkins_build_url
    )

    db.add(test)
    db.commit()
    db.refresh(test)

    return test.to_dict()


# ============== Release Test Cycle APIs ==============

@router.get("/release-cycles", response_model=List[dict])
async def list_release_cycles(
    project: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all release test cycles with optional filtering"""
    query = db.query(ReleaseTestCycle)

    if project:
        query = query.filter(ReleaseTestCycle.project == project)
    if platform:
        query = query.filter(ReleaseTestCycle.platform == platform)
    if status:
        query = query.filter(ReleaseTestCycle.status == status)

    cycles = query.order_by(ReleaseTestCycle.created_at.desc()).all()

    # Update cycle status based on latest test results
    for cycle in cycles:
        tests = db.query(ReleaseCandidateTest).filter(
            ReleaseCandidateTest.version == cycle.version,
            ReleaseCandidateTest.project == cycle.project
        ).all()
        _update_cycle_status_from_tests(cycle, tests, db)
        db.refresh(cycle)  # Refresh cycle to get latest status

    return [cycle.to_dict() for cycle in cycles]


@router.post("/release-cycles", response_model=dict)
async def create_release_cycle(cycle_data: ReleaseTestCycleCreate, db: Session = Depends(get_db)):
    """Create a new release test cycle"""
    # Check if a cycle with the same version, platform, and project already exists
    existing_cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.version == cycle_data.version,
        ReleaseTestCycle.platform == cycle_data.platform,
        ReleaseTestCycle.project == cycle_data.project
    ).first()

    if existing_cycle:
        raise HTTPException(
            status_code=400,
            detail=f"A cycle with version '{cycle_data.version}', platform '{cycle_data.platform}', and project '{cycle_data.project}' already exists."
        )

    cycle = ReleaseTestCycle(
        version=cycle_data.version,
        project=cycle_data.project,
        platform=cycle_data.platform,
        description=cycle_data.description,
        cycle_metadata=cycle_data.metadata or {}
    )

    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    return cycle.to_dict()


@router.get("/release-cycles/{cycle_id}", response_model=dict)
async def get_release_cycle(cycle_id: str, db: Session = Depends(get_db)):
    """Get a specific release test cycle by ID"""
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle ID format")

    cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.id == cycle_uuid
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Release cycle not found")

    return cycle.to_dict()


@router.put("/release-cycles/{cycle_id}", response_model=dict)
async def update_release_cycle(cycle_id: str, cycle_data: ReleaseTestCycleUpdate, db: Session = Depends(get_db)):
    """Update a release test cycle"""
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle ID format")

    cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.id == cycle_uuid
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Release cycle not found")

    # Update fields
    update_data = cycle_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cycle, key, value)

    db.commit()
    db.refresh(cycle)

    return cycle.to_dict()


@router.delete("/release-cycles/{cycle_id}", status_code=204)
async def delete_release_cycle(cycle_id: str, db: Session = Depends(get_db)):
    """
    Delete a release test cycle and all associated test executions.
    Since test records are created without cycle_id, we delete by matching
    version + project + platform pattern.
    """
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle ID format")

    cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.id == cycle_uuid
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Release cycle not found")

    # Delete associated test records by version + project
    # Since cycle_id is not set when creating tests, we match by version and project
    deleted_count = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.version == cycle.version,
        ReleaseCandidateTest.project == cycle.project
    ).delete(synchronize_session=False)

    logger.info(f"Deleted {deleted_count} test records for cycle {cycle.version} ({cycle.project})")

    # Delete the cycle
    db.delete(cycle)
    db.commit()

    return {"detail": f"Release cycle and {deleted_count} associated test(s) deleted successfully"}


@router.get("/release-cycles/{cycle_id}/tests", response_model=List[dict])
async def list_cycle_tests(cycle_id: str, db: Session = Depends(get_db)):
    """
    List all test executions for a specific cycle.
    Since test records are created without cycle_id, we fetch by version + project + platform.
    Only returns sub-task tests (not parent pipeline tests) to avoid double counting.
    Also updates cycle status based on latest test results.
    """
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle ID format")

    cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.id == cycle_uuid
    ).first()

    if not cycle:
        raise HTTPException(status_code=404, detail="Release cycle not found")

    # Fetch tests by version, project, and platform (since cycle_id is not set when creating tests)
    all_tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.version == cycle.version,
        ReleaseCandidateTest.project == cycle.project,
        ReleaseCandidateTest.platform == cycle.platform
    ).all()

    # Update cycle status based on current test results
    _update_cycle_status_from_tests(cycle, all_tests, db)

    # Filter to only sub-tasks (tests with is_subtask metadata or platform contains token patterns)
    subtask_tests = [
        test for test in all_tests
        if (test.test_metadata and test.test_metadata.get('is_subtask')) or
           any(suffix in test.platform for suffix in ['_fac_token', '_fgt_token', '_ftc_token_on_fac', '_ftc_token_on_fgt'])
    ]

    # If we found subtasks, return only subtasks; otherwise return all tests (for manual uploads)
    tests = subtask_tests if subtask_tests else all_tests

    return [test.to_dict() for test in tests]


# ============== Original Release Test APIs ==============

@router.put("/release-tests/{test_id}", response_model=dict)
async def update_release_test(test_id: str, test_data: ReleaseTestUpdate, db: Session = Depends(get_db)):
    """Update release candidate test entry"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Update fields if provided
    update_data = test_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        # Handle special cases
        if key == "apk_file_id" and value is not None:
            try:
                setattr(test, key, uuid.UUID(value))
            except (ValueError, TypeError) as e:
                # If it's already a UUID or invalid, skip conversion
                setattr(test, key, value)
        elif key == "test_metadata":
            # Map test_metadata to metadata column
            setattr(test, "metadata", value)
        elif key in ["passed_count", "failed_count", "skipped_count", "duration", "jenkins_build_number"]:
            # Convert numeric fields to integers
            try:
                setattr(test, key, int(value) if value is not None else 0)
            except (ValueError, TypeError):
                setattr(test, key, 0)
        else:
            setattr(test, key, value)

    db.commit()
    db.refresh(test)

    return test.to_dict()


@router.delete("/release-tests/{test_id}", status_code=204)
async def delete_release_test(test_id: str, db: Session = Depends(get_db)):
    """Delete release candidate test entry"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    db.delete(test)
    db.commit()

    return {"detail": "Release test deleted successfully"}


@router.delete("/release-tests/batch", status_code=200)
async def delete_release_tests_batch(
    platform: str,
    version: str,
    project: str,
    db: Session = Depends(get_db)
):
    """
    Delete all release test entries for a specific platform + version + project combination.
    This includes both parent tests and sub-task tests.
    Uses LIKE matching to handle sub-tasks (e.g., android_14 matches android_14_fac_token).
    """
    # Extract base platform (e.g., android_14 from android_14_fac_token)
    # This handles cases where the platform includes subtask suffix
    base_platform = platform
    for suffix in ['_fac_token', '_fgt_token', '_ftc_token_on_fac', '_ftc_token_on_fgt']:
        if platform.endswith(suffix):
            base_platform = platform[:-len(suffix)]
            break

    # Get all tests where platform starts with the base platform
    # This will match both parent (android_14) and subtasks (android_14_fac_token, etc.)
    # Use like with % wildcard to match all subtasks
    tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.platform.like(f'{base_platform}%'),
        ReleaseCandidateTest.version == version,
        ReleaseCandidateTest.project == project
    ).all()

    if not tests:
        raise HTTPException(
            status_code=404,
            detail=f"No tests found for platform={platform}, version={version}, project={project}"
        )

    # Delete all matching tests
    deleted_count = 0
    for test in tests:
        db.delete(test)
        deleted_count += 1

    db.commit()

    return {
        "message": f"Successfully deleted {deleted_count} test(s)",
        "deleted_count": deleted_count,
        "platform": platform,
        "version": version,
        "project": project
    }


@router.get("/release-tests/{test_id}/test-cases", response_model=dict)
async def get_release_test_cases(test_id: str, db: Session = Depends(get_db)):
    """Get test cases for a specific release test"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    test_cases = []
    if test.test_metadata and 'test_cases' in test.test_metadata:
        test_cases = test.test_metadata['test_cases']

    return {"test_cases": test_cases}


@router.get("/release-tests/{test_id}/mantis-issues", response_model=dict)
async def get_release_test_mantis_issues(test_id: str, db: Session = Depends(get_db)):
    """Get Mantis issues for a specific release test"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Import Mantis service
    from app.services.mantis_service import mantis_service

    mantis_issues = []
    if test.test_metadata and 'mantis_issues' in test.test_metadata:
        mantis_issue_ids = test.test_metadata['mantis_issues']
        if isinstance(mantis_issue_ids, list):
            for issue_id in mantis_issue_ids:
                try:
                    issue = mantis_service.get_issue(issue_id)
                    if issue:
                        mantis_issues.append(issue)
                except Exception:
                    # Skip issues that can't be fetched
                    continue

    return {"mantis_issues": mantis_issues}


@router.post("/release-tests/populate-from-allure", response_model=dict)
async def populate_release_test_from_allure(
    test_id: str,
    build_url: str,  # Jenkins build URL (e.g., http://.../job/.../64/)
    build_number: Optional[int] = None,  # Optional build number
    db: Session = Depends(get_db)
):
    """Automatically populate release test data from Allure report URL"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    # Get the test record
    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Import Jenkins service to use the Allure fetching function
    from app.services.jenkins_service import JenkinsService

    # Create a Jenkins service instance (using default settings)
    jenkins_service = JenkinsService()

    # Fetch Allure report data (expects build URL, not allure URL)
    allure_data = jenkins_service.fetch_allure_report_data(build_url, build_number)
    if not allure_data:
        raise HTTPException(
            status_code=400, detail="Failed to fetch Allure report data")

    # Update the test record with Allure data
    test.passed_count = allure_data.get('passed_count', 0)
    test.failed_count = allure_data.get('failed_count', 0)
    test.skipped_count = allure_data.get('skipped_count', 0)
    test.duration = allure_data.get('duration', 0)
    test.jenkins_build_url = allure_url
    # Set status based on results (broken counts as failed)
    if test.failed_count > 0 or test.broken_count > 0:
        from app.models.release_test import TestStatus
        test.status = TestStatus.FAILED
    elif test.passed_count > 0:
        from app.models.release_test import TestStatus
        test.status = TestStatus.PASSED
    else:
        from app.models.release_test import TestStatus
        test.status = TestStatus.SKIPPED

    db.commit()
    db.refresh(test)

    return {"message": "Release test populated successfully", "test": test.to_dict()}


@router.post("/release-tests/populate-from-zip", response_model=dict)
async def populate_release_test_from_zip(
    test_id: str,
    zip_file_path: str,
    db: Session = Depends(get_db)
):
    """Automatically populate release test data from zip file containing test results"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    # Get the test record
    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Import Jenkins service to use the zip extraction function
    from app.services.jenkins_service import JenkinsService

    # Create a Jenkins service instance (using default settings)
    jenkins_service = JenkinsService()

    # Extract results from zip file
    results_data = jenkins_service.extract_results_from_zip(zip_file_path)
    if not results_data:
        raise HTTPException(
            status_code=400, detail="Failed to extract results from zip file")

    # Update the test record with extracted data
    test.passed_count = results_data.get('passed_count', 0)
    test.failed_count = results_data.get('failed_count', 0)
    test.skipped_count = results_data.get('skipped_count', 0)
    test.duration = results_data.get('duration', 0)

    # Store test cases in metadata instead of a separate column
    # Create a new dict to ensure SQLAlchemy detects the change
    new_metadata = dict(test.test_metadata) if test.test_metadata else {}
    new_metadata['test_cases'] = results_data.get('test_cases', [])
    test.test_metadata = new_metadata

    # Set status based on results (broken counts as failed)
    if test.failed_count > 0 or test.broken_count > 0:
        from app.models.release_test import TestStatus
        test.status = TestStatus.FAILED
    elif test.passed_count > 0:
        from app.models.release_test import TestStatus
        test.status = TestStatus.PASSED
    else:
        from app.models.release_test import TestStatus
        test.status = TestStatus.SKIPPED

    db.commit()
    db.refresh(test)

    return {"message": "Release test populated successfully", "test": test.to_dict()}


@router.post("/release-tests/{test_id}/upload-zip", response_model=dict)
async def upload_and_populate_from_zip(
    test_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a ZIP file and populate release test data from it"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    # Get the test record
    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400, detail="Only ZIP files are allowed")

    # Save uploaded file temporarily
    temp_dir = "/tmp/test_results"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")

    try:
        # Save the uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Import Jenkins service to use the zip extraction function
        from app.services.jenkins_service import JenkinsService

        # Create a Jenkins service instance (using default settings)
        jenkins_service = JenkinsService()

        # Extract results from zip file
        results_data = jenkins_service.extract_results_from_zip(temp_file_path)
        if not results_data:
            raise HTTPException(
                status_code=400, detail="Failed to extract results from zip file")

        # Update the test record with extracted data
        test.passed_count = results_data.get('passed_count', 0)
        test.failed_count = results_data.get('failed_count', 0)
        test.skipped_count = results_data.get('skipped_count', 0)
        test.duration = results_data.get('duration', 0)

        # Store test cases in metadata instead of a separate column
        # Create a new dict to ensure SQLAlchemy detects the change
        new_metadata = dict(test.test_metadata) if test.test_metadata else {}
        new_metadata['test_cases'] = results_data.get('test_cases', [])
        test.test_metadata = new_metadata

        # Set status based on results (broken counts as failed)
        if test.failed_count > 0 or test.broken_count > 0:
            from app.models.release_test import TestStatus
            test.status = TestStatus.FAILED
        elif test.passed_count > 0:
            from app.models.release_test import TestStatus
            test.status = TestStatus.PASSED
        else:
            from app.models.release_test import TestStatus
            test.status = TestStatus.SKIPPED

        db.commit()
        db.refresh(test)

        return {"message": "Release test populated successfully", "test": test.to_dict()}

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/release-tests/{test_id}/start-jenkins-test", response_model=dict)
async def start_jenkins_test(
    test_id: str,
    build_number: str,
    dns: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Start a Jenkins test for the release test"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    # Get the test record
    test = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Import Jenkins service
    from app.services.jenkins_service import JenkinsService, extract_job_path
    from jenkins import JenkinsException

    jenkins_service = JenkinsService()

    # Prepare parameters based on platform
    platform = test.platform
    if platform == "android":
        # Android parameters
        params = {
            "ftm_apk_version": f"ftma_v6.4.0.{build_number}.apk",
            "mobile_emulator": "google_api",
            "RUN_STAGE": "ALL"
        }
        if dns:
            params["fgt_ftm_dns"] = dns
        job_url = "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_15/job/android_15_auto/"
    elif platform == "ios":
        # iOS parameters
        params = {
            "ftm_ipa_version": "test"
        }
        if dns:
            params["fgt_ftm_dns"] = dns
        job_url = "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/iPhone8-ios16/job/ios16_auto_test/build?delay=0sec"
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported platform: {platform}")

    try:
        # Trigger Jenkins job
        job_path = extract_job_path(job_url)
        jenkins_service._build_job(job_path, params)

        # Update test record with Jenkins info
        test.jenkins_job_name = job_path
        test.status = "running"
        test.started_at = datetime.utcnow()
        test.test_metadata = test.test_metadata or {}
        test.test_metadata["jenkins_params"] = params
        db.commit()
        db.refresh(test)

        return {
            "message": "Jenkins test started successfully",
            "test": test.to_dict(),
            "job_url": job_url,
            "parameters": params
        }
    except JenkinsException as e:
        logger.error(f"Jenkins error: {e}")
        raise HTTPException(status_code=500, detail=f"Jenkins error: {str(e)}")
    except Exception as e:
        logger.error(f"Error starting Jenkins test: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting Jenkins test: {str(e)}")


@router.post("/release-tests/trigger-jenkins", response_model=dict)
async def trigger_jenkins_release_test(
    build_number: str,
    dns: Optional[str] = None,
    platform: Optional[str] = None,
    version: Optional[str] = None,
    project: Optional[str] = "ftm",
    db: Session = Depends(get_db)
):
    """
    Trigger Jenkins jobs for release test directly.
    This creates a test record and triggers both Android and iOS Jenkins jobs.
    Uses default payloads from admin_configs table.
    """
    from app.services.jenkins_service import JenkinsService, extract_job_path
    from jenkins import JenkinsException
    import threading
    from time import sleep

    jenkins_service = JenkinsService()
    results = {"android": None, "ios": None}

    # Build job URLs
    android_job_url = "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_15/job/android_15_auto/"
    ios_job_url = "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/iPhone8-ios16/job/ios16_auto_test/build?delay=0sec"

    # Fetch default payloads from admin_configs table
    android_default_payload = {}
    ios_default_payload = {}
    try:
        android_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "android_default_payload"
        ).first()
        if android_config and android_config.config_value:
            android_default_payload = android_config.config_value

        ios_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "ios_default_payload"
        ).first()
        if ios_config and ios_config.config_value:
            ios_default_payload = ios_config.config_value
    except Exception as e:
        logger.warning(f"Failed to fetch default payloads, using defaults: {e}")

    def trigger_android_job():
        try:
            # Start with default payload from admin_configs
            params = android_default_payload.copy() if android_default_payload else {}

            # Always generate ftm_apk_version dynamically based on build_number
            params["ftm_apk_version"] = f"ftma_v6.4.0.{build_number}.apk"

            # Set defaults if not in config
            if "docker_tag" not in params:
                params["docker_tag"] = "debug_ftm_auto_latest"
            if "mobile_emulator" not in params:
                params["mobile_emulator"] = "google_api"
            if "RUN_STAGE" not in params:
                params["RUN_STAGE"] = "ALL"

            # Override dns if provided
            if dns:
                params["fgt_ftm_dns"] = dns

            job_path = extract_job_path(android_job_url)
            jenkins_service._build_job(job_path, params)

            # Create test record for Android
            android_test = ReleaseCandidateTest(
                build_number=build_number,
                platform="android",
                version=version or "auto",
                project=project or "ftm",
                test_suite="release",
                test_type="full",
                status="running",
                started_at=datetime.utcnow(),
                jenkins_job_name=job_path,
                jenkins_build_url=android_job_url,
                test_metadata={"jenkins_params": params}
            )
            db.add(android_test)
            db.commit()
            db.refresh(android_test)

            results["android"] = {
                "status": "success",
                "test_id": str(android_test.id),
                "job_url": android_job_url,
                "parameters": params
            }
        except Exception as e:
            logger.error(f"Android Jenkins error: {e}")
            results["android"] = {"status": "error", "error": str(e)}

    def trigger_ios_job():
        try:
            # Start with default payload from admin_configs
            params = ios_default_payload.copy() if ios_default_payload else {}

            # Always generate ftm_ipa_version dynamically based on build_number
            params["ftm_ipa_version"] = f"ftm_i_v6.4.0.{build_number}.ipa"

            # Set defaults if not in config
            if "docker_tag" not in params:
                params["docker_tag"] = "debug_ftm_auto_latest"
            if "RUN_STAGE" not in params:
                params["RUN_STAGE"] = "ALL"

            # Override dns if provided
            if dns:
                params["fgt_ftm_dns"] = dns

            job_path = extract_job_path(ios_job_url)
            jenkins_service._build_job(job_path, params)

            # Create test record for iOS
            ios_test = ReleaseCandidateTest(
                build_number=build_number,
                platform="ios",
                version=version or "auto",
                project=project or "ftm",
                test_suite="release",
                test_type="full",
                status="running",
                started_at=datetime.utcnow(),
                jenkins_job_name=job_path,
                jenkins_build_url=ios_job_url,
                test_metadata={"jenkins_params": params}
            )
            db.add(ios_test)
            db.commit()
            db.refresh(ios_test)

            results["ios"] = {
                "status": "success",
                "test_id": str(ios_test.id),
                "job_url": ios_job_url,
                "parameters": params
            }
        except Exception as e:
            logger.error(f"iOS Jenkins error: {e}")
            results["ios"] = {"status": "error", "error": str(e)}

    # Trigger both jobs in parallel threads
    threads = []
    if platform is None or platform == "android":
        t = threading.Thread(target=trigger_android_job)
        t.start()
        threads.append(t)

    if platform is None or platform == "ios":
        t = threading.Thread(target=trigger_ios_job)
        t.start()
        threads.append(t)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    return {
        "message": "Jenkins tests triggered",
        "results": results,
        "build_number": build_number
    }


@router.post("/release-tests/trigger-pipeline", response_model=dict)
async def trigger_pipeline_release_test(
    build_number: str,
    dns: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    version: Optional[str] = None,
    project: Optional[str] = "ftm",
    pipeline_name: Optional[str] = "release_pipeline",
    db: Session = Depends(get_db)
):
    """
    Trigger a pipeline of Jenkins jobs for release testing.
    A pipeline contains 4 jobs:
    1. android_15_auto
    2. ios16_auto_test
    3. android_14_auto (if exists)
    4. ios15_auto_test (if exists)

    After all jobs complete, fetch Allure reports and aggregate results.
    """
    from app.services.jenkins_service import jenkins_service, extract_job_path
    from jenkins import JenkinsException
    import threading
    from time import sleep
    import requests

    results = {"android": None, "ios": None, "android_14": None, "ios_15": None}
    job_urls = {
        "android": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_15/job/android_15_auto/",
        "ios": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/iPhone8-ios16/job/ios16_auto_test/build?delay=0sec",
        "android_14": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_14/job/android_14_auto/",
        "ios_15": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/iPhone8-ios15/job/ios15_auto_test/"
    }

    # Fetch default payloads
    android_default_payload = {}
    ios_default_payload = {}
    try:
        android_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "android_default_payload").first()
        if android_config and android_config.config_value:
            android_default_payload = android_config.config_value
        ios_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "ios_default_payload").first()
        if ios_config and ios_config.config_value:
            ios_default_payload = ios_config.config_value
    except Exception as e:
        logger.warning(f"Failed to fetch default payloads: {e}")

    triggered_jobs = []

    def trigger_job(platform_key, job_url):
        try:
            is_android = "android" in platform_key
            is_ios = "ios" in platform_key

            # Use default payload from admin_configs
            if is_android:
                params = android_default_payload.copy() if android_default_payload else {}
                params["ftm_apk_version"] = f"ftma_v6.4.0.{build_number}.apk"
                if "docker_tag" not in params:
                    params["docker_tag"] = "debug_ftm_auto_latest"
                if "mobile_emulator" not in params:
                    params["mobile_emulator"] = "google_api"
                if "RUN_STAGE" not in params:
                    params["RUN_STAGE"] = "ALL"
            else:
                params = ios_default_payload.copy() if ios_default_payload else {}
                params["ftm_ipa_version"] = f"ftm_i_v6.4.0.{build_number}.ipa"
                if "docker_tag" not in params:
                    params["docker_tag"] = "debug_ftm_auto_latest"
                if "RUN_STAGE" not in params:
                    params["RUN_STAGE"] = "ALL"

            if dns:
                params["fgt_ftm_dns"] = dns

            job_path = extract_job_path(job_url)
            jenkins_service._build_job(job_path, params)

            # Create test record
            test = ReleaseCandidateTest(
                build_number=build_number,
                platform=platform_key,
                version=version or "auto",
                project=project or "ftm",
                test_suite="release",
                test_type="full",
                status="running",
                started_at=datetime.utcnow(),
                jenkins_job_name=job_path,
                jenkins_build_url=job_url,
                test_metadata={"jenkins_params": params, "pipeline_name": pipeline_name}
            )
            db.add(test)
            db.commit()
            db.refresh(test)

            results[platform_key] = {
                "status": "success",
                "test_id": str(test.id),
                "job_url": job_url,
                "parameters": params,
                "build_number": test.id
            }
            triggered_jobs.append({
                "platform": platform_key,
                "job_url": job_url,
                "test_id": str(test.id)
            })

            logger.info(f"Triggered {platform_key} with params: {params}")

        except Exception as e:
            logger.error(f"Error triggering {platform_key}: {e}")
            results[platform_key] = {"status": "error", "error": str(e)}

    # Trigger jobs in parallel
    threads = []
    platforms_to_run = platforms if platforms else ["android", "ios", "android_14", "ios_15"]

    for plat in platforms_to_run:
        if plat in job_urls:
            t = threading.Thread(target=trigger_job, args=(plat, job_urls[plat]))
            t.start()
            threads.append(t)

    # Wait for all to complete
    for t in threads:
        t.join()

    return {
        "message": f"Pipeline triggered with {len(triggered_jobs)} jobs",
        "pipeline_name": pipeline_name,
        "build_number": build_number,
        "triggered_jobs": triggered_jobs,
        "results": results
    }


@router.get("/release-tests/pipeline-status/{build_number}")
async def get_pipeline_status(
    build_number: str,
    db: Session = Depends(get_db)
):
    """
    Get status of all jobs in a pipeline for a given build number.
    If all jobs are complete, fetch Allure reports and aggregate results.
    """
    from app.services.jenkins_service import jenkins_service

    # Get all test records for this build number
    tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number
    ).all()

    if not tests:
        raise HTTPException(status_code=404, detail="No tests found for this build number")

    pipeline_status = {
        "build_number": build_number,
        "jobs": [],
        "all_complete": True,
        "all_success": True,
        "aggregate_results": None
    }

    for test in tests:
        job_status = {
            "test_id": str(test.id),
            "platform": test.platform,
            "status": test.status,
            "jenkins_build_url": test.jenkins_build_url,
            "allure_url": None,
            "results": None
        }

        # Check if test is complete
        if test.status in ["running", "pending"]:
            pipeline_status["all_complete"] = False

        # Try to fetch Allure report if complete
        if test.status in ["SUCCESS", "FAILED", "UNSTABLE"]:
            if test.jenkins_build_url:
                # Use the build URL directly (the method will construct artifact URL)
                build_url = test.jenkins_build_url.rstrip('/') + '/'
                build_num = test.jenkins_build_number
                job_status["allure_url"] = f"{build_url}allure/"
                logger.info(f"Fetching Allure report from: {build_url} (build #{build_num})")

                # Fetch Allure data
                allure_data = jenkins_service.fetch_allure_report_data(build_url, build_num)
                if allure_data:
                    job_status["results"] = allure_data
                    test.passed_count = allure_data.get('passed_count', 0)
                    test.failed_count = allure_data.get('failed_count', 0)
                    test.skipped_count = allure_data.get('skipped_count', 0)
                    test.broken_count = allure_data.get('broken_count', 0)
                    test.duration = allure_data.get('duration', 0)
                    # Create a new dict to ensure SQLAlchemy detects the change
                    new_metadata = dict(test.test_metadata) if test.test_metadata else {}
                    new_metadata['test_cases'] = allure_data.get('test_cases', [])
                    test.test_metadata = new_metadata
                    db.commit()

        pipeline_status["jobs"].append(job_status)

    # If all complete, aggregate results
    if pipeline_status["all_complete"]:
        aggregate = {
            "total_passed": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "total_duration": 0,
            "test_cases": []
        }
        for job in pipeline_status["jobs"]:
            if job.get("results"):
                aggregate["total_passed"] += job["results"].get("passed_count", 0)
                aggregate["total_failed"] += job["results"].get("failed_count", 0)
                aggregate["total_skipped"] += job["results"].get("skipped_count", 0)
                aggregate["total_duration"] += job["results"].get("duration", 0)
                aggregate["test_cases"].extend(job["results"].get("test_cases", []))

        pipeline_status["aggregate_results"] = aggregate

    return pipeline_status


# Jenkins job URL templates
JENKINS_JOB_TEMPLATES = {
    "android_15": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_15/job/android_15_auto/",
    "android_14": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_14/job/android_14_auto/",
    "android_13": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_13/job/android_13_auto/",
    "android_12": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_12/job/android_12_auto/",
    "android_11": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_11/job/android_11_auto/",
    "android_10": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/android/job/android_10/job/android_10_auto/",
    "ios_26": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/ios26/job/ios26_auto_test/",
    "ios_18": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/ios18/job/ios18_auto_test/",
    "ios_17": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/ios17/job/ios17_auto_test/",
    "ios_16": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/ios16/job/ios16_auto_test/",
    "ios_15": "http://10.160.13.30:8080/job/mobile_test/job/FortiToken_Mobile/job/iOS/job/ios15/job/ios15_auto_test/",
}


@router.post("/release-tests/trigger-versioned", response_model=dict)
async def trigger_versioned_release_test(
    build_number: str,
    android_versions: Optional[str] = None,
    ios_versions: Optional[str] = None,
    dns: Optional[str] = None,
    version: Optional[str] = None,
    project: Optional[str] = "ftm",
    platform_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger Jenkins jobs for selected Android/iOS versions.
    Creates test records immediately with PENDING status, then updates asynchronously.

    platform_filter: if 'android', only trigger android versions; if 'ios', only trigger iOS versions.
    """
    from app.services.jenkins_service import JenkinsService, extract_job_path
    from app.services.release_test_worker import release_test_worker
    import threading

    jenkins_service_inst = JenkinsService()
    results = {}
    created_tests = []

    # Parse versions - only parse the ones matching the platform filter
    if platform_filter == 'android':
        android_list = android_versions.split(',') if android_versions else []
        ios_list = []
    elif platform_filter == 'ios':
        android_list = []
        ios_list = ios_versions.split(',') if ios_versions else []
    else:
        # No filter - parse both (original behavior)
        android_list = android_versions.split(',') if android_versions else []
        ios_list = ios_versions.split(',') if ios_versions else []

    # Fetch default payloads
    android_default_payload = {}
    ios_default_payload = {}
    try:
        android_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "android_default_payload").first()
        if android_config and android_config.config_value:
            android_default_payload = android_config.config_value
        ios_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "ios_default_payload").first()
        if ios_config and ios_config.config_value:
            ios_default_payload = ios_config.config_value
    except Exception as e:
        logger.warning(f"Failed to fetch default payloads: {e}")

    # Step 1: No deduplication - always create new records
    # Step 2: Create parent test records (one per platform version) and trigger Jenkins
    for ver in android_list + ios_list:
        if ver not in JENKINS_JOB_TEMPLATES:
            continue

        is_android = ver in ['android_10', 'android_11', 'android_12', 'android_13', 'android_14', 'android_15']
        parent_job_url = JENKINS_JOB_TEMPLATES[ver]
        parent_job_path = extract_job_path(parent_job_url)

        # Use default payload from admin_configs
        if is_android:
            params = android_default_payload.copy() if android_default_payload else {}
            params["ftm_apk_version"] = f"ftma_v6.4.0.{build_number}.apk"
            if "docker_tag" not in params:
                params["docker_tag"] = "debug_ftm_auto_latest"
            if "mobile_emulator" not in params:
                params["mobile_emulator"] = "google_api"
            if "RUN_STAGE" not in params:
                params["RUN_STAGE"] = "ALL"
        else:
            params = ios_default_payload.copy() if ios_default_payload else {}
            params["ftm_ipa_version"] = f"ftm_i_v6.4.0.{build_number}.ipa"
            if "docker_tag" not in params:
                params["docker_tag"] = "debug_ftm_auto_latest"
            if "RUN_STAGE" not in params:
                params["RUN_STAGE"] = "ALL"

        if dns:
            params["fgt_ftm_dns"] = dns

        # Always create new test record (no deduplication)
        test = ReleaseCandidateTest(
            build_number=build_number,
            platform=ver,
            version=version or "auto",
            project=project or "ftm",
            test_suite="release",
            test_type="full",
            status="pending",
            started_at=datetime.utcnow(),
            jenkins_job_name=parent_job_path,
            jenkins_build_url=parent_job_url,
            test_metadata={
                "is_parent": True,
                "jenkins_params": params
            }
        )
        db.add(test)
        db.commit()
        db.refresh(test)

        results[ver] = {
            "status": "triggered",
            "test_id": str(test.id),
            "job_url": parent_job_url,
            "parameters": params
        }
        created_tests.append({
            "test": test,
            "job_url": parent_job_url,
            "params": params,
            "is_android": is_android
        })

        logger.info(f"Created parent record for {ver}")

        # Create 4 sub-task records for this platform (for tracking status only)
        for task_key, task_display, android_pattern, ios_pattern in SUBTASK_DEFINITIONS:
            # Generate job name by replacing version pattern
            base_pattern = android_pattern if is_android else ios_pattern
            version_match = None
            for v in ['android_10', 'android_11', 'android_12', 'android_13', 'android_14', 'android_15', 'ios16', 'ios_16']:
                if v in base_pattern:
                    version_match = v
                    break

            if version_match and version_match != ver:
                job_name = base_pattern.replace(version_match, ver)
            else:
                job_name = base_pattern

            # Generate subtask URL
            parent_job_url_stripped = parent_job_url.rstrip('/')
            parts = parent_job_url_stripped.split('/')
            if len(parts) > 1:
                base_parts = parts[:-1]
                subtask_job_url = '/'.join(base_parts) + f'/{job_name}/'
            else:
                subtask_job_url = f"{parent_job_url.rstrip('/')}/{job_name}/"

            # Always create new subtask record (no deduplication)
            subtask_platform = f"{ver}_{task_key}"
            subtask = ReleaseCandidateTest(
                build_number=build_number,
                platform=subtask_platform,
                version=version or "auto",
                project=project or "ftm",
                test_suite="release",
                test_type="full",
                status="pending",
                jenkins_job_name=job_name,
                jenkins_build_url=subtask_job_url,
                test_metadata={
                    "task_name": task_key,
                    "task_display": task_display,
                    "is_subtask": True,
                    "parent_id": str(test.id)
                }
            )
            db.add(subtask)
            db.commit()

        logger.info(f"Created 4 sub-task records for {ver}")

    # Step 3: Trigger parent pipeline jobs asynchronously (NOT subtasks)
    def trigger_and_monitor(test_id, test_platform, job_url, params):
        try:
            from sqlalchemy.orm import Session
            from app.core.database import engine
            with Session(engine) as thread_db:
                test = thread_db.query(ReleaseCandidateTest).filter(
                    ReleaseCandidateTest.id == test_id
                ).first()

                if not test:
                    logger.error(f"Test {test_id} not found")
                    return

                job_path = extract_job_path(job_url)

                # Record the time before triggering to use as reference
                trigger_time = datetime.utcnow()

                # Trigger Jenkins job
                jenkins_service_inst._build_job(job_path, params)
                logger.info(f"Triggered Jenkins job for {test_platform}")

                # Wait a bit for Jenkins to queue the build
                import time
                time.sleep(2)

                # Get the build number from Jenkins (the last build after trigger time)
                build_number = jenkins_service_inst.get_latest_build_number(job_path, trigger_time)
                logger.info(f"Got build number {build_number} for {test_platform}")

                # Update status to running and store build number
                test.status = 'running'
                test.started_at = datetime.utcnow()
                if build_number:
                    test.jenkins_build_number = build_number
                    logger.info(f"Stored build number {build_number} for test {test_id}")
                thread_db.commit()

                logger.info(f"Updated test {test_id} to running status")

        except Exception as e:
            logger.error(f"Error triggering {test_platform}: {e}")
            try:
                from sqlalchemy.orm import Session
                from app.core.database import engine
                with Session(engine) as error_db:
                    test = error_db.query(ReleaseCandidateTest).filter(
                        ReleaseCandidateTest.id == test_id
                    ).first()
                    if test:
                        test.status = 'error'
                        test.test_metadata = test.test_metadata or {}
                        test.test_metadata['error'] = str(e)
                        error_db.commit()
            except Exception as e2:
                logger.error(f"Failed to update error status: {e2}")

    # Trigger parent jobs only (not subtasks)
    trigger_threads = []
    for test_data in created_tests:
        t = threading.Thread(
            target=trigger_and_monitor,
            args=(
                str(test_data["test"].id),
                test_data["test"].platform,
                test_data["job_url"],
                test_data["params"]
            )
        )
        t.start()
        trigger_threads.append(t)

    # Wait for all trigger threads to complete
    for t in trigger_threads:
        t.join()

    return {
        "message": f"Triggered {len(android_list) + len(ios_list)} Jenkins jobs",
        "build_number": build_number,
        "results": results,
        "created_count": len(created_tests)
    }


class PipelineSubTask(BaseModel):
    """Pipeline sub-task model"""
    name: str
    display_name: str
    status: str  # running, waiting, passed, failed
    build_url: Optional[str] = None
    duration: Optional[int] = None


class PipelineInfo(BaseModel):
    """Pipeline information model"""
    platform: str  # android_15, ios_16, etc.
    build_number: str
    status: str  # running, waiting, passed, failed
    sub_tasks: List[PipelineSubTask]
    main_job_url: Optional[str] = None


# Sub-task definitions for FTM pipeline
# Subtask definitions: (task_key, task_display, android_job_pattern, ios_job_pattern)
# Android subtask job: android_14_auto_{task} -> android_14_auto_fac_token
# iOS subtask job: ios16_{task}_view -> ios16_fac_token_view
SUBTASK_DEFINITIONS = [
    ("fac_token", "FortiAuthenticator Token", "android_15_auto_fac_token", "ios16_fac_token_view"),
    ("fgt_token", "FortiGate Token", "android_15_auto_fgt_token", "ios16_fgt_token_view"),
    ("ftc_token_on_fac", "FTC on FAC", "android_15_auto_ftc_token_on_fac", "ios16_ftc_token_on_fac_view"),
    ("ftc_token_on_fgt", "FTC on FGT", "android_15_auto_ftc_token_on_fgt", "ios16_ftc_token_on_fgt_view"),
]


@router.get("/release-tests/pipeline-subtasks/{build_number}", response_model=List[dict])
async def get_pipeline_subtasks(
    build_number: str,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get pipeline sub-tasks for a given build number.
    Fetches information from Jenkins about the 4 sub-tasks under each pipeline.
    Returns sub-task records from database with status from Jenkins.
    """
    from app.services.jenkins_service import jenkins_service, extract_job_path
    import re

    # Get test records for this build number (these are the sub-task records)
    query = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number
    )
    if platform:
        query = query.filter(ReleaseCandidateTest.platform.like(f'{platform}%'))

    tests = query.all()

    subtasks = []

    for test in tests:
        subtask_info = {
            "id": str(test.id),
            "platform": test.platform,
            "os_version": test.platform.split('_')[1] if '_' in test.platform else '',
            "task_name": test.test_metadata.get('task_name', '') if test.test_metadata else '',
            "task_display": test.test_metadata.get('task_display', '') if test.test_metadata else '',
            "status": test.status,
            "build_url": test.jenkins_build_url,
            "build_number": test.jenkins_build_number,
            "parent_build_number": build_number,
            "passed_count": test.passed_count,
            "failed_count": test.failed_count,
            "skipped_count": test.skipped_count,
        }
        subtasks.append(subtask_info)

    # If no subtasks found in database, try to fetch from Jenkins directly
    if not subtasks:
        tests = db.query(ReleaseCandidateTest).filter(
            ReleaseCandidateTest.build_number == build_number
        ).all()

        for test in tests:
            if not test.jenkins_build_url:
                continue

            build_url = test.jenkins_build_url
            # Extract base job path
            match = re.search(r'(/job/mobile_test/[^/]+/[^/]+/[^/]+/[^/]+/[^/]+/)', build_url)
            if not match:
                continue

            base_job_path = match.group(1)

            for task_key, task_display, android_pattern, ios_pattern in SUBTASK_DEFINITIONS:
                try:
                    # Construct subtask job path
                    is_android = 'android' in test.platform.lower()
                    job_name = android_pattern if is_android else ios_pattern
                    # Replace version pattern with actual version
                    version_match = re.search(r'android_(\d+)|ios_(\d+)', test.platform)
                    if version_match:
                        version = version_match.group(1) or version_match.group(2)
                        job_name = job_name.replace('_15', f'_{version}').replace('16', version)

                    subtask_job_path = f"{base_job_path}{job_name}/"
                    job_path_clean = extract_job_path(subtask_job_path)

                    build_info = jenkins_service.server.get_job_info(job_path_clean)
                    last_build = build_info.get('lastBuild')

                    if last_build:
                        build_num = last_build.get('number')
                        is_building = last_build.get('building', False)
                        result = last_build.get('result')

                        if is_building:
                            status = 'RUNNING'
                        elif result:
                            status = result
                        else:
                            status = 'PENDING'

                        subtasks.append({
                            "platform": test.platform,
                            "os_version": test.platform.split('_')[1] if '_' in test.platform else '',
                            "task_name": task_key,
                            "task_display": task_display,
                            "status": status,
                            "build_url": last_build.get('url'),
                            "build_number": build_num,
                            "parent_build_number": build_number,
                        })
                except Exception as e:
                    logger.warning(f"Could not fetch sub-task {task_key}: {e}")
                    subtasks.append({
                        "platform": test.platform,
                        "os_version": test.platform.split('_')[1] if '_' in test.platform else '',
                        "task_name": task_key,
                        "task_display": task_display,
                        "status": "WAITING",
                        "build_url": None,
                        "build_number": None,
                        "parent_build_number": build_number,
                    })

    return subtasks


@router.post("/release-tests/create-pipeline-subtasks/{build_number}", response_model=dict)
async def create_pipeline_subtasks(
    build_number: str,
    db: Session = Depends(get_db)
):
    """
    Create sub-task records for a pipeline build.
    Called after triggering a pipeline to create the 4 sub-task records.
    """
    # Get parent test records for this build number
    parent_tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number
    ).all()

    created_count = 0

    for parent_test in parent_tests:
        # Create 4 sub-task records for each parent test
        for task_key, task_display, android_pattern, ios_pattern in SUBTASK_DEFINITIONS:
            is_android = 'android' in parent_test.platform.lower()
            job_name = android_pattern if is_android else ios_pattern

            # Create sub-task test record
            subtask = ReleaseCandidateTest(
                build_number=build_number,
                platform=f"{parent_test.platform}_{task_key}",
                version=parent_test.version,
                project=parent_test.project,
                test_suite=parent_test.test_suite,
                test_type=parent_test.test_type,
                status="pending",
                test_metadata={"task_name": task_key, "task_display": task_display, "parent_id": str(parent_test.id)},
                jenkins_job_name=parent_test.jenkins_job_name,
            )
            db.add(subtask)
            created_count += 1

    db.commit()

    return {"message": f"Created {created_count} sub-task records", "count": created_count}


@router.get("/release-tests/refresh-subtasks/{build_number}", response_model=dict)
async def refresh_subtask_status(
    build_number: str,
    db: Session = Depends(get_db)
):
    """
    Refresh sub-task status from Jenkins and fetch Allure reports if complete.
    Updates sub-task records with current Jenkins status and results.

    Only updates status if:
    - jenkins_build_number is set (subtask has been triggered by parent pipeline)
    - OR the build timestamp is newer than the test record's created_at
    """
    from app.services.jenkins_service import jenkins_service, extract_job_path
    from datetime import datetime
    import re

    # Get all sub-task records for this build
    subtasks = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number,
        ReleaseCandidateTest.test_metadata['task_name'].is_not(None)
    ).all()

    updated_count = 0
    results = []

    for subtask in subtasks:
        task_name = subtask.test_metadata.get('task_name')
        result_info = {
            "id": str(subtask.id),
            "platform": subtask.platform,
            "task_name": task_name,
            "status": subtask.status,
        }

        logger.info(f"Processing subtask: {task_name}, platform={subtask.platform}, status={subtask.status}, build_num={subtask.jenkins_build_number}, url={subtask.jenkins_build_url}")

        # Skip if already completed (passed/failed/skipped are final states)
        if subtask.status in ['passed', 'failed', 'skipped']:
            results.append(result_info)
            continue

        # If jenkins_build_number is not set, check Jenkins for any build
        if not subtask.jenkins_build_number:
            try:
                job_path = extract_job_path(subtask.jenkins_build_url)
                logger.info(f"Checking Jenkins for subtask {task_name} at path: {job_path}")

                job_info = jenkins_service.server.get_job_info(job_path)
                last_build = job_info.get('lastBuild')

                logger.info(f"Subtask {task_name}: last_build = {last_build}")

                if last_build:
                    build_num = last_build.get('number')
                    build_url = last_build.get('url')

                    # Get full build info from Jenkins API (includes timestamp and building status)
                    # The lastBuild from job_info only contains shallow data, need to fetch full build info
                    try:
                        full_build_info = jenkins_service.server.get_build_info(job_path, build_num)
                        is_building = full_build_info.get('building', False)
                        build_timestamp = full_build_info.get('timestamp', 0)
                    except Exception as fetch_error:
                        logger.warning(f"Could not fetch full build info for {task_name}: {fetch_error}")
                        is_building = False
                        build_timestamp = 0

                    # Convert subtask created_at to timestamp (seconds)
                    subtask_created_ts = int(subtask.created_at.timestamp())
                    # Jenkins timestamp is in milliseconds, convert to seconds
                    build_ts_seconds = build_timestamp // 1000 if build_timestamp > 100000000000 else build_timestamp

                    logger.info(f"Subtask {task_name}: build={build_num}, building={is_building}, build_ts={build_ts_seconds}, created_ts={subtask_created_ts}")

                    # Accept the build if it's currently running OR it's newer than the subtask record
                    # Allow 10 minutes tolerance for clock drift and pipeline delays
                    time_tolerance = 600
                    is_new_build = (build_ts_seconds >= subtask_created_ts - time_tolerance)

                    if is_building or is_new_build:
                        subtask.jenkins_build_number = build_num
                        if not subtask.jenkins_build_url:
                            subtask.jenkins_build_url = build_url
                        logger.info(f"Accepted build {build_num} for subtask {task_name} (building={is_building})")
                    else:
                        logger.info(f"Build {build_num} is older (ts={build_ts_seconds}, created={subtask_created_ts}), keeping as pending")
                        results.append(result_info)
                        continue
                else:
                    # No build yet - subtask job hasn't been triggered by parent pipeline
                    logger.info(f"No lastBuild found for subtask {task_name}, keeping as pending")
                    results.append(result_info)
                    continue
            except Exception as e:
                logger.info(f"Could not check Jenkins job for subtask {task_name}: {e}")
                results.append(result_info)
                continue

        # Get status from Jenkins
        if subtask.jenkins_build_url and subtask.jenkins_build_number:
            try:
                job_path = extract_job_path(subtask.jenkins_build_url)
                build_num = subtask.jenkins_build_number

                build_info = jenkins_service.server.get_build_info(job_path, build_num)
                is_building = build_info.get('building', False)
                result = build_info.get('result')

                # Map Jenkins result to database enum values
                status_map = {
                    'success': 'passed',
                    'failure': 'failed',
                    'unstable': 'failed',
                    'aborted': 'skipped',
                }

                if is_building:
                    subtask.status = 'running'
                elif result:
                    result_lower = result.lower()
                    subtask.status = status_map.get(result_lower, result_lower)

                # Fetch Allure report if complete
                if result and result in ['SUCCESS', 'FAILURE', 'UNSTABLE']:
                    build_url = subtask.jenkins_build_url.rstrip('/') + '/'
                    build_num = subtask.jenkins_build_number
                    logger.info(f"Fetching Allure report from: {build_url} (build #{build_num})")
                    allure_data = jenkins_service.fetch_allure_report_data(build_url, build_num)
                    if allure_data:
                        subtask.passed_count = allure_data.get('passed_count', 0)
                        subtask.failed_count = allure_data.get('failed_count', 0)
                        subtask.skipped_count = allure_data.get('skipped_count', 0)
                        subtask.broken_count = allure_data.get('broken_count', 0)
                        subtask.duration = allure_data.get('duration', 0)
                        # Create a new dict to ensure SQLAlchemy detects the change
                        new_metadata = dict(subtask.test_metadata) if subtask.test_metadata else {}
                        new_metadata['test_cases'] = allure_data.get('test_cases', [])
                        subtask.test_metadata = new_metadata

                result_info["status"] = subtask.status
                result_info["passed_count"] = subtask.passed_count
                result_info["failed_count"] = subtask.failed_count

                updated_count += 1
            except Exception as e:
                logger.warning(f"Could not update sub-task {task_name}: {e}")
                result_info["error"] = str(e)

        results.append(result_info)

    db.commit()

    # Update cycle status based on test results
    if build_number:
        try:
            update_cycle_status(build_number, db)
        except Exception as e:
            logger.warning(f"Could not update cycle status: {e}")

    return {
        "message": f"Refreshed {updated_count} sub-task statuses",
        "count": updated_count,
        "subtasks": results
    }


@router.get("/release-tests/refresh-allure/{build_number}", response_model=dict)
async def refresh_allure_reports(
    build_number: str,
    db: Session = Depends(get_db)
):
    """
    Refresh Allure report data for release test records by build_number.
    Fetches Allure reports from Jenkins for completed builds (SUCCESS/FAILURE/UNSTABLE).
    Only updates records that have jenkins_build_url set.
    Uses async requests to avoid blocking.
    """
    import concurrent.futures

    # Get all test records for this build_number
    tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number
    ).all()

    if not tests:
        return {
            "message": f"No test records found for build {build_number}",
            "count": 0,
            "results": []
        }

    updated_count = 0
    results = []

    def fetch_allure_for_test(test):
        """Inner function to fetch Allure data for a single test"""
        result_info = {
            "id": str(test.id),
            "platform": test.platform,
            "build_number": test.build_number,
        }

        # Skip if no Jenkins build URL or no build number
        if not test.jenkins_build_url:
            result_info["message"] = "No Jenkins build URL"
            return result_info, False

        # Skip if no build number - means the test hasn't been triggered yet
        if not test.jenkins_build_number:
            result_info["message"] = "No Jenkins build number (test not triggered yet)"
            return result_info, False

        # Use build URL directly (method will construct artifact URL)
        build_url = test.jenkins_build_url.rstrip('/') + '/'
        build_num = test.jenkins_build_number
        logger.info(f"Fetching Allure report for {test.platform}: {build_url} (build #{build_num})")

        try:
            # Create Jenkins service instance and fetch Allure report data
            jenkins_service = JenkinsService()
            allure_data = jenkins_service.fetch_allure_report_data(build_url, build_num)

            if allure_data and allure_data.get('total', 0) > 0:
                result_info["allure_data"] = allure_data
                result_info["message"] = "Allure data fetched"
                return result_info, True
            else:
                result_info["message"] = "No Allure data available"
                logger.info(f"No Allure data for {test.platform}: {allure_url}")
                return result_info, False
        except Exception as e:
            result_info["error"] = str(e)
            logger.warning(f"Could not fetch Allure data for {test.platform}: {e}")
            return result_info, False

    # Use ThreadPoolExecutor for concurrent Allure fetching
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_test = {executor.submit(fetch_allure_for_test, test): test for test in tests}

        for future in concurrent.futures.as_completed(future_to_test):
            test = future_to_test[future]
            try:
                result_info, has_data = future.result()
            except Exception as e:
                logger.error(f"Error fetching Allure for {test.platform}: {e}")
                result_info = {"platform": test.platform, "error": str(e)}
                has_data = False

            if has_data:
                # Update database record
                allure_data = result_info.get("allure_data", {})
                test.passed_count = allure_data.get('passed_count', 0)
                test.failed_count = allure_data.get('failed_count', 0)
                test.skipped_count = allure_data.get('skipped_count', 0)
                test.broken_count = allure_data.get('broken_count', 0)
                test.duration = allure_data.get('duration', 0)

                # Store test cases in metadata (always update)
                # Create a new dict to ensure SQLAlchemy detects the change
                new_metadata = dict(test.test_metadata) if test.test_metadata else {}
                new_metadata['test_cases'] = allure_data.get('test_cases', [])
                test.test_metadata = new_metadata

                # Set status based on results (broken counts as failed)
                if test.failed_count > 0 or test.broken_count > 0:
                    test.status = TestStatus.FAILED
                elif test.passed_count > 0:
                    test.status = TestStatus.PASSED
                else:
                    test.status = TestStatus.SKIPPED

                updated_count += 1
                result_info["passed_count"] = test.passed_count
                result_info["failed_count"] = test.failed_count
                result_info["skipped_count"] = test.skipped_count
                result_info["status"] = test.status
                logger.info(f"Updated Allure data for {test.platform}: {test.passed_count} passed, {test.failed_count} failed")

            results.append(result_info)

    db.commit()

    # Update cycle status after refreshing Allure data
    try:
        update_cycle_status(build_number, db)
    except Exception as e:
        logger.warning(f"Could not update cycle status: {e}")

    return {
        "message": f"Refreshed Allure data for {updated_count} test records",
        "count": updated_count,
        "results": results
    }


def _update_cycle_status_from_tests(cycle, tests, db):
    """
    Helper function to update cycle status based on test results.
    Status only indicates if the cycle is complete, not the test results.
    - 'running': some tests are still running
    - 'completed': all tests are complete (regardless of pass/fail)
    - 'pending': no tests have started yet
    """
    if not tests:
        logger.debug(f"Cycle {cycle.version} ({cycle.project}): No tests found")
        return

    # Filter to only sub-tasks
    subtask_tests = [
        test for test in tests
        if (test.test_metadata and test.test_metadata.get('is_subtask')) or
           any(suffix in test.platform for suffix in ['_fac_token', '_fgt_token', '_ftc_token_on_fac', '_ftc_token_on_fgt'])
    ]

    # Use subtasks if available, otherwise use all tests
    target_tests = subtask_tests if subtask_tests else tests

    if not target_tests:
        logger.debug(f"Cycle {cycle.version} ({cycle.project}): No target tests found")
        return

    # Get status values - handle both enum and string values
    def get_status_value(t):
        """Get status as string, handling both enum and string values"""
        if hasattr(t.status, 'value'):
            return t.status.value  # For enum types like TestStatus
        return str(t.status)  # For string values

    statuses = [get_status_value(t) for t in target_tests]

    # Count by status
    total = len(target_tests)
    completed = sum(1 for s in statuses if s in ['passed', 'failed', 'skipped', 'error'])
    running = sum(1 for s in statuses if s == 'running')

    # Determine cycle status (only running/completed/pending, no 'failed')
    if running > 0:
        new_status = 'running'
    elif completed == total and total > 0:
        new_status = 'completed'
    else:
        new_status = 'pending'

    logger.debug(f"Cycle {cycle.version} ({cycle.project}): total={total}, completed={completed}, running={running}, new_status={new_status}, statuses={statuses}")

    # Update if changed
    if cycle.status != new_status:
        cycle.status = new_status
        if new_status == 'completed':
            cycle.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Updated cycle {cycle.version} ({cycle.project}) status from {cycle.status} to {new_status} (total={total}, completed={completed}, running={running}, statuses={statuses})")
    else:
        logger.debug(f"Cycle {cycle.version} ({cycle.project}): status unchanged ({new_status})")


def update_cycle_status(build_number: str, db: Session):
    """
    Update ReleaseTestCycle status based on associated test results.
    Only considers sub-task tests (not parent pipeline tests) to avoid double counting.
    - If all sub-tasks are complete (passed/failed), mark cycle as 'completed' or 'failed'
    - If any sub-task is running, mark cycle as 'running'
    - Otherwise keep as 'pending'
    """
    # Get the version and project from the test record
    test_sample = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.build_number == build_number
    ).first()

    if not test_sample:
        return

    version = test_sample.version
    project = test_sample.project

    # Find the cycle
    cycle = db.query(ReleaseTestCycle).filter(
        ReleaseTestCycle.version == version,
        ReleaseTestCycle.project == project
    ).first()

    if not cycle:
        return

    # Get all tests for this cycle
    all_tests = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.version == version,
        ReleaseCandidateTest.project == project
    ).all()

    if not all_tests:
        return

    # Filter to only sub-tasks (tests with is_subtask metadata or platform contains token patterns)
    subtask_tests = [
        test for test in all_tests
        if (test.test_metadata and test.test_metadata.get('is_subtask')) or
           any(suffix in test.platform for suffix in ['_fac_token', '_fgt_token', '_ftc_token_on_fac', '_ftc_token_on_fgt'])
    ]

    # Use subtasks if available, otherwise use all tests (for manual uploads)
    tests = subtask_tests if subtask_tests else all_tests

    if not tests:
        return

    # Convert status to string for comparison (handles both enum and string values)
    statuses = [str(t.status) for t in tests]

    # Count by status
    total = len(tests)
    running = sum(1 for s in statuses if s == 'running')
    completed = sum(1 for s in statuses if s in ['passed', 'failed', 'skipped', 'error'])

    # Determine cycle status (only running/completed/pending, no 'failed')
    if running > 0:
        new_status = 'running'
    elif completed > 0 and completed == total:
        # All tests completed
        new_status = 'completed'
    else:
        # No tests completed yet
        new_status = 'pending'

    # Update if changed
    if cycle.status != new_status:
        cycle.status = new_status
        if new_status == 'completed':
            cycle.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Updated cycle {version} ({project}) status to {new_status}")


@router.post("/release-tests/fetch-from-jenkins", response_model=dict)
async def fetch_from_jenkins(
    version: str,
    project: str = "ftm",
    platform: str = None,
    db: Session = Depends(get_db)
):
    """
    Fetch test results from Jenkins for a specific version and project.
    This API checks Jenkins for recent builds and creates/updates test records.
    """
    from app.services.jenkins_service import jenkins_service, extract_job_path
    import re

    try:
        # Project mapping to Jenkins folder names
        project_folder_map = {
            'ftm': 'FortiToken_Mobile',
            'fortiexplorer': 'FortiExplorer_Go',
            'fortiedr': 'FortiEDR_Mobile'
        }
        project_folder = project_folder_map.get(project.lower(), 'FortiToken_Mobile')

        # Jenkins job path structure
        android_base_path = f"mobile_test/{project_folder}/android"
        ios_base_path = f"mobile_test/{project_folder}/iOS"

        results = {
            "android": [],
            "ios": [],
            "count": 0,
            "subtasks": []
        }

        # Fetch from Android job if platform matches
        if not platform or platform.startswith('android'):
            # Search recent builds for Android - check subfolders like android_15, android_14, etc.
            for android_ver in ['android_15', 'android_14', 'android_13', 'android_12', 'android_11', 'android_10']:
                try:
                    # Get the folder info first
                    folder_path = f"{android_base_path}/{android_ver}"
                    folder_info = jenkins_service.server.get_job_info(folder_path)

                    # Get sub-jobs from the folder
                    jobs = folder_info.get('jobs', [])
                    if not jobs:
                        continue

                    # Find the auto test job (e.g., android_15_auto)
                    auto_job = None
                    for job in jobs:
                        if '_auto' in job.get('name', '') and not any(x in job.get('name', '') for x in ['fac', 'fgt', 'ftc']):
                            auto_job = job
                            break

                    if not auto_job:
                        continue

                    # Get the last build from the auto job
                    job_name = auto_job['name']
                    job_info = jenkins_service.server.get_job_info(f"{folder_path}/{job_name}")
                    last_build = job_info.get('lastBuild')

                    if last_build:
                        build_num = last_build.get('number')
                        build_url = last_build.get('url')
                        is_building = last_build.get('building', False)
                        result = last_build.get('result')

                        # Determine status
                        status = 'running' if is_building else (result.lower() if result else 'pending')

                        # Check if we already have this test
                        existing = db.query(ReleaseCandidateTest).filter(
                            ReleaseCandidateTest.build_number == str(build_num),
                            ReleaseCandidateTest.platform == android_ver,
                            ReleaseCandidateTest.version == version
                        ).first()

                        if not existing:
                            # Create test record
                            test = ReleaseCandidateTest(
                                build_number=str(build_num),
                                platform=android_ver,
                                version=version,
                                project=project,
                                test_suite="release",
                                test_type="full",
                                status=status,
                                jenkins_job_name=f"{folder_path}/{job_name}",
                                jenkins_build_number=build_num,
                                jenkins_build_url=build_url,
                            )
                            db.add(test)
                            db.commit()
                            results["android"].append(test.to_dict())

                        # Fetch Allure report if complete
                        if result in ['SUCCESS', 'FAILURE', 'UNSTABLE']:
                            current_build_url = build_url.rstrip('/') + '/'
                            logger.info(f"Fetching Allure report: {current_build_url} (build #{build_num})")
                            allure_data = jenkins_service.fetch_allure_report_data(current_build_url, build_num)
                            if allure_data:
                                if existing:
                                    existing.passed_count = allure_data.get('passed_count', 0)
                                    existing.failed_count = allure_data.get('failed_count', 0)
                                    existing.skipped_count = allure_data.get('skipped_count', 0)
                                    existing.broken_count = allure_data.get('broken_count', 0)
                                    # Create a new dict to ensure SQLAlchemy detects the change
                                    new_metadata = dict(existing.test_metadata) if existing.test_metadata else {}
                                    new_metadata['test_cases'] = allure_data.get('test_cases', [])
                                    existing.test_metadata = new_metadata
                                    db.commit()
                                else:
                                    test.passed_count = allure_data.get('passed_count', 0)
                                    test.failed_count = allure_data.get('failed_count', 0)
                                    test.skipped_count = allure_data.get('skipped_count', 0)
                                    test.broken_count = allure_data.get('broken_count', 0)
                                    # Create a new dict to ensure SQLAlchemy detects the change
                                    new_metadata = dict(test.test_metadata) if test.test_metadata else {}
                                    new_metadata['test_cases'] = allure_data.get('test_cases', [])
                                    test.test_metadata = new_metadata
                                    db.commit()

                        results["count"] += 1
                except Exception as e:
                    logger.debug(f"Android {android_ver} job not found: {e}")

        # Fetch from iOS job if platform matches
        if not platform or platform.startswith('ios'):
            # Search recent builds for iOS
            for ios_ver in ['ios_26', 'ios_18', 'ios_17', 'ios_16', 'ios_15']:
                try:
                    # Get the folder info first
                    folder_path = f"{ios_base_path}/{ios_ver}"
                    folder_info = jenkins_service.server.get_job_info(folder_path)

                    # Get sub-jobs from the folder
                    jobs = folder_info.get('jobs', [])
                    if not jobs:
                        continue

                    # Find the auto test job
                    auto_job = None
                    for job in jobs:
                        if '_auto' in job.get('name', '') and not any(x in job.get('name', '') for x in ['fac', 'fgt', 'ftc']):
                            auto_job = job
                            break

                    if not auto_job:
                        continue

                    # Get the last build from the auto job
                    job_name = auto_job['name']
                    job_info = jenkins_service.server.get_job_info(f"{folder_path}/{job_name}")
                    last_build = job_info.get('lastBuild')

                    if last_build:
                        build_num = last_build.get('number')
                        build_url = last_build.get('url')
                        is_building = last_build.get('building', False)
                        result = last_build.get('result')

                        # Determine status
                        status = 'running' if is_building else (result.lower() if result else 'pending')

                        # Check if we already have this test
                        existing = db.query(ReleaseCandidateTest).filter(
                            ReleaseCandidateTest.build_number == str(build_num),
                            ReleaseCandidateTest.platform == ios_ver,
                            ReleaseCandidateTest.version == version
                        ).first()

                        if not existing:
                            # Create test record
                            test = ReleaseCandidateTest(
                                build_number=str(build_num),
                                platform=ios_ver,
                                version=version,
                                project=project,
                                test_suite="release",
                                test_type="full",
                                status=status,
                                jenkins_job_name=f"{folder_path}/{job_name}",
                                jenkins_build_number=build_num,
                                jenkins_build_url=build_url,
                            )
                            db.add(test)
                            db.commit()
                            results["ios"].append(test.to_dict())

                        # Fetch Allure report if complete
                        if result in ['SUCCESS', 'FAILURE', 'UNSTABLE']:
                            current_build_url = build_url.rstrip('/') + '/'
                            logger.info(f"Fetching Allure report: {current_build_url} (build #{build_num})")
                            allure_data = jenkins_service.fetch_allure_report_data(current_build_url, build_num)
                            if allure_data:
                                if existing:
                                    existing.passed_count = allure_data.get('passed_count', 0)
                                    existing.failed_count = allure_data.get('failed_count', 0)
                                    existing.skipped_count = allure_data.get('skipped_count', 0)
                                    existing.broken_count = allure_data.get('broken_count', 0)
                                    # Create a new dict to ensure SQLAlchemy detects the change
                                    new_metadata = dict(existing.test_metadata) if existing.test_metadata else {}
                                    new_metadata['test_cases'] = allure_data.get('test_cases', [])
                                    existing.test_metadata = new_metadata
                                    db.commit()
                                else:
                                    test.passed_count = allure_data.get('passed_count', 0)
                                    test.failed_count = allure_data.get('failed_count', 0)
                                    test.skipped_count = allure_data.get('skipped_count', 0)
                                    test.broken_count = allure_data.get('broken_count', 0)
                                    # Create a new dict to ensure SQLAlchemy detects the change
                                    new_metadata = dict(test.test_metadata) if test.test_metadata else {}
                                    new_metadata['test_cases'] = allure_data.get('test_cases', [])
                                    test.test_metadata = new_metadata
                                    db.commit()

                        results["count"] += 1
                except Exception as e:
                    logger.debug(f"iOS {ios_ver} job not found: {e}")

        db.commit()

        return {
            "success": True,
            "count": results["count"],
            "android": results["android"],
            "ios": results["ios"],
            "subtasks": results["subtasks"]
        }
    except Exception as e:
        logger.error(f"Error fetching from Jenkins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/release-tests/all-subtasks", response_model=dict)
async def get_all_pipeline_subtasks(
    platform_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all pipeline sub-tasks grouped by platform.
    Returns a summary of all running and completed sub-tasks.
    """
    # Get recent tests (last 100)
    tests = db.query(ReleaseCandidateTest).order_by(
        ReleaseCandidateTest.created_at.desc()
    ).limit(100).all()

    result = {
        "android": [],
        "ios": [],
        "android_13": [],
        "android_14": [],
        "android_15": [],
        "ios_15": [],
        "ios_16": [],
        "ios_17": [],
        "ios_18": [],
        "ios_26": []
    }

    for test in tests:
        if test.platform not in result:
            result[test.platform] = []

        if test.jenkins_build_url:
            result[test.platform].append({
                "build_number": test.build_number,
                "status": test.status,
                "jenkins_build_url": test.jenkins_build_url,
                "started_at": test.started_at.isoformat() if test.started_at else None
            })

    return result


@router.get("/release-tests/stream", response_model=List[dict])
async def stream_release_tests(
    platform: str,
    version: Optional[str] = None,
    project: Optional[str] = None,
    last_updated: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Stream release tests with optional last_updated timestamp.
    Returns tests that have been updated since last_updated.
    Used for real-time UI updates.
    """
    query = db.query(ReleaseCandidateTest).filter(
        ReleaseCandidateTest.platform.like(f'{platform}%')
    )

    if version:
        query = query.filter(ReleaseCandidateTest.version == version)
    if project:
        query = query.filter(ReleaseCandidateTest.project == project)

    if last_updated:
        from datetime import datetime
        try:
            cutoff = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            query = query.filter(ReleaseCandidateTest.updated_at > cutoff)
        except Exception:
            pass  # If parsing fails, return all

    tests = query.all()
    return [test.to_dict() for test in tests]


# ============== Release Test Configuration APIs ==============

@router.get("/release-test-config", response_model=ReleaseTestConfig)
async def get_release_test_config(db: Session = Depends(get_db)):
    """
    Get release test configuration (allowed versions and build numbers).
    Returns config with versions, build_numbers, disabled_versions, and version_build_numbers.
    """
    config = db.query(AdminConfig).filter(
        AdminConfig.config_key == "release_test_config"
    ).first()

    if config and config.config_value:
        config_value = config.config_value
        # Parse version_build_numbers if exists
        version_build_numbers_data = config_value.get("version_build_numbers", [])
        version_build_numbers = [
            VersionBuildNumber(**item) if isinstance(item, dict) else item
            for item in version_build_numbers_data
        ] if version_build_numbers_data else []

        return ReleaseTestConfig(
            versions=config_value.get("versions", []),
            build_numbers=config_value.get("build_numbers", []),
            disabled_versions=config_value.get("disabled_versions", []),
            version_build_numbers=version_build_numbers
        )

    # Return empty config if not set
    return ReleaseTestConfig()


@router.post("/release-test-config", response_model=ReleaseTestConfig)
async def set_release_test_config(
    config_data: ReleaseTestConfig,
    db: Session = Depends(get_db)
):
    """
    Set release test configuration (allowed versions and build numbers).
    Admin only.
    """
    existing_config = db.query(AdminConfig).filter(
        AdminConfig.config_key == "release_test_config"
    ).first()

    # Parse version_build_numbers
    version_build_numbers_data = []
    if config_data.version_build_numbers:
        for item in config_data.version_build_numbers:
            if isinstance(item, VersionBuildNumber):
                version_build_numbers_data.append(item.dict())
            else:
                version_build_numbers_data.append(item)

    config_value = {
        "versions": config_data.versions,
        "build_numbers": config_data.build_numbers,
        "disabled_versions": config_data.disabled_versions,
        "version_build_numbers": version_build_numbers_data
    }

    if existing_config:
        existing_config.config_value = config_value
        db.commit()
        db.refresh(existing_config)
        return ReleaseTestConfig(**config_value)
    else:
        new_config = AdminConfig(
            config_key="release_test_config",
            config_value=config_value,
            description="Release test configuration - allowed versions and build numbers"
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return ReleaseTestConfig(**config_value)


@router.delete("/release-test-config", response_model=dict)
async def delete_release_test_config(db: Session = Depends(get_db)):
    """
    Delete release test configuration.
    Admin only.
    """
    config = db.query(AdminConfig).filter(
        AdminConfig.config_key == "release_test_config"
    ).first()

    if config:
        db.delete(config)
        db.commit()
        return {"message": "Release test configuration deleted"}

    raise HTTPException(status_code=404, detail="Configuration not found")
