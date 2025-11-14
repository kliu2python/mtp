"""
Virtual Machine models
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class VMStatus(str, enum.Enum):
    """VM status enum"""
    RUNNING = "running"
    STOPPED = "stopped"
    TESTING = "testing"
    FAILED = "failed"
    PROVISIONING = "provisioning"


class VMPlatform(str, enum.Enum):
    """VM platform enum"""
    FORTIGATE = "FortiGate"
    FORTIAUTHENTICATOR = "FortiAuthenticator"


class VMProvider(str, enum.Enum):
    """VM provider enum"""
    DOCKER = "DOCKER"
    OPENSTACK = "OPENSTACK"


class VirtualMachine(Base):
    """Virtual Machine model"""
    __tablename__ = "virtual_machines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    platform = Column(SQLEnum(VMPlatform), nullable=False)
    version = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    ssh_username = Column(String, nullable=True)
    ssh_password = Column(String, nullable=True)
    status = Column(SQLEnum(VMStatus), default=VMStatus.STOPPED)
    docker_container_id = Column(String, nullable=True)
    
    # Test metrics
    test_priority = Column(Integer, default=3)  # 1-5
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    last_test_time = Column(DateTime, nullable=True)
    
    # Resource usage
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    
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
            "platform": self.platform.value if self.platform else None,
            "version": self.version,
            "ip_address": self.ip_address,
            "ssh_username": self.ssh_username,
            "ssh_password": self.ssh_password,
            "status": self.status.value if self.status else None,
            "docker_container_id": self.docker_container_id,
            "test_priority": self.test_priority,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": round(self.passed_tests / self.total_tests * 100, 2) if self.total_tests > 0 else 0,
            "last_test_time": self.last_test_time.isoformat() if self.last_test_time else None,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TestRecord(Base):
    __tablename__ = "test_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vm_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    test_suite = Column(String, nullable=False)
    test_case = Column(String, nullable=False)
    status = Column(String, nullable=False)
    duration = Column(Float, default=0.0)
    error_message = Column(String, nullable=True)
    screenshot_path = Column(String, nullable=True)
    log_path = Column(String, nullable=True)

    # FIXED HERE:
    meta = Column("metadata", JSON, default=dict)

    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "vm_id": str(self.vm_id),
            "test_suite": self.test_suite,
            "test_case": self.test_case,
            "status": self.status,
            "duration": self.duration,
            "error_message": self.error_message,
            "screenshot_path": self.screenshot_path,
            "log_path": self.log_path,
            "metadata": self.meta,          # return original key
            "executed_at": self.executed_at.isoformat() if self.executed_at else None
        }

