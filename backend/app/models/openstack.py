"""
OpenStack models for credential and resource management
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class OpenStackCredential(Base):
    """OpenStack credential model for secure storage"""
    __tablename__ = "openstack_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    auth_url = Column(String, nullable=False)  # e.g., https://openstack.example.com:5000/v3
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # TODO: Encrypt in production
    project_name = Column(String, nullable=False)
    project_domain_name = Column(String, default="Default")
    user_domain_name = Column(String, default="Default")
    region_name = Column(String, nullable=True)

    # Additional configuration
    verify_ssl = Column(Boolean, default=True)
    description = Column(String, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_password=False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "name": self.name,
            "auth_url": self.auth_url,
            "username": self.username,
            "project_name": self.project_name,
            "project_domain_name": self.project_domain_name,
            "user_domain_name": self.user_domain_name,
            "region_name": self.region_name,
            "verify_ssl": self.verify_ssl,
            "description": self.description,
            "is_active": self.is_active,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_password:
            data["password"] = self.password

        return data


class OpenStackImage(Base):
    """Cached OpenStack image information for FGT and FAC"""
    __tablename__ = "openstack_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # OpenStack image details
    openstack_image_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # FortiGate or FortiAuthenticator
    version = Column(String, nullable=True)

    # Image metadata
    size_gb = Column(Integer, nullable=True)
    min_disk = Column(Integer, nullable=True)
    min_ram = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    properties = Column(JSON, default=dict)

    # Tracking
    is_active = Column(Boolean, default=True)
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "credential_id": str(self.credential_id),
            "openstack_image_id": self.openstack_image_id,
            "name": self.name,
            "platform": self.platform,
            "version": self.version,
            "size_gb": self.size_gb,
            "min_disk": self.min_disk,
            "min_ram": self.min_ram,
            "status": self.status,
            "properties": self.properties,
            "is_active": self.is_active,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
