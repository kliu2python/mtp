"""
Admin Configuration Model
Stores admin configurations including default payloads for Jenkins jobs
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base


class AdminConfig(Base):
    """Admin configuration model - stores default payloads and other admin settings"""
    __tablename__ = "admin_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Config key for lookup
    config_key = Column(String, unique=True, nullable=False, index=True)

    # Config value (JSON)
    config_value = Column(JSON, default=dict)

    # Description
    description = Column(Text, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    # Created by (admin username)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by
        }
