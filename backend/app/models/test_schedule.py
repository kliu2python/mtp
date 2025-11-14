"""
Test Schedule models for automated test execution
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ScheduleStatus(str, enum.Enum):
    """Schedule status enum"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class TestSchedule(Base):
    """Test Schedule model for automated nightly/recurring tests"""
    __tablename__ = "test_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Schedule configuration
    cron_expression = Column(String, nullable=False)  # "0 2 * * *" = 2 AM daily
    timezone = Column(String, default="UTC")

    # Test configuration
    test_config = Column(JSON, nullable=False)  # Full test configuration

    # Target selection
    vm_ids = Column(JSON, default=list)  # List of VM IDs
    device_ids = Column(JSON, default=list)  # List of device IDs
    apk_id = Column(UUID(as_uuid=True), nullable=True)  # Optional APK file ID

    # Notification settings
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_emails = Column(JSON, default=list)  # List of email addresses
    notification_teams_webhook = Column(String, nullable=True)  # Teams webhook URL

    # Status and metadata
    status = Column(SQLEnum(ScheduleStatus), default=ScheduleStatus.ACTIVE)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String, nullable=True)  # "success", "failed", "running"
    last_run_task_id = Column(String, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)

    # Ownership and tracking
    created_by = Column(String, nullable=True)
    tags = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "test_config": self.test_config,
            "vm_ids": self.vm_ids,
            "device_ids": self.device_ids,
            "apk_id": str(self.apk_id) if self.apk_id else None,
            "notify_on_success": self.notify_on_success,
            "notify_on_failure": self.notify_on_failure,
            "notification_emails": self.notification_emails,
            "notification_teams_webhook": self.notification_teams_webhook,
            "status": self.status.value if self.status else None,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_task_id": self.last_run_task_id,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": round((self.successful_runs / self.total_runs * 100) if self.total_runs > 0 else 0, 2),
            "created_by": self.created_by,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
