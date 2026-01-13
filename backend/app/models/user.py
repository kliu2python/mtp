"""
User Model
Handles both local users and SAML-authenticated users
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enum"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class AuthProvider(str, enum.Enum):
    """Authentication provider enum"""
    LOCAL = "local"
    SAML = "saml"


class User(Base):
    """User model - supports both local and SAML authentication"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Info
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)

    # Local Authentication
    hashed_password = Column(String, nullable=True)  # Only for local users

    # SAML Authentication
    saml_name_id = Column(String, nullable=True, index=True)  # SAML NameID
    saml_session_index = Column(String, nullable=True)  # For SLO
    saml_attributes = Column(JSON, default=dict)  # SAML user attributes

    # Authentication Provider
    auth_provider = Column(SQLEnum(AuthProvider), default=AuthProvider.LOCAL, nullable=False)

    # Authorization
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Permissions (JSON array of permission strings)
    permissions = Column(JSON, default=list)

    # Session Management
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "auth_provider": self.auth_provider.value if self.auth_provider else None,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "permissions": self.permissions,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

        if include_sensitive:
            data.update({
                "saml_name_id": self.saml_name_id,
                "saml_attributes": self.saml_attributes,
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None
            })

        return data

    def is_locked(self):
        """Check if account is locked"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True
        return permission in self.permissions

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return self.role == role
