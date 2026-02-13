"""
Warehouse Activity Model
Tracks user activities in the warehouse (fetch, recycle, upload)
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.core.database import Base


class WarehouseActivity(Base):
    """Model for tracking warehouse user activities"""
    __tablename__ = "warehouse_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_email = Column(String, nullable=False, index=True)  # Store user email for display
    user_name = Column(String, nullable=False)  # Store user name for display
    action = Column(String, nullable=False)  # fetch, recycle, upload
    code_type = Column(String, nullable=True)  # FortiGate, FortiAuthenticator, FortiToken, FortiIdentityCloud
    code_value = Column(String, nullable=True)  # The actual code (partial for display)
    count = Column(Integer, nullable=True)  # Number of codes uploaded
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<WarehouseActivity(id={self.id}, user='{self.user_name}', action='{self.action}')>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_email": self.user_email,
            "user_name": self.user_name,
            "action": self.action,
            "code_type": self.code_type,
            "code_value": self.code_value,
            "count": self.count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }