"""
Jenkins Build Model
Represents a build execution, similar to Jenkins build history
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class BuildStatus(str, enum.Enum):
    """Build status enum"""
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    UNSTABLE = "unstable"
    ABORTED = "aborted"
    TIMEOUT = "timeout"


class JenkinsBuild(Base):
    """Jenkins Build model - represents a single build execution"""
    __tablename__ = "jenkins_builds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job relationship
    job_id = Column(UUID(as_uuid=True), ForeignKey("jenkins_jobs.id"), nullable=False, index=True)
    job_name = Column(String, nullable=False, index=True)
    build_number = Column(Integer, nullable=False)

    # Agent assignment
    node_id = Column(UUID(as_uuid=True), ForeignKey("jenkins_nodes.id"), nullable=True)
    node_name = Column(String, nullable=True)

    # Build Status
    status = Column(SQLEnum(BuildStatus), default=BuildStatus.QUEUED, nullable=False)
    result = Column(String, nullable=True)  # SUCCESS, FAILURE, UNSTABLE, ABORTED

    # Timing
    queued_time = Column(DateTime, default=datetime.utcnow)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds

    # Build Configuration (snapshot at build time)
    build_config = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    environment_vars = Column(JSON, default=dict)

    # Execution Details
    workspace = Column(String, nullable=True)  # Workspace path on agent
    console_output = Column(Text, default="")  # Console log output
    exit_code = Column(Integer, nullable=True)

    # Docker Execution Details
    docker_image = Column(String, nullable=True)
    container_name = Column(String, nullable=True)

    # Test Results
    test_suite = Column(String, nullable=True)
    test_total = Column(Integer, default=0)
    test_passed = Column(Integer, default=0)
    test_failed = Column(Integer, default=0)
    test_skipped = Column(Integer, default=0)

    # Artifacts
    artifacts = Column(JSON, default=list)  # List of artifact paths
    allure_results_path = Column(String, nullable=True)
    screenshots_path = Column(String, nullable=True)
    logs_path = Column(String, nullable=True)

    # Error Information
    error_message = Column(Text, nullable=True)
    error_stacktrace = Column(Text, nullable=True)

    # Notifications
    email_sent = Column(Boolean, default=False)
    notification_error = Column(String, nullable=True)

    # Metadata
    triggered_by = Column(String, nullable=True)  # User or system
    trigger_cause = Column(String, nullable=True)  # Manual, SCM, Webhook, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "job_name": self.job_name,
            "build_number": self.build_number,
            "display_name": f"#{self.build_number}",
            "full_display_name": f"{self.job_name} #{self.build_number}",
            "node_id": str(self.node_id) if self.node_id else None,
            "node_name": self.node_name,
            "status": self.status.value if self.status else None,
            "result": self.result,
            "queued_time": self.queued_time.isoformat() if self.queued_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "duration_string": self._format_duration(self.duration),
            "build_config": self.build_config,
            "parameters": self.parameters,
            "environment_vars": self.environment_vars,
            "workspace": self.workspace,
            "console_output": self.console_output,
            "exit_code": self.exit_code,
            "docker_image": self.docker_image,
            "container_name": self.container_name,
            "test_suite": self.test_suite,
            "test_total": self.test_total,
            "test_passed": self.test_passed,
            "test_failed": self.test_failed,
            "test_skipped": self.test_skipped,
            "test_pass_rate": round(self.test_passed / self.test_total * 100, 2) if self.test_total > 0 else 0,
            "artifacts": self.artifacts,
            "allure_results_path": self.allure_results_path,
            "screenshots_path": self.screenshots_path,
            "logs_path": self.logs_path,
            "error_message": self.error_message,
            "error_stacktrace": self.error_stacktrace,
            "email_sent": self.email_sent,
            "notification_error": self.notification_error,
            "triggered_by": self.triggered_by,
            "trigger_cause": self.trigger_cause,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def _format_duration(self, seconds):
        """Format duration in human-readable format"""
        if not seconds:
            return None

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
