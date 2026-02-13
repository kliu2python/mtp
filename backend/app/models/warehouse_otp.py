"""
Warehouse OTP Model
Stores OTP codes for warehouse authentication
"""
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class WarehouseOTP(Base):
    """Model for storing warehouse OTP codes"""
    __tablename__ = "warehouse_otps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, index=True, unique=True)  # User email (@fortinet.com only)
    otp_code = Column(String, nullable=False)  # Generated OTP code
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Expiration time
    is_verified = Column(Boolean, default=False, nullable=False)  # Whether OTP has been verified
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)  # When OTP was verified

    def __repr__(self):
        return f"<WarehouseOTP(id={self.id}, email='{self.email}', is_verified={self.is_verified})>"

    def is_expired(self):
        """Check if OTP is expired"""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self):
        """Check if OTP is valid (not expired and not verified)"""
        return not self.is_expired() and not self.is_verified

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "email": self.email,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None
        }