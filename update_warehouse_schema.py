#!/usr/bin/env python3
"""
Script to update warehouse_activities table schema to match the model definition
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import uuid

def update_warehouse_activities_schema():
    """Update the warehouse_activities table schema to match the model"""

    # Connect to the database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="testplatform",
        user="testuser",
        password="testpass"
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        print("Connected to database. Updating warehouse_activities table schema...")

        # Get current columns
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'warehouse_activities'
            ORDER BY ordinal_position
        """)

        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        print(f"Current columns: {column_names}")

        # Handle id column - needs to be UUID type
        # Since we can't easily convert an integer id to UUID, we'll need to recreate the table
        # First, let's check if the id column is integer
        cursor.execute("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'warehouse_activities' AND column_name = 'id'
        """)

        id_column_info = cursor.fetchone()
        if id_column_info and id_column_info[0] == 'integer':
            print("Converting id column from integer to UUID...")

            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE warehouse_activities_new (
                    id UUID PRIMARY KEY,
                    user_email VARCHAR,
                    user_name VARCHAR NOT NULL,
                    action VARCHAR,
                    code_type VARCHAR,
                    code_value VARCHAR,
                    count INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            # Copy data from old table to new table with UUID conversion
            # For existing records, we'll generate random UUIDs
            cursor.execute("""
                INSERT INTO warehouse_activities_new
                (id, user_email, user_name, action, code_type, code_value, count, created_at)
                SELECT
                    gen_random_uuid(),
                    user_email,
                    user_name,
                    action,
                    code_type,
                    code_value,
                    count,
                    created_at
                FROM warehouse_activities
            """)

            # Drop old table and rename new one
            cursor.execute("DROP TABLE warehouse_activities")
            cursor.execute("ALTER TABLE warehouse_activities_new RENAME TO warehouse_activities")

            # Add indexes
            cursor.execute("CREATE INDEX ix_warehouse_activities_action ON warehouse_activities (action)")
            cursor.execute("CREATE INDEX ix_warehouse_activities_code_type ON warehouse_activities (code_type)")
            cursor.execute("CREATE INDEX ix_warehouse_activities_created_at ON warehouse_activities (created_at)")
            cursor.execute("CREATE INDEX ix_warehouse_activities_user_email ON warehouse_activities (user_email)")

        # Show final schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'warehouse_activities'
            ORDER BY ordinal_position
        """)

        final_columns = cursor.fetchall()
        print("\nFinal table schema:")
        for col in final_columns:
            print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")

        print("Schema update completed successfully!")

    except Exception as e:
        print(f"Error updating schema: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_warehouse_activities_schema()