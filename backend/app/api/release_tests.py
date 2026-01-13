"""
Release Candidate Test API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.release_test import ReleaseCandidateTest, TestStatus

router = APIRouter()


class ReleaseTestCreate(BaseModel):
    """Payload for creating a release candidate test entry"""
    build_number: str
    platform: str
    version: str
    test_suite: str
    test_type: str
    status: Optional[str] = None
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
    query = db.query(ReleaseCandidateTest)

    if platform:
        query = query.filter(ReleaseCandidateTest.platform == platform)
    if status:
        query = query.filter(ReleaseCandidateTest.status == status)
    if build_number:
        query = query.filter(ReleaseCandidateTest.build_number == build_number)
    if version:
        query = query.filter(ReleaseCandidateTest.version == version)

    # Order by build number for consistent sorting
    query = query.order_by(ReleaseCandidateTest.build_number)

    tests = query.offset(skip).limit(limit).all()

    return [test.to_dict() for test in tests]


@router.get("/release-tests/{test_id}", response_model=dict)
async def get_release_test(test_id: str, db: Session = Depends(get_db)):
    """Get release candidate test by ID"""
    try:
        test_uuid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID format")

    test = db.query(ReleaseCandidateTest).filter(ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    return test.to_dict()


@router.post("/release-tests", response_model=dict, status_code=201)
async def create_release_test(test_data: ReleaseTestCreate, db: Session = Depends(get_db)):
    """Create a new release candidate test entry"""
    test = ReleaseCandidateTest(
        build_number=test_data.build_number,
        platform=test_data.platform,
        version=test_data.version,
        test_suite=test_data.test_suite,
        test_type=test_data.test_type,
        status=test_data.status if test_data.status else TestStatus.PENDING,
        apk_file_id=uuid.UUID(test_data.apk_file_id) if test_data.apk_file_id else None,
        test_metadata=test_data.test_metadata or {},
        notes=test_data.notes
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

    test = db.query(ReleaseCandidateTest).filter(ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    # Update fields if provided
    update_data = test_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        # Handle special cases
        if key == "apk_file_id" and value is not None:
            setattr(test, key, uuid.UUID(value))
        elif key == "test_metadata":
            # Map test_metadata to test_metadata column
            setattr(test, "test_metadata", value)
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

    test = db.query(ReleaseCandidateTest).filter(ReleaseCandidateTest.id == test_uuid).first()
    if not test:
        raise HTTPException(status_code=404, detail="Release test not found")

    db.delete(test)
    db.commit()

    return {"detail": "Release test deleted successfully"}