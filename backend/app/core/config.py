"""
Core configuration settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )
    
    # App
    APP_NAME: str = "Test Automation Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/testplatform.db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://frontend:80",
        "https://mtp.qa.fortinet-us.com",
        "http://mtp.qa.fortinet-us.com"
    ]
    
    # File Storage
    UPLOAD_DIR: str = "/test-files"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    # Docker
    DOCKER_HOST: str = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    
    # Appium
    APPIUM_ANDROID_URL: str = os.getenv("APPIUM_ANDROID_URL", "http://appium-android:4723")
    APPIUM_IOS_URL: str = os.getenv("APPIUM_IOS_URL", "http://appium-ios:4724")

    # Device Nodes API (for proxy)
    DEVICE_NODES_API_URL: str = os.getenv("DEVICE_NODES_API_URL", "http://10.160.13.118:8090")
    
    # AI Services
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Jenkins
    JENKINS_URL: str = os.getenv("JENKINS_URL", "http://10.160.13.30:8080/job/mobile_test/")
    JENKINS_USERNAME: str = os.getenv("JENKINS_USERNAME", "taas-api")
    JENKINS_API_TOKEN: str = os.getenv("JENKINS_API_TOKEN", "118eed0315e68f05695c4db245f358f2d0")
    JOB_PATH: dict = {
        "ios17": "mobile_test/FortiToken_Mobile/iOS/iPhone12-ios17/ios17_auto_test",
        "ios16": "mobile_test/FortiToken_Mobile/iOS/iPhone8-ios16/ios16_auto_test",
        "ios18": "mobile_test/FortiToken_Mobile/iOS/iPhone11-ios18/ios18_auto_test",
        "ios15": "mobile_test/FortiToken_Mobile/iOS/iPhone7-ios15/ios15_auto_test"
    }

    # Monitoring
    PROMETHEUS_PORT: int = 9090

    # Mantis
    MANTIS_DB_PATH: str = os.getenv("MANTIS_DB_PATH", "./data/mantis_data.db")
    MANTIS_TABLE_NAME: str = os.getenv("MANTIS_TABLE_NAME", "issues_49_FortiToken")
    
settings = Settings()
