"""
Jenkins Job Model
Represents a job definition similar to Jenkins jobs/pipelines
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class JobType(str, enum.Enum):
    """Job type enum"""
    FREESTYLE = "freestyle"  # Simple job with shell commands
    PIPELINE = "pipeline"    # Pipeline job with Jenkinsfile
    DOCKER = "docker"        # Docker-based execution


class JenkinsJob(Base):
    """Jenkins Job model - defines a job/pipeline configuration"""
    __tablename__ = "jenkins_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    job_type = Column(SQLEnum(JobType), default=JobType.DOCKER, nullable=False)

    # Job Configuration
    script = Column(Text, nullable=True)  # Shell script or Jenkinsfile content
    required_labels = Column(JSON, default=list)  # Required agent labels (e.g., ["android", "docker"])

    # Docker Configuration (for docker job type)
    docker_registry = Column(String, nullable=True)
    docker_image = Column(String, nullable=True)
    docker_tag = Column(String, default="latest")

    # Test Configuration
    test_suite = Column(String, nullable=True)
    test_markers = Column(String, nullable=True)
    lab_config = Column(String, nullable=True)
    platform = Column(String, nullable=True)  # android, ios, etc.

    # Workspace Configuration
    workspace_path = Column(String, default="/home/jenkins/workspace")
    config_mount_source = Column(String, default="/home/jenkins/custom_config")

    # Build Options
    max_concurrent_builds = Column(Integer, default=1)
    build_timeout = Column(Integer, default=7200)  # seconds (2 hours default)
    keep_builds = Column(Integer, default=30)  # Number of builds to keep

    # Notification Configuration
    email_recipients = Column(String, nullable=True)
    notify_on_success = Column(Boolean, default=True)
    notify_on_failure = Column(Boolean, default=True)

    # Job State
    enabled = Column(Boolean, default=True)
    next_build_number = Column(Integer, default=1)
    last_build_time = Column(DateTime, nullable=True)
    last_build_status = Column(String, nullable=True)  # SUCCESS, FAILURE, UNSTABLE

    # Statistics
    total_builds = Column(Integer, default=0)
    successful_builds = Column(Integer, default=0)
    failed_builds = Column(Integer, default=0)

    # Additional Configuration
    parameters = Column(JSON, default=dict)  # Job parameters
    environment_vars = Column(JSON, default=dict)  # Environment variables

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "job_type": self.job_type.value if self.job_type else None,
            "required_labels": self.required_labels,
            "docker_registry": self.docker_registry,
            "docker_image": self.docker_image,
            "docker_tag": self.docker_tag,
            "test_suite": self.test_suite,
            "test_markers": self.test_markers,
            "lab_config": self.lab_config,
            "platform": self.platform,
            "workspace_path": self.workspace_path,
            "config_mount_source": self.config_mount_source,
            "max_concurrent_builds": self.max_concurrent_builds,
            "build_timeout": self.build_timeout,
            "keep_builds": self.keep_builds,
            "email_recipients": self.email_recipients,
            "notify_on_success": self.notify_on_success,
            "notify_on_failure": self.notify_on_failure,
            "enabled": self.enabled,
            "next_build_number": self.next_build_number,
            "last_build_time": self.last_build_time.isoformat() if self.last_build_time else None,
            "last_build_status": self.last_build_status,
            "total_builds": self.total_builds,
            "successful_builds": self.successful_builds,
            "failed_builds": self.failed_builds,
            "success_rate": round(self.successful_builds / self.total_builds * 100, 2) if self.total_builds > 0 else 0,
            "parameters": self.parameters,
            "environment_vars": self.environment_vars,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by
        }
