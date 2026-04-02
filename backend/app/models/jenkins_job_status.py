"""
Jenkins Job Status Database Model
Track and cache Jenkins Job execution status
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class JenkinsJobStatus(Base):
    """
    Jenkins Job Status - Track Jenkins Job execution status

    Status logic:
    1. If running_build_number exists, status is 'running'
    2. If no running_build_number, check last_completed_build_timestamp
    3. If last_completed_build_timestamp >= parameter_timestamp, status is 'completed'
    4. If last_completed_build_timestamp < parameter_timestamp, status is 'pending'
    """
    __tablename__ = "jenkins_job_statuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job information
    job_name = Column(String, nullable=False, index=True)  # Job name
    job_url = Column(String, nullable=False, index=True)  # Job URL

    # Timestamp parameter
    # User-provided reference timestamp (ISO format)
    parameter_timestamp = Column(DateTime, nullable=True)

    # Running status
    # Currently running build number (if any)
    running_build_number = Column(Integer, nullable=True)
    # Start timestamp of current running build
    running_build_timestamp = Column(DateTime, nullable=True)
    # Estimated remaining time of running build (milliseconds)
    running_build_eta = Column(BigInteger, default=0)

    # Last completed status
    # Last completed build number
    last_completed_build_number = Column(Integer, nullable=True)
    # Timestamp of last completed build
    last_completed_build_timestamp = Column(DateTime, nullable=True)
    # Result of last completed build (SUCCESS, FAILURE, UNSTABLE, ABORTED)
    last_completed_build_result = Column(String, nullable=True)

    # Computed status field
    # Computed status: running, completed, pending
    computed_status = Column(String, nullable=True, index=True)
    # Timestamp when status was computed
    status_computed_at = Column(DateTime, nullable=True)

    # Metadata
    job_metadata = Column("job_metadata", JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True)

    # Composite index
    __table_args__ = (
        Index('idx_jenkins_job_status_composite', 'job_name', 'computed_status'),
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "job_name": self.job_name,
            "job_url": self.job_url,
            "parameter_timestamp": self.parameter_timestamp.isoformat() if self.parameter_timestamp else None,
            "running_build_number": self.running_build_number,
            "running_build_timestamp": self.running_build_timestamp.isoformat() if self.running_build_timestamp else None,
            "running_build_eta": self.running_build_eta,
            "last_completed_build_number": self.last_completed_build_number,
            "last_completed_build_timestamp": self.last_completed_build_timestamp.isoformat() if self.last_completed_build_timestamp else None,
            "last_completed_build_result": self.last_completed_build_result,
            "computed_status": self.computed_status,
            "status_computed_at": self.status_computed_at.isoformat() if self.status_computed_at else None,
            "job_metadata": self.job_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }

    @staticmethod
    def compute_status_from_params(
        running_build_number: int = None,
        last_completed_timestamp: datetime = None,
        parameter_timestamp: datetime = None
    ) -> str:
        """
        Compute status from parameters

        Logic:
        1. If running_build_number exists, return 'running'
        2. If no running_build_number, check last_completed_timestamp
        3. If last_completed_timestamp >= parameter_timestamp, return 'completed'
        4. If last_completed_timestamp < parameter_timestamp, return 'pending'

        Args:
            running_build_number: Currently running build number
            last_completed_timestamp: Timestamp of last completed build
            parameter_timestamp: User-provided reference timestamp

        Returns:
            str: 'running', 'completed', or 'pending'
        """
        # 1. If there's a running build, status is running
        if running_build_number:
            return 'running'

        # 2. If no reference timestamp, cannot determine, return pending
        if not parameter_timestamp:
            return 'pending'

        # 3. If no completed build, return pending
        if not last_completed_timestamp:
            return 'pending'

        # 4. Compare timestamps
        # If last completed time >= parameter time, it's completed
        if last_completed_timestamp >= parameter_timestamp:
            return 'completed'

        # 5. Otherwise, not started yet
        return 'pending'
