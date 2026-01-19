#!/usr/bin/env python3
"""
Script to add the api_key column to the virtual_machines table in PostgreSQL.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.core.config import settings

def add_api_key_column():
    """Add api_key column to virtual_machines table"""
    try:
        # Use the actual PostgreSQL database URL from the docker-compose.yml
        database_url = "postgresql://testuser:testpass@db:5432/testplatform"

        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            print(f"Working with database: {database_url}")

            # Check if the api_key column exists
            result = db.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'virtual_machines'
                AND column_name = 'api_key'
            """))

            if result.fetchone():
                print("Column api_key already exists in virtual_machines table")
                return True

            # Add the api_key column
            db.execute(text("ALTER TABLE virtual_machines ADD COLUMN api_key VARCHAR"))
            db.commit()
            print("Successfully added api_key column to virtual_machines table")
            return True

        except Exception as e:
            db.rollback()
            print(f"Error adding api_key column: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        print(f"Failed to connect to database or perform operation: {e}")
        return False

if __name__ == "__main__":
    print("Running database migration to add api_key column...")
    success = add_api_key_column()
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")
        sys.exit(1)