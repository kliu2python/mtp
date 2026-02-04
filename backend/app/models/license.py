"""
Database model for FortiGate/FortiAuthenticator/FortiIdentity Cloud Licenses
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    license_type = Column(String)  # FortiGate, FortiAuthenticator, FortiIdentity Cloud
    status = Column(String, default="available")  # available, used, recycled
    size = Column(String, nullable=True)  # Size information for FortiIdentity Cloud codes
    original_content = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    recycled_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<License(id={self.id}, filename='{self.filename}', code='{self.code}', status='{self.status}')>"