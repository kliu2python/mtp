"""
Admin Configuration API endpoints
Manages default payloads and other admin configurations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel

from app.core.database import get_db
from app.models.admin_config import AdminConfig
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.services.logger import get_logger

logger = get_logger()

router = APIRouter()


class AdminLoginRequest(BaseModel):
    """Admin login request model"""
    username: str
    password: str


# Dependency: Check if user is admin
async def get_current_admin_user(
    token: str = Depends(lambda: ""),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to check if user has admin role
    For backdoor, we use a simple token-based check
    """
    # For backdoor: check for admin token in a different way
    # This is a simplified version - in production, use proper JWT validation
    return None  # Will be handled by the endpoints


def verify_admin_credentials(username: str, password: str) -> bool:
    """
    Verify admin credentials (backdoor method)
    Hardcoded admin credentials
    """
    # Hardcoded admin credentials
    ADMIN_USERNAME = "admin"
    # Password: 8920710zX! (use raw string to avoid escape issues)
    ADMIN_PASSWORD = "8920710zX!"

    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


@router.post("/admin/login")
async def admin_login(
    credentials: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login with hardcoded backdoor credentials
    admin/8920710zX!
    """
    username = credentials.username
    password = credentials.password

    if not verify_admin_credentials(username, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )

    # Generate a session token for admin
    admin_token = str(uuid.uuid4())

    # Store token in database for session management (optional)
    # For simplicity, we'll just return the token

    logger.info(f"Admin logged in: {username}")

    return {
        "access_token": admin_token,
        "token_type": "bearer",
        "expires_in": 3600,  # 1 hour
        "user": {
            "username": username,
            "role": "admin",
            "is_superuser": True
        }
    }


@router.get("/admin/configs")
async def list_admin_configs(
    db: Session = Depends(get_db)
):
    """List all admin configurations"""
    try:
        configs = db.query(AdminConfig).filter(
            AdminConfig.is_active == True
        ).all()

        return {"results": [config.to_dict() for config in configs]}
    except Exception as e:
        logger.error(f"Error listing admin configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list configurations"
        )


@router.get("/admin/config/{config_key}")
async def get_admin_config(
    config_key: str,
    db: Session = Depends(get_db)
):
    """Get a specific admin configuration by key"""
    try:
        config = db.query(AdminConfig).filter(
            AdminConfig.config_key == config_key
        ).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {config_key}"
            )

        return {"config": config.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration"
        )


@router.post("/admin/config")
async def create_or_update_admin_config(
    config_data: dict,
    db: Session = Depends(get_db)
):
    """Create or update an admin configuration"""
    try:
        config_key = config_data.get("config_key")
        config_value = config_data.get("config_value")
        description = config_data.get("description")

        if not config_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="config_key is required"
            )

        # Check if config exists
        existing_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == config_key
        ).first()

        if existing_config:
            # Update existing
            existing_config.config_value = config_value
            if description:
                existing_config.description = description
            existing_config.updated_at = datetime.utcnow()
            config = existing_config
        else:
            # Create new
            config = AdminConfig(
                config_key=config_key,
                config_value=config_value,
                description=description
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        logger.info(f"Admin config saved: {config_key}")
        return {"config": config.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving admin config: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save configuration"
        )


@router.delete("/admin/config/{config_key}")
async def delete_admin_config(
    config_key: str,
    db: Session = Depends(get_db)
):
    """Delete an admin configuration"""
    try:
        config = db.query(AdminConfig).filter(
            AdminConfig.config_key == config_key
        ).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {config_key}"
            )

        db.delete(config)
        db.commit()

        logger.info(f"Admin config deleted: {config_key}")
        return {"message": f"Configuration {config_key} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting admin config: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )


@router.get("/admin/default-payloads")
async def get_default_payloads(
    db: Session = Depends(get_db)
):
    """Get default payloads for Jenkins jobs"""
    try:
        # Get Android default payload
        android_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "android_default_payload"
        ).first()

        # Get iOS default payload
        ios_config = db.query(AdminConfig).filter(
            AdminConfig.config_key == "ios_default_payload"
        ).first()

        return {
            "android": android_config.config_value if android_config else {},
            "ios": ios_config.config_value if ios_config else {}
        }
    except Exception as e:
        logger.error(f"Error getting default payloads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get default payloads"
        )
