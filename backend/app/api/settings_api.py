import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.settings import PlatformSettingsResponse, UpdatePlatformSettings
from app.services.settings_service import platform_settings_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=PlatformSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Fetch the persisted platform settings."""
    try:
        return platform_settings_service.get_settings(db)
    except Exception as exc:
        logger.error("Failed to load platform settings: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load settings"
        )


@router.put("", response_model=PlatformSettingsResponse)
def update_settings(payload: UpdatePlatformSettings, db: Session = Depends(get_db)):
    """Update and persist platform settings."""
    try:
        updates = payload.model_dump(exclude_unset=True)
        return platform_settings_service.update_settings(db, updates)
    except Exception as exc:
        logger.error("Failed to update platform settings: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update settings"
        )
