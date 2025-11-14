"""
Test Schedule Management API
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid as uuid_lib

from app.core.database import get_db
from app.models.test_schedule import TestSchedule, ScheduleStatus
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ScheduleCreate(BaseModel):
    """Schema for creating a test schedule"""
    name: str
    description: Optional[str] = None
    cron_expression: str
    timezone: str = "UTC"
    test_config: dict
    vm_ids: Optional[List[str]] = []
    device_ids: Optional[List[str]] = []
    apk_id: Optional[str] = None
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_emails: Optional[List[str]] = []
    notification_teams_webhook: Optional[str] = None
    enabled: bool = True
    tags: Optional[List[str]] = []


class ScheduleUpdate(BaseModel):
    """Schema for updating a test schedule"""
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    test_config: Optional[dict] = None
    vm_ids: Optional[List[str]] = None
    device_ids: Optional[List[str]] = None
    apk_id: Optional[str] = None
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_emails: Optional[List[str]] = None
    notification_teams_webhook: Optional[str] = None
    enabled: Optional[bool] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("/")
async def list_schedules(
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    List all test schedules

    Args:
        enabled_only: Only return enabled schedules
        db: Database session

    Returns:
        List of schedules
    """
    query = db.query(TestSchedule)

    if enabled_only:
        query = query.filter(TestSchedule.enabled == True)

    schedules = query.order_by(TestSchedule.created_at.desc()).all()

    return {
        "total": len(schedules),
        "schedules": [schedule.to_dict() for schedule in schedules]
    }


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """
    Get a specific schedule by ID

    Args:
        schedule_id: Schedule UUID
        db: Database session

    Returns:
        Schedule details
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule_dict = schedule.to_dict()

    # Add job info if available
    job_info = scheduler_service.get_job_info(schedule_id)
    if job_info:
        schedule_dict['job_info'] = job_info

    return schedule_dict


@router.post("/")
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new test schedule

    Args:
        schedule_data: Schedule creation data
        db: Database session

    Returns:
        Created schedule
    """
    try:
        # Validate cron expression
        cron_parts = schedule_data.cron_expression.split()
        if len(cron_parts) != 5:
            raise HTTPException(
                status_code=400,
                detail="Invalid cron expression. Format: 'minute hour day month day_of_week'"
            )

        # Create schedule
        schedule = TestSchedule(
            name=schedule_data.name,
            description=schedule_data.description,
            cron_expression=schedule_data.cron_expression,
            timezone=schedule_data.timezone,
            test_config=schedule_data.test_config,
            vm_ids=schedule_data.vm_ids or [],
            device_ids=schedule_data.device_ids or [],
            apk_id=uuid_lib.UUID(schedule_data.apk_id) if schedule_data.apk_id else None,
            notify_on_success=schedule_data.notify_on_success,
            notify_on_failure=schedule_data.notify_on_failure,
            notification_emails=schedule_data.notification_emails or [],
            notification_teams_webhook=schedule_data.notification_teams_webhook,
            enabled=schedule_data.enabled,
            status=ScheduleStatus.ACTIVE if schedule_data.enabled else ScheduleStatus.PAUSED,
            tags=schedule_data.tags or []
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        # Add to scheduler if enabled
        if schedule.enabled and schedule.status == ScheduleStatus.ACTIVE:
            try:
                await scheduler_service.add_job(schedule)
            except Exception as e:
                logger.error(f"Failed to add schedule to scheduler: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to schedule job: {str(e)}")

        logger.info(f"Created schedule: {schedule.name} (ID: {schedule.id})")

        return {
            "message": "Schedule created successfully",
            "schedule": schedule.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    update_data: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a test schedule

    Args:
        schedule_id: Schedule UUID
        update_data: Update data
        db: Database session

    Returns:
        Updated schedule
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    try:
        # Update fields
        if update_data.name is not None:
            schedule.name = update_data.name
        if update_data.description is not None:
            schedule.description = update_data.description
        if update_data.cron_expression is not None:
            # Validate cron expression
            cron_parts = update_data.cron_expression.split()
            if len(cron_parts) != 5:
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            schedule.cron_expression = update_data.cron_expression
        if update_data.timezone is not None:
            schedule.timezone = update_data.timezone
        if update_data.test_config is not None:
            schedule.test_config = update_data.test_config
        if update_data.vm_ids is not None:
            schedule.vm_ids = update_data.vm_ids
        if update_data.device_ids is not None:
            schedule.device_ids = update_data.device_ids
        if update_data.apk_id is not None:
            schedule.apk_id = uuid_lib.UUID(update_data.apk_id) if update_data.apk_id else None
        if update_data.notify_on_success is not None:
            schedule.notify_on_success = update_data.notify_on_success
        if update_data.notify_on_failure is not None:
            schedule.notify_on_failure = update_data.notify_on_failure
        if update_data.notification_emails is not None:
            schedule.notification_emails = update_data.notification_emails
        if update_data.notification_teams_webhook is not None:
            schedule.notification_teams_webhook = update_data.notification_teams_webhook
        if update_data.enabled is not None:
            schedule.enabled = update_data.enabled
        if update_data.status is not None:
            schedule.status = ScheduleStatus(update_data.status)
        if update_data.tags is not None:
            schedule.tags = update_data.tags

        schedule.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(schedule)

        # Update scheduler
        await scheduler_service.remove_job(schedule_id)
        if schedule.enabled and schedule.status == ScheduleStatus.ACTIVE:
            await scheduler_service.add_job(schedule)

        logger.info(f"Updated schedule: {schedule.name}")

        return {
            "message": "Schedule updated successfully",
            "schedule": schedule.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """
    Delete a test schedule

    Args:
        schedule_id: Schedule UUID
        db: Database session

    Returns:
        Success message
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    try:
        # Remove from scheduler
        await scheduler_service.remove_job(schedule_id)

        # Delete from database
        db.delete(schedule)
        db.commit()

        logger.info(f"Deleted schedule: {schedule.name}")

        return {"message": "Schedule deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


@router.post("/{schedule_id}/pause")
async def pause_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """
    Pause a schedule (disable temporarily)

    Args:
        schedule_id: Schedule UUID
        db: Database session

    Returns:
        Updated schedule
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.status = ScheduleStatus.PAUSED
    schedule.updated_at = datetime.utcnow()
    db.commit()

    # Remove from scheduler
    await scheduler_service.remove_job(schedule_id)

    return {
        "message": "Schedule paused",
        "schedule": schedule.to_dict()
    }


@router.post("/{schedule_id}/resume")
async def resume_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """
    Resume a paused schedule

    Args:
        schedule_id: Schedule UUID
        db: Database session

    Returns:
        Updated schedule
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if not schedule.enabled:
        raise HTTPException(status_code=400, detail="Cannot resume a disabled schedule")

    schedule.status = ScheduleStatus.ACTIVE
    schedule.updated_at = datetime.utcnow()
    db.commit()

    # Add back to scheduler
    await scheduler_service.add_job(schedule)

    return {
        "message": "Schedule resumed",
        "schedule": schedule.to_dict()
    }


@router.post("/{schedule_id}/trigger")
async def trigger_schedule_now(schedule_id: str, db: Session = Depends(get_db)):
    """
    Manually trigger a schedule to run immediately

    Args:
        schedule_id: Schedule UUID
        db: Database session

    Returns:
        Trigger result
    """
    schedule = db.query(TestSchedule).filter(TestSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    try:
        # Execute the scheduled test immediately
        await scheduler_service._execute_scheduled_test(schedule_id)

        return {
            "message": "Schedule triggered successfully",
            "schedule_id": schedule_id
        }
    except Exception as e:
        logger.error(f"Failed to trigger schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger schedule: {str(e)}")


@router.get("/stats/summary")
async def get_schedule_stats(db: Session = Depends(get_db)):
    """
    Get statistics about test schedules

    Returns:
        Schedule statistics
    """
    total = db.query(TestSchedule).count()
    active = db.query(TestSchedule).filter(
        TestSchedule.status == ScheduleStatus.ACTIVE,
        TestSchedule.enabled == True
    ).count()
    paused = db.query(TestSchedule).filter(
        TestSchedule.status == ScheduleStatus.PAUSED
    ).count()
    disabled = db.query(TestSchedule).filter(
        TestSchedule.enabled == False
    ).count()

    # Get total runs
    all_schedules = db.query(TestSchedule).all()
    total_runs = sum(s.total_runs for s in all_schedules)
    successful_runs = sum(s.successful_runs for s in all_schedules)
    failed_runs = sum(s.failed_runs for s in all_schedules)

    return {
        "total_schedules": total,
        "active_schedules": active,
        "paused_schedules": paused,
        "disabled_schedules": disabled,
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate": round((successful_runs / total_runs * 100) if total_runs > 0 else 0, 2)
    }
