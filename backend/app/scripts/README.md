# Database Migration Scripts

This directory contains scripts for migrating existing file-based data to the new database system.

## Scripts

### migrate_licenses_to_db.py
Migrates existing FortiGate/FortiAuthenticator license data from the file system to the database.

### migrate_fortitokens_to_db.py
Migrates existing FortiToken data from the file system to the database.

### test_database_integration.py
Tests that the database integration is working correctly.

## Usage

Run the migration scripts after upgrading to the new version:

```bash
# Navigate to the backend directory
cd /path/to/backend

# Run the license migration
python app/scripts/migrate_licenses_to_db.py

# Run the FortiToken migration
python app/scripts/migrate_fortitokens_to_db.py

# Test the database integration
python app/scripts/test_database_integration.py
```

## How It Works

1. The migration scripts scan the existing file-based data directories
2. For each PDF file, they extract the code and metadata
3. They create database entries with the appropriate status
4. The existing file-based system continues to work for backward compatibility
5. New operations use the database for better tracking and state management

## Benefits

- Proper state tracking (available → used → recycled → available)
- Better querying and reporting capabilities
- Eliminates the need for artificial file creation during recycling
- Maintains relationship between codes and original files
- Enables better history tracking and auditing