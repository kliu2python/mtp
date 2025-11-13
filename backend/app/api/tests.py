"""
Test Execution API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.services.test_executor import test_executor

router = APIRouter()


class TestJobConfig(BaseModel):
    name: str
    vm_id: str
    device_ids: List[str]
    test_scripts: List[str]
    test_files: dict = {}
    environment: dict = {}
    timeout: int = 3600


@router.post("/execute")
async def execute_test(
    config: TestJobConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute a test job"""
    try:
        # Validate VM and devices exist
        # Queue test execution
        task_id = await test_executor.queue_test(config, db)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Test job queued successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_test_status(task_id: str):
    """Get test execution status"""
    status = await test_executor.get_status(task_id)
    return status


@router.get("/coverage")
async def get_coverage_report(db: Session = Depends(get_db)):
    """Get test coverage report"""
    # Return mock data for now
    return {
        "total_manual_cases": 2100,
        "total_auto_cases": 1234,
        "coverage_percentage": 78.5,
        "by_platform": {
            "FortiGate 7.4.x": 92,
            "FortiGate 7.2.x": 65,
            "FortiAuthenticator": 54
        }
    }
