"""
Test script to verify database integration for licenses and fortitokens
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path so we can import the models
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.core.database import _build_engine_kwargs
from app.models.license import License
from app.models.fortitoken import FortiToken

def test_database_integration():
    """Test that the database models are working correctly"""

    # Create database engine
    engine_kwargs = _build_engine_kwargs(settings.DATABASE_URL)
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Test License model
        print("Testing License model...")
        license_count = db.query(License).count()
        print(f"Found {license_count} licenses in database")

        # Show first few licenses
        licenses = db.query(License).limit(5).all()
        for license in licenses:
            print(f"  - License: {license.filename} ({license.code}) - Status: {license.status}")

        # Test FortiToken model
        print("\nTesting FortiToken model...")
        fortitoken_count = db.query(FortiToken).count()
        print(f"Found {fortitoken_count} FortiTokens in database")

        # Show first few FortiTokens
        fortitokens = db.query(FortiToken).limit(5).all()
        for fortitoken in fortitokens:
            print(f"  - FortiToken: {fortitoken.filename} ({fortitoken.code}) - Status: {fortitoken.status}")

        print("\nDatabase integration test completed successfully!")

    except Exception as e:
        print(f"Error during database integration test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database_integration()