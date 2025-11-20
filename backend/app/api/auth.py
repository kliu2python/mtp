"""Authentication API - Local user registration and login"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.config import settings
from app.schemas.auth import (
    UserRegister, UserLogin, UserResponse, Token,
    PasswordChange, PasswordReset, UserUpdate
)
from app.services.auth_service import auth_service
from app.models.user import User, AuthProvider

router = APIRouter()
logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        token: JWT token from request header
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = auth_service.decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new local user

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user object
    """
    # Create user
    user = auth_service.create_user(
        db=db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        auth_provider=AuthProvider.LOCAL
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    logger.info(f"User registered: {user.username}")
    return user.to_dict()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password (OAuth2 compatible)

    Args:
        form_data: OAuth2 form data (username, password)
        db: Database session

    Returns:
        JWT access token
    """
    # Authenticate user
    user = auth_service.authenticate_user(
        db=db,
        username=form_data.username,
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = auth_service.generate_user_token(user)

    logger.info(f"User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user.to_dict()
    }


@router.post("/login/json", response_model=Token)
async def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with JSON payload (alternative to OAuth2 form)

    Args:
        credentials: User login credentials
        db: Database session

    Returns:
        JWT access token
    """
    # Authenticate user
    user = auth_service.authenticate_user(
        db=db,
        username=credentials.username,
        password=credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Generate token
    access_token = auth_service.generate_user_token(user)

    logger.info(f"User logged in: {user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user.to_dict()
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user profile

    Args:
        current_user: Current authenticated user

    Returns:
        User profile
    """
    return current_user.to_dict()


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile

    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user profile
    """
    try:
        if user_update.email:
            current_user.email = user_update.email

        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name

        db.commit()
        db.refresh(current_user)

        logger.info(f"User profile updated: {current_user.username}")
        return current_user.to_dict()

    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password

    Args:
        password_change: Password change data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Verify current password
    if current_user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for non-local users"
        )

    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password set for this account"
        )

    if not auth_service.verify_password(
        password_change.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    success = auth_service.update_user_password(
        db=db,
        user=current_user,
        new_password=password_change.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    logger.info(f"Password changed for user: {current_user.username}")
    return {"message": "Password updated successfully"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout current user

    Note: In a stateless JWT system, logout is typically handled client-side
    by discarding the token. This endpoint is provided for consistency.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify if the current token is valid

    Args:
        current_user: Current authenticated user

    Returns:
        User info if token is valid
    """
    return {
        "valid": True,
        "user": current_user.to_dict()
    }
