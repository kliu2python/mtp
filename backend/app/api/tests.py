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
    device_ids: List[str] = []
    test_scripts: List[str] = []
    test_files: dict = {}
    environment: dict = {}
    timeout: int = 3600
    execution_method: Optional[str] = "docker"
    platform: Optional[str] = "ios"
    test_suite: Optional[str] = None
    test_markers: Optional[str] = None
    lab_config: Optional[str] = None
    docker_registry: Optional[str] = None
    docker_image: Optional[str] = None
    docker_tag: Optional[str] = None


@router.post("/execute")
async def execute_test(
    config: TestJobConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Execute a test job"""
    try:
        # Validate VM and devices exist
        # Convert Pydantic model to dict and merge with environment
        config_dict = config.model_dump()

        # Merge top-level test parameters into environment for test executor
        config_dict['environment'].update({
            'execution_method': config.execution_method,
            'platform': config.platform,
            'test_suite': config.test_suite,
            'test_markers': config.test_markers,
            'lab_config': config.lab_config,
            'docker_registry': config.docker_registry,
            'docker_image': config.docker_image,
            'docker_tag': config.docker_tag,
        })

        # Queue test execution
        task_id = await test_executor.queue_test(config_dict, db)

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


@router.get("/previous/{vm_id}")
async def get_previous_test_config(vm_id: str):
    """Get the last test configuration for a VM"""
    # Find the most recent completed or failed test for this VM
    all_tasks = test_executor.get_all_tasks()
    vm_tests = [
        t for t in all_tasks
        if t.get('config', {}).get('vm_id') == vm_id
    ]

    if not vm_tests:
        raise HTTPException(status_code=404, detail="No previous tests found for this VM")

    # Sort by start_time, most recent first
    vm_tests.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    latest_test = vm_tests[0]

    return {
        "task_id": latest_test.get('task_id'),
        "config": latest_test.get('config', {}),
        "status": latest_test.get('status'),
        "start_time": latest_test.get('start_time')
    }


class RerunTestConfig(BaseModel):
    docker_tag: str


@router.post("/rerun/{task_id}")
async def rerun_test_with_tag(
    task_id: str,
    rerun_config: RerunTestConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Re-run a previous test with modified docker tag"""
    # Get the original test configuration
    status = await test_executor.get_status(task_id)

    if not status or 'config' not in status:
        raise HTTPException(status_code=404, detail="Test not found")

    # Clone the config and update docker tag
    config_dict = status['config'].copy()
    config_dict['environment']['docker_tag'] = rerun_config.docker_tag

    # Queue new test execution
    new_task_id = await test_executor.queue_test(config_dict, db)

    return {
        "task_id": new_task_id,
        "status": "queued",
        "message": f"Test re-queued with docker tag: {rerun_config.docker_tag}",
        "original_task_id": task_id
    }


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
