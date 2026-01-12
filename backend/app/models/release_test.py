"""
Release Candidate Test models
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class TestStatus(str, enum.Enum):
    """Test status enum"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ReleaseCandidateTest(Base):
    """Release Candidate Test model for tracking build test status"""
    __tablename__ = "release_candidate_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    build_number = Column(String, nullable=False, index=True)  # e.g., "1.2.3-rc1"
    platform = Column(String, nullable=False)  # android, ios
    version = Column(String, nullable=False)  # e.g., "1.2.3"

    # Test information
    test_suite = Column(String, nullable=False)  # functional, integration, regression
    test_type = Column(String, nullable=False)  # smoke, acceptance, etc.

    # Status tracking
    status = Column(SQLEnum(TestStatus), default=TestStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Integer, default=0)  # seconds

    # Results
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)

    # Jenkins integration
    jenkins_job_name = Column(String, nullable=True)
    jenkins_build_number = Column(Integer, nullable=True)
    jenkins_build_url = Column(String, nullable=True)

    # Associated files
    apk_file_id = Column(UUID(as_uuid=True), nullable=True)  # Link to APK/IPA file

    # Metadata
    test_metadata = Column("metadata", JSON, default=dict)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "build_number": self.build_number,
            "platform": self.platform,
            "version": self.version,
            "test_suite": self.test_suite,
            "test_type": self.test_type,
            "status": self.status.value if self.status else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "jenkins_job_name": self.jenkins_job_name,
            "jenkins_build_number": self.jenkins_build_number,
            "jenkins_build_url": self.jenkins_build_url,
            "apk_file_id": str(self.apk_file_id) if self.apk_file_id else None,
            "metadata": self.test_metadata,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }