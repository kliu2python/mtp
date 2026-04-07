"""
User Management API endpoints
Manages admin users: create, delete, change password, list
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.models.user import User, UserRole, AuthProvider
from app.services.auth_service import auth_service
from app.services.logger import get_logger

logger = get_logger()

router = APIRouter()


class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    full_name: Optional[str] = None
    role: str = "admin"
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """Password change request model"""
    new_password: str = Field(..., min_length=1)


@router.get("/admin/users", response_model=List[dict])
async def list_users(
    db: Session = Depends(get_db)
):
    """
    List all users
    """
    try:
        users = db.query(User).filter(
            User.deleted_at.is_(None)
        ).all()

        return [user.to_dict(include_sensitive=False) for user in users]
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.post("/admin/users", response_model=dict)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new admin user
    """
    try:
        # Check if username already exists
        existing_user = db.query(User).filter(
            User.username == user_data.username
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' already exists"
            )

        # Check if email already exists
        existing_email = db.query(User).filter(
            User.email == user_data.email
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists"
            )

        # Create new user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=UserRole(user_data.role),
            auth_provider=AuthProvider.LOCAL,
            is_active=True,
            is_superuser=user_data.is_superuser,
            hashed_password=auth_service.hash_password(user_data.password)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"User created: {user_data.username}")
        return new_user.to_dict(include_sensitive=False)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/admin/users/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID
    """
    try:
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id),
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )

        return user.to_dict(include_sensitive=False)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.put("/admin/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a user
    """
    try:
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id),
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )

        # Update fields
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.role is not None:
            user.role = UserRole(user_data.role)
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.is_superuser is not None:
            user.is_superuser = user_data.is_superuser

        db.commit()
        db.refresh(user)

        logger.info(f"User updated: {user.username}")
        return user.to_dict(include_sensitive=False)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Soft delete a user
    """
    try:
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id),
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )

        # Soft delete
        from datetime import datetime
        user.deleted_at = datetime.utcnow()

        db.commit()

        logger.info(f"User deleted: {user.username}")
        return {"message": f"User {user.username} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post("/admin/users/{user_id}/change-password")
async def change_user_password(
    user_id: str,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Change a user's password
    """
    try:
        user = db.query(User).filter(
            User.id == uuid.UUID(user_id),
            User.deleted_at.is_(None)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )

        # Update password
        user.hashed_password = auth_service.hash_password(password_data.new_password)
        db.commit()

        logger.info(f"Password changed for user: {user.username}")
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
