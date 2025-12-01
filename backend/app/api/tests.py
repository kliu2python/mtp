"""
Test Execution API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.services.test_executor import test_executor
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
