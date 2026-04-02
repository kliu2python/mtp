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


class ReleaseTestCycle(Base):
    """
    Release Test Cycle - represents a testing cycle/plan for a specific version.
    This is the main entity that groups test executions together.
    """
    __tablename__ = "release_test_cycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Version information
    version = Column(String, nullable=False)  # e.g., "6.4.0"

    # Project information
    project = Column(String, nullable=False, default="ftm")  # ftm, fortiexplorer, fortiedr

    # Cycle information
    platform = Column(String, nullable=False)  # android, ios, or "all"
    description = Column(Text, nullable=True)

    # Status tracking (overall cycle status)
    status = Column(String, default="pending")  # pending, running, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Cycle metadata
    cycle_metadata = Column("cycle_metadata", JSON, default=dict)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "version": self.version,
            "project": self.project,
            "platform": self.platform,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cycle_metadata": self.cycle_metadata,
            # Statistics
            "total_tests": self.cycle_metadata.get('total_tests', 0) if self.cycle_metadata else 0,
            "passed_tests": self.cycle_metadata.get('passed_tests', 0) if self.cycle_metadata else 0,
            "failed_tests": self.cycle_metadata.get('failed_tests', 0) if self.cycle_metadata else 0,
        }


class ReleaseCandidateTest(Base):
    """
    Release Candidate Test - represents a single test execution within a cycle.
    This can be a parent test (e.g., android_15) or a subtask (e.g., android_15_fac_token).
    """
    __tablename__ = "release_candidate_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to parent cycle
    cycle_id = Column(UUID(as_uuid=True), ForeignKey('release_test_cycles.id', ondelete='CASCADE'), nullable=True, index=True)

    # Build information
    build_number = Column(String, nullable=False, index=True)  # e.g., "0022"
    platform = Column(String, nullable=False)  # android, ios, android_15, android_15_fac_token, etc.
    version = Column(String, nullable=False)  # e.g., "6.4.0"

    # Project information
    project = Column(String, nullable=False, default="ftm")  # ftm, fortiexplorer, fortiedr

    # Test information
    test_suite = Column(String, nullable=False, default="release")
    test_type = Column(String, nullable=False, default="full")

    # Status tracking
    status = Column(SQLEnum(TestStatus), default=TestStatus.PENDING)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Integer, default=0)  # seconds

    # Results
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    broken_count = Column(Integer, default=0)

    # Jenkins integration
    jenkins_job_name = Column(String, nullable=True)
    jenkins_build_number = Column(Integer, nullable=True)
    jenkins_build_url = Column(String, nullable=True)

    # Associated files
    apk_file_id = Column(UUID(as_uuid=True), nullable=True)

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
            "cycle_id": str(self.cycle_id) if self.cycle_id else None,
            "build_number": self.build_number,
            "platform": self.platform,
            "version": self.version,
            "project": self.project,
            "test_suite": self.test_suite,
            "test_type": self.test_type,
            "status": self.status.value if self.status else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "broken_count": self.broken_count,
            "jenkins_job_name": self.jenkins_job_name,
            "jenkins_build_number": self.jenkins_build_number,
            "jenkins_build_url": self.jenkins_build_url,
            "apk_file_id": str(self.apk_file_id) if self.apk_file_id else None,
            "metadata": self.test_metadata,
            "notes": self.notes,
            "test_cases": self.test_metadata.get('test_cases', []) if self.test_metadata else [],
            "mantis_issues": self.test_metadata.get('mantis_issues', []) if self.test_metadata else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
