"""
Test Execution Model - Stores test execution history in database
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class TestStatus(str, enum.Enum):
    """Test execution status"""
    QUEUED = "queued"
    ACQUIRING_NODE = "acquiring_node"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestExecution(Base):
    """Model for storing test execution data"""
    __tablename__ = "test_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String, unique=True, nullable=False, index=True)

    # Configuration
    config = Column(JSON, nullable=False)

    # Status and progress
    status = Column(SQLEnum(TestStatus), nullable=False, default=TestStatus.QUEUED)
    progress = Column(Integer, default=0)

    # Results
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Node information
    node_id = Column(String, nullable=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Report paths
    allure_report_path = Column(String, nullable=True)
    html_report_path = Column(String, nullable=True)

    def to_dict(self):
        """Convert to dictionary"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "task_id": self.task_id,
            "config": self.config,
            "status": self.status.value if isinstance(self.status, TestStatus) else self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "node_id": self.node_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": duration,
            "allure_report_path": self.allure_report_path,
            "html_report_path": self.html_report_path,
        }
