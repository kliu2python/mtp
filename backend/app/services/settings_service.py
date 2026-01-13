"""Service for managing persisted platform settings."""
from sqlalchemy.orm import Session

from app.core.config import settings as config_settings
from app.models.settings import PlatformSettings


class PlatformSettingsService:
    """Encapsulates CRUD operations for platform settings."""

    def get_settings(self, db: Session) -> PlatformSettings:
        """Return the existing settings row or create one with defaults."""
        settings = db.query(PlatformSettings).first()
        if settings is None:
            settings = PlatformSettings(
                jenkins_url=config_settings.JENKINS_URL,
                jenkins_username=config_settings.JENKINS_USERNAME,
                jenkins_api_token=config_settings.JENKINS_API_TOKEN,
                ai_provider="openai",
                ai_model="gpt-4.1",
                artifact_storage_path="/var/lib/mtp/artifacts",
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    def update_settings(self, db: Session, updates: dict) -> PlatformSettings:
        """Persist provided settings values."""
        settings = self.get_settings(db)
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings


platform_settings_service = PlatformSettingsService()
