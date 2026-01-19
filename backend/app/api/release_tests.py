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

from app.core.database import get_db
from app.models.release_test import ReleaseCandidateTest, TestStatus
from app.services.logger import get_logger

logger = get_logger()
router = APIRouter()


class ReleaseTestCreate(BaseModel):
    """Payload for creating a release candidate test entry"""
    build_number: str
    platform: str
    version: str
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
            query = query.filter(ReleaseCandidateTest.platform == platform)
        if status:
            query = query.filter(ReleaseCandidateTest.status == status)
        if build_number:
            query = query.filter(
                ReleaseCandidateTest.build_number == build_number)
        if version:
            query = query.filter(ReleaseCandidateTest.version == version)

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

    test = ReleaseCandidateTest(
        build_number=test_data.build_number,
        platform=test_data.platform,
        version=test_data.version,
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
    allure_url: str,
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

    # Fetch Allure report data
    allure_data = jenkins_service.fetch_allure_report_data(allure_url)
    if not allure_data:
        raise HTTPException(
            status_code=400, detail="Failed to fetch Allure report data")

    # Update the test record with Allure data
    test.passed_count = allure_data.get('passed_count', 0)
    test.failed_count = allure_data.get('failed_count', 0)
    test.skipped_count = allure_data.get('skipped_count', 0)
    test.duration = allure_data.get('duration', 0)
    test.jenkins_build_url = allure_url
    # Set status based on results
    if test.failed_count > 0:
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
    if not test.test_metadata:
        test.test_metadata = {}
    test.test_metadata['test_cases'] = results_data.get('test_cases', [])

    # Set status based on results
    if test.failed_count > 0:
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
        if not test.test_metadata:
            test.test_metadata = {}
        test.test_metadata['test_cases'] = results_data.get('test_cases', [])

        # Set status based on results
        if test.failed_count > 0:
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
