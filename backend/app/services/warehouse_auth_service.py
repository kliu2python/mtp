"""
Warehouse Authentication Service
Handles OTP generation, verification, and warehouse activity logging
"""
import logging
import random
import string
import smtplib
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
import requests

from app.models.warehouse_otp import WarehouseOTP
from app.models.warehouse_activity import WarehouseActivity
from app.models.user import User

logger = logging.getLogger(__name__)


class WarehouseAuthService:
    """Service for handling warehouse authentication"""

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def send_otp_email(email: str, otp_code: str) -> bool:
        """
        Send OTP email using the reviewfinder API

        Args:
            email: Recipient email address
            otp_code: OTP code to send

        Returns:
            True if email was sent successfully
        """
        try:
            # Call the external API to send OTP
            url = "http://10.160.24.17:30423/reviewfinder/v1/smtp/send"
            payload = {
                "subject": "[mobile test pilot] OTP for warehouse operation",
                "body": f"This is the otp for warehouse operation: {otp_code}",
                "recipients": [email],
                "use_bcc": False
            }

            response = requests.post(url, json=payload)
            response.raise_for_status()

            logger.info(f"OTP sent successfully to {email}")
            return True
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to email service for {email}: {e}")
            # Even if email sending fails, we can still create the OTP in database
            # The frontend will show a warning that email might not be sent
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout when sending OTP to {email}: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send OTP to {email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error when sending OTP to {email}: {e}")
            return False

    def create_otp_for_email(self, db: Session, email: str) -> Optional[WarehouseOTP]:
        """
        Create a new OTP for the given email address (must be @fortinet.com)

        Args:
            db: Database session
            email: Email address to create OTP for

        Returns:
            WarehouseOTP object or None if invalid email
        """
        # Validate email domain
        if not email.endswith('@fortinet.com'):
            logger.warning(f"Invalid email domain for OTP creation: {email}")
            return None

        # Generate new OTP
        otp_code = self.generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)  # 10 minute expiration

        # Check if there's an existing OTP for this email
        existing_otp = db.query(WarehouseOTP).filter(
            WarehouseOTP.email == email
        ).first()

        if existing_otp:
            # Update existing OTP
            existing_otp.otp_code = otp_code
            existing_otp.expires_at = expires_at
            existing_otp.is_verified = False
            existing_otp.verified_at = None
            db.commit()
            db.refresh(existing_otp)
            otp_record = existing_otp
        else:
            # Create new OTP record
            otp_record = WarehouseOTP(
                email=email,
                otp_code=otp_code,
                expires_at=expires_at
            )
            db.add(otp_record)
            db.commit()
            db.refresh(otp_record)

        # Send OTP via email
        if self.send_otp_email(email, otp_code):
            return otp_record
        else:
            # If email fails, delete the OTP record
            db.delete(otp_record)
            db.commit()
            return None

    def verify_otp(self, db: Session, email: str, otp_code: str) -> bool:
        """
        Verify an OTP code for the given email

        Args:
            db: Database session
            email: Email address
            otp_code: OTP code to verify

        Returns:
            True if OTP is valid and verified
        """
        # Find OTP record
        otp_record = db.query(WarehouseOTP).filter(
            WarehouseOTP.email == email
        ).first()

        if not otp_record:
            logger.warning(f"No OTP found for email: {email}")
            return False

        # Check if OTP is valid
        if otp_record.is_valid() and otp_record.otp_code == otp_code:
            # Mark as verified
            otp_record.is_verified = True
            otp_record.verified_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"OTP verified successfully for {email}")
            return True
        else:
            logger.warning(f"Invalid or expired OTP for {email}")
            return False

    def is_otp_verified(self, db: Session, email: str) -> bool:
        """
        Check if there's a verified OTP for the given email

        Args:
            db: Database session
            email: Email address

        Returns:
            True if there's a verified, non-expired OTP
        """
        otp_record = db.query(WarehouseOTP).filter(
            WarehouseOTP.email == email
        ).first()

        if not otp_record:
            return False

        # Check if OTP is verified and not expired
        return otp_record.is_verified and not otp_record.is_expired()

    def log_warehouse_activity(
        self,
        db: Session,
        user_email: str,
        user_name: str,
        action: str,
        code_type: Optional[str] = None,
        code_value: Optional[str] = None,
        count: Optional[int] = None
    ) -> WarehouseActivity:
        """
        Log a warehouse activity

        Args:
            db: Database session
            user_email: User email address
            user_name: User name
            action: Action performed (fetch, recycle, upload)
            code_type: Type of code (FortiGate, FortiAuthenticator, etc.)
            code_value: The code value (partially masked for display)
            count: Number of codes (for uploads)

        Returns:
            WarehouseActivity object
        """
        activity = WarehouseActivity(
            user_email=user_email,
            user_name=user_name,
            action=action,
            code_type=code_type,
            code_value=code_value,
            count=count
        )

        db.add(activity)
        db.commit()
        db.refresh(activity)

        logger.info(f"Warehouse activity logged: {user_name} {action} {code_type or ''}")
        return activity

    def get_recent_activities(self, db: Session, limit: int = 50) -> list:
        """
        Get recent warehouse activities

        Args:
            db: Database session
            limit: Maximum number of activities to return

        Returns:
            List of recent activities
        """
        activities = db.query(WarehouseActivity).order_by(
            WarehouseActivity.created_at.desc()
        ).limit(limit).all()

        return [activity.to_dict() for activity in activities]


# Global instance
warehouse_auth_service = WarehouseAuthService()