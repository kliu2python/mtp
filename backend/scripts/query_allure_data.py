#!/usr/bin/env python3
"""
Query Allure Report Data from Database

Usage:
    python scripts/query_allure_data.py [--platform android] [--version 6.4.0]
    python scripts/query_allure_data.py --stats
    python scripts/query_allure_data.py --test-cases --limit 20
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from prettytable import PrettyTable
from app.core.database import SessionLocal
from app.models.allure_report import AllureReportSummary, AllureTestCase
from app.models.release_test import ReleaseCandidateTest
from sqlalchemy import func, desc


def print_table(headers, rows):
    """Print data as a formatted table"""
    table = PrettyTable(headers)
    table.align = "l"
    for row in rows:
        table.add_row(row)
    print(table)


def query_summaries(platform=None, version=None, limit=20):
    """Query allure report summaries"""
    db = SessionLocal()
    try:
        query = db.query(
            AllureReportSummary.build_number,
            AllureReportSummary.version,
            AllureReportSummary.project,
            AllureReportSummary.platform,
            AllureReportSummary.total,
            AllureReportSummary.passed_count,
            AllureReportSummary.failed_count,
            AllureReportSummary.pass_rate,
            AllureReportSummary.report_timestamp,
        )

        if platform:
            query = query.filter(AllureReportSummary.platform.like(f'{platform}%'))
        if version:
            query = query.filter(AllureReportSummary.version == version)

        results = query.order_by(
            desc(AllureReportSummary.created_at)
        ).limit(limit).all()

        if not results:
            print("No data found")
            return

        headers = ['Build', 'Version', 'Project', 'Platform', 'Total', 'Passed', 'Failed', 'Pass Rate%', 'Time']
        rows = []
        for r in results:
            rows.append([
                r.build_number,
                r.version,
                r.project,
                r.platform,
                r.total,
                r.passed_count,
                r.failed_count,
                f"{r.pass_rate:.1f}" if r.pass_rate else "N/A",
                r.report_timestamp.strftime('%Y-%m-%d %H:%M') if r.report_timestamp else 'N/A'
            ])

        print(f"\n=== Allure Report Summaries ({len(results)} records) ===\n")
        print_table(headers, rows)

    finally:
        db.close()


def query_stats():
    """Query import statistics"""
    db = SessionLocal()
    try:
        # Overall stats
        total_tests = db.query(func.count(ReleaseCandidateTest.id)).scalar()
        imported_tests = db.query(func.count(func.distinct(AllureReportSummary.release_test_id))).scalar()
        total_summaries = db.query(func.count(AllureReportSummary.id)).scalar()
        total_test_cases = db.query(func.count(AllureTestCase.id)).scalar()

        print("\n=== Allure Import Statistics ===\n")
        print(f"Total Release Tests:     {total_tests}")
        print(f"Imported Tests:          {imported_tests}")
        print(f"Total Summaries:         {total_summaries}")
        print(f"Total Test Cases:        {total_test_cases}")

        if total_tests > 0:
            percentage = (imported_tests / total_tests) * 100
            print(f"Import Percentage:       {percentage:.1f}%")

        # Stats by platform
        print("\n=== Stats by Platform ===\n")
        platform_stats = db.query(
            AllureReportSummary.platform,
            func.count(AllureReportSummary.id),
            func.sum(AllureReportSummary.total),
            func.avg(AllureReportSummary.pass_rate)
        ).group_by(AllureReportSummary.platform).all()

        headers = ['Platform', 'Reports', 'Total Tests', 'Avg Pass Rate%']
        rows = []
        for ps in platform_stats:
            rows.append([
                ps[0],
                ps[1],
                ps[2] or 0,
                f"{ps[3]:.1f}" if ps[3] else "N/A"
            ])

        print_table(headers, rows)

    finally:
        db.close()


def query_test_cases(limit=20):
    """Query recent test cases"""
    db = SessionLocal()
    try:
        results = db.query(
            AllureTestCase.name,
            AllureTestCase.status,
            AllureTestCase.duration_ms,
            AllureTestCase.suite,
            AllureReportSummary.build_number,
            AllureReportSummary.platform,
        ).join(
            AllureReportSummary,
            AllureTestCase.summary_id == AllureReportSummary.id
        ).order_by(
            desc(AllureReportSummary.created_at)
        ).limit(limit).all()

        if not results:
            print("No test cases found")
            return

        headers = ['Test Name', 'Status', 'Duration(ms)', 'Suite', 'Build', 'Platform']
        rows = [[r.name, r.status, r.duration_ms, r.suite, r.build_number, r.platform] for r in results]

        print(f"\n=== Recent Test Cases ({len(results)} records) ===\n")
        print_table(headers, rows)

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Query Allure report data')
    parser.add_argument('--platform', '-p', help='Filter by platform')
    parser.add_argument('--version', '-v', help='Filter by version')
    parser.add_argument('--limit', '-l', type=int, default=20, help='Limit results')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics')
    parser.add_argument('--test-cases', '-t', action='store_true', help='Show test cases')

    args = parser.parse_args()

    if args.stats:
        query_stats()
    elif args.test_cases:
        query_test_cases(limit=args.limit)
    else:
        query_summaries(platform=args.platform, version=args.version, limit=args.limit)


if __name__ == '__main__':
    main()
