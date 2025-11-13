"""
Jenkins Slave Node models for connection pool management
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class NodeStatus(str, enum.Enum):
    """Node status enum"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    TESTING = "testing"


class JenkinsNode(Base):
    """Jenkins Slave Node model for test execution pool"""
    __tablename__ = "jenkins_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)

    # SSH Connection details
    host = Column(String, nullable=False)
    port = Column(Integer, default=22, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=True)
    ssh_key = Column(String, nullable=True)  # Path to SSH private key

    # Node capabilities
    max_executors = Column(Integer, default=2, nullable=False)  # Max parallel tests
    current_executors = Column(Integer, default=0, nullable=False)  # Currently running
    labels = Column(JSON, default=list)  # e.g., ["android", "ios", "linux"]

    # Status and health
    status = Column(SQLEnum(NodeStatus), default=NodeStatus.OFFLINE)
    enabled = Column(Boolean, default=True)
    last_ping_time = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)

    # Metrics
    total_tests_executed = Column(Integer, default=0)
    total_tests_passed = Column(Integer, default=0)
    total_tests_failed = Column(Integer, default=0)
    average_test_duration = Column(Integer, default=0)  # in seconds

    # Resource usage
    cpu_usage = Column(Integer, default=0)  # percentage
    memory_usage = Column(Integer, default=0)  # percentage
    disk_usage = Column(Integer, default=0)  # percentage

    # Metadata
    tags = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "max_executors": self.max_executors,
            "current_executors": self.current_executors,
            "available_executors": self.max_executors - self.current_executors,
            "labels": self.labels,
            "status": self.status.value if self.status else None,
            "enabled": self.enabled,
            "last_ping_time": self.last_ping_time.isoformat() if self.last_ping_time else None,
            "last_error": self.last_error,
            "total_tests_executed": self.total_tests_executed,
            "total_tests_passed": self.total_tests_passed,
            "total_tests_failed": self.total_tests_failed,
            "pass_rate": round(self.total_tests_passed / self.total_tests_executed * 100, 2) if self.total_tests_executed > 0 else 0,
            "average_test_duration": self.average_test_duration,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
