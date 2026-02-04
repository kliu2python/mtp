"""
Database model for FortiTokens
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class FortiToken(Base):
    __tablename__ = "fortitokens"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    code = Column(String, unique=True, index=True)
    status = Column(String, default="available")  # available, used, recycled
    original_content = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    recycled_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<FortiToken(id={self.id}, filename='{self.filename}', code='{self.code}', status='{self.status}')>"