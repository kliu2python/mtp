from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class PlatformSettings(Base):
    """Persisted platform-wide integration and AI settings."""

    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, default=1)
    jenkins_url = Column(String, nullable=True)
    jenkins_username = Column(String, nullable=True)
    jenkins_api_token = Column(String, nullable=True)

    ai_provider = Column(String, default="openai")
    ai_base_url = Column(String, nullable=True)
    ai_api_key = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)

    artifact_storage_path = Column(String, default="/var/lib/mtp/artifacts")
    notification_email = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
