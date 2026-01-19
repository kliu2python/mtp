#!/usr/bin/env python3
"""
Script to remove the api_key column from the virtual_machines table.
For SQLite, we need to recreate the table without the column.
"""

import sys
import os
import sqlite3

# Add the backend directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.config import settings

def remove_api_key_column():
    """Remove api_key column from virtual_machines table"""
    try:
        if settings.DATABASE_URL.startswith('sqlite'):
            db_path = settings.DATABASE_URL.replace('sqlite:///', '')
            print(f"Working with SQLite database: {db_path}")

            # Connect directly to SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            try:
                # Check if the api_key column exists
                cursor.execute("PRAGMA table_info(virtual_machines)")
                columns = cursor.fetchall()
                column_names = [column[1] for column in columns]

                if 'api_key' not in column_names:
                    print("Column api_key does not exist in virtual_machines table")
                    return True

                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")

                # Create new table without api_key column
                cursor.execute("""
                    CREATE TABLE virtual_machines_new (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        platform TEXT NOT NULL,
                        version TEXT NOT NULL,
                        ip_address TEXT,
                        ssh_username TEXT,
                        ssh_password TEXT,
                        web_url TEXT,
                        web_username TEXT,
                        web_password TEXT,
                        provider TEXT,
                        status TEXT,
                        docker_container_id TEXT,
                        test_priority INTEGER,
                        total_tests INTEGER,
                        passed_tests INTEGER,
                        failed_tests INTEGER,
                        last_test_time TIMESTAMP,
                        cpu_usage REAL,
                        memory_usage REAL,
                        disk_usage REAL,
                        tags TEXT,
                        config TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                """)

                # Copy data from old table to new table (excluding api_key)
                cursor.execute("""
                    INSERT INTO virtual_machines_new
                    SELECT id, name, platform, version, ip_address, ssh_username,
                           ssh_password, web_url, web_username, web_password,
                           provider, status, docker_container_id, test_priority,
                           total_tests, passed_tests, failed_tests, last_test_time,
                           cpu_usage, memory_usage, disk_usage, tags, config,
                           created_at, updated_at
                    FROM virtual_machines
                """)

                # Drop old table
                cursor.execute("DROP TABLE virtual_machines")

                # Rename new table to original name
                cursor.execute("ALTER TABLE virtual_machines_new RENAME TO virtual_machines")

                # Recreate the index
                cursor.execute("CREATE UNIQUE INDEX ix_virtual_machines_name ON virtual_machines (name)")

                # Commit transaction
                conn.commit()
                print("Successfully removed api_key column from virtual_machines table")
                return True

            except Exception as e:
                conn.rollback()
                print(f"Error removing api_key column: {e}")
                return False
            finally:
                conn.close()
        else:
            print("This script only supports SQLite databases")
            return False

    except Exception as e:
        print(f"Failed to connect to database or perform operation: {e}")
        return False

if __name__ == "__main__":
    print("Running database migration to remove api_key column...")
    success = remove_api_key_column()
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")
        sys.exit(1)