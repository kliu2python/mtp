"""Authentication Service - Handles user authentication and authorization"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User, AuthProvider, UserRole
from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for local and SAML users"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            data: Data to encode in the token
            expires_delta: Optional expiration time delta

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and verify a JWT token

        Args:
            token: JWT token to decode

        Returns:
            Decoded token data or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        username: str,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        role: UserRole = UserRole.USER,
        **kwargs
    ) -> Optional[User]:
        """
        Create a new user

        Args:
            db: Database session
            email: User email
            username: Username
            password: Password (for local users)
            full_name: Full name
            auth_provider: Authentication provider
            role: User role
            **kwargs: Additional user fields

        Returns:
            Created user or None if failed
        """
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(
                or_(User.email == email, User.username == username)
            ).first()

            if existing_user:
                logger.warning(f"User already exists: {email} or {username}")
                return None

            # Create user
            user_data = {
                "email": email,
                "username": username,
                "full_name": full_name,
                "auth_provider": auth_provider,
                "role": role,
                **kwargs
            }

            # Hash password for local users
            if auth_provider == AuthProvider.LOCAL and password:
                user_data["hashed_password"] = AuthService.hash_password(password)

            user = User(**user_data)
            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(f"User created: {username} ({email}) with provider {auth_provider}")
            return user

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.rollback()
            return None

    @staticmethod
    def authenticate_user(
        db: Session,
        username: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a local user with username and password

        Args:
            db: Database session
            username: Username or email
            password: Password

        Returns:
            Authenticated user or None
        """
        try:
            # Find user by username or email
            user = db.query(User).filter(
                or_(User.username == username, User.email == username)
            ).filter(
                User.auth_provider == AuthProvider.LOCAL,
                User.is_active == True
            ).first()

            if not user:
                logger.warning(f"User not found: {username}")
                return None

            # Check if account is locked
            if user.is_locked():
                logger.warning(f"Account locked: {username}")
                return None

            # Verify password
            if not user.hashed_password:
                logger.warning(f"No password set for user: {username}")
                return None

            if not AuthService.verify_password(password, user.hashed_password):
                # Increment failed login attempts
                user.failed_login_attempts += 1

                # Lock account after 5 failed attempts for 30 minutes
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                    logger.warning(f"Account locked due to failed attempts: {username}")

                db.commit()
                logger.warning(f"Invalid password for user: {username}")
                return None

            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            db.commit()

            logger.info(f"User authenticated: {username}")
            return user

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return db.query(User).filter(User.id == user_id, User.is_active == True).first()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return db.query(User).filter(User.username == username, User.is_active == True).first()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return db.query(User).filter(User.email == email, User.is_active == True).first()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    @staticmethod
    def get_or_create_saml_user(
        db: Session,
        saml_name_id: str,
        saml_attributes: Dict[str, Any]
    ) -> Optional[User]:
        """
        Get or create a user from SAML attributes

        Args:
            db: Database session
            saml_name_id: SAML NameID
            saml_attributes: SAML user attributes

        Returns:
            User object
        """
        try:
            # Try to find existing SAML user
            user = db.query(User).filter(
                User.saml_name_id == saml_name_id,
                User.auth_provider == AuthProvider.SAML
            ).first()

            if user:
                # Update SAML attributes
                user.saml_attributes = saml_attributes
                user.last_login = datetime.utcnow()
                db.commit()
                db.refresh(user)
                logger.info(f"SAML user logged in: {user.username}")
                return user

            # Extract user info from SAML attributes
            email = saml_attributes.get('email', [None])[0]
            username = saml_attributes.get('username', [None])[0] or email.split('@')[0] if email else None
            full_name = saml_attributes.get('displayName', [None])[0] or saml_attributes.get('cn', [None])[0]

            if not email or not username:
                logger.error("Missing required SAML attributes: email or username")
                return None

            # Create new SAML user
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                auth_provider=AuthProvider.SAML,
                saml_name_id=saml_name_id,
                saml_attributes=saml_attributes,
                role=UserRole.USER,
                is_active=True,
                last_login=datetime.utcnow()
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            logger.info(f"SAML user created: {username} ({email})")
            return user

        except Exception as e:
            logger.error(f"Error getting/creating SAML user: {e}")
            db.rollback()
            return None

    @staticmethod
    def update_user_password(
        db: Session,
        user: User,
        new_password: str
    ) -> bool:
        """Update user password"""
        try:
            if user.auth_provider != AuthProvider.LOCAL:
                logger.warning(f"Cannot update password for non-local user: {user.username}")
                return False

            user.hashed_password = AuthService.hash_password(new_password)
            db.commit()

            logger.info(f"Password updated for user: {user.username}")
            return True

        except Exception as e:
            logger.error(f"Error updating password: {e}")
            db.rollback()
            return False

    @staticmethod
    def generate_user_token(user: User) -> str:
        """Generate JWT token for user"""
        token_data = {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value
        }

        access_token = AuthService.create_access_token(data=token_data)
        return access_token


# Global auth service instance
auth_service = AuthService()
