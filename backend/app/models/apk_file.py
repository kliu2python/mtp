"""
APK/IPA File models for mobile app testing
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AppPlatform(str, enum.Enum):
    """Application platform enum"""
    ANDROID = "android"
    IOS = "ios"


class ApkFile(Base):
    """APK/IPA File model for managing mobile application binaries"""
    __tablename__ = "apk_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    display_name = Column(String, nullable=False)  # User-friendly name
    platform = Column(SQLEnum(AppPlatform), nullable=False)

    # File info
    file_path = Column(String, nullable=False, unique=True)
    file_size = Column(Integer, default=0)  # bytes
    file_hash = Column(String, nullable=True)  # SHA256

    # App metadata (parsed from APK/IPA)
    package_name = Column(String, nullable=True)  # com.fortinet.fac
    version_name = Column(String, nullable=True)  # 1.2.3
    version_code = Column(Integer, nullable=True)  # 123
    min_sdk_version = Column(String, nullable=True)  # Android only
    target_sdk_version = Column(String, nullable=True)  # Android only
    bundle_id = Column(String, nullable=True)  # iOS only

    # Additional metadata
    description = Column(String, nullable=True)
    tags = Column(JSON, default=list)  # ["fac", "production", "v1.2.3"]
    app_metadata = Column(JSON, default=dict)  # Extra parsed metadata

    # Status
    is_active = Column(Boolean, default=True)
    uploaded_by = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "display_name": self.display_name,
            "platform": self.platform.value if self.platform else None,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "package_name": self.package_name,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "min_sdk_version": self.min_sdk_version,
            "target_sdk_version": self.target_sdk_version,
            "bundle_id": self.bundle_id,
            "description": self.description,
            "tags": self.tags,
            "app_metadata": self.app_metadata,
            "is_active": self.is_active,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
