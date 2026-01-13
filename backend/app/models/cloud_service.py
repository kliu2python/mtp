"""Cloud service configuration model."""
from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class CloudService(Base):
    """Represents a cloud service endpoint available to the test platform."""

    __tablename__ = "cloud_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    server_ip = Column(String, nullable=True)
    server_dns = Column(String, nullable=True)
    client_ip = Column(String, nullable=False)
    server_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def display_name(self) -> Optional[str]:
        """Return the preferred display name for the cloud service."""
        return self.name or self.server_dns or self.server_ip or self.client_ip

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.display_name(),
            "server_ip": self.server_ip,
            "server_dns": self.server_dns,
            "client_ip": self.client_ip,
            "server_version": self.server_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
