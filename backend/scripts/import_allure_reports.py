#!/usr/bin/env python3
"""
Import Allure Reports from Jenkins to Database

This script fetches Allure report data from Jenkins for existing
ReleaseCandidateTest records and stores them in the allure_report_summaries
and allure_test_cases tables.

Usage:
    # Import all
    python scripts/import_allure_reports.py

    # Import for specific platform
    python scripts/import_allure_reports.py --platform android

    # Import for specific version
    python scripts/import_allure_reports.py --version 6.4.0

    # Re-import existing data
    python scripts/import_allure_reports.py --reimport
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.services.allure_import_service import AllureImportService
from app.services.logger import get_logger

logger = get_logger()


def main():
    parser = argparse.ArgumentParser(
        description='Import Allure reports from Jenkins to database'
    )
    parser.add_argument(
        '--platform', '-p',
        help='Filter by platform (e.g., android, ios)'
    )
    parser.add_argument(
        '--version', '-v',
        help='Filter by version (e.g., 6.4.0)'
    )
    parser.add_argument(
        '--project', '-j',
        help='Filter by project (e.g., ftm)'
    )
    parser.add_argument(
        '--reimport', '-r',
        action='store_true',
        help='Re-import existing data'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be imported without actually importing'
    )

    args = parser.parse_args()

    # Create database session
    db = SessionLocal()

    try:
        # Get count of existing release tests
        from app.models.release_test import ReleaseCandidateTest
        from app.models.allure_report import AllureReportSummary

        query = db.query(ReleaseCandidateTest)

        if args.platform:
            query = query.filter(ReleaseCandidateTest.platform.like(f'{args.platform}%'))
            platform_info = f"platform={args.platform}"
        else:
            platform_info = None

        if args.version:
            query = query.filter(ReleaseCandidateTest.version == args.version)
            version_info = f"version={args.version}"
        else:
            version_info = None

        if args.project:
            query = query.filter(ReleaseCandidateTest.project == args.project)
            project_info = f"project={args.project}"
        else:
            project_info = None

        release_tests = query.all()
        total_count = len(release_tests)

        # Check how many already have summaries
        test_ids = [t.id for t in release_tests]
        existing_count = 0
        if test_ids:
            existing_count = db.query(AllureReportSummary).filter(
                AllureReportSummary.release_test_id.in_(test_ids)
            ).count()

        print("\n" + "=" * 60)
        print("Allure Report Import Summary")
        print("=" * 60)
        print(f"Filters: {', '.join(filter(None, [platform_info, version_info, project_info])) or 'None'}")
        print(f"Total release tests found: {total_count}")
        print(f"Already imported: {existing_count}")
        print(f"To import: {total_count - existing_count}")
        print("=" * 60)

        if args.dry_run:
            print("\n[DRY RUN] No data was imported")
            return

        # Perform import
        print("\nStarting import...")
        service = AllureImportService(db)
        stats = service.import_from_existing_release_tests(
            platform_filter=args.platform,
            version_filter=args.version,
            project_filter=args.project,
            reimport_existing=args.reimport,
        )

        print("\n" + "=" * 60)
        print("Import Results")
        print("=" * 60)
        print(f"  Total processed: {stats.get('total', 0)}")
        print(f"  Imported:        {stats.get('imported', 0)}")
        print(f"  Skipped:         {stats.get('skipped', 0)}")
        print(f"  Failed:          {stats.get('failed', 0)}")
        print(f"  Test cases:      {stats.get('test_cases_imported', 0)}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
