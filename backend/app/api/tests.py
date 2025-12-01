"""
Test Execution API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Dict, Any, List
from uuid import UUID
import logging

from app.core.database import get_db
from app.services.test_executor import test_executor
from app.models.vm import TestRecord
from app.schemas.test import (
    TestExecutionRequest,
    TestExecutionResponse,
    TestStatusResponse,
    TestConfigResponse,
    TestRerunRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute", response_model=TestExecutionResponse)
async def execute_test(
    request: TestExecutionRequest,
    db: Session = Depends(get_db)
):
    """
    Execute a test on a VM with the new flow:
    1. Select app version (APK/IPA)
    2. Select test scope (smoke, regression, integration, critical, release)
    3. Select test environment (qa, release, production)
    4. Start test execution

    Args:
        request: Test execution request with all parameters
        db: Database session

    Returns:
        Test execution response with task ID
    """
    try:
        logger.info(f"Executing test: {request.name} on VM {request.vm_id}")
        result = test_executor.execute_test(request, db)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error executing test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute test: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=TestStatusResponse)
async def get_test_status(task_id: str):
    """
    Get status of a test execution

    Args:
        task_id: Test execution task ID

    Returns:
        Current test status with progress information
    """
    try:
        logger.info(f"Getting status for task: {task_id}")
        status_response = test_executor.get_test_status(task_id)
        return status_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting test status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test status: {str(e)}"
        )


@router.get("/previous/{vm_id}", response_model=TestConfigResponse)
async def get_previous_test_config(
    vm_id: int,
    db: Session = Depends(get_db)
):
    """
    Get previous test configuration for a VM

    Args:
        vm_id: VM ID
        db: Database session

    Returns:
        Previous test configuration and history
    """
    try:
        logger.info(f"Getting previous test config for VM: {vm_id}")
        config = test_executor.get_previous_test_config(vm_id, db)
        return config
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting previous test config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get previous test config: {str(e)}"
        )


@router.post("/rerun/{task_id}", response_model=TestExecutionResponse)
async def rerun_test(
    task_id: str,
    rerun_request: TestRerunRequest,
    db: Session = Depends(get_db)
):
    """
    Re-run a previous test with optional parameter overrides

    Args:
        task_id: Original task ID to rerun
        rerun_request: Optional overrides (docker_tag, timeout)
        db: Database session

    Returns:
        New test execution response
    """
    try:
        logger.info(f"Re-running test: {task_id}")
        result = test_executor.rerun_test(
            task_id,
            docker_tag=rerun_request.docker_tag,
            timeout=rerun_request.timeout,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error re-running test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run test: {str(e)}"
        )


@router.get("/history/vm/{vm_id}")
async def get_vm_test_history(
    vm_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get test history for a specific VM

    Args:
        vm_id: VM UUID
        limit: Maximum number of records to return (default: 50, max: 500)
        offset: Number of records to skip (default: 0)
        db: Database session

    Returns:
        Test history records with pagination info
    """
    try:
        logger.info(f"Getting test history for VM: {vm_id}")

        # Convert string to UUID
        vm_uuid = UUID(vm_id)

        # Query test records
        query = db.query(TestRecord).filter(TestRecord.vm_id == vm_uuid)

        # Get total count
        total = query.count()

        # Get paginated results
        records = query.order_by(desc(TestRecord.executed_at)).offset(offset).limit(limit).all()

        return {
            "vm_id": vm_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": [record.to_dict() for record in records]
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid VM ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting VM test history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test history: {str(e)}"
        )


@router.get("/history/apk/{apk_file_id}")
async def get_apk_test_history(
    apk_file_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get test history for a specific APK/IPA file

    Args:
        apk_file_id: APK/IPA file UUID
        limit: Maximum number of records to return (default: 50, max: 500)
        offset: Number of records to skip (default: 0)
        db: Database session

    Returns:
        Test history records with pagination info
    """
    try:
        logger.info(f"Getting test history for APK/IPA: {apk_file_id}")

        # Convert string to UUID
        apk_uuid = UUID(apk_file_id)

        # Query test records
        query = db.query(TestRecord).filter(TestRecord.apk_file_id == apk_uuid)

        # Get total count
        total = query.count()

        # Get paginated results
        records = query.order_by(desc(TestRecord.executed_at)).offset(offset).limit(limit).all()

        return {
            "apk_file_id": apk_file_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": [record.to_dict() for record in records]
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid APK file ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting APK test history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test history: {str(e)}"
        )


@router.get("/analytics/vm/{vm_id}")
async def get_vm_test_analytics(
    vm_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get test analytics and summary for a specific VM

    Args:
        vm_id: VM UUID
        db: Database session

    Returns:
        Test analytics including pass rates, trends, and statistics
    """
    try:
        logger.info(f"Getting test analytics for VM: {vm_id}")

        # Convert string to UUID
        vm_uuid = UUID(vm_id)

        # Get all test records for this VM
        records = db.query(TestRecord).filter(TestRecord.vm_id == vm_uuid).all()

        if not records:
            return {
                "vm_id": vm_id,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "pass_rate": 0.0,
                "average_duration": 0.0,
                "last_test_date": None,
                "test_suites": [],
                "recent_failures": []
            }

        # Calculate statistics
        total_tests = len(records)
        passed_tests = sum(1 for r in records if r.status.lower() in ['passed', 'success'])
        failed_tests = sum(1 for r in records if r.status.lower() in ['failed', 'error'])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        average_duration = sum(r.duration for r in records) / total_tests if total_tests > 0 else 0.0

        # Get test suites statistics
        suite_stats = {}
        for record in records:
            suite = record.test_suite
            if suite not in suite_stats:
                suite_stats[suite] = {"total": 0, "passed": 0, "failed": 0}
            suite_stats[suite]["total"] += 1
            if record.status.lower() in ['passed', 'success']:
                suite_stats[suite]["passed"] += 1
            elif record.status.lower() in ['failed', 'error']:
                suite_stats[suite]["failed"] += 1

        test_suites = [
            {
                "name": suite,
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            }
            for suite, stats in suite_stats.items()
        ]

        # Get recent failures (last 10)
        recent_failures = [
            record.to_dict()
            for record in sorted(records, key=lambda r: r.executed_at, reverse=True)
            if record.status.lower() in ['failed', 'error']
        ][:10]

        # Get last test date
        last_test = max(records, key=lambda r: r.executed_at)

        return {
            "vm_id": vm_id,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": round(pass_rate, 2),
            "average_duration": round(average_duration, 2),
            "last_test_date": last_test.executed_at.isoformat() if last_test.executed_at else None,
            "test_suites": test_suites,
            "recent_failures": recent_failures
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid VM ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting VM test analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test analytics: {str(e)}"
        )


@router.get("/analytics/apk/{apk_file_id}")
async def get_apk_test_analytics(
    apk_file_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get test analytics and summary for a specific APK/IPA file

    Args:
        apk_file_id: APK/IPA file UUID
        db: Database session

    Returns:
        Test analytics including pass rates, trends, and statistics
    """
    try:
        logger.info(f"Getting test analytics for APK/IPA: {apk_file_id}")

        # Convert string to UUID
        apk_uuid = UUID(apk_file_id)

        # Get all test records for this APK
        records = db.query(TestRecord).filter(TestRecord.apk_file_id == apk_uuid).all()

        if not records:
            return {
                "apk_file_id": apk_file_id,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "pass_rate": 0.0,
                "average_duration": 0.0,
                "last_test_date": None,
                "vms_tested": [],
                "test_suites": [],
                "recent_failures": []
            }

        # Calculate statistics
        total_tests = len(records)
        passed_tests = sum(1 for r in records if r.status.lower() in ['passed', 'success'])
        failed_tests = sum(1 for r in records if r.status.lower() in ['failed', 'error'])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        average_duration = sum(r.duration for r in records) / total_tests if total_tests > 0 else 0.0

        # Get VMs tested
        vm_ids = list(set(str(r.vm_id) for r in records))

        # Get test suites statistics
        suite_stats = {}
        for record in records:
            suite = record.test_suite
            if suite not in suite_stats:
                suite_stats[suite] = {"total": 0, "passed": 0, "failed": 0}
            suite_stats[suite]["total"] += 1
            if record.status.lower() in ['passed', 'success']:
                suite_stats[suite]["passed"] += 1
            elif record.status.lower() in ['failed', 'error']:
                suite_stats[suite]["failed"] += 1

        test_suites = [
            {
                "name": suite,
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            }
            for suite, stats in suite_stats.items()
        ]

        # Get recent failures (last 10)
        recent_failures = [
            record.to_dict()
            for record in sorted(records, key=lambda r: r.executed_at, reverse=True)
            if record.status.lower() in ['failed', 'error']
        ][:10]

        # Get last test date
        last_test = max(records, key=lambda r: r.executed_at)

        return {
            "apk_file_id": apk_file_id,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": round(pass_rate, 2),
            "average_duration": round(average_duration, 2),
            "last_test_date": last_test.executed_at.isoformat() if last_test.executed_at else None,
            "vms_tested": vm_ids,
            "test_suites": test_suites,
            "recent_failures": recent_failures
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid APK file ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting APK test analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test analytics: {str(e)}"
        )
