"""
Test Device models
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class DeviceType(str, enum.Enum):
    """Device type enum"""
    PHYSICAL_IOS = "physical_ios"
    PHYSICAL_ANDROID = "physical_android"
    EMULATOR_IOS = "emulator_ios"
    EMULATOR_ANDROID = "emulator_android"
    CLOUD_IOS = "cloud_ios"
    CLOUD_ANDROID = "cloud_android"


class DeviceStatus(str, enum.Enum):
    """Device status enum"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TestDevice(Base):
    """Test Device model"""
    __tablename__ = "test_devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    device_type = Column(SQLEnum(DeviceType), nullable=False)
    platform = Column(String, nullable=False)  # iOS, Android
    os_version = Column(String, nullable=False)
    
    # Connection info
    connection_type = Column(String, default="usb")  # usb, wifi, cloud
    device_id = Column(String, nullable=False, unique=True)  # UDID or Serial
    adb_id = Column(String, nullable=True)  # Android only
    appium_url = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.AVAILABLE)
    current_test_id = Column(UUID(as_uuid=True), nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    # Capabilities
    capabilities = Column(JSON, default=dict)
    supported_apps = Column(JSON, default=list)
    
    # Resources
    battery_level = Column(Integer, default=100)
    storage_free = Column(Integer, default=0)  # MB
    
    # Metadata
    location = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "device_type": self.device_type.value if self.device_type else None,
            "platform": self.platform,
            "os_version": self.os_version,
            "connection_type": self.connection_type,
            "device_id": self.device_id,
            "adb_id": self.adb_id,
            "appium_url": self.appium_url,
            "status": self.status.value if self.status else None,
            "current_test_id": str(self.current_test_id) if self.current_test_id else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "capabilities": self.capabilities,
            "supported_apps": self.supported_apps,
            "battery_level": self.battery_level,
            "storage_free": self.storage_free,
            "location": self.location,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
