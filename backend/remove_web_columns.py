#!/usr/bin/env python3
"""
Script to remove the web_* columns from the virtual_machines table in PostgreSQL.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.core.config import settings

def remove_web_columns():
    """Remove web_* columns from virtual_machines table"""
    try:
        # Use the actual PostgreSQL database URL from the docker-compose.yml
        database_url = "postgresql://testuser:testpass@db:5432/testplatform"

        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            print(f"Working with database: {database_url}")

            # Columns to remove
            columns_to_remove = ['web_url', 'web_username', 'web_password']

            for column in columns_to_remove:
                try:
                    # Check if the column exists
                    result = db.execute(text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'virtual_machines'
                        AND column_name = :column_name
                    """), {"column_name": column})

                    if result.fetchone():
                        # Remove the column
                        db.execute(text(f"ALTER TABLE virtual_machines DROP COLUMN {column}"))
                        print(f"Successfully removed column {column} from virtual_machines table")
                    else:
                        print(f"Column {column} does not exist in virtual_machines table")
                except Exception as e:
                    print(f"Error removing column {column}: {e}")

            db.commit()
            print("Successfully removed web_* columns from virtual_machines table")
            return True

        except Exception as e:
            db.rollback()
            print(f"Error removing web_* columns: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        print(f"Failed to connect to database or perform operation: {e}")
        return False

if __name__ == "__main__":
    print("Running database migration to remove web_* columns...")
    success = remove_web_columns()
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")
        sys.exit(1)