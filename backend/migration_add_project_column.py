"""
Migration script to add project column to release_candidate_tests table
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import sqlite3
import os

def migrate_sqlite():
    """Migrate SQLite database"""
    # For SQLite, we need to use raw SQL
    db_path = settings.DATABASE_URL.replace('sqlite:///', '')

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add the column
        cursor.execute("ALTER TABLE release_candidate_tests ADD COLUMN project TEXT DEFAULT 'ftm'")
        print("Added project column to release_candidate_tests table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column already exists")
        else:
            print(f"Error adding column: {e}")

    # Update all existing records to have project='ftm' if they don't have a project value
    cursor.execute("UPDATE release_candidate_tests SET project = 'ftm' WHERE project IS NULL")
    print("Updated existing records with project='ftm'")

    conn.commit()
    conn.close()

def migrate_postgresql():
    """Migrate PostgreSQL database"""
    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Add the column
            conn.execute(text("ALTER TABLE release_candidate_tests ADD COLUMN IF NOT EXISTS project VARCHAR DEFAULT 'ftm'"))
            print("Added project column to release_candidate_tests table")

            # Update all existing records to have project='ftm' if they don't have a project value
            conn.execute(text("UPDATE release_candidate_tests SET project = 'ftm' WHERE project IS NULL"))
            print("Updated existing records with project='ftm'")

            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Error during migration: {e}")

def migrate():
    if settings.DATABASE_URL.startswith("sqlite"):
        migrate_sqlite()
    else:
        migrate_postgresql()

if __name__ == "__main__":
    migrate()
    print("Migration completed successfully!")