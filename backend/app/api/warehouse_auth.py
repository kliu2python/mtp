"""
Warehouse Authentication API
Endpoints for OTP generation, verification, and activity logging
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.warehouse_otp import WarehouseOTP
from app.models.warehouse_activity import WarehouseActivity
from app.services.warehouse_auth_service import warehouse_auth_service
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateOTPRequest(BaseModel):
    """Request model for generating OTP"""
    email: str


class VerifyOTPRequest(BaseModel):
    """Request model for verifying OTP"""
    email: str
    otp_code: str


class OTPResponse(BaseModel):
    """Response model for OTP operations"""
    success: bool
    message: str
    expires_at: Optional[str] = None


class WarehouseActivityResponse(BaseModel):
    """Response model for warehouse activities"""
    id: str
    user_email: str
    user_name: str
    action: str
    code_type: Optional[str] = None
    code_value: Optional[str] = None
    count: Optional[int] = None
    created_at: str


@router.post("/generate-otp", response_model=OTPResponse)
async def generate_otp(request: GenerateOTPRequest, db: Session = Depends(get_db)):
    """
    Generate and send OTP to the user's @fortinet.com email

    Args:
        request: Email address to send OTP to
        db: Database session

    Returns:
        OTPResponse indicating success or failure
    """
    email = request.email.strip().lower()

    # Validate email domain
    if not email.endswith('@fortinet.com'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only @fortinet.com email addresses are allowed"
        )

    # Generate and send OTP
    otp_record = warehouse_auth_service.create_otp_for_email(db, email)

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate or send OTP"
        )

    return OTPResponse(
        success=True,
        message="OTP sent to your email",
        expires_at=otp_record.expires_at.isoformat() if otp_record.expires_at else None
    )


@router.post("/verify-otp", response_model=OTPResponse)
async def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP code for the given email

    Args:
        request: Email and OTP code to verify
        db: Database session

    Returns:
        OTPResponse indicating success or failure
    """
    email = request.email.strip().lower()
    otp_code = request.otp_code.strip()

    # Verify OTP
    is_valid = warehouse_auth_service.verify_otp(db, email, otp_code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )

    return OTPResponse(
        success=True,
        message="OTP verified successfully"
    )


@router.get("/activities", response_model=List[WarehouseActivityResponse])
async def get_warehouse_activities(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent warehouse activities

    Args:
        limit: Maximum number of activities to return (default: 50)
        db: Database session

    Returns:
        List of recent warehouse activities
    """
    activities = warehouse_auth_service.get_recent_activities(db, limit)
    return activities


@router.get("/is-authenticated/{email}")
async def is_authenticated(email: str, db: Session = Depends(get_db)):
    """
    Check if user is authenticated (has verified OTP)

    Args:
        email: Email address to check
        db: Database session

    Returns:
        Authentication status
    """
    email = email.strip().lower()
    is_verified = warehouse_auth_service.is_otp_verified(db, email)

    return {
        "email": email,
        "is_authenticated": is_verified
    }